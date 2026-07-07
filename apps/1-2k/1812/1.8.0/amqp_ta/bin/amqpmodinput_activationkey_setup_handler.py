import os,logging
import sys

import splunk
import splunk.admin
import splunk.entity as entity

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
    
#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","amqpmodinput_app_setuphandler.log")

# Set up a specific logger
logger = logging.getLogger('amqpmodinput')

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
                for arg in ['activation_key' ]:
                    self.supportedArgs.addOptArg(arg)           
                
                
        except:  
            e = sys.exc_info()[0]  
            logger.error("Error setting up propertys : %s" % e) 


    def handleList(self, confInfo):

        try:
            
            logger.debug("listing")

            entities = entity.getEntities(['storage', 'passwords'], namespace="amqp_ta", owner='nobody', sessionKey=self.getSessionKey())


            for i, c in entities.items():
                if c['eai:acl']['app'] ==  "amqp_ta":
                    username = c['username']
                    password = c['clear_password']
                    if username == "activation_key":
                        confInfo['activationkey'].append('activation_key', password)
             
        except:  
            e = sys.exc_info()[0]  
            logger.error("Error listing propertys : %s" % e) 
        

    def handleEdit(self, confInfo):

        try:
            logger.debug("edit")
            if self.callerArgs.data['activation_key'][0] in [None, '']:
                self.callerArgs.data['activation_key'][0] = ''
            
            
            activation_key = self.callerArgs.data['activation_key'][0]                 
           
      
            # a hack to support create/update/deletes , clear out passwords.conf , and re-write it.
            try:
                entities = entity.getEntities(['storage', 'passwords'], namespace="amqp_ta", owner='nobody', sessionKey=self.getSessionKey())           
                for i, c in entities.items():
                    if c['eai:acl']['app'] ==  "amqp_ta":
                        username = c['username']
                        if username == "activation_key":
                            entity.deleteEntity(['storage', 'passwords'],":activation_key:",namespace="amqp_ta", owner='nobody', sessionKey=self.getSessionKey())           
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error deleting activation_key credential , perhaps this is the first setup run and it did not yet exist (that is ok) : %s" % e) 
            

            try:
                logger.debug("creating activation_key credential")
                new_credential = entity.Entity(['storage', 'passwords'], "activation_key", contents={'password':activation_key}, namespace="amqp_ta",owner='nobody')
                entity.setEntity(new_credential,sessionKey=self.getSessionKey())
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error creating activation_key credential : %s" % e)

            

        except:  
                e = sys.exc_info()[0]  
                logger.error("Error editing propertys : %s" % e)  

def main():
    logger.debug("main")
    splunk.admin.init(ConfigHandler, splunk.admin.CONTEXT_NONE)


if __name__ == '__main__':

    main()
