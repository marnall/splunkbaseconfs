import sys
import os
import splunk.appbuilder as appbuilder
import splunk.admin as admin
import splunk.entity as en

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger


class ConfigApp(admin.MConfigHandler):
    handledActions = [admin.ACTION_LIST, admin.ACTION_EDIT]

    def setup(self):
        # check if handler is supported by the script
        if self.requestedAction not in self.handledActions:
            raise admin.BadActionException(
                "This handler does not support this action (%d)." % self.requestedAction)
        else:
            if self.requestedAction == admin.ACTION_EDIT:
                for arg in ['host', 'port', 'proxy-enable']:
                    self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        confDict = self.readConf("settings")
        if confDict is not None:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in ['proxy-enable']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    if key in ['host'] and val in [None, '']:
                        val = ''
                    if key in ['port'] and val in [None, '']:
                        val = ''
                    confInfo[stanza].append(key, val)

    '''
    After user clicks Save on setup screen, take updated parameters, normalize them, and 
    save them somewhere
    '''

    def handleEdit(self, confInfo):
        # self.actionNotImplemented()
        # name = self.callerArgs.id
        args = self.callerArgs
        logger = setup_logger()

        if int(args.data['proxy-enable'][0]) == 1:
            args.data['proxy-enable'][0] = '1'

            if args.data['host'][0] in [None, '']:
                args.data['host'][0] = ''
                logger.error("Proxy enabled but host address is not configured for the proxy server")

            if args.data['port'][0] in [None, '']:
                args.data['port'][0] = ''
                logger.error("Proxy enabled but port is not configured for the proxy server")

        else:
            args.data['proxy-enable'][0] = '0'

            if args.data['host'][0] in [None, '']:
                args.data['host'][0] = ''

            if args.data['port'][0] in [None, '']:
                args.data['port'][0] = ''

        '''
        Since we are using a conf file to store parameters, write them to the [setupentity] stanza
        in <appname>/local/myappsetup.conf  
        '''

        self.writeConf('settings', 'proxies', self.callerArgs.data)


# initialize the handler
# admin.init(HelloTemplates, admin.CONTEXT_APP_AND_USER)
admin.init(ConfigApp, admin.CONTEXT_NONE)
