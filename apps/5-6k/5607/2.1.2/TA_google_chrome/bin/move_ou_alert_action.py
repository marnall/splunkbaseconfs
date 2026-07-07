import import_declare_test
import os
import io
from contextlib import redirect_stdout
import sys
import json
import logevent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from TA_google_chrome_api_calls import GoogleWorkflowCalls
from TA_google_chrome_api_calls import ADDON_NAME
import logging
from solnlib import conf_manager, log

required_parameters = {'server_uri',
                       'session_key'}


def logger_for_input(input_name) -> logging.Logger:
    normalized_input = input_name.split("/")[-1]
    return log.Logs().get_logger(
        f"ta_google_chrome_{normalized_input}"
    )


def get_account_info(session_key, account_name):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_google_chrome_admin_console_connection",
    )
    account_conf_file = cfm.get_conf("ta_google_chrome_admin_console_connection")
    return account_conf_file.get(account_name)


class MoveOuAlertAction(object):
    def __init__(self, **kwargs):
        self.params = {}
        for k, v in kwargs.items():
            self.params[k] = v
        self.setup_util = None
        self.__sa_credentials = ''

    def set_api_key(self):
        self.__sa_credentials = get_account_info(self.params['session_key'], self.params['configuration']['saccount'])

    def validate_params(self, logger):
        if not required_parameters.issubset(self.params):
            return False

        return True

    def run_alert(self, logger):

        if self.validate_params(logger):
            logger.info('Getting API key')
            self.set_api_key()
            self.implement_alert_action(logger, **self.params['configuration'])
        else:
            # return valid error
            pass

    def implement_alert_action(self, logger, **kwargs):

        def remove_response_text_on_success(response):
            # removes any response text for successful calls as it might contain sensitive data
            if response.status_code in [200, 201]:
                return ''
            else:
                return response.text

        def log_alert_action_result(logger, call_output, response):

            response_text_temp = remove_response_text_on_success(response)

            logger.info("Alert Action output: {}".format(repr(call_output)))
            logger.info("Response status code: {}".format(repr(response.status_code)))
            logger.info("Response text: {}".format(repr(response_text_temp)))

        def log_summary(call_output, response):
            ''' This function logs the API call status and response.

            :param call_output: input used to make the API call
            :param response:    API call results
            :return: None
            '''

            response_text_temp = remove_response_text_on_success(response)

            event_dict = {
                'alert_name': self.params['search_name'],
                'action_metadata': self.params['configuration'],
                'execution_logs': repr(call_output),
                'response_status': response.status_code,
                'response_text': response_text_temp
            }

            event = json.dumps(event_dict)
            source = os.path.basename(sys.argv[0])
            sourcetype = 'google_chrome_alert_action'
            host = self.params['server_host']
            index = '_internal'

            logevent.log_event(self.params, event, source, sourcetype, host, index)

        sa_key = json.loads(self.__sa_credentials.get('service_account'))
        customerID = self.__sa_credentials.get('customerID')
        admin_email = self.__sa_credentials.get('admin_email')
        ou_path = str(self.params['configuration']['ou_path'])
        deviceID = str(self.params['configuration']['directory_device_id'])
        alert_scope = str(self.params['configuration'].get('scope', ''))
        profile_user = str(self.params['configuration']['profile_user'])

        api_call = GoogleWorkflowCalls(sa_key=sa_key,
                                       customerID=customerID,
                                       admin_email=admin_email
                                       )

        if alert_scope == '':
            logger.info('Scope is blank. Defaults to "both" setting')
        else:
            logger.info('Scope is set to {scope}'.format(scope=alert_scope))

        f = io.StringIO()
        if alert_scope != 'browser':
            logger.info('Moving profile {profile_user} to OU: {OU}'.format(
                profile_user=profile_user,
                OU=ou_path))

            if profile_user == '':
                logger.info('The profile_user field is empty. Skipping...')
            else:

                with redirect_stdout(f):
                    # captures stdout prints into a variable

                    api_call.move_user_to_OU(ou_path, profile_user)

                call_output = f.getvalue()

                log_alert_action_result(logger, call_output, api_call.response)
                log_summary(call_output, api_call.response)

        if alert_scope != 'user':
            logger.info('Moving device {deviceID} to OU: {OU}'.format(
                deviceID=self.params['configuration']['device_id'],
                OU=ou_path))

            if deviceID == '':

                if profile_user == '':
                    logger.info('The directory_device_id field is empty. Skipping...')

            else:

                with redirect_stdout(f):

                    api_call.move_browser_to_OU(ou_path, deviceID)

                    call_output = f.getvalue()
                    log_alert_action_result(logger, call_output, api_call.response)
                    log_summary(call_output, api_call.response)


if __name__ == '__main__':

    logger = logger_for_input('move_ou_alert_action')

    logger.info("Alert Action move to OU triggered")

    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        try:
            modular_alert = MoveOuAlertAction(**payload)

            session_key = modular_alert.params['session_key']
            # get log level based on settings conf file
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name=f"{ADDON_NAME}_settings",
            )
            logger.setLevel(log_level)

            logger.info("Alert name: {alert_name}".format(alert_name=(modular_alert.params['search_name'])))

            modular_alert.run_alert(logger)

            logger.info("Alert Action end")
            sys.exit(0)
        except Exception as e:
            logger.error("Unhandled exception: " + str(e))

    else:
        print("Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
