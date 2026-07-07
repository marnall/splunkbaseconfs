__author__ = 'strong'

import splunk.admin as admin
import target_manager as tm
import util as util

logger = util.getLogger()

class TargetsHandler(admin.MConfigHandler):
    def setup(self):
        logger.debug('setup')
        self.capabilityRead = "edit_input_defaults"
        self.capabilityWrite = "edit_input_defaults"
        if self.requestedAction in [admin.ACTION_CREATE, admin.ACTION_EDIT]:
            for key in tm.TARGET_PROPERTIES:
                self.supportedArgs.addReqArg(key)

    def handleList(self, confInfo):
        """
        @api {get} /saas-snow/splunk_app_servicenow_targets list Splunk connection
        @apiName list-targets
        @apiGroup Targets
        @apiSuccess {Atom.Entry} entry target Splunk connection
        """
        self._logRequest()
        targets = self._get_target_manager().list_targets()
        logger.info("list targets %s" % targets)
        for (key, entry) in targets:
            d = confInfo[key]
            for (k, v) in entry.iteritems():
                d.append(k, v)
        return

    def handleCreate(self, confInfo):
        return self.handleEdit(confInfo)

    def handleEdit(self, confInfo):
        """
        @api {post} /saas-snow/splunk_app_servicenow_targets create Splunk connection
        @apiName create-target
        @apiGroup Targets
        @apiParam name Splunk host name
        @apiParam port Splunk management port
        @apiParam scheme Splunkd scheme
        @apiParam username Splunkd username
        @apiParam password Splunkd password
        @apiSuccess {Atom.Entry} entry created Splunk connection
        """
        self._logRequest()
        # TODO: test whether the target server has aws add-on install
        self._get_target_manager().add_target(self.callerArgs.id, util.flattenArgs(self.callerArgs))
        return

    def handleRemove(self, confInfo):
        """
        @api {delete} /saas-snow/splunk_app_servicenow_targets/:name remove a Splunk connection
        @apiName delete-target
        @apiGroup Targets
        """
        self._logRequest()
        self._get_target_manager().remove_target(self.callerArgs.id)
        return

    def _get_target_manager(self):
        return tm.TargetManager(app=self.appName, owner=self.userName, session_key=self.getSessionKey())

    def _logRequest(self):
        logger.info('action %s name %s args %s' % (self.requestedAction, self.callerArgs.id, self.callerArgs))

admin.init(TargetsHandler, admin.CONTEXT_APP_ONLY)