import sys
import splunk.admin as admin
import splunk.entity as en
import sn_sec_util as snutil
import logging, logging.handlers

'''
As described in the wiki, using the handleList and handleEdit methods to store and test
instance settings
'''

class ConfigApp(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['url', 'username', 'password', 'proxy_url', 'proxy_port', 'proxy_username', 'proxy_password']:
                self.supportedArgs.addOptArg(arg)
                

    def handleList(self, confInfo):
        confDict = self.readConf("sn_sec_instance")
        snPwd, prxPwd = snutil.getCredentials(self.getSessionKey())
        if confDict is not None:
            for stanza, settings in list(confDict.items()):
                for key, val in list(settings.items()):
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
    def handleEdit(self, confInfo):
        if self.callerArgs.data['url'][0] in [None, '']:
            self.callerArgs.data['url'][0] = ''
        if self.callerArgs.data['username'][0] in [None, '']:
            self.callerArgs.data['username'][0] = ''
        if self.callerArgs.data['proxy_url'][0] in [None, '']:
            self.callerArgs.data['proxy_url'][0] = ''
        if self.callerArgs.data['proxy_port'][0] in [None, '']:
            self.callerArgs.data['proxy_port'][0] = ''
        if self.callerArgs.data['proxy_username'][0] in [None, '']:
            self.callerArgs.data['proxy_username'][0] = ''

        snutil.setCredentials(self.getSessionKey(), self.callerArgs.data['password'][0], self.callerArgs.data['proxy_password'][0])
        self.callerArgs.data['proxy_password'][0] = ''
        self.callerArgs.data['password'][0] = ''
        
        self.writeConf('sn_sec_instance', 'sn_instance', self.callerArgs.data)
            
# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)

