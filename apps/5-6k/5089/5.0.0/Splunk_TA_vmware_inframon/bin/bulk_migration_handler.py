# splunk sdk imports
import splunk.admin as admin
import splunk
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

# importing core python packages
from collections import defaultdict
import datetime

# importing rest_utility
from rest_utility import setup_logger, RestError
import rest_utility as ru

# stanza imports
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'Splunk_TA_vmware_inframon', 'bin']))

from ta_vmware_inframon.models import PoolStanza, TAVMwareCollectionStanza
from hydra_inframon.models import HydraNodeStanza

# defining constants
local_host_path = splunk.mergeHostPath()
logger = setup_logger(log_name="pool_configuration.log",
                      logger_name="pool_configuration")

REQUIRED_ARGS_EDIT = ['destination_pool']
OPT_ARGS_EDIT = ['dcn_list', 'vcenter_list']


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
        This is used for adding optional and required arguments for particular requests."""
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in REQUIRED_ARGS_EDIT:
                self.supportedArgs.addReqArg(arg)

            for arg in OPT_ARGS_EDIT:
                self.supportedArgs.addOptArg(arg)

    def handleEdit(self, conf_info):
        """When POST request is done on the endpoint bulk_migration, this method is called,
         It migrates given DCNs and vCenters from source pool to the destination pool"""
        try:
            args = self.callerArgs
            local_session_key = self.getSessionKey()
            vc_list = args.get("vcenter_list", [])
            dcn_list = args.get("dcn_list", [])
            destination_pool = args.get("destination_pool")[0]

            if destination_pool == [None]:
                logger.error("Destination pool name can not be empty.")
                raise RestError(400, "Destination pool name can not be empty.")

            destination_pool_stanza = PoolStanza.from_name(destination_pool, "Splunk_TA_vmware_inframon",
                                                           host_path=local_host_path,
                                                           session_key=local_session_key)

            if not destination_pool_stanza:
                logger.error("Failed to find destination pool")
                raise RestError(400, "Failed to find destination pool")

            source_pool_dict = defaultdict(
                lambda: {"node_modification_time": False, "collection_modification_time": False})

            failed_dcn_migration = list()
            failed_vc_migration = list()

            for vc in vc_list:
                vc_stanza = TAVMwareCollectionStanza.from_name(vc, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                                               session_key=local_session_key)

                if not vc_stanza:
                    logger.error("Requested vCenter {0} doesn't exists".format(vc))
                    failed_vc_migration.append(vc)
                else:
                    source_pool_name = vc_stanza.pool_name
                    vc_stanza.pool_name = destination_pool
                    if source_pool_name == destination_pool:
                        logger.info(
                            "source pool and destination pool is same, not migrating vc:{0}".format(vc))
                        continue
                    if vc_stanza.passive_save():
                        source_pool_dict[source_pool_name].update(
                            {"collection_modification_time": datetime.datetime.utcnow()})
                        destination_pool_stanza.collection_modification_time = datetime.datetime.utcnow()
                        logger.info(
                            "[pool={1}][pool={2}]vCenter: {0} is migrated from {1} to {2} successfully".format(vc,
                                                                                                               source_pool_name,
                                                                                                               destination_pool))
                    else:
                        failed_vc_migration.append(vc)
                        logger.error("[pool={1}][pool={2}]Failed to migrate vCenter {0} from {1} to {2} ".format(vc,
                                                                                                                 source_pool_name,
                                                                                                                 destination_pool))

            if len(failed_vc_migration) > 0:
                conf_info["vcenter_migration"]["status"] = "500"
                conf_info["vcenter_migration"]["message"] = "Failed to migrate these vCenters:{0}".format(
                    failed_vc_migration)
                logger.error("[pool={1}]Failed to migrate these vCenters:{0} to the pool: {1}".format(
                    failed_vc_migration, destination_pool))
            elif len(vc_list) > 0:
                conf_info["vcenter_migration"]["status"] = "200"
                conf_info["vcenter_migration"][
                    "message"] = "All the vCenters migrated successfully to the pool: {0}".format(
                    destination_pool)
                logger.info("[pool={0}]All the vCenters migrated successfully to the pool: {0}".format(
                    destination_pool))
            else:
                logger.info("No vcenters passed to migrate.")

            for node in dcn_list:
                node_stanza = HydraNodeStanza.from_name(node, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                                        session_key=local_session_key)

                if not node_stanza:
                    failed_dcn_migration.append(node)
                    logger.error("Requested DCN {0} doesn't exists".format(node))
                else:
                    source_pool_name = node_stanza.pool_name
                    node_stanza.pool_name = destination_pool

                    if source_pool_name == destination_pool:
                        logger.info("source pool and destination pool is same, not migrating DCN:{0}".format(node))
                        continue

                    if node_stanza.passive_save():
                        # TODO: clear cache
                        auth_token = ru.get_node_auth_token(node_stanza, local_session_key, logger)
                        ru.clear_session(node, auth_token, local_session_key, logger)
                        source_pool_dict[source_pool_name].update(
                            {"node_modification_time": datetime.datetime.utcnow()})
                        destination_pool_stanza.node_modification_time = datetime.datetime.utcnow()
                        logger.info(
                            "[pool={1}][pool={2}]DCN: {0} is successfully migrated from: {1} to: {2}".format(node,
                                                                                                             source_pool_name,
                                                                                                             destination_pool))
                    else:
                        failed_dcn_migration.append(node)
                        logger.error("[pool={1}][pool={2}]Failed to migrate DCN {0} from: {1} to: {2}".format(node,
                                                                                                              source_pool_name,
                                                                                                              destination_pool))

            if len(failed_dcn_migration) > 0:
                conf_info["dcn_migration"]["status"] = "500"
                conf_info["dcn_migration"]["message"] = "Failed to migrate these DCNs:{0}".format(
                    failed_dcn_migration)
                logger.error("[pool={1}]Failed to migrate these DCNs:{0} to the pool: {1}".format(
                    failed_dcn_migration, destination_pool))
            elif len(dcn_list) > 0:
                conf_info["dcn_migration"]["status"] = "200"
                conf_info["dcn_migration"][
                    "message"] = "All the DCNs migrated successfully to the pool: {0}".format(
                    destination_pool)
                logger.info("[pool={0}]All the DCNs migrated successfully to the pool: {0}".format(
                    destination_pool))
            else:
                logger.info("No DCNs passed to migrate.")

            for pool_name, modification_time in source_pool_dict.items():
                pool_stanza = PoolStanza.from_name(pool_name, "Splunk_TA_vmware_inframon",
                                                   host_path=local_host_path,
                                                   session_key=local_session_key)
                if not pool_stanza:
                    logger.error("Failed to find pool: {0}".format(pool_name))
                    continue

                if modification_time["node_modification_time"]:
                    logger.info("updating node_modification_time:{0} for pool: {1}.".format(
                        modification_time["node_modification_time"], pool_name))
                    pool_stanza.node_modification_time = modification_time["node_modification_time"]
                    if pool_stanza.passive_save():
                        logger.info(
                            "[pool={0}]node modification time successfully updated for pool:{0}".format(pool_name))
                    else:
                        logger.error("[pool={0}]Failed to update node modification time for pool:{0}".format(pool_name))

                if modification_time["collection_modification_time"]:
                    logger.info("updating collection_modification_time: {0} for pool: {1}.".format(
                        modification_time["collection_modification_time"], pool_name))
                    pool_stanza.collection_modification_time = modification_time["collection_modification_time"]
                    if pool_stanza.passive_save():
                        logger.info("[pool={0}]collection modification time successfully updated for pool: {0}".format(
                            pool_name))
                    else:
                        logger.error(
                            "[pool={0}]Failed to update collection modification time for pool: {0}".format(pool_name))

            if destination_pool_stanza.passive_save():
                logger.info("[pool={0}]Destination Pool successfully updated: {0}".format(destination_pool))
                conf_info["pool"]["status"] = "200"
                conf_info["pool"]["message"] = "Pool successfully updated."
            else:
                logger.info("[pool={0}]Failed to update Destination Pool: {0}".format(destination_pool))
                conf_info["pool"]["status"] = "500"
                conf_info["pool"]["message"] = "Failed to update the Pool."

        except Exception as e:
            logger.exception(e)
            raise e


admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)
