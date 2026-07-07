# Copyright 2020 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import splunk.admin as admin
import splunk.appbuilder as appbuilder
import logging
import splunk.appserver.mrsparkle.lib.util as util
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


#def get_splunkd_endpoint():
 #   if os.environ.get("SPLUNKD_URI"):
 #       return os.environ["SPLUNKD_URI"]
 #   else:
  #      splunkd_uri = get_splunkd_uri()
 #       os.environ["SPLUNKD_URI"] = splunkd_uri
 #       return splunkd_uri


_APPNAME = 'TA-trellix-epo-saas-connector'


def setup_logger(level):
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('splunk.appserver.%s.controllers.trellix_saas_apply_tag' % _APPNAME)
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(
        make_splunkhome_path(['var', 'log', 'splunk', 'trellix_SaaS_api_invoker.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


logger = setup_logger(logging.DEBUG)


class TrellixSaaSAPIInvoker(admin.MConfigHandler):

    # Leave it for setting REST model
    endpoint = None

    # action parameter for getting clear credentials
    ACTION_CRED = "--cred--"
    handledActions = [admin.ACTION_LIST, admin.ACTION_CREATE, admin.ACTION_EDIT]

    def __init__(self, *args, **kwargs):
        # use classic inheritance to be compatible for
        # old version of Splunk private SDK
        #print("*** Arguments === inside Init ***")
        logger.debug("*** Arguments === inside Init ***")
        admin.MConfigHandler.__init__(self, *args, **kwargs)
        self.payload = self._convert_payload()
        logger.debug("*** Request payload  === "+ str(self.payload))


    def setup(self):
        """
        Must be implemented by the derived class.  Defines arguments and validation
        info.  Called before the handle*() functions.
        Should:
          - inspect self.requestedAction.
          - populate self.supportedArgs via addReqArg() and addOptarg().
          - set pipelineName and processorName if appropriate.
        """
        # Throw if requestedAction is incorrect
        # What is supportedArgs?
        # What are pipelineName and ProcessorName?
        logger.debug("*** Arguments === inside Setup ***")
        if self.requestedAction not in self.handledActions:            
            raise admin.BadActionException(
                "This handler does not support this action (%d)." % self.requestedAction)
        if self.requestedAction == admin.ACTION_CREATE:
            for arg in self.requiredArgs:
                self.supportedArgs.addReqArg(arg)
            for arg in self.optionalArgs:
                self.supportedArgs.addOptArg(arg)

        """if self.requestedAction == admin.ACTION_EDIT:
           for arg in self.optionalArgs:
                self.supportedArgs.addOptArg(field.name)"""        

    def handleCreate(self, confInfo):
        """Called when user invokes the "create" action."""
        logger.debug("*** Arguments === inside the Hnadle Create ***")
        
        self.actionNotImplemented()

    def handleEdit(self, confInfo):
        """Called when user invokes the "edit" action."""
        logger.debug("*** Arguments === inside the Hnadle Edit ***")
        self.actionNotImplemented()

    def handleList(self, confInfo):
        logger.debug("*** Arguments ===" + str( self.supportedArgs.args)) 
        logger.debug("*** Arguments === inside the Hnadle List ***")       
        """Called when user invokes the "list" action."""
        for template in appbuilder.getTemplates():
            confInfo[template].append('text', 'Hello world!')

    def handleMembers(self, confInfo):
        """Called when user invokes the "members" action."""
        logger.debug("*** Arguments === inside the Hnadle Member ***")
        self.actionNotImplemented()

    def handleReload(self, confInfo):
        """Called when user invokes the "reload" action."""
        logger.debug("*** Arguments === inside the Hnadle Reload ***")
        self.actionNotImplemented()

    def handleRemove(self, confInfo):
        """Called when user invokes the "remove" action."""
        logger.debug("*** Arguments === inside the Hnadle Remove ***")
        self.actionNotImplemented()

    def handleCustom(self, confInfo):
        """
        Called when user invokes a custom action.  Implementer can find out which
        action is requested by checking self.customAction and self.requestedAction.
        The former is a string, the latter an action type (create/edit/delete/etc).
        """
        logger.debug("*** Arguments === inside the Hnadle Custom ***")
        self.actionNotImplemented()

    def _convert_payload(self):
        check_actions = (admin.ACTION_CREATE, admin.ACTION_EDIT)
        if self.requestedAction not in check_actions:
            return None

        payload = {}
        for filed, value in self.callerArgs.data.items():
            payload[filed] = value[0] if value and value[0] else ""
        return payload
    
    def validate(self):
        return True


# initialize the handler
admin.init(TrellixSaaSAPIInvoker, admin.CONTEXT_APP_AND_USER)