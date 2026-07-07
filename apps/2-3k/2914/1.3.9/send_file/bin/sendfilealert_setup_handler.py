import os,logging
import sys

import splunk
import splunk.admin
import splunk.entity as entity

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
    
#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","sendfilealert_app_setuphandler.log")

# Set up a specific logger
logger = logging.getLogger('sendfilealert')

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
                for arg in ['credential_key' ]:
                    self.supportedArgs.addOptArg(arg)           
                for arg in ['credential' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['param.log_level' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['param.activationkey' ]:
                    self.supportedArgs.addOptArg(arg)
                
        except:  
            e = sys.exc_info()[0]  
            logger.error("Error setting up propertys : %s" % e) 


    def handleList(self, confInfo):

        try:
            
            logger.debug("listing")

            entities = entity.getEntities(['storage', 'passwords'], namespace="send_file", owner='nobody', sessionKey=self.getSessionKey())
            credential_list = []
            credential_key_list = []


            for i, c in entities.items():
                if c['eai:acl']['app'] ==  "send_file":
                    credential_list.append(c['clear_password'])
                    credential_key_list.append(c['username'])

            global_entities = entity.getEntities(['admin', 'alert_actions','sendfile'], namespace="send_file", owner='nobody', sessionKey=self.getSessionKey())
            
            log_level = ""
            activationkey = ""

            for i, c in global_entities.items():
                if c['eai:acl']['app'] ==  "send_file":
                    log_level = c['param.log_level']
                    activationkey = c['param.activationkey']

            confInfo['sendfilealert'].append('param.log_level', log_level) 
            confInfo['sendfilealert'].append('param.activationkey', activationkey)                 
            confInfo['sendfilealert'].append('credential', "::".join(credential_list))
            confInfo['sendfilealert'].append('credential_key', "::".join(credential_key_list))

        except:  
            e = sys.exc_info()[0]  
            logger.error("Error listing propertys : %s" % e) 
        

    def handleEdit(self, confInfo):

        try:
            logger.debug("edit")
            if self.callerArgs.data['credential_key'][0] in [None, '']:
                self.callerArgs.data['credential_key'][0] = ''
            
            if self.callerArgs.data['credential'][0] in [None, '']:
                self.callerArgs.data['credential'][0] = ''
            

            if self.callerArgs.data['param.log_level'][0] in [None, '']:
                self.callerArgs.data['param.log_level'][0] = ''

            if self.callerArgs.data['param.activationkey'][0] in [None, '']:
                self.callerArgs.data['param.activationkey'][0] = ''

            credential_key_str = self.callerArgs.data['credential_key'][0]                 
            credential_str = self.callerArgs.data['credential'][0]

            log_level = self.callerArgs.data['param.log_level'][0]
            activationkey = self.callerArgs.data['param.activationkey'][0]

            
            
        
      
            # a hack to support create/update/deletes , clear out passwords.conf , and re-write it.
            try:
                entities = entity.getEntities(['storage', 'passwords'], namespace="send_file", owner='nobody', sessionKey=self.getSessionKey())           
                for i, c in entities.items():
                    if c['eai:acl']['app'] ==  "send_file":
                        entity.deleteEntity(['storage', 'passwords'],":%s:" % c['username'],namespace="send_file", owner='nobody', sessionKey=self.getSessionKey())           
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error deleting send_file credential , perhaps this is the first setup run and it did not yet exist (that is ok) : %s" % e) 
            

            for credential_key,credential in zip(credential_key_str.split('::'),credential_str.split('::')):
                try:
                    logger.debug("creating send_file credential")
                    new_credential = entity.Entity(['storage', 'passwords'], credential_key, contents={'password':credential}, namespace="send_file",owner='nobody')
                    entity.setEntity(new_credential,sessionKey=self.getSessionKey())
                except:  
                    e = sys.exc_info()[0]  
                    logger.error("Error creating send_file credential : %s" % e)

            try:
                logger.debug("creating global settings")
                new_global_settings= entity.Entity(['admin', 'alert_actions'], 'sendfile', contents={'param.log_level':log_level,'param.activationkey':activationkey}, namespace="send_file",owner='nobody')
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
