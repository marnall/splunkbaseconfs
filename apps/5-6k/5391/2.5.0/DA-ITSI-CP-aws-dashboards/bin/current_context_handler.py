__author__ = 'frank'

import os
import sys
try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
    sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'DA-ITSI-CP-aws-dashboards', 'lib']))
except ImportError:
    sys.path.insert(0, os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'DA-ITSI-CP-aws-dashboards', 'lib'))

import splunk.admin as admin
import cp_aws_bin.utils.app_util as util
from splunklib.client import Entity
from cp_aws_bin.utils.local_manager import LocalServiceManager


class CurrentContextHandler(admin.MConfigHandler):
    def setup(self):
        pass

    def handleList(self, confInfo):
        session_key = self.getSessionKey()
        service = LocalServiceManager(app=util.APP_NAME, session_key=session_key).get_local_service()

        current_context = Entity(service, 'authentication/current-context')

        roles = current_context.content['roles']
        capabilities = current_context.content['capabilities']

        confInfo['current_context'].append('roles', roles)
        confInfo['current_context'].append('capabilities', capabilities)
        confInfo['current_context'].append('username', current_context.content['username'])
        confInfo['current_context'].append('is_admin', 'admin_all_objects' in capabilities or 'admin' in roles)
        # Change 1 instead of util.is_swc_admin function call(admin role removed in cp) 
        confInfo['current_context'].append('is_aws_admin', "1")

        return


admin.init(CurrentContextHandler, admin.CONTEXT_APP_ONLY)