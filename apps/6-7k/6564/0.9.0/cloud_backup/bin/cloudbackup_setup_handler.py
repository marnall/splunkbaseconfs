import os,logging
import sys

import splunk
import splunk.admin
import splunk.entity as entity

import json

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from logging.handlers import TimedRotatingFileHandler


SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","cloudbackup_app_setuphandler.log")
logger = logging.getLogger('cloudbackup')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)


class ConfigHandler(splunk.admin.MConfigHandler):

    def setup(self):
        try:
            logger.info("setup")
            if self.requestedAction == splunk.admin.ACTION_EDIT:
                for arg in ['configs' ]:
                    self.supportedArgs.addOptArg(arg)           
                # for arg in ['credential' ]:
                #     self.supportedArgs.addOptArg(arg)
                
        except:  
            e = sys.exc_info()[0]  
            logger.error("Error setting up propertys : %s" % e) 


    def handleList(self, confInfo):

        # try:
            
            logger.info("listing")

            entities = entity.getEntities(['storage', 'passwords'], namespace="cloud_backup", owner='nobody', sessionKey=self.getSessionKey())
            credential_list = []
            credential_key_list = []

            outconfig = []
        
            for i, c in entities.items():
                #s3config = {}
                logger.debug("in entities")
                if c['eai:acl']['app'] ==  "cloud_backup":
                    username = c['username']
                    #credential_list.append(c['clear_password'])
                    s3config = json.loads(c['clear_password'])
                    logger.debug("s3config: " + str(s3config))
                    #s3config['name'] = username
                    #s3config = {'name': username, 'credential': s3config}
                    outconfig.append(s3config)

            logger.debug("s3config for listing: " + str(outconfig))
            confInfo['cloudbackup'].append('configs', json.dumps(outconfig))
            #confInfo['cloudbackup'].append('credential_key', "::".join(credential_key_list))

        # except:  
        #     e = sys.exc_info()[0]  
        #     logger.error("Error listing propertys : %s" % e) 
        

    def handleEdit(self, confInfo):

        logger.info("in handleEdit")
        # import sys, os
        # sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
        # import splunk_debug as dbg
        # dbg.enable_debugging(timeout=25)

        # try:
        configs = []
        b64 = self.callerArgs.data['configs'][0]
#        configs.append(json.loads(strtmp))
        import base64
        strtmp = base64.b64decode(b64)
        configs = json.loads(strtmp)

        logger.info("edit my data: " + str(configs))

        # if self.callerArgs.data['credential_key'][0] in [None, '']:
        #     self.callerArgs.data['credential_key'][0] = ''
        
        # if self.callerArgs.data['credential'][0] in [None, '']:
        #     self.callerArgs.data['credential'][0] = ''
        

        # credential_key_str = self.callerArgs.data['credential_key'][0]                 
        # credential_str = self.callerArgs.data['credential'][0]

        # logger.info("edit.. data: " + str(self.callerArgs.data))
        # logger.info("edit.. credential_str: " + str(credential_str))
    
#            try:
        # delete all entries first..
# #
        entities = entity.getEntities(['storage', 'passwords'], namespace="cloud_backup", owner='nobody', sessionKey=self.getSessionKey())           
        for i, c in entities.items():
            if c['eai:acl']['app'] ==  "cloud_backup":
                username = c['username']
                entity.deleteEntity(['storage', 'passwords'],":%s:" % c['username'],namespace="cloud_backup", owner='nobody', sessionKey=self.getSessionKey())           
            # except:  
            #     e = sys.exc_info()[0]  
            #     logger.error("Error deleting mqtt_ta credential , perhaps this is the first setup run and it did not yet exist (that is ok) : %s" % e) 

#         # set new config
        for config in configs:
            logger.info("creating cloud_backup credential" + config['name'])
            password = config.copy()
            #password.pop('name')
            password_str = json.dumps(password)
            new_credential = entity.Entity(['storage', 'passwords'], config['name'], contents={'password':password_str}, namespace="cloud_backup",owner='nobody')
            entity.setEntity(new_credential,sessionKey=self.getSessionKey())
#
        # a hack to support create/update/deletes , clear out passwords.conf , and re-write it.
        # try:
        #     entities = entity.getEntities(['storage', 'passwords'], namespace="cloud_backup", owner='nobody', sessionKey=self.getSessionKey())           
        #     for i, c in entities.items():
        #         if c['eai:acl']['app'] ==  "cloud_backup":
        #             username = c['username']
        #             if not username == "activation_key":
        #                 entity.deleteEntity(['storage', 'passwords'],":%s:" % c['username'],namespace="cloud_backup", owner='nobody', sessionKey=self.getSessionKey())           
        # except:  
        #     e = sys.exc_info()[0]  
        #     logger.error("Error deleting cloud_backup credential , perhaps this is the first setup run and it did not yet exist (that is ok) : %s" % e) 
        

        #for credential_key,credential in zip(credential_key_str.split('::'),credential_str.split('::')):
            #try:

            #except:  
                # e = sys.exc_info()[0]  
                # logger.error("Error creating cloud_backup credential : %s" % e)

        

        # except:  
        #         e = sys.exc_info()[0]  
        #         logger.error("Error editing propertys : %s" % e)  

def main():
    logger.debug("main")
    splunk.admin.init(ConfigHandler, splunk.admin.CONTEXT_NONE)


if __name__ == '__main__':

    main()
