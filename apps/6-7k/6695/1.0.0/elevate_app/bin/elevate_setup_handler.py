'''
Custom Setup Page Python handler

October 2022

Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Elevate Security
'''

import os,logging
import sys
import splunk
import splunk.admin
import splunk.entity as entity
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

#app naming constants
APP_NAME = "elevate_app"
CONF_FILE = "elevate"
STANZA_NAME = "elevate_settings"
MODINPUT_STANZA = "elevate_rest"
MACRO_INDEX_STANZA="elevate_index"
    
#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var/log/splunk/elevate_setup.log")

# Set up a specific logger
logger = logging.getLogger('elevate_setup')

#default logging level
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)


class ConfigHandler(splunk.admin.MConfigHandler):

    def setup(self):
        try:
       
            if self.requestedAction == splunk.admin.ACTION_EDIT:
                
                for arg in ['api_host' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['tenant_id' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['api_key' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['rest_index' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['polling_interval' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['log_level' ]:
                    self.supportedArgs.addOptArg(arg)

                
        except:  
            e = sys.exc_info()[0]  
            logger.error("Error setting up propertys : %s" % e) 


    def handleList(self, confInfo):

        try:

            logger.info("Reading Elevate Configuration File")

            confDict = self.readConf(CONF_FILE)
            tenant_id = ''
            if None != confDict:
                for stanza, settings in confDict.items():
                    if stanza == STANZA_NAME:
                        
                        for key, val in settings.items():

                            if val in [None, '']:
                                val = ''

                            if key == "tenant_id":
                                tenant_id = val

                            confInfo["elevateapp"].append(key, val)

                        logger.info("Getting encrypted credentials")
                        entities = entity.getEntities(['storage', 'passwords'], namespace=APP_NAME, owner='nobody', sessionKey=self.getSessionKey())
                        
                        api_key = ''
                        
                        for i, c in entities.items():
                            if c['eai:acl']['app'] ==  APP_NAME:
                                if c['username'] == tenant_id:
                                    api_key =  c['clear_password']
                            
                        confInfo["elevateapp"].append('api_key', api_key)
                        
                        confDict = self.readConf("inputs")
                        if None != confDict:
                            for stanza, settings in confDict.items():
                                if stanza == MODINPUT_STANZA:
                                    for key, val in settings.items():

                                        if val in [None, '']:
                                            val = ''

                                        if key == "index":
                                            confInfo["elevateapp"].append("rest_index", val)  
                                        if key == "polling_interval":
                                            confInfo["elevateapp"].append("polling_interval", val)                                     
        except:  
            e = sys.exc_info()[0]  
            logger.error("Error listing propertys : %s" % e) 
        

    def handleEdit(self, confInfo):

        try:

            logger.info("Writing Elevate Configuration Settings")

            if self.callerArgs.data['api_host'][0] in [None, '']:
                self.callerArgs.data['api_host'][0] = ''
            if self.callerArgs.data['tenant_id'][0] in [None, '']:
                self.callerArgs.data['tenant_id'][0] = ''
            if self.callerArgs.data['api_key'][0] in [None, '']:
                self.callerArgs.data['api_key'][0] = ''
            if self.callerArgs.data['rest_index'][0] in [None, '']:
                self.callerArgs.data['rest_index'][0] = ''
            if self.callerArgs.data['polling_interval'][0] in [None, '']:
                self.callerArgs.data['polling_interval'][0] = ''
            if self.callerArgs.data['log_level'][0] in [None, '']:
                self.callerArgs.data['log_level'][0] = ''
            

            tenant_id = self.callerArgs.data['tenant_id'][0]                 
            api_key = self.callerArgs.data['api_key'][0]
            polling_interval = self.callerArgs.data['polling_interval'][0]
            rest_index = self.callerArgs.data['rest_index'][0]
                   
            #prune these out , we don't want them saved in in elevate.conf
            del self.callerArgs.data['api_key']
            del self.callerArgs.data['polling_interval']
            del self.callerArgs.data['rest_index']
            
            #set app context for updating conf files
            self.appName = APP_NAME           

            #update elevate.conf
            self.writeConf(CONF_FILE, STANZA_NAME, self.callerArgs.data)

            #update defaults in inputs.conf
            inputs_params = {}
            inputs_params['polling_interval'] = polling_interval
            inputs_params['index'] = rest_index
            self.writeConf("inputs", MODINPUT_STANZA, inputs_params)

            #update index in macro defintions
            new_index='index='+rest_index
            self.writeConf('macros', MACRO_INDEX_STANZA, {'definition':new_index})


            logger.info("Setting encrypted credentials")
            # a hack to support create/update/deletes , clear out passwords.conf , and re-write it.
            try:
                entities = entity.getEntities(['storage', 'passwords'], namespace=APP_NAME, owner='nobody', sessionKey=self.getSessionKey())           
                for i, c in entities.items():
                    if c['eai:acl']['app'] ==  APP_NAME:
                        entity.deleteEntity(['storage', 'passwords'],":%s:" % c['username'],namespace=APP_NAME, owner='nobody', sessionKey=self.getSessionKey())           
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error deleting elevate_app credential , perhaps this is the first setup run and it did not yet exist (that is ok) : %s" % e) 
            
            
            try:
                new_credential = entity.Entity(['storage', 'passwords'], tenant_id, contents={'password':api_key}, namespace=APP_NAME,owner='nobody')
                entity.setEntity(new_credential,sessionKey=self.getSessionKey())
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error creating elevate_app credential : %s" % e)

    
        except:  
                e = sys.exc_info()[0]  
                logger.error("Error editing propertys : %s" % e)  

def main():
    splunk.admin.init(ConfigHandler, splunk.admin.CONTEXT_NONE)


if __name__ == '__main__':

    main()
