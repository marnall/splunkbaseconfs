__author__ = 'strong'

import splunk.admin as admin
import target_manager as tm
import splunklib.client as client
import util

logger = util.getLogger()

class BaseHandler(admin.MConfigHandler):

    def setup(self):
        logger.debug('setup')
        self.capabilityRead = "edit_input_defaults"
        self.capabilityWrite = "edit_input_defaults"

    def _get_target_service(self, target, target_app=None, target_owner=None):
        logger.info('get target service %s' % target)
        target_manager = tm.TargetManager(app=self.appName, owner=self.userName, session_key=self.getSessionKey())
        target_properties = target_manager.get_target(target)
        if target_app:
            target_properties['app'] = target_app
        if target_owner:
            target_properties['owner'] = target_owner
        if target_properties:
            logger.info('target service props %s' % target_properties)
            service = client.Service(**target_properties)
            # TODO: anyway to cache the session key?
            if not target == target_manager.local_splunk_host:
                service = service.login()
                logger.info('login %s ! %s' % (service.host, service.token))
            return service
        else:
            raise admin.ArgValidationException("target %s does not exist" % target)

    def _get_ta_target_service(self, target):
        """
        return service stub that under Splunk_TA_aws context
        :param target: target Splunk instance
        :return: service stub
        """
        return self._get_target_service(target, target_app=tm.TARGET_APP, target_owner=tm.TARGET_OWNER)

