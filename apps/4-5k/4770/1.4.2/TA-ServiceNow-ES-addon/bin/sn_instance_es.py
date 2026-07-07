import sys
import json
import splunk.admin as admin
import splunk.entity as en
import sn_sec_util as snutil
import logging, logging.handlers

'''
As described in the wiki, using the handleList and handleEdit methods to store and test
instance settings
'''

ARGS = ['realm', 'password', 'proxy_password']

class ConfigApp(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    def setup(self):
        for arg in ARGS:
            self.supportedArgs.addOptArg(arg)
        
                

    def handleList(self, confInfo):
       
        confDict = self.readConf("sn_sec_instance_es")
        if confDict is not None:
            for stanza, settings in confDict.items():
                snPwd, prxPwd = snutil.getCredentials(self.getSessionKey(), stanza)
                for key, val in settings.items():
                    if val in [None, '']:
                        val = ''
                        if key == "password":
                            val = snPwd
                        elif key == "proxy_password":
                            val = prxPwd
                    confInfo[stanza].append(key, val)
                    

    '''
    After user clicks Save on setup screen, take updated parameters, normalize them, and 
    save them - save passwords to special location
    '''
    def handleCreate(self, confInfo):
        
        try:
            for arg in ARGS:
                if self.callerArgs.data[arg][0] in [None, '']:
                    self.callerArgs.data[arg][0] = ''
            realm = self.callerArgs.data['realm'][0]
            snutil.setCredentials(self.getSessionKey(), realm, self.callerArgs.data['password'][0], self.callerArgs.data['proxy_password'][0])
            
        except Exception as excpt:
            logging.error("Error in edit: {}".format(excpt))

            
# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)

