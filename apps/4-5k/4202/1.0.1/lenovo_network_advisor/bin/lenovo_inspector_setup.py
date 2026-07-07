from simple_rest_handler import RestHandler, IntegerFieldValidator, BooleanFieldValidator, log_function_invocation
import splunk.admin as admin
import splunk.entity as en
# import your required python modules
import shutil
import os
import logging

class ConfigApp(RestHandler):

    # Below is the name of the conf file (example.conf)
    conf_file = 'lenovo_inspector'

    # Below are the list of parameters that are accepted
    PARAM_DEBUG = 'debug'
    PARAM_FOO = 'foo'
    PARAM_SOME_INTEGER = 'some_integer'
    PARAM_SWITCHIP = 'SwitchIP'
    PARAM_LOGIN_NAME_STR = 'SwitchUser'
    PARAM_LOGIN_PASSWORD_STR = 'SwitchPassword'
    PARAM_SWITCHPROTOCOL_STR = 'SwitchProtocol'
    PARAM_HEALTH_MONITOR = 'Health'
    PARAM_TRAFFIC_MONITOR = 'Traffic'
    PARAM_CONGTESTION_MONITOR = 'Congestion'
    PARAM_BUFFER_MONITOR = 'Buffer'
    PARAM_FORWARDER_HOSTNAME = 'Forwarder'

    # Below are the list of valid and required parameters
    valid_params = [PARAM_SWITCHIP, PARAM_LOGIN_NAME_STR, PARAM_LOGIN_PASSWORD_STR, PARAM_SWITCHPROTOCOL_STR, PARAM_HEALTH_MONITOR, PARAM_TRAFFIC_MONITOR, PARAM_CONGTESTION_MONITOR, PARAM_BUFFER_MONITOR, PARAM_FORWARDER_HOSTNAME]
    #required_params = [PARAM_SWITCHIP, PARAM_LOGIN_NAME_STR, PARAM_LOGIN_PASSWORD_STR, PARAM_SWITCHPROTOCOL_STR, PARAM_HEALTH_MONITOR, PARAM_TRAFFIC_MONITOR, PARAM_CONGTESTION_MONITOR, PARAM_BUFFER_MONITOR, PARAM_FORWARDER_HOSTNAME]

    required_params = []   
    # List of fields and how they will be validated
    field_validators = {
        #PARAM_DEBUG : BooleanFieldValidator(),
        #PARAM_SOME_INTEGER : IntegerFieldValidator(0, 65535)
    }

    # General variables
    app_name = "lenovo_network_advisor"

    # Logger info
    logger_file_name = 'lenovo_network_advisor.log'
    logger_name = 'ConfLogger'
    logger_level = logging.DEBUG

    @log_function_invocation
    def handleEditCreate_prefix_callback(self):
	pass
    	#os.system('cp -f /opt/splunk/etc/apps/lenovo_network_advisor/local/lenovo_inspector.conf /opt/splunk/etc/apps/search/local/lenovo_inspector.conf  ')

    @log_function_invocation
    def handleEditCreate_suffix_callback(self):
	os.system('rm -fr /opt/splunk/etc/deployment-apps/lenovo_network_advisor')
    	os.system('mkdir -p /opt/splunk/etc/deployment-apps/lenovo_network_advisor')
    	os.system('mkdir -p /opt/splunk/etc/deployment-apps/lenovo_network_advisor/bin')
    	os.system('mkdir -p /opt/splunk/etc/deployment-apps/lenovo_network_advisor/default')
    	os.system('mkdir -p /opt/splunk/etc/deployment-apps/lenovo_network_advisor/local')
    	os.system('mkdir -p /opt/splunk/etc/deployment-apps/lenovo_network_advisor/logs')
    	os.system('echo "Logme" > /opt/splunk/etc/deployment-apps/lenovo_network_advisor/logs/logme')
    	os.system('cp -f /opt/splunk/etc/apps/search/local/lenovo_inspector.conf  /opt/splunk/etc/deployment-apps/lenovo_network_advisor/local/lenovo_inspector.conf')
    	os.system('cp -f /opt/splunk/etc/apps/lenovo_network_advisor/default/lenovo_inspector.conf  /opt/splunk/etc/deployment-apps/lenovo_network_advisor/default')

    	os.system('./inputs_generator.sh > /opt/splunk/etc/deployment-apps/lenovo_network_advisor/local/inputs.conf')
    	os.system('cp -f *.sh  *.py /opt/splunk/etc/deployment-apps/lenovo_network_advisor/bin')
	os.system('./add-signature.sh')

# initialize the handler
if __name__ == "__main__":
    #command="echo \" %s \" > /opt/splunk/var/log/splunk/environ" % os.environ
    #os.system(command)
    admin.init(ConfigApp, admin.CONTEXT_NONE)
