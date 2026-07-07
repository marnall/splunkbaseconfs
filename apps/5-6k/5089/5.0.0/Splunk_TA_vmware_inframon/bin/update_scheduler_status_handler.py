# splunk sdk imports
import splunk.admin as admin
import splunk
from splunk.entity import controlEntity

# importing core python packages
import json
from httplib2 import ServerNotFoundError
try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus

# importing rest_utility
from rest_utility import setup_logger, RestError
import rest_utility as ru

# defining global constants
local_host_path = splunk.mergeHostPath()
logger = setup_logger(log_name="pool_configuration.log",
                      logger_name="pool_configuration")

REQUIRED_ARGS_EDIT = ['action']


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
        This is used for adding optional and required arguments for particular requests."""
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in REQUIRED_ARGS_EDIT:
                self.supportedArgs.addReqArg(arg)

    def handleEdit(self, conf_info):
        """This method is called at POST request on update_scheduler_status endpoint. This will enable or disable the
        pool based on the value of action parameter. It also enables hierarchy agent when action is enable."""
        try:
            args = self.callerArgs
            pool_name = self.callerArgs.id
            pool_name_encoded = quote_plus(pool_name)
            local_session_key = self.getSessionKey()
            action = args.get("action")[0]

            uri = '/servicesNS/nobody/Splunk_TA_vmware_inframon/data/inputs/ta_vmware_collection_scheduler_inframon/' + pool_name_encoded + "/"
            input_uri = local_host_path.rstrip("/") + uri

            controlEntity(action, input_uri + action, sessionKey=local_session_key)

            logger.info("[pool={1}]action: {0} on pool: {1} performed successfully.".format(action, pool_name))

            if action == "enable":
                uri = '/servicesNS/nobody/Splunk_TA_vmware_inframon/data/inputs/script/%24SPLUNK_HOME%252Fetc%252Fapps%252FSplunk_TA_vmware_inframon%252Fbin%252Fta_vmware_hierarchy_agent.py/disable'
                path = local_host_path.rstrip("/") + uri

                ru.splunk_rest_request(path, logger,
                                       local_session_key=local_session_key,
                                       session_key=local_session_key, method="POST", raise_all_errors=True)

                uri = '/servicesNS/nobody/Splunk_TA_vmware_inframon/data/inputs/script/%24SPLUNK_HOME%252Fetc%252Fapps%252FSplunk_TA_vmware_inframon%252Fbin%252Fta_vmware_hierarchy_agent.py/enable'
                path = local_host_path.rstrip("/") + uri

                ru.splunk_rest_request(path, logger,
                                       local_session_key=local_session_key,
                                       session_key=local_session_key, method="POST", raise_all_errors=True)
                logger.info("[pool={0}]hierarchy agent enabled.".format(pool_name))

            conf_info["data"]["status"] = "200"
            conf_info["data"]["message"] = "action: {0} performed successfully on pool: {1}".format(action, pool_name)

        except ServerNotFoundError as e:
            logger.error(
                "[pool={1}]Could not reach node={0}, could not perform any action on pool={1} Exception = {2} occurred".format(
                    local_host_path, pool_name, e))
            raise RestError(500, "Could not reach node={0}, could not perform any action".format(local_host_path))
        except splunk.ResourceNotFound as e:
            logger.error("pool: {0} not found, could not perform any action".format(pool_name))
            logger.exception(e)
            raise RestError(500, "pool: {0} not found, could not perform any action".format(pool_name))
        except Exception as e:
            logger.exception(e)
            raise e


admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)
