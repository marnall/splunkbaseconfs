import json
import logging
import logevent
import os
import io
import sys
from contextlib import redirect_stdout
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from TA_google_chrome_api_calls import GoogleWorkflowCalls
from TA_google_chrome_api_calls import ADDON_NAME
from solnlib import conf_manager, log, modular_input, credentials


@Configuration()
class moveuserou(StreamingCommand):
    sa_name = Option(
        doc='''
        **Syntax:** **fieldname=***<fieldname>*
        **Description:** Name of the field that will hold the genre name''',
        require=True)

    ou_name = Option(
        doc='''
        **Syntax:** **fieldname=***<fieldname>*
        **Description:** Name of the field that will hold the genre name''',
        require=True)

    device_user = Option(
        doc='''
        **Syntax:** **fieldname=***<fieldname>*
        **Description:** Name of the field that will hold the genre name''',
        require=True)

    def stream(self, records):

        def remove_response_text_on_success(response):
            # removes any response text for successful calls as it might contain sensitive data
            if response.status_code in [200, 201, 204]:
                return ''
            else:
                return response.text

        def log_alert_action_result(logger, call_output, response):

            response_text_temp = remove_response_text_on_success(response)
            logger.info("Workflow Action output: {}".format(repr(call_output)))
            logger.info("Response status code: {}".format(repr(response.status_code)))
            logger.info("Response text: {}".format(repr(response_text_temp)))

        try:

            ###############################################
            # to get command parameters  value
            ###############################################
            sa_name = str(self.sa_name)
            ou_name = str(self.ou_name)
            device_user = str(self.device_user)

            ###############################################
            # To Get session key
            ###############################################
            session_key = self._metadata.searchinfo.session_key

            ###############################################
            # To Get splunk internal log path
            ###############################################

            session_path = self._metadata.searchinfo.dispatch_dir
            dispatch_index = session_path.find("dispatch")
            before_dispatch = session_path[:dispatch_index]
            splunk_log_path = before_dispatch.replace("run", "log")

            ###############################################
            # setting log path
            ###############################################

            log.Logs.set_context(directory=splunk_log_path)
            logger = log.Logs().get_logger('google_chrome_workflow_action')

            ###############################################
            # To read & get conf file settings
            ###############################################
            cfm = conf_manager.ConfManager(session_key, ADDON_NAME, realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_google_chrome_admin_console_connection")
            account_conf_file = cfm.get_conf("ta_google_chrome_admin_console_connection")
            customerID = account_conf_file.get(sa_name).get("customerID")
            admin_email = account_conf_file.get(sa_name).get("admin_email")
            sa_key = json.loads(account_conf_file.get(sa_name).get("service_account"))

            ##############################################################################################
            # Calling Alert Action function
            ##############################################################################################

            username = self._metadata.searchinfo.username
            user_info = f'username: {username}, triggered Move User to OU workflow action'
            logger.info(user_info)
            move_log = f'Moving user {device_user} to OU: {ou_name}'
            logger.info(move_log)
            api_call = GoogleWorkflowCalls(sa_key=sa_key, customerID=customerID, admin_email=admin_email)
            f = io.StringIO()
            with redirect_stdout(f):
                api_call.move_user_to_OU(ou_name, device_user)
                call_output = f.getvalue()
                log_alert_action_result(logger, call_output, api_call.response)

            logger.info("Workflow Action Ended")
            for record in records:
                record["response"] = api_call.response.status_code
                yield record

        except Exception as e:
            error_log = f'Failed: {e}'
            logger.error(str(error_log))
            logger.info("Response status code: 400")
            logger.info("Workflow Action Ended")
            for record in records:
                record["response"] = "400"
                yield record


dispatch(moveuserou, sys.argv, sys.stdin, sys.stdout, __name__)
