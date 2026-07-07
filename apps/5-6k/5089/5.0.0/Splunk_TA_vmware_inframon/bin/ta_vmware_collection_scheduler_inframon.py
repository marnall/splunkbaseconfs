# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
# Core Python Imports
import sys
import re
import time
import datetime
import threading
import json
# Append SA-Hydra-inframon/bin to the Python path

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))

# Import TA-VMware-inframon collection code

from ta_vmware_inframon.models import TAVMwareCollectionStanza, PoolStanza, TemplateStanza
import ta_vmware_inframon.simple_vsphere_utils as vsu
from ta_vmware_hierarchy_agent import main
# Import from SA-Hydra-inframon

from hydra_inframon.hydra_scheduler import HydraScheduler, HydraCollectionManifest, HydraConfigToken
from hydra_inframon.logging_utils import format_log_message
from hydra_inframon.models import SplunkStoredCredential


def _token_identity(token):
    return (
        token.target,
        token.task,
        json.dumps(token.special, sort_keys=True, default=str),
    )


def _merge_existing_tokens(old_token_list, new_token_list):
    """
    Reuse existing tokens when the derived token identity matches so schedule
    state is preserved while metadata is refreshed from the newly built token.
    """
    final_token_list = []
    added_token_list = []
    new_tokens_by_identity = {_token_identity(token): token for token in new_token_list}
    reused_identities = set()

    for old_token in old_token_list:
        matched_token = new_tokens_by_identity.get(_token_identity(old_token))
        if matched_token is None:
            continue

        old_token.metadata = matched_token.metadata
        old_token.metadata_id = matched_token.metadata_id
        old_token.interval = matched_token.interval
        old_token._expiration_period = matched_token._expiration_period
        old_token.atomic = matched_token.atomic

        final_token_list.append(old_token)
        reused_identities.add(_token_identity(matched_token))

    for new_token in new_token_list:
        if _token_identity(new_token) in reused_identities:
            continue
        final_token_list.append(new_token)
        added_token_list.append(new_token)

    return final_token_list, added_token_list

class TAVMwareScheduler(HydraScheduler):
    """
    TA-VMware-inframon implementation of the HydraScheduler. Breaks up collection conf and
    distributes it to all worker nodes.
    Significant overloads:
        establishCollectionManifest - custom break up of perf task by hosts in the vc
    """
    title = "TA-VMware-inframon Collection Scheduler"
    description = "Breaks up the TA-VMware-inframon collection into config tokens and distributes jobs to all worker nodes. Should only have 1 of these active at a time."
    collection_model = TAVMwareCollectionStanza
    app = "Splunk_TA_vmware_inframon"
    collection_conf_name = "inframon_ta_vmware_collection.conf"
    worker_input_name = "ta_vmware_collection_worker_inframon"

    def getPassword(self, realm, user):
        """
        This method pulls the clear password from storage/passwords for a
        particular realm and user. This wraps the util method for logging purposes.
        args:
            realm - the realm associated with the stored credential
            user - the user name associated with the stored credential

        RETURNS the clear string of the password, None if not found
        """
        #note we are relying on splunk's internal automagical session_key storage
        password = SplunkStoredCredential.get_password(realm, user, app=self.app, host_path=self.local_server_uri, session_key=self.local_session_key)
        if password is None:
            self.logger.warning("Could not find a stored credential for realm={0} and user={1}, returning None".format(realm, user))
            return None
        else:
            return password

    def checkvCenterConnectivity(self, rewrite=False):
        """
        Check vCenter connectivity status and update it into conf file
        """
        #Get collection conf information
        collects = self.collection_model.all(host_path=self.local_server_uri, sessionKey=self.local_session_key)
        collects._owner = "nobody"
        collects = collects.filter_by_app(self.app)
        for collect in collects:
            if self.pool_name == collect.pool_name:
                username = collect.username
                for target in collect.target:
                    password = self.getPassword(target, username)
                    try:
                        #Set up the connection
                        vss = vsu.vSphereService(target, username, password)
                        if(vss.logout()) :
                            self.logger.debug("User={0} successfully logout from {1}".format(username, target))
                        else :
                            self.logger.warn("User={0} failed to logout from {1}".format(username, target))
                        if not collect.credential_validation:
                            collect.credential_validation = True
                            if not collect.passive_save():
                                self.logger.error("Failed to save collection stanza=%s while updating credential validation", str(collect))
                            else:
                                self.setConfModificationTime("collection")
                                self.logger.info("Updating the conf modification time property for vc=%s", str(target))
                    except (vsu.ConnectionFailure, vsu.LoginFailure) as e:
                        self.logger.error("Could not connect to target=%s", target)
                        self.logger.exception(e)
                        if collect.credential_validation or rewrite:
                            collect.credential_validation = False
                            if not collect.passive_save():
                                self.logger.error("Failed to save collection stanza=%s while updating credential validation", str(collect))
                            else:
                                self.setConfModificationTime("collection")
                                self.logger.info("Updating the conf modification time property for vc=%s", str(target))

    def updateTargetDictStatus(self, target_info_dict):
        """
        Get the target info dict and update the status of target like target connectivity checked time and
        target host list prepared time.
        """
        target_info_dict["is_timediff_lt_4hr"] = True
        if (time.time() - target_info_dict["target_status_checkedtime"] >= 1800):
            target_info_dict["target_status_checkedtime"] = time.time()
            self.logger.info("Rechecking vCenter connectivity as 30 minutes elapsed.")
            self.checkvCenterConnectivity()

        if (time.time() - target_info_dict["target_hostlist_updatedtime"] >= 14400):
            target_info_dict["is_timediff_lt_4hr"] = False
            target_info_dict["target_hostlist_updatedtime"] = time.time()
            self.logger.info("Re-establishing collection manifest to get updated host list as conf file has not been modified since last 4 hours.")

    def getConfModificationTime(self):

        try:
            pool_stanza = PoolStanza.from_name(self.pool_name, "Splunk_TA_vmware_inframon", host_path=self.local_server_uri,
                                                    session_key=self.local_session_key)
            node_modification_time = pool_stanza.node_modification_time
            collection_modification_time = pool_stanza.collection_modification_time
        except Exception as e:
            self.logger.error("Couldn't read the node_modification_time and collection_modification_time properties of the pool=%s", self.pool_name)
            self.logger.exception(e)
            return None, None

        return node_modification_time, collection_modification_time

    def setConfModificationTime(self, entity_type):
        try:
            pool_stanza = PoolStanza.from_name(self.pool_name, "Splunk_TA_vmware_inframon", host_path=self.local_server_uri, session_key=self.local_session_key)
            if entity_type == "node":
                pool_stanza.node_modification_time = datetime.datetime.utcnow()
            elif entity_type == "collection":
                pool_stanza.collection_modification_time = datetime.datetime.utcnow()
            else:
                self.logger.error("Unrecognized Conf Parameter in setConfModificationTime")
            if not pool_stanza.passive_save():
                self.logger.error("Couldn't save the conf modification time property for type: %s of the pool: %s", entity_type, self.pool_name)
        except Exception as e:
            self.logger.error("Couldn't set the conf modification time property for type: %s of the pool: %s", entity_type, self.pool_name)

    def distributeHierarchy(self):
        """
        Call Hierarchy agent script for current pool to prepare host-vm list and distribute it among the nodes
        """
        thread_obj = threading.Thread(target=main, name=self.pool_name, args=(self.local_server_uri, self.local_session_key, [self.pool_name], ))
        thread_obj.start()

    def establishCollectionManifest(self, calculate_auto_offset = False, total_heads = 0, is_timediff_lt_4hr = True, old_token_list=[]):
        """
        Get the information from the collection conf then break it up into
        atomic tasks and place them in the collection manifest

        return HydraCollectionManifest with entire contents of collect conf file
        """
        self.logger.info(
            format_log_message(
                "Scheduler is building collection manifest from configured vCenter collection stanzas",
                {
                    "event": "scheduler.manifest.build",
                    "status": "start",
                    "component": "scheduler",
                    "pool": self.pool_name,
                    "calculate_auto_offset": calculate_auto_offset,
                    "total_heads": total_heads,
                    "refresh_with_recent_host_cache": is_timediff_lt_4hr,
                    "existing_token_count": len(old_token_list),
                },
            )
        )

        #Get collection conf information
        collects = self.collection_model.all(host_path=self.local_server_uri, sessionKey=self.local_session_key)
        collects._owner = "nobody"
        collects = collects.filter_by_app(self.app)
        pool_stanza = PoolStanza.from_name(self.pool_name, "Splunk_TA_vmware_inframon", host_path=self.local_server_uri,
                                                    session_key=self.local_session_key)

        template_stanza = TemplateStanza.from_name(pool_stanza.template_name, "Splunk_TA_vmware_inframon", host_path=self.local_server_uri,
                                                        session_key=self.local_session_key)

        metadata_dict = {}
        collect_list = []
        new_token_list = []
        final_token_list = []
        added_token_list = []
        for collect in collects:
            if self.pool_name == collect.pool_name:
                self.logger.info(
                    format_log_message(
                        "Scheduler is processing collection stanza",
                        {
                            "event": "scheduler.manifest.build",
                            "status": "processing",
                            "component": "scheduler",
                            "pool": self.pool_name,
                            "stanza": collect.name,
                            "target_type": collect.target_type,
                        },
                    )
                )
                if is_timediff_lt_4hr and not collect.credential_validation:
                    self.logger.warning(
                        format_log_message(
                            "Scheduler skipped collection stanza because credential validation is failing",
                            {
                                "event": "scheduler.manifest.build",
                                "status": "skipped",
                                "reason": "credential_validation_failed",
                                "component": "scheduler",
                                "pool": self.pool_name,
                                "stanza": collect.name,
                                "target_type": collect.target_type,
                            },
                        )
                    )
                    continue
                config = {}
                username = collect.username
                for field in collect.model_fields:
                    #forgive me this but models don't implement a get item function so we have to do this
                    config[field] = getattr(collect, field)
                for field in pool_stanza.model_fields:
                    if field not in ['description', 'template_name', 'collection_modification_time', 'node_modification_time']:
                        config[field] = getattr(pool_stanza, field)
                for field in template_stanza.model_fields:
                    if not field.endswith('ui_fields'):
                        # TODO: Remove this sorting and deduplication for the inframon_ta_vmware_template.conf fields, once we have Fields' configuration page in the build
                        config[field] = sorted(set(getattr(template_stanza, field)))

                self.logger.debug(
                    format_log_message(
                        "Scheduler parsed collection stanza into merged metadata",
                        {
                            "event": "scheduler.manifest.build",
                            "status": "parsed",
                            "component": "scheduler",
                            "pool": self.pool_name,
                            "stanza": collect.name,
                            "field_count": len(config),
                            "target_count": len(collect.target) if collect.target is not None else 0,
                            "task_count": len(pool_stanza.task) if pool_stanza.task is not None else 0,
                        },
                    )
                )
                metadata_id = "metadata_" + collect.name
                collect_list.append(collect.name)
                metadata_dict[metadata_id] = config
                for target in collect.target:
                    for task in pool_stanza.task:
                        special = {}
                        if task == "hostvmperf":
                            #if vcenter, we need to break up the task by the number of hosts
                            if collect.target_type == "vc":
                                #Set up the connection
                                password = self.getPassword(target, username)
                                try:
                                    vss = vsu.vSphereService(target, username, password)
                                    host_token_count = 0
                                    if (collect.managed_host_excludelist is not None) and (collect.managed_host_excludelist != "None"):
                                        exclude_re_search = re.compile(collect.managed_host_excludelist, flags=re.S).search
                                    else:
                                        #fake re search method, always doesn't match
                                        def exclude_re_search(s): return None
                                    if (collect.managed_host_includelist is not None) and (collect.managed_host_includelist != "None"):
                                        include_re_search = re.compile(collect.managed_host_includelist, flags=re.S).search
                                    else:
                                        #fake re search method, always matches (sorta, really just always returns true instead of None match object but whatevs)
                                        def include_re_search(s): return True
                                    #Pull the host list from the vc, note this does mean that adding/removing hosts from a vc implies a
                                    #required restart of the collector, or at least a conf reread.
                                    for host in vss.get_host_list():
                                        host_name = host["name"]
                                        if exclude_re_search(host_name) or (include_re_search(host_name) is None):
                                            self.logger.debug("ignoring host=%s while parsing vc=%s into host specific task due to managed host includelist/excludelist", host_name, target)
                                        else:
                                            special = {}
                                            special["perf_target_hosts"] = [host["moid"]]
                                            special["perf_collection_type"] = task
                                            self.logger.debug(
                                                format_log_message(
                                                    "Scheduler derived host-scoped hostvmperf token",
                                                    {
                                                        "event": "scheduler.manifest.build",
                                                        "status": "derived_host_token",
                                                        "component": "scheduler",
                                                        "pool": self.pool_name,
                                                        "stanza": collect.name,
                                                        "target": target,
                                                        "task": task,
                                                        "perf_target_hosts": special["perf_target_hosts"],
                                                    },
                                                )
                                            )
                                            new_token_list.append(HydraConfigToken(target, username, task, metadata_id, self.logger, metadata=config, special=special))
                                            host_token_count += 1
                                    self.logger.debug(
                                        format_log_message(
                                            "Scheduler expanded vCenter hostvmperf task into host-scoped tokens",
                                            {
                                                "event": "scheduler.manifest.build",
                                                "status": "expanded_hosts",
                                                "component": "scheduler",
                                                "pool": self.pool_name,
                                                "stanza": collect.name,
                                                "target": target,
                                                "task": task,
                                                "derived_token_count": host_token_count,
                                            },
                                        )
                                    )
                                    if not collect.credential_validation:
                                        collect.credential_validation = True
                                        if not collect.passive_save():
                                            self.logger.error("Failed to save collection stanza=%s", str(collect))
                                        else:
                                            self.setConfModificationTime("collection")
                                            self.logger.info("Updating the conf modification time property for vc=%s", str(target))

                                    #logout
                                    if(vss.logout()) :
                                        self.logger.debug("User={0} successfully logout from {1}".format(username, target))
                                    else :
                                        self.logger.warn("User={0} failed to logout from {1}".format(username, target))
                                except vsu.ConnectionFailure as e:
                                    self.logger.exception(
                                        format_log_message(
                                            "Scheduler could not connect to vCenter while deriving hostvmperf tokens",
                                            {
                                                "event": "scheduler.manifest.build",
                                                "status": "fail",
                                                "reason": "vcenter_connection_failed",
                                                "component": "scheduler",
                                                "pool": self.pool_name,
                                                "stanza": collect.name,
                                                "target": target,
                                                "task": task,
                                            },
                                        )
                                    )
                                    collect.credential_validation = False
                                    if not collect.passive_save():
                                        self.logger.error("Failed to save collection stanza=%s as failing on credential validation", str(collect))
                                    else:
                                        self.setConfModificationTime("collection")
                                        self.logger.info("Updating the conf modification time property for vc=%s", str(target))
                                except vsu.LoginFailure as e:
                                    self.logger.exception(
                                        format_log_message(
                                            "Scheduler could not authenticate to vCenter while deriving hostvmperf tokens",
                                            {
                                                "event": "scheduler.manifest.build",
                                                "status": "fail",
                                                "reason": "vcenter_login_failed",
                                                "component": "scheduler",
                                                "pool": self.pool_name,
                                                "stanza": collect.name,
                                                "target": target,
                                                "task": task,
                                                "username": username,
                                            },
                                        )
                                    )
                                    collect.credential_validation = False
                                    if not collect.passive_save():
                                        self.logger.error("Failed to save collection stanza=%s as failing on credential validation", str(collect))
                                    else:
                                        self.setConfModificationTime("collection")
                                        self.logger.info("Updating the conf modification time property for vc=%s", str(target))
                            elif collect.target_type == "unmanaged":
                                special["perf_target_hosts"] = ["ha-host"]
                                special["perf_collection_type"] = task
                                self.logger.debug("parsing unmanaged=%s task into single hostvmperf task with perf_target_hosts=%s", target, special["perf_target_hosts"])
                                new_token_list.append(HydraConfigToken(target, username, task, metadata_id, self.logger, metadata=config, special=special))
                            else:
                                special["perf_target_hosts"] = []
                                special["perf_collection_type"] = task
                                self.logger.debug("parsing target_type unknown=%s task into single hostvmperf task with perf_target_hosts=%s", target, special["perf_target_hosts"])
                                new_token_list.append(HydraConfigToken(target, username, task, metadata_id, self.logger, metadata=config, special=special))
                        elif task == "clusterperf" or task == "vcperf" or task == "datastoreperf":
                            special["perf_target_hosts"] = []
                            special["perf_collection_type"] = task
                            new_token_list.append(HydraConfigToken(target, username, task, metadata_id, self.logger, metadata=config, special=special))
                        else:
                            new_token_list.append(HydraConfigToken(target, username, task, metadata_id, self.logger, metadata=config, special={}))

        final_token_list, added_token_list = _merge_existing_tokens(old_token_list, new_token_list)

        self.logger.debug(
            format_log_message(
                "Scheduler finished deriving config tokens for collection manifest",
                {
                    "event": "scheduler.manifest.build",
                    "status": "derived_tokens",
                    "component": "scheduler",
                    "pool": self.pool_name,
                    "metadata_count": len(metadata_dict),
                    "collection_count": len(collect_list),
                    "new_token_count": len(new_token_list),
                    "reused_token_count": len(final_token_list) - len(added_token_list),
                    "added_token_count": len(added_token_list),
                },
            )
        )

        # calculate auto offset
        if calculate_auto_offset:
            self.getConfigTokenOffsets(added_token_list, total_heads, schedular_execution_time=15, head_dist_bucketsize=2)

        #Distribute Metadata to all nodes
        self.metadata_dict = metadata_dict
        manifest = HydraCollectionManifest(self.logger, metadata_dict, final_token_list, self.app, collect_list)
        self.logger.info(
            format_log_message(
                "Scheduler built collection manifest",
                {
                    "event": "scheduler.manifest.build",
                    "status": "success",
                    "component": "scheduler",
                    "pool": self.pool_name,
                    "metadata_count": len(metadata_dict),
                    "collection_count": len(collect_list),
                    "token_count": len(final_token_list),
                    "added_token_count": len(added_token_list),
                },
            )
        )
        return manifest

if __name__ == '__main__':
    scheduler = TAVMwareScheduler()
    scheduler.execute()
    sys.exit(0)
