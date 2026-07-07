import os,logging
import sys

import splunk
import splunk.admin
import splunk.entity as entity

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
    
#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","twilioalert_app_setuphandler.log")

# Set up a specific logger
logger = logging.getLogger('twilioalert')

#default logging level , can be overidden in stanza config
logger.setLevel(logging.ERROR)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)


class ConfigHandler(splunk.admin.MConfigHandler):

    def setup(self):
        try:
            logger.debug("setup")
            if self.requestedAction == splunk.admin.ACTION_EDIT:              
                for arg in ['param.log_level' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['param.authtoken' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['param.accountsid' ]:
                    self.supportedArgs.addOptArg(arg)
                
        except:  
            e = sys.exc_info()[0]  
            logger.error("Error setting up propertys : %s" % e) 


    def handleList(self, confInfo):

        try:
            
            logger.debug("listing")

            global_entities = entity.getEntities(['admin', 'alert_actions','twilio'], namespace="twilio_alert", owner='nobody', sessionKey=self.getSessionKey())
            
            log_level = ""
            accountsid = ""
            authtoken = ""

            for i, c in global_entities.items():
                if c['eai:acl']['app'] ==  "twilio_alert":
                    log_level = c['param.log_level']
                    accountsid = c['param.accountsid']


            entities = entity.getEntities(['storage', 'passwords'], namespace="twilio_alert", owner='nobody', sessionKey=self.getSessionKey())
            
            for i, c in entities.items():
                if c['eai:acl']['app'] ==  "twilio_alert":
                    username = c['username']
                    if username == accountsid:
                        authtoken = c['clear_password']
        

            confInfo['twilioalert'].append('param.authtoken', authtoken) 
            confInfo['twilioalert'].append('param.accountsid', accountsid) 
            confInfo['twilioalert'].append('param.log_level', log_level) 
            
        except:  
            e = sys.exc_info()[0]  
            logger.error("Error listing propertys : %s" % e) 
        

    def handleEdit(self, confInfo):

        try:
            logger.debug("edit")
            
            if self.callerArgs.data['param.log_level'][0] in [None, '']:
                self.callerArgs.data['param.log_level'][0] = ''

            if self.callerArgs.data['param.authtoken'][0] in [None, '']:
                self.callerArgs.data['param.authtoken'][0] = ''

            if self.callerArgs.data['param.accountsid'][0] in [None, '']:
                self.callerArgs.data['param.accountsid'][0] = ''

            log_level = self.callerArgs.data['param.log_level'][0]
            authtoken = self.callerArgs.data['param.authtoken'][0]
            accountsid = self.callerArgs.data['param.accountsid'][0]
            
      
            # a hack to support create/update/deletes , clear out passwords.conf , and re-write it.
            try:
                entities = entity.getEntities(['storage', 'passwords'], namespace="twilio_alert", owner='nobody', sessionKey=self.getSessionKey())           
                for i, c in entities.items():
                    if c['eai:acl']['app'] ==  "twilio_alert":
                        username = c['username']
                        if not username == "activation_key":
                            entity.deleteEntity(['storage', 'passwords'],":%s:" % c['username'],namespace="twilio_alert", owner='nobody', sessionKey=self.getSessionKey())           
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error deleting twilio_alert credential , perhaps this is the first setup run and it did not yet exist (that is ok) : %s" % e) 
            

            
            try:
                logger.debug("creating twilio_alert credential")
                new_credential = entity.Entity(['storage', 'passwords'], accountsid, contents={'password':authtoken}, namespace="twilio_alert",owner='nobody')
                entity.setEntity(new_credential,sessionKey=self.getSessionKey())
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error creating twilio_alert credential : %s" % e)

            try:
                logger.debug("creating global settings")
                new_global_settings= entity.Entity(['admin', 'alert_actions'], 'twilio', contents={'param.log_level':log_level,'param.accountsid':accountsid}, namespace="twilio_alert",owner='nobody')
                entity.setEntity(new_global_settings,sessionKey=self.getSessionKey())
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error creating global settings : %s" % e)

        except:  
                e = sys.exc_info()[0]  
                logger.error("Error editing propertys : %s" % e)  

def main():
    logger.debug("main")
    splunk.admin.init(ConfigHandler, splunk.admin.CONTEXT_NONE)


if __name__ == '__main__':

    main()
