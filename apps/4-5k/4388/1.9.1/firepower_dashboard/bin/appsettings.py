import splunk
import splunk.admin as admin
import splunk.entity as en
import os,sys

splunk_home = os.getenv('SPLUNK_HOME')
sys.path.append(splunk_home + '/etc/apps/firepower_dashboard/bin/')

from logger import setup_logging as create_logger
logger = create_logger('firepower_logger', 'firepower.log')

class AppSettings(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for myarg in ['base_url','native_base_url']:
                self.supportedArgs.addOptArg(myarg)

    def handleList(self, confInfo):
        global logger
        confDict = self.readConf("appsetup")
        if None != confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():

                    try:
                        if key in ['base_url','native_base_url'] and val in [None, '']:
                            val = ''
                    except Exception as exp:
                        pass
                    confInfo[stanza].append(key, val)

    def handleEdit(self, confInfo):
        self.writeConf('appsetup', 'app_config', self.callerArgs.data)

admin.init(AppSettings, admin.CONTEXT_NONE)
