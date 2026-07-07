'''
Custom Mantisnet Setup Handler

This module performs the backend custom setup logic for the setup.xml file

January 2020

Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Mantisnet ( www.mantisnet.com )
'''

import os,logging
import sys

import splunk
import splunk.admin
import splunk.entity as entity

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
    
#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var/log/splunk/mantisnet_app_setuphandler.log")

# Set up a specific logger
logger = logging.getLogger('mantisnet')

logger.setLevel(logging.DEBUG)

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
                
                for arg in ['index']:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['bootstrap_server']:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['log_level']:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['username']:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['password']:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['data_input']:
                    self.supportedArgs.addOptArg(arg)

            

        except:  
            e = sys.exc_info()[0]  
            logger.error("Error setting up propertys : %s" % e) 


    def handleList(self, confInfo):

        try:
            
            logger.debug("listing")
            
            entities = entity.getEntities(['data', 'indexes'], namespace="mantisnet_app", owner='nobody', sessionKey=self.getSessionKey())
            index_list = []
            for i, c in entities.items():
                if not i.startswith("_"):
                    index_list.append(i)
               
            username = ''
            confDict = self.readConf("inputs")
            if None != confDict:
                for stanza, settings in confDict.items():
                    if stanza == "mantisnet_kafka":
                        logger.debug("stanza : "+stanza)
                        for key, val in settings.items():
                            if key in ['username']:
                                if val in [None, '']:
                                    val = ''
                                username = val
                            if key in ['index']:
                                if val in [None, '']:
                                    val = ','.join(index_list)
                                else:
                                    index_list.remove(val)
                                    index_list.insert(0,val)
                                    val = ','.join(index_list)

                            if key in ['log_level'] and val in [None, '']:
                                val = ''
                            if key in ['bootstrap_server'] and val in [None, '']:
                                val = ''
                            

                            confInfo[stanza].append(key, val)
                        entities = entity.getEntities(['storage', 'passwords'], namespace="mantisnet_app", owner='nobody', sessionKey=self.getSessionKey())
                        password = ''
                        for i, c in entities.items():
                            if c['username'] == username: 
                                password = c['clear_password']
                    
                        confInfo[stanza].append('password', password)

        except:  
            e = sys.exc_info()[0]  
            logger.error("Error listing propertys : %s" % e) 

    def handleEdit(self, confInfo):

        try:
            logger.debug("edit")
            if self.callerArgs.data['username'][0] in [None, '']:
                self.callerArgs.data['username'][0] = ''
            if self.callerArgs.data['data_input'][0] in [None, '']:
                self.callerArgs.data['data_input'][0] = ''
            if self.callerArgs.data['password'][0] in [None, '']:
                self.callerArgs.data['password'][0] = ''
            if self.callerArgs.data['index'][0] in [None, '']:
                self.callerArgs.data['index'][0] = ''
            if self.callerArgs.data['log_level'][0] in [None, '']:
                self.callerArgs.data['log_level'][0] = ''  
            if self.callerArgs.data['bootstrap_server'][0] in [None, '']:
                self.callerArgs.data['bootstrap_server'][0] = ''   
            

            username = self.callerArgs.data['username'][0]
            
            #prune out password , we want to save this encrytped in passwords.conf , not clear in inputs.conf
            password = self.callerArgs.data['password'][0]
            del self.callerArgs.data['password']

            data_input = self.callerArgs.data['data_input'][0]
            del self.callerArgs.data['data_input']

            logger.info("data_input : %s" % data_input) 

            #write global mod input settings to inputs.conf
            self.writeConf('inputs', 'mantisnet_kafka', self.callerArgs.data)


            #update index in macro defintions
            new_index='index='+self.callerArgs.data['index'][0]
            self.writeConf('macros', 'mantisnet_index', {'definition':new_index})

            #determine app version
            appDict = self.readConf("mantisnet")
            if None != appDict:
                for stanza, settings in appDict.items():
                    if stanza == "settings":
                        for key, val in settings.items():
                            if key in ['app_version_type']:
                                if val in [None, '']:
                                    val = 'unknown'
                                app_version_type= val

            self.writeConf('macros', 'mantisnet_version', {'definition':'eval version=\"%s\"' % app_version_type})
            
            
            
            try:

                logger.debug("server info")

                is_indexer_or_forwarder = False
                entities = entity.getEntities(['server', 'info'], namespace="mantisnet_app", owner='nobody', sessionKey=self.getSessionKey())
                for i, c in entities.items():
                    server_roles = ['indexer','universal_forwarder','heavyweight_forwarder','lightweight_forwarder'] 
                    for role in server_roles:
                        if role in c['server_roles']:
                            is_indexer_or_forwarder = True


                logger.debug("is_indexer_or_forwarder:"+str(is_indexer_or_forwarder))

                #enable inputs for indexers or forwarders

                if data_input == "0" :
                    if is_indexer_or_forwarder :
                        logger.debug("Enabling Kafka Inputs")
                        entities = entity.getEntities(['data', 'inputs','mantisnet_kafka'], namespace="mantisnet_app", owner='nobody', sessionKey=self.getSessionKey())
                        for i, c in entities.items():
                            uri = c.getFullPath()+"/enable"
                            entity.controlEntity('enable',uri,sessionKey=self.getSessionKey())

                
                if is_indexer_or_forwarder :
                    logger.debug("Enabling Lookup Scripted Inputs")
                    
                    logger.info("Enabling public_dns_lookup.py")
                    uri = "/servicesNS/nobody/mantisnet_app/data/inputs/script/.%252Fbin%252Fpublic_dns_lookup.py/enable"
                    entity.controlEntity('enable',uri,sessionKey=self.getSessionKey())

            except:  
                e = sys.exc_info()[0]  
                logger.error("Error enabling Mantisnet Kafka inputs : %s" % e)
      
            
            #a hack to allow updating of a credential in passwords.conf which you can't do using the standard storage/passwords via setup.xml
            try:
                logger.debug("deleting mantisnet kafka credential")          
                entity.deleteEntity(['storage', 'passwords'],":%s:" % username,namespace="mantisnet_app", owner='nobody', sessionKey=self.getSessionKey())           
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error deleting mantisnet credential , perhaps this is the first setup run and it did not yet exist (that is ok) : %s" % e) 
            try:
                logger.debug("creating mantisnet credential")
                new_credential = entity.Entity(['storage', 'passwords'], username, contents={'password':password}, namespace="mantisnet_app",owner='nobody')
                entity.setEntity(new_credential,sessionKey=self.getSessionKey())
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error creating mantisnet credential : %s" % e)
        except:  
                e = sys.exc_info()[0]  
                logger.error("Error editing propertys : %s" % e)  

def main():
    logger.debug("main")
    splunk.admin.init(ConfigHandler, splunk.admin.CONTEXT_NONE)


if __name__ == '__main__':

    main()