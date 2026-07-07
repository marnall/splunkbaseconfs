import splunk.admin as admin
import time
import json
import dome9_utils

import logging
from logger_manager import setup_logging
LOGGER = setup_logging("checkpoint_dome9_setup_status", logging.INFO)


class SetupStatusRestcall(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    def setup(self):
        """
        Sets the input arguments
        :return: None
        """
        # Set up the valid parameters
        for arg in ['page']:
            # For now there is no input parameter in this endpoint
            self.supportedArgs.addOptArg(arg)


    def handleList(self, conf_info):
        """
        handles GET method request
        """
        LOGGER.debug("handleList")

        try:
            # Endpoint can only be requested through current app's namespace as it requires to access conf file of the App.
            LOGGER.debug("App: " + str(self.context != admin.CONTEXT_NONE and self.appName  or "-") + " - User: " + str(self.context == admin.CONTEXT_APP_AND_USER and self.userName or "-"))
            conf_dict = self.readConf(dome9_utils.CONF_FILE_NAME)
            if 'API' not in conf_dict:
                conf_info[dome9_utils.STANZA_NAME]['setup_error'] = "Error in checkpoint_dome9.conf file. API stanza should be present."
                conf_info[dome9_utils.STANZA_NAME]['api_key'] = "Error"
                return
            
            LOGGER.debug("self.caller: " + str(self.callerArgs))
            if 'page' in self.callerArgs and self.callerArgs['page'][0]:
                page = str(self.callerArgs['page'][0])
                if page:
                    # if page is present then the request coming from the dashboard, it should return with api_key status
                    credentials = dome9_utils.get_credentials(LOGGER, self.getSessionKey(), conf_dict)
                    
                    if 'api_key' in credentials and credentials['api_key']:
                        conf_info[dome9_utils.STANZA_NAME]['api_key'] = "Success"
                        conf_info[dome9_utils.STANZA_NAME]['setup_success'] = "API Key is available."
                    else:
                        conf_info[dome9_utils.STANZA_NAME]['api_key'] = "Error"
                        conf_info[dome9_utils.STANZA_NAME]['setup_error'] = "API Key is not configured."
                    return

            conf_dict = conf_dict['API']
            current_time = time.time()
            if (current_time - float(conf_dict['msg_time'])) <= 30.000:
                # we won't return any messages after 30 second of message been added to conf file
                if 'setup_error' in conf_dict and conf_dict['setup_error'].strip():
                    conf_info[dome9_utils.STANZA_NAME]['setup_error'] = conf_dict['setup_error'].strip()
                elif 'setup_success' in conf_dict and conf_dict['setup_success'].strip():
                    conf_info[dome9_utils.STANZA_NAME]['setup_success'] = conf_dict['setup_success'].strip()
                return

            conf_info[dome9_utils.STANZA_NAME]['setup_success'] = ""
            conf_info[dome9_utils.STANZA_NAME]['setup_error'] = ""
                    
        except Exception as e:
            LOGGER.exception("Exception while getting checkpoint dome9 setup status. " + str(e))
            raise e
    

if __name__ == "__main__":
    admin.init(SetupStatusRestcall, admin.CONTEXT_APP_AND_USER)