# splunk sdk imports
import splunk.admin as admin
import splunk
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

# importing rest_utility
from rest_utility import setup_logger, RestError
import rest_utility as ru

# hydra imports
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'Splunk_TA_vmware_inframon', 'bin']))
from hydra_inframon.models import HydraNodeStanza
from ta_vmware_inframon.models import PoolStanza

# defining global constants
entity_type = "node"
local_host_path = splunk.mergeHostPath()
logger = setup_logger(log_name="dcn_configuration.log",
                      logger_name="dcn_configuration")

REQUIRED_ARGS_EDIT = ['source_pool', 'destination_pool']


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
        This is used for adding optional and required arguments for particular requests."""
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in REQUIRED_ARGS_EDIT:
                self.supportedArgs.addReqArg(arg)

    def handleEdit(self, conf_info):
        """When POST request is done on the endpoint dcn_migration, this method is called,
        It migrates target DCN from source pool to the destination pool"""
        try:
            args = self.callerArgs
            node = self.callerArgs.id
            local_session_key = self.getSessionKey()

            node_stanza = HydraNodeStanza.from_name(node, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                                    session_key=local_session_key)

            if not node_stanza:
                logger.error("Requested DCN {0} doesn't exists".format(node))
                raise RestError(404, "Requested DCN {0} doesn't exists".format(node))
            else:
                source_pool = args.get("source_pool")[0]
                destination_pool = args.get("destination_pool")[0]

                if source_pool == destination_pool:
                    logger.error("[pool={0}]source pool and destination pool cannot be the same.".format(source_pool))
                    raise RestError(400, "Source pool and destination pool cannot be the same.")

                source_pool_stanza = PoolStanza.from_name(source_pool, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                                          session_key=local_session_key)

                destination_pool_stanza = PoolStanza.from_name(destination_pool, "Splunk_TA_vmware_inframon",
                                                               host_path=local_host_path, session_key=local_session_key)

                if source_pool_stanza and destination_pool_stanza:
                    node_stanza.pool_name = destination_pool

                    if node_stanza.passive_save():
                        ru.set_conf_modification_time(source_pool, entity_type, local_session_key, logger)
                        ru.set_conf_modification_time(destination_pool, entity_type, local_session_key, logger)

                        auth_token = ru.get_node_auth_token(node_stanza, local_session_key, logger)
                        ru.clear_session(node, auth_token, local_session_key, logger)
                        conf_info['data']['status'] = 200
                        conf_info['data']['message'] = "DCN {0} is migrated from {1} to {2} successfully".format(node,
                                                                                                                 source_pool,
                                                                                                                 destination_pool)
                        logger.info("[pool={1}][pool={2}]DCN {0} is migrated from {1} to {2} successfully".format(node,
                                                                                                                  source_pool,
                                                                                                                  destination_pool))
                    else:
                        logger.error("[pool={1}][pool={2}]Error in migration of DCN {0} from {1} to {2}".format(node,
                                                                                                                source_pool,
                                                                                                                destination_pool))
                        raise RestError(500, "Error in migration of DCN {0}".format(node))
                else:
                    logger.error("[pool={0}][pool={1}]Failed to find source or destination pool".format(source_pool,
                                                                                                        destination_pool))
                    raise RestError(400, "Failed to find source or destination pool")

        except Exception as e:
            logger.exception(e)
            raise e


admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)
