'''
Custom Rundeck Setup Handler

This module performs the backend custom setup logic for the setup.xml file

June 2018

Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Rundeck, Inc. ( www.rundeck.com )
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
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var/log/splunk/rundeck_app_setuphandler.log")

# Set up a specific logger
logger = logging.getLogger('Rundeck')

#default logging level , can be overidden in stanza config
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
                for arg in ['https_api_host' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['index' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['log_level' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['auth_token' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['polling_interval' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['backfill' ]:
                    self.supportedArgs.addOptArg(arg)

        except:  
            e = sys.exc_info()[0]  
            logger.error("Error setting up propertys : %s" % e) 

    def handleList(self, confInfo):

        try:

            logger.debug("listing")

            entities = entity.getEntities(['data', 'indexes'], namespace="rundeck_app", owner='nobody', sessionKey=self.getSessionKey())
            index_list = []
            for i, c in entities.items():
                if not i.startswith("_"):
                    index_list.append(i)

            host = ''
            confDict = self.readConf("inputs")
            if None != confDict:
                for stanza, settings in confDict.items():
                    if stanza == "rundeck":
                        logger.debug("stanza : "+stanza)
                        for key, val in settings.items():
                            if key in ['https_api_host']:
                                if val in [None, '']:
                                    val = ''
                                host = val
                            if key in ['index']:
                                if val in [None, '']:
                                    val = ','.join(index_list)
                                else:
                                    index_list.remove(val)
                                    index_list.insert(0,val)
                                    val = ','.join(index_list)

                            if key in ['log_level'] and val in [None, '']:
                                val = ''
                            if key in ['polling_interval'] and val in [None, '']:
                                val = ''
                            if key in ['backfill'] and val in [None, '']:
                                val = ''

                            confInfo[stanza].append(key, val)
                        entities = entity.getEntities(['storage', 'passwords'], namespace="rundeck_app", owner='nobody', sessionKey=self.getSessionKey())
                        auth_token = ''
                        for i, c in entities.items():
                            if c['username'] == host: 
                                auth_token = c['clear_password']

                        confInfo[stanza].append('auth_token', auth_token)

        except:  
            e = sys.exc_info()[0]  
            logger.error("Error listing propertys : %s" % e) 

    def handleEdit(self, confInfo):

        try:
            logger.debug("edit")
            if self.callerArgs.data['https_api_host'][0] in [None, '']:
                self.callerArgs.data['https_api_host'][0] = ''
            if self.callerArgs.data['index'][0] in [None, '']:
                self.callerArgs.data['index'][0] = ''
            if self.callerArgs.data['log_level'][0] in [None, '']:
                self.callerArgs.data['log_level'][0] = ''    
            if self.callerArgs.data['auth_token'][0] in [None, '']:
                self.callerArgs.data['auth_token'][0] = ''
            if self.callerArgs.data['polling_interval'][0] in [None, '']:
                self.callerArgs.data['polling_interval'][0] = ''
            if self.callerArgs.data['backfill'][0] in [None, '']:
                self.callerArgs.data['backfill'][0] = ''

            host = self.callerArgs.data['https_api_host'][0]

            #prune out auth token , we want to save this encrytped in passwords.conf , not clear in inputs.conf
            auth_token = self.callerArgs.data['auth_token'][0]
            del self.callerArgs.data['auth_token']

            #write global mod input settings to inputs.conf
            self.writeConf('inputs', 'rundeck', self.callerArgs.data)

            #update index in macro defintions
            new_index='index='+self.callerArgs.data['index'][0]
            self.writeConf('macros', 'rundeck_index', {'definition':new_index})

            #determine app version
            appDict = self.readConf("rundeck")
            if None != appDict:
                for stanza, settings in appDict.items():
                    if stanza == "settings":
                        for key, val in settings.items():
                            if key in ['app_version_type']:
                                if val in [None, '']:
                                    val = 'unknown'
                                app_version_type= val

            self.writeConf('macros', 'rundeck_version', {'definition':'eval version=\"%s\"' % app_version_type})

            #copy settings into alert actions
            #self.writeConf('alert_actions', 'rundeck_jobalert', {'param.https_api_host':self.callerArgs.data['https_api_host'][0]})
            self.writeConf('alert_actions', 'rundeck_jobalert', {'param.log_level':self.callerArgs.data['log_level'][0]})

            try:

                logger.debug("server info")

                is_indexer_or_forwarder = False
                entities = entity.getEntities(['server', 'info'], namespace="rundeck_app", owner='nobody', sessionKey=self.getSessionKey())
                for i, c in entities.items():
                    server_roles = ['indexer','universal_forwarder','heavyweight_forwarder','lightweight_forwarder'] 
                    for role in server_roles:
                        if role in c['server_roles']:
                            is_indexer_or_forwarder = True

                logger.debug("is_indexer_or_forwarder:"+str(is_indexer_or_forwarder))

                #enable REST inputs for indexers or forwarders

                if is_indexer_or_forwarder :
                    entities = entity.getEntities(['data', 'inputs','rundeck'], namespace="rundeck_app", owner='nobody', sessionKey=self.getSessionKey())
                    for i, c in entities.items():
                        uri = c.getFullPath()+"/enable"
                        entity.controlEntity('enable',uri,sessionKey=self.getSessionKey())
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error enabling Rundeck REST inputs : %s" % e)

            #a hack to allow updating of a credential in passwords.conf which you can't do using the standard storage/passwords via setup.xml
            try:
                logger.debug("deleting rundeck credential")          
                entity.deleteEntity(['storage', 'passwords'],":%s:" % host,namespace="rundeck_app", owner='nobody', sessionKey=self.getSessionKey())           
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error deleting rundeck credential , perhaps this is the first setup run and it did not yet exist (that is ok) : %s" % e) 
            try:
                logger.debug("creating rundeck credential")
                new_credential = entity.Entity(['storage', 'passwords'], host, contents={'password':auth_token}, namespace="rundeck_app",owner='nobody')
                entity.setEntity(new_credential,sessionKey=self.getSessionKey())
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error creating rundeck credential : %s" % e)
        except:  
                e = sys.exc_info()[0]  
                logger.error("Error editing propertys : %s" % e)  

def main():
    logger.debug("main")
    splunk.admin.init(ConfigHandler, splunk.admin.CONTEXT_NONE)

if __name__ == '__main__':

    main()