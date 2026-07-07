import import_declare_test # noqa F401
import os
import traceback

from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunktaucclib.rest_handler.endpoint import (
    validator
)
import splunk.admin as admin
import socket
import splunk.clilib.cli_common
import splunklib.client as client
from splunklib.binding import HTTPError

from mandiant_setup_utils import get_conf_file, get_unique_set, get_macro_string
import common.log as log
from setup_consts import SAVEDSEARCHES_DATAMODEL

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


class MandiantMatchedEventsManager(Validator):
  """Class provides methods for handling settings for Mandiant Matched Events"""

  def __init__(self, *args, **kwargs):
    """Initialize the parameters."""
    super(MandiantMatchedEventsManager, self).__init__(*args, **kwargs)
    self._validator = validator
    self._args = args
    self._kwargs = kwargs
    self.path = os.path.abspath(__file__)
    self.data_model_map = {
        "authentication_match": {
            "saved_search_name": "mandiant_match_events_authentication"
        },
        "endpoint_process_match": {
            "saved_search_name": "mandiant_match_events_endpoint_process"
        },
        "endpoint_services_match": {
            "saved_search_name": "mandiant_match_events_endpoint_services"
        },
        "endpoint_filesystem_match": {
            "saved_search_name": "mandiant_match_events_endpoint_filesystem"
        },
        "intrusion_detection_match": {
            "saved_search_name": "mandiant_match_events_intrusion_detection"
        },
        "malware_attacks_match": {
            "saved_search_name": "mandiant_match_events_malware_attacks"
        },
        "network_resolution_match": {
            "saved_search_name": "mandiant_match_events_network_resolution"
        },
        "network_traffic_match": {
            "saved_search_name": "mandiant_match_events_network_traffic"
        },
        "web_match": {
            "saved_search_name": "mandiant_match_events_web"
        }
    }

  def validate(self, value, data):
    """Method to override to from Splunk Validator class. If enable matched events setting is true, enables
        saved searches for the defined data models

        Params:
            value: str - required by Splunk but not used in this function
            data: dict - settings from the Threat Intelligence Event Matching screen

        Returns
            bool: if success True, else False
        """
    try:
      service = create_service()
      notable_search = service.saved_searches["mandiant_create_notables"]

      if data.get('enable_event_matching') == "1":
        self.enable_saved_searches(service, data.get('data_models_to_match', ""))
      else:
        self.disable_saved_searches(service)

      if data.get('enable_notable_alerts') == "1":
        notable_search.enable()
      else:
        notable_search.disable()

      return True
    except Exception as ex:
      logger.error(
        f"Unexpected exception saving Threat Intelligence Event Matching Settings. Exception: {str(ex)}"
      )
      return False

  def enable_saved_searches(self, service, data_models):
    """Enables data_models provided and disables others

        Params:
            service: Splunk service used to connect to Splunk REST API
            data_models: str - comma separated list of data models"""
    data_models_list = data_models.split(",")
    for data_model in self.data_model_map:
      if data_model in data_models_list:
        saved_search = service.saved_searches[self.data_model_map.get(data_model).get('saved_search_name')]
        saved_search.enable()
      else:
        self.disable_saved_search(service, data_model)

  def disable_saved_searches(self, service):
    """Disables saved searches for all data models

        Params:
            service: Splunk service used to connect to Splunk REST API
        """
    for data_model in self.data_model_map:
      self.disable_saved_search(service, data_model)

  def disable_saved_search(self, service, data_model):
    """Disables a saved searches for a named data models

        Params:
            service: Splunk service used to connect to Splunk REST API
            data_model: str - the data model saved search to disable
        """
    saved_search = service.saved_searches[self.data_model_map.get(data_model).get('saved_search_name')]
    saved_search.disable()


class MandiantSavedSearchesManager(Validator):
  """Class provides methods for handling Savedsearches."""

  def __init__(self, *args, **kwargs):
    """Initialize the parameters."""
    super(MandiantSavedSearchesManager, self).__init__(*args, **kwargs)
    self._validator = validator
    self._args = args
    self._kwargs = kwargs
    self.path = os.path.abspath(__file__)

  def enable_savedsearches(self, service, enable_list):
    """Enable the saved searches provided in the parameters."""
    for datamodel_key, saved_searches_name in SAVEDSEARCHES_DATAMODEL.items():
      if datamodel_key in enable_list:
        saved_search = service.saved_searches[saved_searches_name]
        saved_search.enable()
        logger.debug("Saved Search: {} is enabled Successfully.".format(saved_searches_name))

  def disable_savedsearches(self, service, disable_list):
    """Disable the saved searches provided in the parameters."""
    for datamodel_key, saved_searches_name in SAVEDSEARCHES_DATAMODEL.items():
      if datamodel_key in disable_list:
        saved_search = service.saved_searches[saved_searches_name]
        saved_search.disable()
        logger.debug("Saved Search: {} is disabled Successfully".format(saved_searches_name))

  def update_macros(self, service, macro_name, macro_string):
    """Update macro with the indexes provided."""
    service.post("properties/macros/{}".format(macro_name), definition=macro_string)

  def validate(self, value, data):
    """Enable/disable the savedsearches for the entered parameters."""
    try:
      # Reading values from conf file
      conf = get_conf_file(file="ta_mandiant_advantage_settings")
      parameters = conf.get("correlation_parameters", {})
      enabled_savedsearches = parameters.get("enabled_savedsearches", None)
      list_enabled_savedsearches = []
      if enabled_savedsearches:
        list_enabled_savedsearches = enabled_savedsearches.split(",")

      enable_ss = data.get('enable_correlation', 0)
      enable_tstats = data.get('accelerated_search', 0)
      data_model_list = list(get_unique_set(data.get('data_models')))
      indicator_ttl = str(data.get('indicator_ttl', 0))

      # Removing _ from the start of the value
      for index in range(len(data_model_list)):
        data_model_list[index] = data_model_list[index].strip("_")

      # Creating client for connecting server
      logger.debug("Creating Splunk Client object.")
      service = create_service()

      # Updating macro of Indicator TTL.
      try:
        self.update_macros(service, "mandiant_indicator_retiring_days", indicator_ttl.strip("_"))
        logger.debug("\"mandiant_indicator_retiring_days\" macro updated.")
      except HTTPError:
        logger.error("Error while retrieving Macro: {}".format(traceback.format_exc()))
        self.put_msg("Error while retrieving Macro. Kindly check log file for more details.")
        return False
      except Exception as e:
        msg = "Unrecognized error: {}".format(str(e))
        logger.error(msg)
        self.put_msg(msg)
        logger.error(traceback.format_exc())
        return False

      if bool(int(enable_ss)):
        if bool(int(enable_tstats)):
          for index in range(len(data_model_list)):
            data_model_list[index] = "{}_{}".format(data_model_list[index], "tstats")

        # Getting list of datamodel that needs to be enable and disable.
        enable_list = list(filter(lambda x: x not in set(list_enabled_savedsearches), data_model_list))
        disable_list = list(filter(lambda x: x not in set(data_model_list), list_enabled_savedsearches))

        # Enable the scheduled saved search
        if len(enable_list) > 0:
          self.enable_savedsearches(service, enable_list)
          logger.info("Savedsearches Enabled Successfully.")

        # Disable the scheduled saved search
        if len(disable_list) > 0:
          self.disable_savedsearches(service, disable_list)
          logger.info("Savedsearches Disabled Successfully.")

        enabled_datamodel = ",".join(data_model_list)
        data['enabled_savedsearches'] = enabled_datamodel
        return True
      else:
        if len(list_enabled_savedsearches) > 0:
          self.disable_savedsearches(service, list_enabled_savedsearches)
          logger.info("Savedsearches Disabled Successfully.")
          conf.update("correlation_parameters", {'enabled_savedsearches': None})
        else:
          logger.info("No Savedsearches are running.")
        return True
    except HTTPError:
      logger.error("Error while retrieving Saved Search: {}".format(traceback.format_exc()))
      self.put_msg("Error while retrieving Saved Search. Kindly check log file for more details.")
      return False
    except Exception as e:
      msg = "Unrecognized error: {}".format(str(e))
      logger.error(msg)
      self.put_msg(msg)
      logger.error(traceback.format_exc())
      return False
    else:
      return True


class ValidateTTL(Validator):
  """Validator class to validate values for Days Back field."""

  def validate(self, value, data):
    """Validate method to perform action."""
    days_back = data["indicator_ttl"]
    if days_back.startswith("_"):
      try:
        days_back = int(days_back[1:])
        if days_back >= 0:
          data["indicator_ttl"] = days_back
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
        data["indicator_ttl"] = days_back
      except ValueError:
        self.put_msg("Invalid value for field Indicator Time Window. Enter valid integer in the allowed range of [0 and 180].")    # noqa: E501
        return False
    return True


class MandiantIndicatorSettingsMacroManager(Validator):

  def __init__(self, *args, **kwargs):
    """Initialize the parameters."""
    super(MandiantIndicatorSettingsMacroManager, self).__init__(*args, **kwargs)

  def update_macros(self, service, macro_name, macro_value):
    service.post(f"properties/macros/{macro_name}", definition=macro_value)

  def validate(self, value, data):
    """Update the macros with the provided indexes."""
    try:
      service = create_service()
      self.update_macros(service, "mandiant_indicator_time_window", data.get('days_back'))
      index = data.get('index')
      if index == "default":
        index = "main"
      self.update_macros(service, "mandiant_indicator_index", index)
      self.update_macros(service, "mandiant_min_ic_score", data.get('m_score'))
    except HTTPError as ex:
      logger.error(f"Error updating Macros: {traceback.format_exc()}")
      self.put_msg(f"Error updating Macros. {str(ex)}")
      return False
    except Exception as ex:
      msg = f"Unexpected error: {str(ex)}"
      logger.error(msg)
      self.put_msg(msg)
      logger.error(traceback.format_exc())
      return False
    
    return True


class MandiantMacrosManager(Validator):
  """Class provides methods for handling Macros."""

  def __init__(self, *args, **kwargs):
    """Initialize the parameters."""
    super(MandiantMacrosManager, self).__init__(*args, **kwargs)
    self._validator = validator
    self._args = args
    self._kwargs = kwargs
    self.path = os.path.abspath(__file__)

  def update_macros(self, service, macro_name, indexes_string):
    """Update macro with the indexes provided."""
    service.post("properties/macros/{}".format(macro_name), definition=indexes_string)
    logger.debug("Macro: {} is updated Successfully.".format(macro_name))

  def validate(self, value, data):
    """Update the macros with the provided indexes."""
    try:
      service = create_service()
      indexes = data.get("job_index")
      logger.info(indexes)
      status, response_string = get_macro_string(logger, indexes)
      if status:
        self.update_macros(service, "mandiant_validation_indices", response_string)
      else:
        self.put_msg(response_string)
        return False

      indexes = data.get("iocs_index")
      status, response_string = get_macro_string(logger, indexes)
      if status:
        self.update_macros(service, "mandiant_indicator_indices", response_string)
      else:
        self.put_msg(response_string)
        return False

      indexes = data.get("dtm_alerts_index")
      status, response_string = get_macro_string(logger, indexes)
      if status:
        self.update_macros(service, "mandiant_dtm_alert_indices", response_string)
      else:
        self.put_msg(response_string)
        return False

      indexes = data.get("asm_issues_index")
      status, response_string = get_macro_string(logger, indexes)
      if status:
        self.update_macros(service, "mandiant_asm_issues_indices", response_string)
      else:
        self.put_msg(response_string)
        return False

      indexes = data.get("asm_entities_index")
      status, response_string = get_macro_string(logger, indexes)
      if status:
        self.update_macros(service, "mandiant_asm_entities_indices", response_string)
      else:
        self.put_msg(response_string)
        return False

      indexes = data.get("target_index")
      status, response_string = get_macro_string(logger, indexes)
      if status:
        self.update_macros(service, "mandiant_target_indices", response_string)
      else:
        self.put_msg(response_string)
        return False
      return True
    except HTTPError:
      logger.error("Error while retrieving Macros: {}".format(traceback.format_exc()))
      self.put_msg("Error while retrieving Macros. Kindly check log file for more details.")
      return False
    except Exception as e:
      msg = "Unrecognized error: {}".format(str(e))
      logger.error(msg)
      self.put_msg(msg)
      logger.error(traceback.format_exc())
      return False
    else:
      return True
