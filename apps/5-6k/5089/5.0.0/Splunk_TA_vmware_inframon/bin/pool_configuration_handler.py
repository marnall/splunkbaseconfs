# splunk sdk imports
import splunk.admin as admin
import splunk
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

# importing core python packages
import json
from httplib2 import ServerNotFoundError
from collections import defaultdict
import datetime
import re
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
from ta_vmware_inframon.models import PoolStanza, TAVMwareCollectionStanza, TemplateStanza

# defining constants here
logger = setup_logger(log_name="pool_configuration.log",
                      logger_name="pool_configuration")
local_host_path = splunk.mergeHostPath()
file_path = make_splunkhome_path(['etc', 'apps', 'Splunk_TA_vmware_inframon', 'bin', 'pool_default_properties.json'])
GLOBAL_POOL_NAME = "Global pool"
atomic_tasks = ['hostinv', 'vminv']

REQUIRED_ARGS_CREATE = ['description', 'collection_parameter']
OPT_ARGS_CREATE = ['host_ui_fields', 'vm_ui_fields', 'datastore_ui_fields', 'cluster_ui_fields']
REQUIRED_ARGS_EDIT = ['description', 'pool', 'collection_parameter']
OPT_ARGS_EDIT = ['host_ui_fields', 'vm_ui_fields', 'datastore_ui_fields', 'cluster_ui_fields']
REQUIRED_ARGS_LIST = ['get_only_poolname']


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
        This is used for adding optional and required arguments for particular requests."""
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in REQUIRED_ARGS_EDIT:
                self.supportedArgs.addReqArg(arg)

            for arg in OPT_ARGS_EDIT:
                self.supportedArgs.addOptArg(arg)

        if self.requestedAction == admin.ACTION_CREATE:
            for arg in REQUIRED_ARGS_CREATE:
                self.supportedArgs.addReqArg(arg)

            for arg in OPT_ARGS_CREATE:
                self.supportedArgs.addOptArg(arg)

        if self.requestedAction == admin.ACTION_LIST:
            for arg in REQUIRED_ARGS_LIST:
                self.supportedArgs.addReqArg(arg)

    def handleRemove(self, conf_info):
        """When DELETE request with the target is done on pool_configuration endpoint, this method is called.
        It expects the name of to be deleted. """
        try:
            pool_name = self.callerArgs.id
            local_session_key = self.getSessionKey()

            if pool_name == GLOBAL_POOL_NAME:
                logger.error("[pool={0}]Pool:{0} cannot be deleted.".format(GLOBAL_POOL_NAME))
                raise RestError(400, "Pool:{0} cannot be deleted.".format(GLOBAL_POOL_NAME))

            pool_stanza = PoolStanza.from_name(pool_name, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                               session_key=local_session_key)
            if pool_stanza:
                # getting all the dcn and vcenter stanzas to arrange then pool wise.
                vc_stanzas = TAVMwareCollectionStanza.all(sessionKey=local_session_key)
                dcn_stanzas = HydraNodeStanza.all(sessionKey=local_session_key)

                failed_dcn_deletion = list()
                failed_vcenter_deletion = list()

                for stanza in vc_stanzas:
                    if stanza.pool_name == pool_name:
                        vc_path = stanza.target[0]
                        logger.info("Deleting vCenter :{0}".format(vc_path))
                        _ = ru.delete_vcenter_forwarder_stanza(vc_path, local_session_key, pool_name, logger)
                        try:
                            _ = ru.delete_vcenter_stanza(vc_path, local_session_key, logger)
                        except:
                            failed_vcenter_deletion.append(vc_path)

                for stanza in dcn_stanzas:
                    if stanza.pool_name == pool_name:
                        node_path = stanza.host
                        logger.info("Deleting Data Collection Node: {0}".format(node_path))
                        try:
                            _ = ru.delete_dcn_stanza(node_path, local_session_key, logger)
                        except:
                            failed_dcn_deletion.append(node_path)

                deletion_failed_message = ""

                if len(failed_dcn_deletion) > 0:
                    logger.error(
                        "[pool={1}]Failed to delete these DCNs :{0} from pool: {1} ".format(
                            failed_dcn_deletion, pool_name))
                    deletion_failed_message = "{0}message: {1} ".format(deletion_failed_message,
                                                                        "Failed to delete these DCNs :{0} from pool: {1} ".format(
                                                                            failed_dcn_deletion, pool_name))

                if len(failed_vcenter_deletion) > 0:
                    logger.error(
                        "[pool={1}]Failed to delete these vCenters:{0} from pool: {1} ".format(
                            failed_vcenter_deletion, pool_name))
                    deletion_failed_message = "{0}message: {1} ".format(deletion_failed_message,
                                                                        "Failed to delete these vCenters:{0} from pool: {1} ".format(
                                                                            failed_vcenter_deletion, pool_name))
                if deletion_failed_message:
                    raise RestError(500, deletion_failed_message)

                # Deleting template stanza of current pool.
                _ = ru.delete_template_stanza(pool_name, local_session_key, logger)

                if pool_stanza.passive_delete():
                    conf_info['data']['status'] = 200
                    conf_info['data']['message'] = "Pool Stanza is deleted successfully"

                    pool_name_encoded = quote_plus(pool_name)
                    path = local_host_path.rstrip(
                        "/") + "/servicesNS/nobody/Splunk_TA_vmware_inframon/data/inputs/ta_vmware_collection_scheduler_inframon/" + pool_name_encoded
                    try:
                        ru.splunk_rest_request(path, logger, local_session_key=local_session_key,
                                               session_key=local_session_key,
                                               method="DELETE", raise_all_errors=True)
                        logger.info("[pool={0}]input successfully deleted for pool= {0}".format(pool_name))
                    except ServerNotFoundError:
                        logger.exception("[pool={1}]Could not reach node={0}, could not delete pool input={1}".format(
                            local_host_path, pool_name))
                    except Exception:
                        logger.exception("[pool={0}]Problem deleting pool input={0}".format(pool_name))
                else:
                    logger.error("[pool={0}]Failed to delete the pool stanza={0}".format(pool_name))
                    raise RestError(500, "Failed to delete the pool stanza={0}".format(pool_name))

            else:
                logger.error("Failed to find the pool stanza={0}, cannot delete it".format(pool_name))
                raise RestError(404, "Failed to find the pool stanza={0}".format(pool_name))

        except Exception as e:
            logger.exception(e)
            raise e

    def handleCreate(self, conf_info):
        """When POST request is done with the first parameter as 'name' on pool_configuration endpoint
        this method is called. All the required parameters for this method is settled up in setup() method."""
        try:
            args = self.callerArgs
            pool_name = self.callerArgs.id
            local_session_key = self.getSessionKey()

            pool_stanza = PoolStanza.from_name(pool_name, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                               session_key=local_session_key)

            if not pool_stanza:
                description = args.get("description", False)
                host_ui_fields = args.get("host_ui_fields", [])
                vm_ui_fields = args.get("vm_ui_fields", [])
                datastore_ui_fields = args.get("datastore_ui_fields", [])
                cluster_ui_fields = args.get("cluster_ui_fields", [])

                # preparing backend fields
                with open(file_path) as fp:
                    field_dict = json.load(fp)
                    field_dict = field_dict["additional_fields"]
                    # preparing field lists
                    host_inv_fields = ru.prepare_field_list(field_dict, host_ui_fields, "HostSystem",
                                                                              logger)
                    vm_inv_fields = ru.prepare_field_list(field_dict, vm_ui_fields, "VirtualMachine",
                                                                          logger)
                    cluster_inv_fields = ru.prepare_field_list(field_dict, cluster_ui_fields,
                                                                                    "ClusterComputeResource", logger)
                    datastore_inv_fields = ru.prepare_field_list(field_dict, datastore_ui_fields, "DataStore",
                                                                    logger)

                collection_dict = json.loads(args.get("collection_parameter", [""])[0])

                for task, val in collection_dict.items():
                    try:
                        if int(val["interval"]) < 0:
                            logger.error(
                                "[pool={1}]Could not save configuration, interval value passed for {0} task is not valid.".format(
                                    task, pool_name))
                            raise RestError(400,
                                            "[pool={1}]Could not save configuration, interval value passed for {0} task is not valid.".format(
                                                task, pool_name))

                        if int(val["expiration"]) < 0:
                            logger.error(
                                "[pool={1}]Could not save configuration, expiration value passed for {0} task is not valid.".format(
                                    task, pool_name))
                            raise RestError(400,
                                            "[pool={1}]Could not save configuration, expiration value passed for {0} task is not valid.".format(
                                                task, pool_name))


                    except ValueError:
                        # This is to raise error for non-integer inputs
                        logger.error(
                            "[pool={1}]Could not save configuration, interval or expiration value passed for {0} task is not valid.".format(
                                task, pool_name))
                        raise RestError(400,
                                        "Could not save configuration, interval or expiration value passed for {0} task is not valid.".format(
                                            task))
                    except KeyError:
                        # This is to raise the error for invalid task parameter
                        logger.error(
                            "[pool={1}]Could not save configuration, parameters passed for {0} task is not valid.".format(
                                task, pool_name))
                        raise RestError(400,
                                        "Could not save configuration, parameters passed for {0} task is not valid.".format(
                                            task))
                    except Exception as e:
                        logger.error(format(e))
                        raise e

                pool_name = pool_name.strip()
                validate_pool_name = re.search(r"[\/\]]+", pool_name)
                if len(pool_name) > 0 and validate_pool_name is None:
                    pool_stanza = PoolStanza("Splunk_TA_vmware_inframon", "nobody", pool_name, sessionKey=local_session_key,
                                             host_path=local_host_path)
                    template_stanza = TemplateStanza("Splunk_TA_vmware_inframon", "nobody", pool_name,
                                                     sessionKey=local_session_key,
                                                     host_path=local_host_path)

                    pool_stanza.node_modification_time = datetime.datetime.utcnow()
                    pool_stanza.collection_modification_time = datetime.datetime.utcnow()

                    # in future, template_name will contain the name of the template which uis applied on a pool.
                    pool_stanza.template_name = pool_name
                    if description:
                        pool_stanza.description = description
                    else:
                        logger.info(
                            "No description was passed, so not saving it for pool={0}".format(pool_name))

                    template_stanza.host_inv_fields = host_inv_fields
                    template_stanza.host_ui_fields = host_ui_fields
                    template_stanza.vm_inv_fields = vm_inv_fields
                    template_stanza.vm_ui_fields = vm_ui_fields
                    template_stanza.datastore_inv_fields = datastore_inv_fields
                    template_stanza.datastore_ui_fields = datastore_ui_fields
                    template_stanza.cluster_inv_fields = cluster_inv_fields
                    template_stanza.cluster_ui_fields = cluster_ui_fields

                    task_list = []
                    for task, val in collection_dict.items():
                        task_list.append(task)
                        key = "{0}_{1}".format(task, "interval")
                        setattr(pool_stanza, key, int(val["interval"]))

                        key = "{0}_{1}".format(task, "expiration")
                        setattr(pool_stanza, key, int(val["expiration"]))

                    pool_stanza.task = task_list
                    pool_stanza.atomic_tasks = atomic_tasks

                    path = local_host_path.rstrip(
                        "/") + "/servicesNS/nobody/Splunk_TA_vmware_inframon/configs/conf-inputs"
                    data = {'name': "ta_vmware_collection_scheduler_inframon://" + pool_name, "duration": 15,
                            "log_level": "INFO", "interval": 15, "disabled": 1}

                    try:
                        ru.splunk_rest_request(path, logger, local_session_key=local_session_key,
                                               session_key=local_session_key,
                                               method="POST", raise_all_errors=True, postargs=data)
                        logger.info("[pool={0}]Input for pool: {0} created successfully.".format(pool_name))
                    except ServerNotFoundError:
                        logger.exception("[pool={1}]Could not reach node={0}, could not create pool input={1}".format(
                            local_host_path, pool_name))
                    except Exception:
                        logger.exception("[pool={0}]Problem creating pool input={0}".format(pool_name))
                else:
                    logger.error("Pool name passed is not valid, can't save {0}".format(pool_name))
                    raise RestError(400, "Pool name passed is not valid")

                pool_stanza.atomic_tasks = atomic_tasks

                if pool_stanza.passive_save():
                    logger.info("[pool={0}]Stanza for pool:{0} saved successfully.".format(pool_name))
                    conf_info['data']['pool_status'] = 200
                    conf_info['data']['pool_message'] = "Pool Stanza is saved successfully."
                else:
                    logger.error("[pool={0}]Problem in saving pool stanza={0}".format(pool_name))
                    raise RestError(500, "Problem in saving pool stanza={0}".format(pool_name))

                if template_stanza.passive_save():
                    logger.info("Template stanza for the pool saved successfully.")
                else:
                    logger.error(
                        "[pool={0}]Problem in saving template stanza(Additional field list) for pool={0}".format(
                            pool_name))

            else:
                logger.error("[pool={0}]Pool stanza with name {0} already exists".format(pool_name))
                raise RestError(400, "Pool stanza with name {0} already exists".format(pool_name))
        except Exception as e:
            logger.exception(e)
            raise e

    def handleList(self, conf_info):
        """When GET request is done on the endpoint this method is called,
        It returns the details of all the configured pools in json format."""
        try:
            local_session_key = self.getSessionKey()
            get_only_poolname = self.callerArgs.get("get_only_poolname")[0]

            stanzas = PoolStanza.all(sessionKey=local_session_key)
            stanzas = stanzas.filter_by_app("Splunk_TA_vmware_inframon")
            stanzas._owner = "nobody"

            get_only_poolname = True if get_only_poolname == 'true' else False

            if get_only_poolname:
                pool_list = []
                for stanza in stanzas:
                    pool_list.append(stanza.name)

                conf_info['data']['pool_list'] = json.dumps(pool_list)
            else:
                pool_dict = {}
                for stanza in stanzas:
                    template_stanza = TemplateStanza.from_name(stanza.template_name, "Splunk_TA_vmware_inframon",
                                                               host_path=local_host_path,
                                                               session_key=local_session_key)

                    task_list = stanza.task
                    collection_parameter = {}

                    for task in task_list:
                        key = "{0}_{1}".format(task, "interval")
                        interval = getattr(stanza, key, "")
                        key = "{0}_{1}".format(task, "expiration")
                        expiration = getattr(stanza, key, "")

                        collection_parameter.update({task: {"interval": interval, "expiration": expiration}})

                    pool_dict[stanza.name] = {
                        "collection_modification_time": stanza.collection_modification_time.strftime(
                            "%Y-%m-%dT%H:%M:%S.%f"),
                        "node_modification_time": stanza.node_modification_time.strftime(
                            "%Y-%m-%dT%H:%M:%S.%f"),
                        "description": stanza.description,
                        "host_ui_fields": template_stanza.host_ui_fields,
                        "vm_ui_fields": template_stanza.vm_ui_fields,
                        "cluster_ui_fields": template_stanza.cluster_ui_fields,
                        "datastore_ui_fields": template_stanza.datastore_ui_fields,
                        "collection_parameter": collection_parameter}

                # getting all the dcn and vcenter stanzas to arrange then pool wise.
                vc_stanzas = TAVMwareCollectionStanza.all(sessionKey=local_session_key)
                dcn_stanzas = HydraNodeStanza.all(sessionKey=local_session_key)

                dcn_list_dict = defaultdict(list)
                for stanza in dcn_stanzas:
                    pool_name = stanza.pool_name
                    dcn_list_dict[pool_name].append(stanza.host)

                vcenter_list_dict = defaultdict(list)
                for stanza in vc_stanzas:
                    pool_name = stanza.pool_name
                    vcenter_list_dict[pool_name].append(stanza.target[0])

                for key, val in pool_dict.items():
                    pool_dict[key].update({"dcn_list": dcn_list_dict[key]})
                    pool_dict[key].update({"vcenter_list": vcenter_list_dict[key]})

                conf_info["data"]["pools"] = json.dumps(pool_dict)

        except Exception as e:
            logger.exception(e)
            raise e

    def handleEdit(self, conf_info):
        """when POST request is done with the target on pool_configuration endpoint, this method is called.
        All the required parameters for this method is settled up in setup() method."""
        try:
            args = self.callerArgs
            target_pool = self.callerArgs.id
            pool_name = args.get("pool")[0]
            local_session_key = self.getSessionKey()

            if target_pool == GLOBAL_POOL_NAME and pool_name != GLOBAL_POOL_NAME:
                logger.error("[pool={0}]Pool: {0} cannot be renamed.".format(GLOBAL_POOL_NAME))
                raise RestError(400, "Pool: {0} cannot be renamed.".format(GLOBAL_POOL_NAME))

            pool_stanza = PoolStanza.from_name(target_pool, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                               session_key=local_session_key)

            template_stanza = TemplateStanza.from_name(target_pool, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                                       session_key=local_session_key)
            pool_name_changed = False
            if pool_stanza:
                pool_name = pool_name.strip()
                validate_pool_name = re.search(r"[\/\]]+", pool_name)
                if len(pool_name) > 0 and validate_pool_name is None:

                    description = args.get("description", False)
                    host_ui_fields = args.get("host_ui_fields", [])
                    vm_ui_fields = args.get("vm_ui_fields", [])
                    datastore_ui_fields = args.get("datastore_ui_fields", [])
                    cluster_ui_fields = args.get("cluster_ui_fields", [])

                    # preparing backend fields
                    with open(file_path) as fp:
                        field_dict = json.load(fp)
                        field_dict = field_dict["additional_fields"]

                        host_inv_fields = ru.prepare_field_list(field_dict, host_ui_fields,
                                                                                  "HostSystem", logger)
                        vm_inv_fields = ru.prepare_field_list(field_dict, vm_ui_fields,
                                                                              "VirtualMachine", logger)
                        cluster_inv_fields = ru.prepare_field_list(field_dict, cluster_ui_fields,
                                                                                        "ClusterComputeResource",
                                                                                        logger)
                        datastore_inv_fields = ru.prepare_field_list(field_dict, datastore_ui_fields, "DataStore",
                                                                        logger)

                    collection_dict = json.loads(args.get("collection_parameter", [""])[0])

                    for task, val in collection_dict.items():
                        try:
                            if int(val["interval"]) < 0:
                                logger.error(
                                    "[pool={1}]Could not save configuration, interval value passed for {0} task is not valid.".format(
                                        task, pool_name))
                                raise RestError(400, "Interval value passed to task interval is not valid.")

                            if int(val["expiration"]) < 0:
                                logger.error(
                                    "[pool={1}]Could not save configuration, interval value passed for {0} task is not valid.".format(
                                        task, pool_name))
                                raise RestError(400,
                                                "Could not save configuration, interval value passed for {0} task is not valid.".format(
                                                    task))


                        except ValueError:
                            # This is to raise error for non-integer inputs
                            logger.error(
                                "[pool={1}]Could not save configuration, interval or expiration value passed for {0} task is not valid.".format(
                                    task, pool_name))
                            raise RestError(400,
                                            "Could not save configuration, interval or expiration value passed for {0} task is not valid.".format(
                                                task))
                        except KeyError:
                            # This is to raise the error for invalid task parameter
                            logger.error(
                                "[pool={1}]Could not save configuration, parameters passed for {0} task is not valid.".format(
                                    task, pool_name))
                            raise RestError(400,
                                            "Could not save configuration, parameters passed for {0} task is not valid.".format(
                                                task))
                        except Exception as e:
                            logger.error("Exception occurred:{0}".format(e))
                            raise e

                    if pool_name != target_pool:

                        pool_name_duplicate = PoolStanza.from_name(pool_name, "Splunk_TA_vmware_inframon",
                                                                   host_path=local_host_path,
                                                                   session_key=local_session_key)

                        if not pool_name_duplicate:

                            pool_name_changed = True

                            pool_stanza = PoolStanza("Splunk_TA_vmware_inframon", "nobody", pool_name,
                                                     sessionKey=local_session_key, host_path=local_host_path)

                            template_stanza = TemplateStanza("Splunk_TA_vmware_inframon", "nobody", pool_name,
                                                             sessionKey=local_session_key, host_path=local_host_path)

                            try:
                                pool_name_encoded = quote_plus(target_pool)

                                info_path = local_host_path.rstrip(
                                    "/") + "/servicesNS/nobody/Splunk_TA_vmware_inframon/data/inputs/ta_vmware_collection_scheduler_inframon/" + pool_name_encoded + "?output_mode=json"

                                disabled = True
                                server_response, server_content = ru.splunk_rest_request(info_path, logger,
                                                                                         local_session_key=local_session_key,
                                                                                         session_key=local_session_key)

                                if server_content is not None:
                                    server_content_dict = json.loads(server_content)
                                    disabled = server_content_dict['entry'][0]['content']['disabled']

                                path = local_host_path.rstrip(
                                    "/") + "/servicesNS/nobody/Splunk_TA_vmware_inframon/configs/conf-inputs"

                                data = {'name': "ta_vmware_collection_scheduler_inframon://" + pool_name, "duration": 15,
                                        "log_level": "INFO", "interval": 15,
                                        "disabled": int(disabled)}
                                ru.splunk_rest_request(path, logger, local_session_key=local_session_key,
                                                       session_key=local_session_key, method="POST",
                                                       raise_all_errors=True, postargs=data)
                            except ServerNotFoundError:
                                logger.exception(
                                    "[pool={1}]Could not reach node={0}, could not create pool input={1}".format(
                                        local_host_path, pool_name))
                            except Exception:
                                logger.exception("[pool={0}]Problem creating pool input={0}".format(pool_name))
                        else:
                            logger.error("[pool={0}]Stanza with new pool name {0} already exists".format(pool_name))
                            raise RestError(400, "Stanza with pool name {0} already exists".format(pool_name))

                    if description:
                        pool_stanza.description = description
                    else:
                        logger.info(
                            "No description was passed, so not saving it for pool={0}".format(pool_name))

                    template_stanza.host_inv_fields = host_inv_fields
                    template_stanza.host_ui_fields = host_ui_fields
                    template_stanza.vm_inv_fields = vm_inv_fields
                    template_stanza.vm_ui_fields = vm_ui_fields
                    template_stanza.datastore_inv_fields = datastore_inv_fields
                    template_stanza.datastore_ui_fields = datastore_ui_fields
                    template_stanza.cluster_inv_fields = cluster_inv_fields
                    template_stanza.cluster_ui_fields = cluster_ui_fields

                    pool_stanza.collection_modification_time = datetime.datetime.utcnow()
                    pool_stanza.node_modification_time = datetime.datetime.utcnow()
                    pool_stanza.template_name = pool_name

                    task_list = []
                    for task, val in collection_dict.items():
                        task_list.append(task)
                        key = "{0}_{1}".format(task, "interval")
                        setattr(pool_stanza, key, int(val["interval"]))

                        key = "{0}_{1}".format(task, "expiration")
                        setattr(pool_stanza, key, int(val["expiration"]))

                    pool_stanza.task = task_list

                    pool_stanza.atomic_tasks = atomic_tasks

                    if pool_stanza.passive_save():
                        conf_info['data']['pool_stanza_status'] = 200
                        conf_info['data']['pool_stanza_message'] = "Pool Stanza edited successfully"

                        if pool_name_changed:
                            logger.info(
                                "[pool={0}][pool={1}]Pool name is changed, Moving all DCN and vCenters from pool: {0} to pool: {1}".format(
                                    target_pool, pool_name))
                            # getting all the dcn and vcenter stanzas to arrange then pool wise.
                            vc_stanzas = TAVMwareCollectionStanza.all(sessionKey=local_session_key)
                            dcn_stanzas = HydraNodeStanza.all(sessionKey=local_session_key)

                            if len(vc_stanzas) == 0:
                                logger.info("[pool={0}]pool: {0} have no vcenters.".format(pool_name))

                            if len(dcn_stanzas) == 0:
                                logger.info("[pool={0}]pool: {0} have no DCNs.".format(pool_name))

                            failed_dcn_migration = list()
                            failed_vc_migration = list()

                            for stanza in vc_stanzas:
                                if stanza.pool_name == target_pool:
                                    vc_path = stanza.target[0]
                                    logger.info("Moving vCenter :{0}".format(vc_path))
                                    stanza.pool_name = pool_name
                                    if not stanza.passive_save():
                                        failed_vc_migration.append(vc_path)
                                        logger.error(
                                            "[pool={1}][pool={2}]Failed to migrate vCenter: {0} from source pool: {1} to destination pool: {2}".format(
                                                vc_path, target_pool, pool_name))
                                    else:
                                        logger.info(
                                            "[pool={1}][pool={2}]vCenter :{0} successfully migrated from source pool: {1} to destination pool: {2}".format(
                                                vc_path, target_pool, pool_name))

                            for stanza in dcn_stanzas:
                                if stanza.pool_name == target_pool:
                                    node_path = stanza.host
                                    logger.info("Moving Data Collection Node: {0}".format(node_path))
                                    stanza.pool_name = pool_name
                                    if not stanza.passive_save():
                                        failed_dcn_migration.append(node_path)
                                        logger.error(
                                            "[pool={1}][pool={2}]Failed to migrate Data Collection Node: {0} from source pool:{1} to destination pool:{2}".format(
                                                node_path, target_pool, pool_name))
                                    else:
                                        auth_token = ru.get_node_auth_token(stanza, local_session_key, logger)
                                        ru.clear_session(node_path, auth_token, local_session_key, logger)
                                        logger.info(
                                            "[pool={1}][pool={2}]Node :{0} successfully migrated from source pool: {1} to destination pool: {2}".format(
                                                node_path, target_pool, pool_name))

                            migration_failed_message = ""

                            if len(failed_dcn_migration) > 0:
                                logger.error(
                                    "[pool={1}][pool={2}] Failed to migrate these DCNs :{0} from source pool: {1} to destination pool: {2}".format(
                                        failed_dcn_migration, target_pool, pool_name))
                                migration_failed_message = "{0}message: {1} ".format(migration_failed_message,
                                                                                     "Failed to migrate these DCNs:{0}.".format(
                                                                                         failed_dcn_migration))

                            if len(failed_vc_migration) > 0:
                                logger.error(
                                    "[pool={1}][pool={2}]Failed to migrate these vCenters:{0} from source pool: {1} to destination pool: {2}".format(
                                        failed_vc_migration, target_pool, pool_name))
                                migration_failed_message = "{0}message: {1} ".format(migration_failed_message,
                                                                                     "Failed to migrate these vCenters:{0}.".format(
                                                                                         failed_vc_migration))

                            if migration_failed_message:
                                raise RestError(500, migration_failed_message)

                            _ = ru.delete_template_stanza(target_pool, local_session_key, logger)

                            target_pool_stanza = PoolStanza.from_name(target_pool, "Splunk_TA_vmware_inframon",
                                                                      host_path=local_host_path,
                                                                      session_key=local_session_key)
                            if not target_pool_stanza.passive_delete():
                                logger.warning(
                                    "[pool={0}]Problem in deleting old pool stanza {0}".format(target_pool))
                            else:

                                pool_name_encoded = quote_plus(target_pool)
                                path = local_host_path.rstrip(
                                    "/") + "/servicesNS/nobody/Splunk_TA_vmware_inframon/data/inputs/ta_vmware_collection_scheduler_inframon/" + pool_name_encoded
                                try:
                                    ru.splunk_rest_request(path, logger, local_session_key=local_session_key,
                                                           session_key=local_session_key, method="DELETE",
                                                           raise_all_errors=True)
                                    logger.info(
                                        "[pool={0}]input for pool={0} deleted successfully.".format(target_pool))
                                except ServerNotFoundError:
                                    logger.exception(
                                        "[pool={1}]Could not reach node={0}, could not delete pool input={1}".format(
                                            local_host_path, target_pool))
                                except Exception:
                                    logger.exception(
                                        "[pool={0}]Problem deleting pool input={0}".format(target_pool))

                    else:
                        logger.error("[pool={0}]Problem in saving pool stanza={0}".format(pool_name))
                        raise RestError(500, "Problem in saving pool stanza={0}".format(pool_name))

                    if template_stanza.passive_save():
                        logger.info("[pool={0}]Template stanza(Additional fields) edited successfully for: {0}".format(
                            pool_name))
                    else:
                        logger.error("[pool={0}]Problem in editing template stanza(Additional fields) for: {0}".format(
                            pool_name))

                else:
                    logger.error("[pool={0}]New Pool name {0} is not valid".format(pool_name))
                    raise RestError(400, "New Pool name {0} is not valid".format(pool_name))
            else:
                logger.error("[pool={0}]Pool with name {0} doesn't exist".format(target_pool))
                raise RestError(404, "Pool with name {0} doesn't exist".format(target_pool))

        except Exception as e:
            logger.exception(e)
            raise e


admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)
