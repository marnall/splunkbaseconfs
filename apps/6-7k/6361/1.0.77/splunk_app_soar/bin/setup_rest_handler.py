# Copyright (C) 2023-2024 Splunk Inc. All Rights Reserved.

from copy import deepcopy
import os
import sys
import json
import time
from traceback import format_exc

import splunk
import splunk.rest
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.bundle_paths import make_splunkhome_path
from configparser import ConfigParser

APP_HOME_DIR = make_splunkhome_path(["etc", "apps", "splunk_app_soar", "bin"])

sys.path.insert(0, APP_HOME_DIR)

from soar_utils import (
    rest_helper,
    setup_logging
)

CLUSTER_INDEXES_CONF = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'master-apps', '_cluster', 'local', 'indexes.conf')
SPLUNK_CMD = os.path.join(os.environ['SPLUNK_HOME'], 'bin', 'splunk')

INDEXES = [
    'phantom_container',
    'phantom_artifact',
    'phantom_action_run',
    'phantom_app_run',
    'phantom_playbook',
    'phantom_custom_function',
    'phantom_decided_list',
    'phantom_container_comment',
    'phantom_container_attachment',
    'phantom_asset',
    'phantom_app',
    'phantom_note',
    'phantom_playbook_run',
    'phantom_system_insights',
    'splunk_app_soar', # for SOAR System Logs
    'os' # for SOAR System Logs
]

APP_NAME = 'splunk_app_soar'
INDEXES_RELOAD_ENDPOINT = '/services/data/indexes/_reload'
STANDALONE_INDEXES_ENDPOINT = f'/servicesNS/nobody/{APP_NAME}/data/indexes'
STANDALONE_POST_INDEXES_ENDPOINT = f'/servicesNS/nobody/{APP_NAME}/configs/conf-indexes'
CLUSTER_CONFIG_ENDPOINT = '/services/cluster/config'
IS_CLUSTER_MASTER_ENDPOINT = '/services/cluster/master/info'
SERVER_ROLES_ENDPOINT = '/services/server/info'
GET_INDEXES_SPLUNK_SEARCH = '| rest servicesNS/nobody/splunk_app_soar/data/indexes | search title IN (phantom_*, splunk_app_soar, os) | fields title'

PUSH_BUNDLE_ENDPOINT = '/services/cluster/manager/control/default/apply'
CHECK_ROLES_ENDPOINT = '/services/authentication/current-context'
DISTRIBUTED_CONFIG_ENDPOINT = '/services/search/distributed/config'

# Cloud Classic/Noah
CLOUD_INDEXES_ENDPOINT = '/services/cluster_blaster_indexes/sh_indexes_manager'

class SoarSetup(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        self.log = setup_logging("soar_setup.log", "create_indexes")
        self.session_key = None
        self.path_info = None
        self.environment = None
        self.instanceType = "enterprise"
        self.cloudClassicNoahIndexes = []
        PersistentServerConnectionApplication.__init__(self)
    
    # -d name=<index_name>
    # if distributed, additionally include: -d coldPath="\$SPLUNK_DB/<index_name>/colddb" -d homePath="\$SPLUNK_DB/<index_name>/db" -d thawedPath="\$SPLUNK_DB/<index_name>/thaweddb"
    # def create_indexes(config, environment):
    #     pass

    def get_environment_mode(self):
        self.log.info("Checking environment mode...")
        mode = None
        roles = None
        try:
            # get mode
            response, contents = rest_helper(self, 'GET', CLUSTER_CONFIG_ENDPOINT)
            if response.status == 200 and contents.get('entry'):
                entry = contents.get('entry')
                entry_length = len(entry)
                if entry_length > 0:
                    mode = entry[0].get('content', {}).get('mode')
        except Exception:
            pass

        try:
            # get role of instance: search_head, indexer, cluster_master, cluster_manager
            response, contents = rest_helper(self, 'GET', SERVER_ROLES_ENDPOINT)
            if response.status == 200 and contents.get('entry'):
                content = contents.get('entry')[0].get('content', {})
                roles = content.get('server_roles')
                instance_type = content.get('instance_type')
                if instance_type:
                    self.instanceType = instance_type
                self.log.debug(f"Instance roles: {roles}")
                self.log.debug(f"Instance type: {instance_type}")
        except splunk.AuthorizationFailed as e:
            self.log.error(format_exc())
            return 404, f"Authorization Error while talking to Splunk [GET][{SERVER_ROLES_ENDPOINT}]: {e}"
        except Exception as e:
            self.log.error(f"ERROR: {e}")
            return 404, f"Error: could not retrieve cluster config. {e}"

        try:
            # check if endpoint exists - only exists for cloud classic and noah clusters
            self.get_cloud_classic_noah_indexes()
            mode = 'cloud_classic_noah'
        except Exception:
            pass

        self.log.debug(f"Mode is: {mode}")
        # scenarios on SH
        if mode is None:
            return 200, 'standalone'
        elif mode == 'cloud_classic_noah':
            return 200, 'cloud_classic_noah'
        elif mode == 'disabled':
            if 'cluster_master' in roles:
                return 200, 'distributed_cluster_master'
            elif 'search_head' in roles:
                return 200, 'distributed_search_head'
            elif 'indexer' in roles and 'search_peer' in roles:
                return 200, 'distributed_indexer'
            elif 'shc_deployer' in roles:
                return 200, 'deployer'
            else:
                return 200, 'standalone'
        else:
            return 200, 'cluster'

    def is_master(self):
        response, contents = rest_helper(self, 'GET', IS_CLUSTER_MASTER_ENDPOINT)
        return response.status == 200

    def get_cloud_classic_noah_indexes(self):
        current_indexes = list()
        payload = {'search': 'name=phantom_* OR os OR splunk_app_soar'}
        response, contents = rest_helper(self, 'GET', CLOUD_INDEXES_ENDPOINT, payload)
        entries = contents.get('entry', [])
        if response.status == 200 and entries:
            for index in entries:
                name = index.get('name')
                if 'phantom_' in name or name == "os" or name == "splunk_app_soar":
                    current_indexes.append(name)
        # self.log.info(f"current indexes: {current_indexes}")
        self.cloudClassicNoahIndexes = current_indexes

    def get_cluster_indexes(self):
        indexes_config = ConfigParser()
        if os.path.isfile(CLUSTER_INDEXES_CONF):
            indexes_config.read(CLUSTER_INDEXES_CONF)
            all_indexes = indexes_config.sections()
            current_indexes = list()
            for index in all_indexes:
                if 'phantom_' in index or index == "os" or index == "splunk_app_soar":
                    current_indexes.append(index)
        else:
            current_indexes = list()
        return current_indexes

    def get_standalone_indexes(self):
        current_indexes = list()
        try: 
            response, contents = rest_helper(self, 'GET', INDEXES_RELOAD_ENDPOINT, {})
        except Exception as e:
            self.log.error(f"Error reloading indexes: {e}")

        try:
            payload = {'summarize': True, 'count': 0, 'search': 'phantom_'}
            response, contents = rest_helper(self, 'GET', STANDALONE_INDEXES_ENDPOINT, payload)
            for item in contents.get('entry'):
                current_indexes.append(item.get('name'))
        except Exception as e:
            self.log.error(f"Error retrieving current indexes: {e}")

        try:
            payload = {'summarize': True, 'count': 0, 'search': 'name=os'}
            response, contents = rest_helper(self, 'GET', STANDALONE_INDEXES_ENDPOINT, payload)
            for item in contents.get('entry'):
                current_indexes.append(item.get('name'))
        except Exception as e:
            self.log.error(f"Error retrieving current indexes: {e}")
        
        try:
            payload = {'summarize': True, 'count': 0, 'search': 'name=splunk_app_soar'}
            response, contents = rest_helper(self, 'GET', STANDALONE_INDEXES_ENDPOINT, payload)
            for item in contents.get('entry'):
                current_indexes.append(item.get('name'))
        except Exception as e:
            self.log.error(f"Error retrieving current indexes: {e}")

        self.log.info(f"Current indexes: {current_indexes}")
        return current_indexes

    def get_current_indexes(self):
        if self.environment == 'standalone' or self.environment == 'distributed_indexer':
            return self.get_standalone_indexes()
        elif self.environment == 'cloud_classic_noah':
            # return self.get_cloud_classic_noah_indexes()
            return self.cloudClassicNoahIndexes
        else:
            if self.is_master():
                return self.get_cluster_indexes()
            return None

    def create_indexes_cloud_classic_noah(self, current_indexes):
        self.log.info("Creating indexes in Cloud...")
        new_indexes = list()
        tmpINDEXES = deepcopy(INDEXES)
        while len(tmpINDEXES) > 0:
            if tmpINDEXES[0] in current_indexes:
                tmpINDEXES.pop(0)
            else:
                payload = {
                    "name": tmpINDEXES[0],
                    "maxTotalDataSizeMB": 500,
                    "frozenTimePeriodInSecs": 30000,
                    "maxGlobalRawDataSizeMB": 6000
                }
                response, contents_json = rest_helper(
                    self, "POST", CLOUD_INDEXES_ENDPOINT, payload
                )
                self.log.debug(f"Adding {tmpINDEXES[0]}: {response.status}. If this is not 201, will try again...")
                if int(response.status) in [201, 200]:
                    new_indexes.append(tmpINDEXES[0])
                    tmpINDEXES.pop(0)
                else:
                    time.sleep(30)
        self.log.info(f"Indexes added: {len(new_indexes)}")
        if len(new_indexes) > 0:
            if response.status in [201, 200]:
                return True, 200, "Indexes pushed", new_indexes
            else:
                return False, response.status, "Error pushing indexes", new_indexes
        else:
            return True, 200, "No new indexes added", new_indexes

    def create_indexes(self):
        current_indexes = self.get_current_indexes()
        new_indexes = list()
        self.log.info(f"Current indexes: {current_indexes}")
        if current_indexes is None:
            return False, 403, "Failed to get current indexes."

        indexes_added = False
        # If standalone or distributed indexer, you can POST directly on same search head
        if self.environment in ['standalone', 'distributed_indexer']:
            # append indexes to indexes.conf "/servicesNS/nobody/splunk_app_soar/configs/conf-indexes"
            # Check the current indexes

            for item in INDEXES:
                if item not in current_indexes:
                    try:
                        indexes_added = True
                        payload = {
                            "name": item,
                            "homePath": f"$SPLUNK_DB/{item}/db",
                            "coldPath": f"$SPLUNK_DB/{item}/colddb",
                            "thawedPath": f"$SPLUNK_DB/{item}/thaweddb",
                            "disabled": 0
                        }
                        response, contents_json = rest_helper(
                            self, "POST", STANDALONE_POST_INDEXES_ENDPOINT, payload
                        )
                        new_indexes.append(item)
                    except Exception as e:
                        return False, response.status, "Error saving '{}'".format(item)
            if indexes_added:
                return True, 200, "New indexes added", new_indexes
            else:
                return True, 200, "No new indexes added", new_indexes
        else: # is cluster
            # on cluster master
            if self.environment == 'cloud_classic_noah':
                return self.create_indexes_cloud_classic_noah(current_indexes)
            else:
                indexes_config = ConfigParser()
                indexes_config.optionxform=str
                for item in INDEXES:
                    if item not in current_indexes:
                        indexes_added = True
                        indexes_config.add_section(item)
                        indexes_config[item]['repFactor'] = 'auto'
                        indexes_config[item]['homePath'] = f'$SPLUNK_DB/{item}/db'
                        indexes_config[item]['coldPath'] = f'$SPLUNK_DB/{item}/colddb'
                        indexes_config[item]['thawedPath'] = f'$SPLUNK_DB/{item}/thaweddb'
                        indexes_config[item]['thawedPath'] = f'$SPLUNK_DB/{item}/thaweddb'
                        new_indexes.append(item)

                if indexes_added:
                    with open(CLUSTER_INDEXES_CONF, 'a') as indexes_conf:
                        indexes_config.write(indexes_conf)

                    response, contents_json = rest_helper(
                        self, "POST", PUSH_BUNDLE_ENDPOINT, {}
                    )
                    if response.status == 200:
                        return True, 200, "Cluster bundle application successful", new_indexes
                    else:
                        return False, response.status, "Cluster bundle application failed", new_indexes
                else:
                    return True, 200, "No new indexes added", new_indexes
        # If distributed, check that you are on master node
        # If distributed, get current _cluster indexes
        # If distributed, add phantom_indexes
        # If distributed, copy indexes back to _cluster/local
        # If distributed, apply bundle

    def get_current_environment(self):
        self.log.info("Checking environment details...")
        # Check if standalone, distributed index, or cluster index
        status, res = self.get_environment_mode()

        if status == 200:
            self.environment = res
            self.log.info(f"Environment mode is: {self.environment}")
        return status == 200, status, res

    def handle_post(self):
        self.log.info(f"Checking if setup is needed. Currently on {self.environment}")
        if not self.is_master() and self.environment in ['cluster', 'deployer'] and self.instanceType == 'enterprise':
            return {"error": "You are not on the cluster manager. This REST call can only be run from the cluster manager.", "status": 403}
        if self.environment.startswith('distributed') and self.environment != 'distributed_indexer' and self.instanceType == 'enterprise':
            return {"error": "You are not on an indexer. This REST call can only be run from an indexer.", "status": 403}
        success, status_code, msg, new_indexes = self.create_indexes()
        if success:
            return {"message": f"POST successful. {msg}", "status": status_code, "new_indexes": new_indexes}
        else:
            return {"error": f"{msg}. Note: Make sure you are running setup from a user with admin privileges.", "status": status_code, "new_indexes": new_indexes}
    
    def handle_get(self):
        self.log.info("Get current phantom indexes")
        if self.environment.startswith('distributed') and self.environment != 'distributed_indexer':
            return {"error": "You are not on an indexer. This REST call can only be run from an indexer.", "status": 403}
        current_indexes = self.get_current_indexes()
        if current_indexes is None:
            return {"error": "You are not on the cluster manager. This REST call can only be run from the cluster manager.", "status": 403}
        return {"message": "GET successful", "content": current_indexes, "status": 200}

    def handle(self, args):
        request = json.loads(args)
        method = request["method"]
        self.session_key = request["session"]["authtoken"]
        self.path_info = request.get("path_info")

        success, status_code, res = self.get_current_environment()
        if success == False:
            contents = {"error": res, "status": status_code }
        else:
            self.log.debug(f"in handle: method is {method}")
            if method == "POST":
                contents = self.handle_post()
            elif method == "GET":
                contents = self.handle_get()
            else:
                contents = {"error": "Invalid or missing arguments", "status": 404}

        status = contents.get("status")
        return json.dumps({"payload": contents, "status": status})