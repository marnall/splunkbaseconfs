# this is a required import
import splunk.rest
import splunk.admin as admin
from splunktalib.common import log

logger = log.Logs('TA-cybersponse').get_logger('cybersponse_setup')


class SetupRestHandler(admin.MConfigHandler):
    cs_args = (
        'address', 'private_key', 'public_key', 'verify_ssl', 'debug', 'tag'
    )

    def setup(self):
        """
        Set up supported arguments
        """
        try:
            if self.requestedAction == admin.ACTION_EDIT:
                for arg in self.cs_args:
                    self.supportedArgs.addOptArg(arg)
        except:
            import traceback
            logger.error("Argument not known in Setup.")
            logger.debug(traceback.format_exc())
            exit(1)

    def handleList(self, confInfo):
        '''
        handleList method: lists configurable parameters in the configuration page
        corresponds to handleractions = list in restmap.conf
        '''
        logger.info("start list")
        confDict = self.readConf("cybersponse")
        if confDict is not None:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in self.cs_args and val is None:
                        val = ''
                    confInfo[stanza].append(key, val)
        logger.info("end list")

    def handleEdit(self, confInfo):
        '''
        handleEdit method: controls the parameters and saves the values
        corresponds to handleractions = edit in restmap.conf

        '''
        logger.info("start edit")
        # Fix Boolean for verify SSL
        if int(self.callerArgs.data['verify_ssl'][0]) == 1:
            self.callerArgs.data['verify_ssl'][0] = '1'
        else:
            self.callerArgs.data['verify_ssl'][0] = '0'

        # Fix Boolean for debug
        if int(self.callerArgs.data['debug'][0]) == 1:
            self.callerArgs.data['debug'][0] = '1'
        else:
            self.callerArgs.data['debug'][0] = '0'

        # Fix Nulls
        for key in self.callerArgs.data.keys():
            if self.callerArgs.data[key][0] == None:
                self.callerArgs.data[key][0] = ''
            # Strip trailing and leading whitespace
            self.callerArgs.data[key][0] = self.callerArgs.data[key][0].strip()
        logger.info("end edit")
        # TODO: Test Connection
        self.writeConf('cybersponse', 'config', self.callerArgs.data)


# initialize the handler
admin.init(SetupRestHandler, admin.CONTEXT_APP_ONLY)
