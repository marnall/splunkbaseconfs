# encoding = utf-8
from __future__ import print_function, absolute_import

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
import splunklib.client as client
from validator import get_host
from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common

class RoleCreator(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        Logger().info("Role creation initiated")
        response = {'payload': {'message': 'Role creation completed'}, 'status': 200}
        try:
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            header = params.get('headers', [])
            host = get_host(header)
            splunkserver = host
            splunkdestapp = "cisco-cloud-security"
            splunkservice = client.connect(host=splunkserver, token=session_token, app=splunkdestapp)

            roles = splunkservice.roles
            new_roles = [
                {'role': 'cs_admin', 'imported_roles': 'user', 'capabilities': ['admin_all_objects', 'accelerate_search', 'cs_admin', 'cs_supervisor', 'cs_user', 'list_accelerate_search', 'list_dist_peer', 'list_search_head_clustering', 'list_search_scheduler', 'list_storage_passwords', 'rest_apps_view', 'rest_properties_get', 'rtsearch', 'run_collect', 'run_mcollect', 'run_msearch', 'schedule_rtsearch', 'schedule_search', 'search']},
                {'role': 'cs_supervisor', 'imported_roles': 'user', 'capabilities': ['accelerate_search', 'cs_supervisor', 'cs_user', 'list_accelerate_search', 'list_dist_peer', 'list_search_head_clustering', 'list_search_scheduler', 'list_storage_passwords', 'rest_apps_view', 'rest_properties_get', 'rtsearch', 'run_collect', 'run_mcollect', 'run_msearch', 'schedule_rtsearch', 'schedule_search', 'search']},
                {'role': 'cs_user', 'imported_roles': 'user', 'capabilities': ['accelerate_search', 'cs_user', 'list_accelerate_search', 'list_dist_peer', 'list_search_head_clustering', 'list_search_scheduler', 'list_storage_passwords', 'rest_apps_view', 'rest_properties_get', 'rtsearch', 'run_collect', 'run_mcollect', 'run_msearch', 'schedule_rtsearch', 'schedule_search', 'search']}
            ]
            for role in new_roles:
                if role['role'] not in roles:
                    created_role = roles.create(role['role'], imported_roles=role['imported_roles'],defaultApp=splunkdestapp)
                    for capability in role['capabilities']:
                        try:
                            created_role.grant(capability)
                            created_role.refresh()
                        except Exception as e:
                            Logger().error("API: role_manager, Exception while assigning capability: {0}".format(str(e)))
                            continue
        except Exception as e:
            Logger().error("API: role_manager, Exception : {0}".format(str(e)))
            response = {'payload': {"message": str(e)}, "status": 500}
        finally:
            Logger().info("Role creation completed")
            return response