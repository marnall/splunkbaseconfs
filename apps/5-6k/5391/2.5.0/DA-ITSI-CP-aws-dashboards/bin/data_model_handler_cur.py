import os
import sys
try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
    sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'DA-ITSI-CP-aws-dashboards', 'lib']))
except ImportError:
    sys.path.insert(0, os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'DA-ITSI-CP-aws-dashboards', 'lib'))
import splunk.admin as admin
import cp_aws_bin.utils.app_util as util
import splunklib.client as client

from cp_aws_bin.utils.local_manager import LocalServiceManager
from data_model.data_model import update_description

logger = util.get_logger()

ARG_TAGS = 'tags'
DEFAULT_APP_NAME = 'DA-ITSI-CP-aws-dashboards'
DEFAULT_OWNER = 'nobody'
DATAMODEL_REST = 'datamodel/model'


"""
@api {post} /saas-aws/da_itsi_cp_aws_data_model_cur update datamodel schema
@apiGroup data model
@apiName update-datamodel
@apiParam {string} tags list of tags
@apiSuccess (201) {Atom.Entry} entry nothing
"""

class DataModelHandler(admin.MConfigHandler):
    def __init__(self, scriptMode, ctxInfo):
        admin.MConfigHandler.__init__(self, scriptMode, ctxInfo)
        self._service = LocalServiceManager(DEFAULT_APP_NAME, DEFAULT_OWNER, self.getSessionKey()).get_local_service()
        self._collection = client.Collection(self._service, DATAMODEL_REST)
        self.shouldAutoList = False

        
    def setup(self):
        for arg in [ARG_TAGS]:
            self.supportedArgs.addReqArg(arg)


    def handleCreate(self, confInfo):
        tags = self.callerArgs[ARG_TAGS][0]
        tags = tags.split('|') if tags else []

        models = self._collection.list(search='name=Detailed_Billing_CUR OR name=Instance_Hour_CUR')

        for model in models:
            description = update_description(model.content.description, tags)
            model.update(**{'description': description})

        return

admin.init(DataModelHandler, admin.CONTEXT_APP_ONLY)