# splunk sdk imports
import splunk.admin as admin
import splunk

# importing core python packages
import json
from httplib2 import ServerNotFoundError

# importing rest_utility
from rest_utility import setup_logger, RestError
import rest_utility as ru

# defining constants here
logger = setup_logger(log_name="pool_configuration.log",
                      logger_name="pool_configuration")
local_host_path = splunk.mergeHostPath()

class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
        This is used for adding optional and required arguments for particular requests."""
        pass

    def handleList(self, conf_info):
        """When GET request is done on the endpoint this method is called,
        It returns the details the status of all the scheduler inputs(pools) in json format."""
        try:
            local_session_key = self.getSessionKey()
            info_path = local_host_path.rstrip(
                        "/") + "/servicesNS/nobody/Splunk_TA_vmware_inframon/data/inputs/ta_vmware_collection_scheduler_inframon?output_mode=json"

            server_response, server_content = ru.splunk_rest_request(info_path, logger,
                                                                    local_session_key=local_session_key,
                                                                    session_key=local_session_key)

            entries = {}
            if server_content is not None:
                server_content_dict = json.loads(server_content)
                entries = server_content_dict['entry']

            pool_disabled_status = {}
            for entry in entries:
                pool_name = entry["name"]
                disabled = entry['content']['disabled']
                pool_disabled_status.update( {pool_name: disabled } )

            conf_info["data"]["isSchedulerDisabled"] = json.dumps(pool_disabled_status)

        except ServerNotFoundError:
            logger.exception("Could not get pool status.")
            raise RestError(500, "Error occured while getting pool status.")
        except Exception as e:
            logger.exception("Error occured while getting pool status.")
            raise e

admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)

            
