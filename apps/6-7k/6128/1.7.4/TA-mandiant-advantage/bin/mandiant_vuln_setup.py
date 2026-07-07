import import_declare_test  # noqa F401
import os
import traceback
import re

from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunktaucclib.rest_handler.endpoint import (
    validator
)
import splunk.admin as admin
import splunk.clilib.cli_common
import socket
import splunklib.client as client
from splunklib.binding import HTTPError
from solnlib.utils import is_true

import common.log as log

logger = log.get_logger(__file__)


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


def update_macros(service, macro_name, macro_string):
  """Update macro with the string provided."""
  service.post("properties/macros/{}".format(macro_name), definition=macro_string)
  logger.debug("Macro: {} is updated Successfully.".format(macro_name))


class GenericVulnValidator(Validator):
  """Generic validator for vulnerability."""

  def __init__(self, *args, **kwargs):
    """Initialize the parameters."""
    super(GenericVulnValidator, self).__init__(*args, **kwargs)
    self.validators = {
        'enable_vuln_correlation': VulnSavedSearchManager(),
        'vuln_indices': VulnIndicesManager(),
        'vuln_src_type': VulnSrcTypeManager(),
        'vuln_fields': VulnFieldsManager(),
        'vuln_host_field': VulnHostFieldManager(),
        'vuln_ttl': ValidateVulnTTL()
    }

  def validate(self, value, data):
    """Validate the data."""
    res = True
    for key, vldr in self.validators.items():
      if not callable(getattr(vldr, 'validate', None)):
        continue

      value = data.get(key)
      vldr.put_msg = self.put_msg
      try:
        if value is None or value == "":
          continue
        if vldr.validate(value, data) is False:
          return False
      except Exception as ex:
        self.put_msg(str(ex))
        return False

    for key, vldr in self.validators.items():
      if not callable(getattr(vldr, 'save', None)):
        continue

      value = data.get(key)
      vldr.put_msg = self.put_msg
      try:
        if vldr.save(value, data) is False:
          res = False
      except Exception:
        # Error in one validator shouldn't stop the saving process of others
        pass

    return res


class VulnSavedSearchManager(Validator):
  """Class provides method to enable/disable saved search for correlation."""

  def __init__(self, *args, **kwargs):
    """Initialize the parameters."""
    super(VulnSavedSearchManager, self).__init__(*args, **kwargs)
    self._validator = validator
    self._args = args
    self._kwargs = kwargs
    self.path = os.path.abspath(__file__)

  def validate(self, value, data):
    """Validate the data."""
    enable_vuln_correlation = data.get('enable_vuln_correlation')
    if is_true(enable_vuln_correlation):
      if not data.get('mandiant_vuln_advantage_account'):
        self.put_msg("Mandiant Advantage Account is required to perform vulnerabilities correlation. \
                    Please select the account in Mandiant Advantage Account field"                                                                                                                                                                                                                                              )
        return False
      if not data.get('vuln_indices'):
        self.put_msg("Vuln fields indices are required to perform vulnerabilities correlation. \
                    Please enter single index or comma separated indices in Vuln Indices field."                                                                                                                                                                                                                                                                                        )
        return False
      if not data.get('vuln_src_type'):
        self.put_msg("Vuln src type is required to perform vulnerabilities correlation. \
                    Please enter single sourcetype or comma separated sourcetypes in Vuln Sourcetypes field."                                                                                                                                                                                                                                                                                                                               )
        return False
      if not data.get('vuln_fields'):
        self.put_msg("Vuln fields is required to perform vulnerabilities correlation. \
                    Please enter single field name or comma separated field name in Vuln Fields."                                                                                                                                                                                                                                                                                           )
        return False
    return True

  def save(self, value, data):
    """Enable and disable savedsearch based on the input given."""
    try:
      enable_ss = data.get('enable_vuln_correlation', 0)
      service = create_service()
      saved_search = service.saved_searches['mandiant_match_vulnerabilities']
      if bool(int(enable_ss)):
        saved_search.enable()
      else:
        saved_search.disable()
    except HTTPError:
      logger.error("Error while retrieving SavedSearch: {}".format(traceback.format_exc()))
      self.put_msg("Error while retrieving SavedSearch. Kindly check log file for more details.")
      return False
    except Exception as e:
      self.put_msg("Unexpected error occurred while updating Savedsearch.")
      logger.error(
          "The following error occurred while updating {} macro. Error: {}".format(
              "mandiant_vuln_indices", e
          )
      )
      return False
    return True


class VulnIndicesManager(Validator):
  """Class provides methods for validating and updating vuln index macro."""

  def __init__(self, *args, **kwargs):
    """Initialize the parameters."""
    super(VulnIndicesManager, self).__init__(*args, **kwargs)
    self._validator = validator
    self._args = args
    self._kwargs = kwargs
    self.path = os.path.abspath(__file__)

  def validate(self, value, data):
    """Validate the data."""
    _iscommaseparated = re.search("^((?:\\w+-*\\w*),)*(?:\\w+-*\\w*)$", value)
    if _iscommaseparated:
      return True
    else:
      self.put_msg(
          "Please enter single index or comma separated indices in Vuln Indices field. \
                Index must start with a letter and followed by alphabetic letters, digits or underscores."
      )
      return False

  def save(self, value, data):
    """Save the given indices and update indices macro."""
    try:
      service = create_service()
      vuln_indices = value
      macro_string = "index IN ({})".format(vuln_indices)
      try:
        update_macros(service, "mandiant_vuln_indices", macro_string)
      except Exception as e:
        self.put_msg("Unexpected error occurred while updating {} macro.".format("mandiant_vuln_indices"))
        logger.error(
            "The following error occurred while updating {} macro. Error: {}".format(
                "mandiant_vuln_indices", e
            )
        )
        return False
    except HTTPError:
      logger.error("Error while retrieving Macros: {}".format(traceback.format_exc()))
      self.put_msg("Error while retrieving Macros. Kindly check log file for more details.")
      return False
    except Exception as e:
      self.put_msg("Unexpected error occurred while updating macro.")
      logger.error(
          "The following error occurred while updating {} macro. Error: {}".format(
              "mandiant_vuln_indices", e
          )
      )
      return False
    return True


class VulnSrcTypeManager(Validator):
  """Class provides methods for validating and updating vuln sourcetype macro."""

  def __init__(self, *args, **kwargs):
    """Initialize the parameters."""
    super(VulnSrcTypeManager, self).__init__(*args, **kwargs)
    self._validator = validator
    self._args = args
    self._kwargs = kwargs
    self.path = os.path.abspath(__file__)

  def validate(self, value, data):
    """Validate the given sourcetypes and update sourcetype macro."""
    _iscommaseparated = re.search("^((?:[^,\\s]+),)*(?:[^,\\s]+)$", value)
    if _iscommaseparated:
      return True
    else:
      self.put_msg("Please enter single sourcetype or comma separated sourcetypes in Vuln Sourcetypes field.")
      return False

  def save(self, value, data):
    """Save the given sourcetypes and update sourcetype macro."""
    try:
      service = create_service()
      vuln_src_types = value
      macro_string = "sourcetype IN ({})".format(vuln_src_types)
      try:
        update_macros(service, "mandiant_vuln_srctypes", macro_string)
      except Exception as e:
        self.put_msg("Unexpected error occurred while updating {} macro.".format("mandiant_vuln_srctypes"))
        logger.error(
            "The following error occurred while updating {} macro. Error: {}".format(
                "mandiant_vuln_srctypes", e
            )
        )
        return False
    except HTTPError:
      logger.error("Error while retrieving Macros: {}".format(traceback.format_exc()))
      self.put_msg("Error while retrieving Macros. Kindly check log file for more details.")
      return False
    except Exception:
      self.put_msg("Unexpected error occurred while updating {} macro.".format("mandiant_vuln_srctypes"))
      logger.error(
          "The following error occurred while updating {} macro. Error: {}".format(
              "mandiant_vuln_srctypes", e
          )
      )
      return False
    return True


class VulnFieldsManager(Validator):
  """Class provides methods for validating and updating vuln fields macro."""

  def __init__(self, *args, **kwargs):
    """Initialize the parameters."""
    super(VulnFieldsManager, self).__init__(*args, **kwargs)
    self._validator = validator
    self._args = args
    self._kwargs = kwargs
    self.path = os.path.abspath(__file__)

  def get_macro_string(self, fields_list):
    """Returns quoted macro string."""
    macro_string = str()
    for field in fields_list:
      macro_string += f'"{field}"' + ","
    return macro_string.rstrip(",")

  def validate(self, value, data):
    """Validate the given fields Value and update fields macro."""
    _iscommaseparated = re.search("^((?:[^,\\s]+),)*(?:[^,\\s]+)$", value)
    if _iscommaseparated:
      return True
    else:
      self.put_msg("Please enter single field name or comma separated field name in Vuln Fields.")
      return False

  def save(self, value, data):
    """Save the given fields Value and update fields macro."""
    try:
      service = create_service()
      vuln_fields = value
      macro_string = self.get_macro_string(vuln_fields.strip(" ").split(","))
      try:
        update_macros(service, "mandiant_vuln_fields", macro_string)
      except Exception as e:
        self.put_msg("Unexpected error occurred while updating {} macro.".format("mandiant_vuln_fields"))
        logger.error(
            "The following error occurred while updating {} macro. Error: {}".format(
                "mandiant_vuln_fields", e
            )
        )
        return False
    except HTTPError:
      logger.error("Error while retrieving Macros: {}".format(traceback.format_exc()))
      self.put_msg("Error while retrieving Macros. Kindly check log file for more details.")
      return False
    except Exception:
      self.put_msg("Unexpected error occurred while updating {} macro.".format("mandiant_vuln_fields"))
      logger.error(
          "The following error occurred while updating {} macro. Error: {}".format(
              "mandiant_vuln_fields", e
          )
      )
      return False
    return True


class VulnHostFieldManager(Validator):
  """Class provides methods for validating and updating vuln host field macro."""

  def __init__(self, *args, **kwargs):
    """Initialize the parameters."""
    super(VulnHostFieldManager, self).__init__(*args, **kwargs)
    self._validator = validator
    self._args = args
    self._kwargs = kwargs
    self.path = os.path.abspath(__file__)

  def validate(self, value, data):
    if not isinstance(value, str):
      self.put_msg("Vuln Host field not of required type string")
      return False
    else:
      return True


  def save(self, value, data):
    """Save the given fields Value and update fields macro."""
    try:
      service = create_service()
      try:
        update_macros(service, "mandiant_vuln_host_field", value)
      except Exception as e:
        self.put_msg(
            "Unexpected error occurred while updating {} macro.".format(
                "mandiant_vuln_host_field"))
        logger.error(
            "The following error occurred while updating {} macro. Error: {}".
            format("mandiant_vuln_host_field", e))
        return False
    except HTTPError:
      logger.error("Error while retrieving Macros: {}".format(
          traceback.format_exc()))
      self.put_msg(
          "Error while retrieving Macros. Kindly check log file for more details."
      )
      return False
    except Exception:
      self.put_msg("Unexpected error occurred while updating {} macro.".format(
          "mandiant_vuln_host_field"))
      logger.error(
          "The following error occurred while updating {} macro. Error: {}".
          format("mandiant_vuln_host_field", e))
      return False
    return True


class ValidateVulnTTL(Validator):
  """Class provides methods for validating and updating vuln retiring days macro."""

  def __init__(self, *args, **kwargs):
    """Initialize the parameters."""
    super(ValidateVulnTTL, self).__init__(*args, **kwargs)
    self._validator = validator
    self._args = args
    self._kwargs = kwargs
    self.path = os.path.abspath(__file__)

  def validate(self, value, data):
    """Validate method to perform action."""
    days_back = value
    if days_back.startswith("_"):
      days_back = int(days_back[1:])
      if days_back < 0:
        self.put_msg("Invalid Value for field Vuln Time Window. Enter valid integer.")
        return False
    else:
      days_back = int(days_back)
      if days_back not in range(0, 181):
        self.put_msg("Invalid value for field Vuln Time Window. Enter valid integer in the allowed range of [0 and 180].")    # noqa: E501
        return False
    return True

  def save(self, value, data):
    """Save method to perform action."""
    days_back = value
    if days_back.startswith("_"):
      try:
        days_back = int(days_back[1:])
        data["vuln_ttl"] = days_back
        service = create_service()
        update_macros(service, "mandiant_vuln_retiring_days", days_back)
      except HTTPError:
        logger.error("Error while retrieving Macros: {}".format(traceback.format_exc()))
        self.put_msg("Error while retrieving Macros. Kindly check log file for more details.")
        return False
    else:
      try:
        days_back = int(days_back)
        data["vuln_ttl"] = days_back
        service = create_service()
        update_macros(service, "mandiant_vuln_retiring_days", days_back)
      except HTTPError:
        logger.error("Error while retrieving Macros: {}".format(traceback.format_exc()))
        self.put_msg("Error while retrieving Macros. Kindly check log file for more details.")
        return False

    return True
