import splunk.admin as admin
import splunk
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

# importing core python packages
from httplib2 import ServerNotFoundError
import datetime
try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus

# importing rest_utility
from rest_utility import setup_logger, RestError
import rest_utility as ru

# TA and SA imports
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'Splunk_TA_vmware_inframon', 'bin']))
from hydra_inframon.models import HydraNodeStanza
from ta_vmware_inframon.models import PoolStanza, TAVMwareCollectionStanza

# defining constants here
logger = setup_logger(log_name="pool_configuration.log",
                      logger_name="pool_configuration")
local_host_path = splunk.mergeHostPath()
GLOBAL_POOL_NAME = "Global pool"

REQUIRED_ARGS_REMOVE = ['destination_pool']


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
            This is used for adding optional and required arguments for particular requests."""
        if self.requestedAction == admin.ACTION_REMOVE:
            for arg in REQUIRED_ARGS_REMOVE:
                self.supportedArgs.addReqArg(arg)

    def handleRemove(self, conf_info):
        """When DELETE request is done on the endpoint migrate_and_Delete, this method is called,
            It deletes the pool given as target(source pool) and migrate its DCNs and vCenters to destination pool"""
        try:
            source_pool = self.callerArgs.id
            local_session_key = self.getSessionKey()
            args = self.callerArgs

            destination_pool = args.get("destination_pool")[0]

            if source_pool == destination_pool:
                logger.error("[pool={0}]source pool and destination pool cannot be the same.".format(source_pool))
                raise RestError(400, "Source pool and destination pool cannot be the same.")

            if source_pool == GLOBAL_POOL_NAME:
                logger.error("[pool={0}]Pool:{0} cannot be deleted.".format(GLOBAL_POOL_NAME))
                raise RestError(400, "Pool:{0} cannot be deleted.".format(GLOBAL_POOL_NAME))

            source_pool_stanza = PoolStanza.from_name(source_pool, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                                      session_key=local_session_key)

            destination_pool_stanza = PoolStanza.from_name(destination_pool, "Splunk_TA_vmware_inframon",
                                                           host_path=local_host_path,
                                                           session_key=local_session_key)

            if not source_pool_stanza or not destination_pool_stanza:
                logger.error("Source pool or Destination pool does not exist. cannot complete the operation")
                raise RestError(400, "Source pool or Destination pool does not exist. cannot complete the operation")

            # getting all the dcn and vcenter stanzas to arrange then pool wise.
            vc_stanzas = TAVMwareCollectionStanza.all(sessionKey=local_session_key)
            dcn_stanzas = HydraNodeStanza.all(sessionKey=local_session_key)

            failed_dcn_migration = list()
            failed_vc_migration = list()

            for stanza in vc_stanzas:
                if stanza.pool_name == source_pool:
                    vc_path = stanza.target[0]
                    logger.info("Moving vCenter :{0}".format(vc_path))
                    stanza.pool_name = destination_pool
                    if not stanza.passive_save():
                        failed_vc_migration.append(vc_path)
                        logger.error(
                            "[pool={1}][pool={2}]Failed to migrate vCenter {0} from {1} to {2} ".format(vc_path,
                                                                                                        source_pool,
                                                                                                        destination_pool))
                    else:
                        destination_pool_stanza.collection_modification_time = datetime.datetime.utcnow()
                        logger.info(
                            "[pool={1}][pool={2}]vCenter :{0} successfully migrated from source pool: {1} to destination pool: {2}".format(
                                vc_path, source_pool, destination_pool))

            for stanza in dcn_stanzas:
                if stanza.pool_name == source_pool:
                    node_path = stanza.host
                    logger.info("Moving Data Collection Node: {0}".format(node_path))
                    stanza.pool_name = destination_pool
                    if not stanza.passive_save():
                        failed_dcn_migration.append(node_path)
                        logger.error(
                            "[pool={1}][pool={2}]Failed to migrate DCN {0} from: {1} to: {2}".format(node_path,
                                                                                                     source_pool,
                                                                                                     destination_pool))
                    else:
                        # TODO: clear cache
                        auth_token = ru.get_node_auth_token(stanza, local_session_key, logger)
                        ru.clear_session(node_path, auth_token, local_session_key, logger)

                        destination_pool_stanza.node_modification_time = datetime.datetime.utcnow()
                        logger.info(
                            "[pool={1}][pool={2}]Node :{0} successfully migrated from source pool: {1} to destination pool: {2}".format(
                                node_path, source_pool, destination_pool))

            migration_failed_message = ""

            if len(failed_dcn_migration) > 0:
                logger.error(
                    "[pool={1}][pool={2}]Failed to migrate these DCNs :{0} from source pool: {1} to destination pool: {2}".format(
                        failed_dcn_migration, source_pool, destination_pool))
                migration_failed_message = "{0}message: {1} ".format(migration_failed_message,
                                                                     "Failed to migrate these DCNs:{0},"
                                                                     " migration can not be performed.".format(
                                                                         failed_dcn_migration))

            if len(failed_vc_migration) > 0:
                logger.error(
                    "[pool={1}][pool={2}]Failed to migrate these vCenters:{0} from source pool: {1} to destination pool: {2}".format(
                        failed_vc_migration, source_pool, destination_pool))
                migration_failed_message = "{0}message: {1} ".format(migration_failed_message,
                                                                     "Failed to migrate these vCenters:{0}, "
                                                                     "migration can not be performed.".format(
                                                                         failed_vc_migration))

            if migration_failed_message:
                raise RestError(500, migration_failed_message)

            _ = ru.delete_template_stanza(source_pool, local_session_key, logger)

            if source_pool_stanza.passive_delete():

                pool_name_encoded = quote_plus(source_pool)
                path = local_host_path.rstrip(
                    "/") + "/servicesNS/nobody/Splunk_TA_vmware_inframon/data/inputs/ta_vmware_collection_scheduler_inframon/" + pool_name_encoded

                try:
                    ru.splunk_rest_request(path, logger, local_session_key=local_session_key,
                                           session_key=local_session_key,
                                           method="DELETE", raise_all_errors=True)
                    logger.info("[pool={0}]input successfully deleted for pool= {0}".format(source_pool))
                    conf_info["pool"]["status"] = "200"
                    conf_info["pool"]["message"] = "Pool successfully deleted."
                except ServerNotFoundError:
                    conf_info["pool"]["status"] = "500"
                    conf_info["pool"]["message"] = "Pool successfully deleted but Failed to delete pool input."
                    logger.exception(
                        "[pool={1}]Could not reach node={0}, could not delete pool input={1}".format(local_host_path,
                                                                                                     source_pool))
                except Exception as e:
                    conf_info["pool"]["status"] = "500"
                    conf_info["pool"]["message"] = "Pool successfully deleted but Failed to delete pool input."
                    logger.exception("[pool={0}]Problem deleting pool input={0} Exception: {1}".format(source_pool, e))

            else:
                logger.error("[pool={0}]Failed to delete source pool: {0}".format(source_pool))
                conf_info["pool"]["status"] = "500"
                conf_info["pool"]["message"] = "Failed to delete source pool: {0}".format(source_pool)

            if destination_pool_stanza.passive_save():
                logger.info("[pool={0}]Destination Pool: {0} updated.".format(destination_pool))
            else:
                logger.error("[pool={0}]Failed to update Destination Pool: {0}".format(destination_pool))

        except Exception as e:
            logger.exception(e)
            raise e


admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)
