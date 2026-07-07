import os,logging
import sys

import splunk
import splunk.admin
import splunk.entity as entity

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
    
#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","restmodinput_app_setuphandler.log")

# Set up a specific logger
logger = logging.getLogger('restmodinput')

#default logging level
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
                
        except:  
            e = sys.exc_info()[0]  
            logger.error("Error setting up propertys : %s" % e) 


    def handleList(self, confInfo):

        try:
            
            logger.debug("listing")

            entities = entity.getEntities(['storage', 'passwords'], namespace="rest_ta",count=0, owner='nobody', sessionKey=self.getSessionKey())
            credential_list = []
            credential_key_list = []


            for i, c in entities.items():
                if c['eai:acl']['app'] ==  "rest_ta":
                    credential_list.append(c['clear_password'])
                    credential_key_list.append(c['username'])
                 
            confInfo['restmodinput'].append('credential', "::".join(credential_list))
            confInfo['restmodinput'].append('credential_key', "::".join(credential_key_list))

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
            

            credential_key_str = self.callerArgs.data['credential_key'][0]                 
            credential_str = self.callerArgs.data['credential'][0]

        
      
            # a hack to support create/update/deletes , clear out passwords.conf , and re-write it.
            try:
                entities = entity.getEntities(['storage', 'passwords'], namespace="rest_ta",count=0, owner='nobody', sessionKey=self.getSessionKey())           
                for i, c in entities.items():
                    if c['eai:acl']['app'] ==  "rest_ta":
                        entity.deleteEntity(['storage', 'passwords'],":%s:" % c['username'],namespace="rest_ta", owner='nobody', sessionKey=self.getSessionKey())           
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error deleting rest_ta credential , perhaps this is the first setup run and it did not yet exist (that is ok) : %s" % e) 
            

            for credential_key,credential in zip(credential_key_str.split('::'),credential_str.split('::')):
                try:
                    logger.debug("creating rest_ta credential")
                    new_credential = entity.Entity(['storage', 'passwords'], credential_key, contents={'password':credential}, namespace="rest_ta",owner='nobody')
                    entity.setEntity(new_credential,sessionKey=self.getSessionKey())
                except:  
                    e = sys.exc_info()[0]  
                    logger.error("Error creating rest_ta credential : %s" % e)

            

        except:  
                e = sys.exc_info()[0]  
                logger.error("Error editing propertys : %s" % e)  

def main():
    logger.debug("main")
    splunk.admin.init(ConfigHandler, splunk.admin.CONTEXT_NONE)


if __name__ == '__main__':

    main()
