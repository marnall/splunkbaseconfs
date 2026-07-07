# Standard library imports
import sys
import os
from datetime import datetime
import time
import json

sys.path.insert(0, os.path.sep.join([os.path.dirname(__file__)]))

# Splunk imports
import splunk.rest as rest

# Local imports
import reach_security_app_for_splunk_declare
from reach_search_execution import SearchExecution
import splunklib.results as results
import splunklib.client as client


class SettingsConfFile:
    """ Class to read/update reach_security_app_for_splunk_settings.conf file. """

    def __init__(self, session_key, logger):
        """
        Init method of SettingsConfFile class.
        :param session_key: current session key of Splunk
        :param logger: logging object
        """
        self.session_key = session_key
        self.logger = logger
        self.app_name = __file__.split(os.sep)[-3]
        self.conf_endpoint = "/servicesNS/nobody/{}/configs/"\
            "conf-reach_security_app_for_splunk_settings/".format(
                self.app_name)

    def read_settings_conf_file(self, stanza="additional_parameters"):
        """
        Reads and returns content of reach_security_app_for_splunk_settings.conf file.
        :param stanza: stanza name of conf file to read
        :return: content of specified stanza
        """
        # Make GET request
        self.logger.debug(
            "Reach Debug: Making Read request for stanza: " + str(stanza))
        try:
            _, content = rest.simpleRequest(self.conf_endpoint + stanza, method='GET',
                                            sessionKey=self.session_key,
                                            getargs={"output_mode": "json"},
                                            raiseAllErrors=True)
        except Exception as e:
            self.logger.error(
                "Reach Error: Error while making request to read"
                " reach_security_app_for_splunk_settings.conf file. Error: " + str(e))
            sys.exit()
        # Parse Result
        try:
            content = json.loads(content)
            content = content['entry'][0]['content']
        except Exception as e:
            self.logger.error(
                "Reach Error: Error while parsing"
                " reach_security_app_for_splunk_settings.conf file. Error: " + str(e))
            sys.exit()

        self.logger.debug(
            "Reach Debug: Successfully parsed Content of reach_security_app_for_splunk_settings"
            " file. Content: " + str(content))
        return content

    def update_settings_conf_file(self, conf_content, stanza="reach_single_execution"):
        """
        Update stanza of reach_security_app_for_splunk_settings.conf file.
        :param conf_content: content to post
        :param stanza: stanza of file to update
        """
        self.logger.debug(
            "Reach Debug: Updating reach_security_app_for_splunk_settings.conf"
            " file with Arguments: " + str(conf_content))
        # Make POST request
        try:
            _, _ = rest.simpleRequest(self.conf_endpoint + stanza, method='POST',
                                      sessionKey=self.session_key,
                                      postargs=conf_content,
                                      raiseAllErrors=True)
        except Exception as e:
            self.logger.error("Reach Error: Error while updating content {} in "
                              "reach_security_app_for_splunk_settings.conf file. Error: {}".format(
                                  conf_content, str(e)))
            sys.exit()


def get_mgmt_port(session_key, logger):
    try:
        _, content = rest.simpleRequest("/services/configs/conf-web/settings", method='GET',
                                        sessionKey=session_key,
                                        getargs={"output_mode": "json"},
                                        raiseAllErrors=True)
    except Exception as e:
        logger.error(
            "Reach Error: Error while making request to read"
            " web.conf file. Error: " + str(e))
        sys.exit()
    # Parse Result
    try:
        content = json.loads(content)
        content = int(content['entry'][0]['content']['mgmtHostPort'][-4:])
        logger.info("Reach Info: Get managemant port from web.conf is {} ".format(content))
    except Exception as e:
        logger.error(
            "Reach Error: Error while parsing"
            " web.conf file. Error: " + str(e))
        sys.exit()
    return content


def get_configured_data(session_key, logger, macro_sourcetype, earliest_time):
    """
    Execute search and find available data.
    :param session_key: current session key of Splunk
    :param logger: logging object
    :param macro_sourcetype: sourcetype of the products for which data needs to be found
    :param earliest_time: earliest time to search for data
    """
    time_filter = {
        "earliest_time": "-{}d".format(earliest_time),
        "latest_time": "now",
        "adhoc_search_level": "fast"
    }
    port = get_mgmt_port(session_key, logger)
    service = client.connect(**{'token': session_key, 'port': port})
    logger.info("Reach Info: Execute the search to get indexes::"
                " | tstats values(sourcetype) where index=* {} by index "
                "| table index".format(macro_sourcetype))
    job_results = results.ResultsReader(service.jobs.oneshot(
        '| tstats values(sourcetype) where index=* {} by index | table index'.format(
            macro_sourcetype), **time_filter))
    macro_index = []
    for item in job_results:
        if isinstance(item, dict):
            macro_index.append("index={}".format(item.get('index')))

    return macro_index


def update_configured_macro(session_key, logger, configured_products, earliest_time="90"):
    """
    Update the configured macro based on data availability.
    :param session_key: current session key of Splunk
    :param logger: logging object
    :param configured_products: products for which data needs to be found
    :param earliest_time: earliest time to search for data
    """
    # proofpoint_tap,pan_os,active_directory
    product_mapping = {
        "active_directory": "activedirectory",
        "proofpoint_tap": "proofpoint_tap_siem",
        "pan_os": "pan:threat"
    }

    macro_sourcetype = ["sourcetype={}".format(
        product_mapping[product]) for product in configured_products.split(",")
        if product_mapping.get(product)]
    macro_sourcetype = " OR ".join(macro_sourcetype)

    macro_index = get_configured_data(
        session_key, logger, macro_sourcetype, earliest_time)
    status = 0 if len(macro_index) == 0 else 1
    products = configured_products.split(",")

    if status:
        macro_index = " OR ".join(list(set(macro_index)))
        endpoints = [("reach_configured_index", macro_index),
                     ("reach_configured_sourcetypes", macro_sourcetype)]
        for endpoint in endpoints:
            try:
                rest.simpleRequest(
                    "/servicesNS/nobody/reach_security_app_for_splunk/properties/macros/"
                    + endpoint[0],
                    session_key,
                    postargs={"definition": endpoint[1]},
                    method="POST",
                    raiseAllErrors=True,
                )
            except Exception:
                err = "Error Occured while updating settings in conf file. Please setup manually."
                raise Exception(err)
    return products, status


def disable_enable_script(action, encoded_script_name, session_key, logger, interval=None):
    """
    Disable or Enable the scripted input.
    :param action: whether to disable or enable the input
    :param encoded_script_name: name of the script to enable or disable input
    :param session_key: current session key of Splunk
    :param logger: logging object
    :param interval: frequency of execution for periodic collection
    :return: true if successfully updated else false
    """
    log_action = action[:-1]
    logger.debug("Reach Debug: {}ing the {} script".format(
        log_action, encoded_script_name))

    postargs = {"disabled": "true" if action == "disable" else "false"}
    if interval:
        postargs['interval'] = interval
    endpoint = "/servicesNS/nobody/reach_security_app_for_splunk/data/inputs/script/" + \
        encoded_script_name
    try:
        rest.simpleRequest(endpoint, method='POST', sessionKey=session_key,
                           postargs=postargs, raiseAllErrors=True)
    except Exception as e:
        logger.error("Reach Error: Error while {}ing the {} script. Error: {}".format(
            log_action, encoded_script_name, e))
        return False

    logger.debug("Reach Debug: Successfully {}ed the {} script".format(
        log_action, encoded_script_name))
    return True


def start_collection(content, logger):
    """
    Method to trigger the collection.
    :param content: content required to trigger the collection
    :param logger: logging object
    """
    session_key = content['session_key']
    execution_type = content.get('execution_type', 'single')
    base_result_path = content['base_result_path']
    stanza = "reach_periodic_execution" \
        if execution_type == 'periodic' else "reach_single_execution"

    # Get the current time
    start_time = int(time.time())
    current_day = datetime.fromtimestamp(
        start_time).strftime('%Y-%m-%dT%H:%M:%S')
    logger.debug(
        "Reach Debug: Starting the process at {} time: ".format(start_time))

    # Create object of settings conf file class
    settings_obj = SettingsConfFile(session_key, logger)

    # Update Status to In Progress, PID to current Process ID and Execution start time
    conf_content = {
        "status": "In Progress",
        "execution_start_time": current_day
    }
    settings_obj.update_settings_conf_file(conf_content, stanza=stanza)

    # Read settings.conf file
    content = settings_obj.read_settings_conf_file()
    start_day = None
    if execution_type == 'periodic':
        stnaza_content = settings_obj.read_settings_conf_file(stanza=stanza)
        start_day = stnaza_content.get('checkpoint_time')

    # Create object of SearchExecution class
    search_exec_obj = SearchExecution(
        session_key, current_day, base_result_path, content, logger, start_day)

    # Check and Remove Older/Partial files if exist
    try:
        search_exec_obj.remove_older_files()
    except Exception as e:
        logger.error(
            "Reach Error: Error while removing older/partial files. Error: " + str(e))
        sys.exit()

    # Start query execution
    result_path = search_exec_obj.execute_search()

    # Update Status to Completed
    status = "Completed"
    end_time = int(time.time())
    ui_end_time = datetime.fromtimestamp(
        end_time).strftime('%Y-%m-%dT%H:%M:%S')

    # Get the file name to store in conf file if result file exist and update the status
    result_file_name = result_path.split(
        os.sep)[-1] if isinstance(result_path, str) and result_path.endswith('zip') else None

    conf_content = {
        "status": status,
        "result_file_name": result_file_name,
        "last_success_time": ui_end_time
    }
    if execution_type == 'periodic':
        conf_content['checkpoint_time'] = current_day
    settings_obj.update_settings_conf_file(conf_content, stanza=stanza)

    logger.debug("Reach Debug: Completed the process at {} time with status: {}".format(
        end_time, status))
    logger.debug("Reach Debug: Completed the backend process in {} seconds".format(
        end_time - start_time))
