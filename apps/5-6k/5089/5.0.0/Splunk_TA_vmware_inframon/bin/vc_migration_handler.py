# splunk sdk imports
import splunk.admin as admin
import splunk
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

# importing rest_utility
from rest_utility import setup_logger, RestError
import rest_utility as ru

# TA imports
sys.path.append(make_splunkhome_path(['etc', 'apps', 'Splunk_TA_vmware_inframon', 'bin']))
from ta_vmware_inframon.models import PoolStanza, TAVMwareCollectionStanza

# defining global constants
local_host_path = splunk.mergeHostPath()
entity_type = "collection"
logger = setup_logger(log_name="vcenter_configuration.log",
                      logger_name="vcenter_configuration")

REQUIRED_ARGS_EDIT = ['source_pool', 'destination_pool']


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
        This is used for adding optional and required arguments for particular requests."""
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in REQUIRED_ARGS_EDIT:
                self.supportedArgs.addReqArg(arg)

    def handleEdit(self, conf_info):
        """when POST request is done with the target on endpoint, this method is called.
            All the required parameters for this method is settled up in setup() method."""
        try:
            args = self.callerArgs
            vc = self.callerArgs.id
            local_session_key = self.getSessionKey()

            vc_stanza = TAVMwareCollectionStanza.from_name(vc, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                                           session_key=local_session_key)

            if not vc_stanza:
                logger.error("Requested vCenter {0} doesn't exists".format(vc))
                raise RestError(404, "Requested vCenter {0} doesn't exists".format(vc))
            else:
                source_pool = args.get("source_pool")[0]
                destination_pool = args.get("destination_pool")[0]

                if source_pool == destination_pool:
                    logger.error(
                        "[pool={0}]source pool and destination pool cannot be the same.".format(source_pool))
                    raise RestError(400, "Source pool and destination pool cannot be the same.")

                source_pool_stanza = PoolStanza.from_name(source_pool, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                                          session_key=local_session_key)

                destination_pool_stanza = PoolStanza.from_name(destination_pool, "Splunk_TA_vmware_inframon",
                                                               host_path=local_host_path, session_key=local_session_key)

                if source_pool_stanza and destination_pool_stanza:
                    vc_stanza.pool_name = destination_pool

                    if vc_stanza.passive_save():
                        ru.set_conf_modification_time(source_pool, entity_type, local_session_key, logger)
                        ru.set_conf_modification_time(destination_pool, entity_type, local_session_key, logger)
                        conf_info['data']['status'] = 200
                        conf_info['data']['message'] = "vCenter {0} is migrated from {1} to {2} successfully".format(vc,
                                                                                                                     source_pool,
                                                                                                                     destination_pool)
                        logger.info(
                            "[pool={1}][pool={2}]vCenter {0} is migrated from {1} to {2} successfully".format(vc,
                                                                                                              source_pool,
                                                                                                              destination_pool))
                    else:
                        logger.error("[pool={1}][pool={2}] Error in migration of vCenter {0} from {1} to {2}".format(vc,
                                                                                                                     source_pool,
                                                                                                                     destination_pool))
                        raise RestError(500, "Error in migration of vCenter {0}".format(vc))
                else:
                    logger.error("[pool={0}][pool={1}]Failed to find source or destination pool".format(source_pool,
                                                                                                        destination_pool))
                    raise RestError(400, "Failed to find source or destination pool")

        except Exception as e:
            logger.exception(e)
            raise e


admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)
