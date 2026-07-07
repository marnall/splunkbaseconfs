import common.log as log
import common.proxy as pro
import const
import os
import socket
import splunk.clilib.cli_common
import requests
import splunk.admin as admin
import splunklib.client as client

# from weakref import proxy
from solnlib.utils import is_true
from splunk.clilib import cli_common as cli
from splunktaucclib.rest_handler.endpoint.validator import Validator



logger = log.get_logger(__file__)

APP_NAME = __file__.split(os.sep)[-3]


class GetSessionKey(admin.MConfigHandler):
  """To get Splunk session key."""

  def __init__(self):
    """Initialize."""
    self.session_key = self.getSessionKey()

def resolve_host(hostname):
    """Resolve hostname to IPv4/IPv6 address."""
    try:
        # This returns a list of (family, type, proto, canonname, sockaddr) tuples
        infos = socket.getaddrinfo(hostname, None)

        # Filter for IPv4 and IPv6 addresses
        ipv4_addresses = [info for info in infos if info[0] == socket.AF_INET]
        ipv6_addresses = [info for info in infos if info[0] == socket.AF_INET6]

        # Prefer IPv4, but fallback to IPv6 if necessary
        if ipv4_addresses:
            address = ipv4_addresses[0][4][0]
        elif ipv6_addresses:
            address = ipv6_addresses[0][4][0]
        else:
            return None  # No suitable address found
        return address
    except socket.gaierror:
        return None


def create_service():
  """Create Service to communicate with splunk."""
  mgmt_uri = splunk.clilib.cli_common.getMgmtUri()
  hostname = mgmt_uri.split("//")[-1].split(":")[0]  # Extract hostname from URI
  mgmt_port = mgmt_uri.split(":")[-1]

  # Resolve hostname to IPv4 address
  ip_address = resolve_host(hostname)
  if not ip_address:
      raise Exception("Failed to resolve Splunk management URI to an IP address.")

  service = client.connect(host=ip_address, port=mgmt_port, token=GetSessionKey().session_key, app="TA-mandiant-advantage")
  return service


def is_splunk_cloud() -> bool:
  """Checks Splunk's `/services/server/info` endpoint to check if the app is 
  running in Splunk Cloud or on-premises
  
  Returns:
  --------
    bool: if cloud True else False
  """
  service = create_service()
  splunk_info = service.info
  if splunk_info.get('instance_type', "") == "cloud":
    return True
  else:
    return False


class ValidateDaysBack(Validator):
  """Validator class to validate values for Days Back field."""

  def validate(self, value, data):
    """Validate method to perform action."""
    days_back = data["days_back"]
    if days_back.startswith("_"):
      try:
        days_back = int(days_back[1:])
        if days_back >= 0:
          data["days_back"] = days_back
        else:
          raise ValueError()
      except ValueError:
        self.put_msg("Invalid Value for field Indicator Time Window. Enter valid integer.")
        return False
    else:
      try:
        days_back = int(days_back)
        if days_back not in range(0, 181):
          raise ValueError()
        data["days_back"] = days_back
      except ValueError:
        self.put_msg("Invalid value for field Indicator Time Window. Enter valid integer in the allowed range of [0 and 180].")    # noqa: E501
        return False
    return True


class ValidateAccountType(Validator):
  """Validator class to empty fields corresponding to dropdown value."""

  def validate_mandiant_advantage_creds(self, client_id, client_secret, endpoint_url, proxy_config):
    """Validation method to validate mandiant advantage creds."""
    try:
      host_url = "https://{}".format(endpoint_url)
      payload = 'grant_type=client_credentials&scope='
      headers = {
          'Content-Type': 'application/x-www-form-urlencoded'
      }
      proxy_settings = pro.transform_proxy_config(proxy_config=proxy_config)
      resp = requests.post(
          host_url + "/token",
          headers=headers,
          data=payload,
          auth=(client_id, client_secret),
          proxies=proxy_settings,
          verify=const.INTEL_VERIFY
      )
      resp.raise_for_status()
      if resp.status_code in (200, 201):
        try:
          resp.json()
          return True
        except Exception:
          msg = "Error occurred while converting response in json. "\
              "There seems to be issue with the API response. "\
              "Please contact Mandiant Advantage support. "
          self.put_msg(msg)
          return False
    except Exception as e:
      if "resp" in locals() and resp.status_code == 401:
        msg = "Invalid API Key Public or API Key Secret."\
            "Please enter the valid credentials."
      elif "resp" in locals() and resp.status_code == 404:
        msg = "Please validate the provided details."
      elif "resp" in locals() and resp.status_code == 429:
        msg = "API limit has exceeded. Please retry after some time."
      elif "resp" in locals() and resp.status_code == 500:
        msg = "Internal server error. Cannot verify Mandiant instance."
      else:
        msg = "Unable to request Mandiant instance. "\
            "Please validate the provided credentials and "\
            "Proxy configurations or check the network connectivity."
        msg = "{} {}".format(msg, e)
      self.put_msg(msg)
      return False

  def validate_mandiant_validation_creds(self, endpoint_url, api_token, validation_verify_ssl, proxy_config):
    """Validation method to validate mandiant validation creds."""
    try:
      headers = {
          'Accept': 'application/json',
          'Authorization': 'Bearer {}'.format(api_token)
      }
      payload = {}
      host_url = ("https://{}/jobs".format(endpoint_url))
      proxy_settings = pro.transform_proxy_config(proxy_config=proxy_config)
      if is_splunk_cloud():
        verify_ssl = True
      else:
        verify_ssl = is_true(validation_verify_ssl)
      resp = requests.get(
          host_url,
          headers=headers,
          data=payload,
          proxies=proxy_settings,
          verify=verify_ssl
      )
      resp.raise_for_status()
      if resp.status_code in (200, 201):
        try:
          resp.json()
          return True
        except Exception:
          msg = "Error occurred while converting response in json. "\
              "There seems to be issue with the API response. "\
              "Please contact Mandiant Advantage support. "
          self.put_msg(msg)
          return False
    except Exception as e:
      if "resp" in locals() and resp.status_code == 401:
        msg = "Invalid Endpoint URL or API Token. Please enter the valid credentials."
      elif "resp" in locals() and resp.status_code == 404:
        msg = "Please validate the provided details."
      elif "resp" in locals() and resp.status_code == 429:
        msg = "API limit has exceeded. Please retry after some time."
      elif "resp" in locals() and resp.status_code == 500:
        msg = "Internal server error. Cannot verify Mandiant instance."
      else:
        msg = "Unable to request Mandiant instance. "\
            "Please validate the provided credentials and "\
            "Proxy configurations or check the network connectivity."
        msg = "{} Error: {}".format(msg, e)
      self.put_msg(msg)
      return False

  def validate_mandiant_asm_creds(self, endpoint_url, access_key, secret_key, validation_verify_ssl, proxy_config):
    """Validation method to validate Mandiant Attack Surface management Credentials."""
    headers = {
        "INTRIGUE_ACCESS_KEY": access_key,
        "INTRIGUE_SECRET_KEY": secret_key
    }

    url = f"https://{endpoint_url}/api/v1/projects"

    proxy_settings = pro.transform_proxy_config(proxy_config=proxy_config)

    try:
      if is_splunk_cloud():
        verify_ssl = True
      else:
        verify_ssl = is_true(validation_verify_ssl)

      resp = requests.get(
          url=url,
          headers=headers,
          proxies=proxy_settings,
          verify=verify_ssl
      )

      resp.raise_for_status()

      try:
        resp_json = resp.json()
        return True
      except Exception as ex:
        msg = f"Unexpected error occurred while converting response in json. "\
                f"There seems to be issue with the API response. "\
                f"Please contact Mandiant Advantage support. Exception: {str(ex)}"
        self.put_msg(msg)
        return False
    except Exception as ex:
      if "resp" in locals() and resp.status_code == 401:
        msg = "Response Code 401: Unable to validate User auth token or api keys"
      elif "resp" in locals() and resp.status_code == 404:
        msg = f"response Code 404. Resource: {url} not found"
      elif "resp" in locals() and resp.status_code == 429:
        msg = "API limit has exceeded. Please retry after some time."
      elif "resp" in locals() and resp.status_code == 500:
        msg = "Internal server error. Cannot verify Mandiant instance."
      else:
        msg = "Unable to request Mandiant instance. "\
            "Please validate the provided credentials and "\
            "Proxy configurations or check tnetwork connectivity."
        msg = "{} Error: {}".format(msg, ex)
      self.put_msg(msg)
      return False

  def validate(self, value, data):
    """Validate method to perform action."""
    if data['account_type'] == "mandiant_advantage":
      client_id = data.get('client_id')
      client_secret = data.get('client_secret')
      endpoint_url = data.get('endpoint_url').strip('/')
      proxy_config = {
          'proxy_enabled': data.get("proxy_enabled"),
          'proxy_username': data.get("proxy_username"),
          'proxy_port': data.get("proxy_port"),
          'proxy_type': data.get("proxy_type"),
          'proxy_password': data.get("proxy_password"),
          'proxy_url': data.get("proxy_url")
      }
      if client_id and not (client_id == '' and client_secret == ''):
        data['api_token'] = ''
        data['validation_api_version'] = ''
        data['validation_verify_ssl'] = ''
      else:
        self.put_msg("API Key Public is required field.")
        return False
      if client_secret and not (client_id == '' and client_secret == ''):
        data['api_token'] = ''
        data['validation_api_version'] = ''
        data['validation_verify_ssl'] = ''
      else:
        self.put_msg("API Key Secret is required field.")
        return False
      return self.validate_mandiant_advantage_creds(client_id, client_secret, endpoint_url, proxy_config)
    elif data['account_type'] == "mandiant_validation":
      endpoint_url = data.get('endpoint_url').strip('/')
      api_token = data.get('api_token')
      validation_api_version = data.get('validation_api_version')
      validation_verify_ssl = data.get('validation_verify_ssl')
      proxy_config = {
          'proxy_enabled': data.get("proxy_enabled"),
          'proxy_username': data.get("proxy_username"),
          'proxy_port': data.get("proxy_port"),
          'proxy_type': data.get("proxy_type"),
          'proxy_password': data.get("proxy_password"),
          'proxy_url': data.get("proxy_url")
      }
      if api_token and not (api_token == '' and validation_api_version == ''):
        data['client_id'] = ''
        data['client_secret'] = ''
      else:
        self.put_msg("API Token is required field.")
        return False
      if validation_api_version and not (api_token == '' and validation_api_version == ''):
        data['client_id'] = ''
        data['client_secret'] = ''
      else:
        self.put_msg("API Version is required field.")
        return False
      return self.validate_mandiant_validation_creds(endpoint_url, api_token, validation_verify_ssl, proxy_config)
    elif data['account_type'] == "mandiant_attack_surface_management":
      endpoint_url = data.get('endpoint_url').strip('/')
      access_key = data.get('access_key')
      secret_key = data.get('secret_key')
      validation_verify_ssl = data.get('validation_verify_ssl')
      proxy_config = {
          'proxy_enabled': data.get("proxy_enabled"),
          'proxy_username': data.get("proxy_username"),
          'proxy_port': data.get("proxy_port"),
          'proxy_type': data.get("proxy_type"),
          'proxy_password': data.get("proxy_password"),
          'proxy_url': data.get("proxy_url")
      }
      return self.validate_mandiant_asm_creds(
          endpoint_url,
          access_key,
          secret_key,
          validation_verify_ssl,
          proxy_config
      )


def check_correct_account(input_type, selected_account):
  """Method to check the correct account is selected for correct input."""
  account_stanza = cli.getConfStanza("ta_mandiant_advantage_account", selected_account)
  account_type = account_stanza.get("account_type")
  return input_type == account_type


class ValidateCorrectAccountIndicator(Validator):
  """Validator class to check the correct account is selected for correct input."""

  def validate(self, value, data):
    """Validate method to perform action."""
    selected_account = data.get('mandiant_advantage_account')
    is_valid = check_correct_account("mandiant_advantage", selected_account)
    if not is_valid:
      self.put_msg(
          '"Mandiant Validation" account is selected for "Mandiant Threat Intelligence" input. \
                    Select the valid "Mandiant Advantage" account.'
      )
      return False
    return True


class ValidateCorrectAccountValidator(Validator):
  """Validator class to check the correct account is selected for correct input."""

  def validate(self, value, data):
    """Validate method to perform action."""
    selected_account = data.get('mandiant_advantage_account')
    is_valid = check_correct_account("mandiant_validation", selected_account)
    if not is_valid:
      self.put_msg(
          '"Mandiant Advantage" account is selected for "Mandiant Security Validation" input. \
                    Select the valid "Mandiant Validation" account.'
      )
      return False
    return True

class ValidateCorrectAccountASM(Validator):
  """Validator class to check the correct account is selected for correct input."""

  def validate(self, value, data):
    """Validate method to perform action."""
    selected_account = data.get('mandiant_advantage_account')
    is_valid = check_correct_account("mandiant_attack_surface_management", selected_account)
    if not is_valid:
      self.put_msg(
          '"Mandiant Advantage" account selected is not for "Mandiant Attack Surface Management". \
                    Select a valid "Mandiant Attack Surface Management" account.'
      )
      return False
    return True
