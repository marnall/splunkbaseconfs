# Standard library imports
import sys
import os
sys.path.insert(0, os.path.sep.join([os.path.dirname(__file__)]))

# Splunk imports
import splunk.rest as rest

# Local imports
import reach_security_app_for_splunk_declare
import reach_logger_manager as log
import reach_search_execution_helper


class SingleExecution(rest.BaseRestHandler):
    """ Rest Handler class for reach_collect_data endpoint. """

    def handle_GET(self):
        """
        Handles GET request.
        """
        logger = log.setup_logging('reach_single_execution', self.sessionKey)
        action = self.request.get('query', {}).get('action', 'execute')
        action = "disable" if action == "cancel" else "enable"
        encoded_script_name = "%24SPLUNK_HOME%252Fetc%252Fapps%252F"\
            "reach_security_app_for_splunk%252Fbin%252Freach_input_single_execution.py"
        try:
            status = reach_search_execution_helper.disable_enable_script(
                action, encoded_script_name, self.sessionKey, logger)
            if action == "disable":
                # Update status to Aborted
                reach_search_execution_helper.SettingsConfFile(
                    self.sessionKey, logger).update_settings_conf_file({"status": "Aborted"})
            return "success" if status else "error"
        except Exception as e:
            logger.error(
                "Reach Error: Error while disabling the input. Error: " + str(e))
            return "error"
