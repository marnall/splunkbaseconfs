'''
Custom Setup Page Python handler

May 2021

Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Neustar
'''

import os,logging
import sys

import splunk
import splunk.admin
import splunk.entity as entity

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

SCRIPTED_INPUT = "script://$SPLUNK_HOME/etc/apps/neustar_app/bin/neustar_s3.py"
    
#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var/log/splunk/neustar_setup.log")

# Set up a specific logger
logger = logging.getLogger('neustar_setup')

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
                for arg in ['access_key_id' ]:
                    self.supportedArgs.addOptArg(arg)           
                for arg in ['secret_key_id' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['external_id' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['aws_assumerole_arn' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['aws_assumerole_sessionname' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['aws_assumerole_duration' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['aws_region' ]:
                    self.supportedArgs.addOptArg(arg)               
                for arg in ['aws_proxy_https' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['aws_connection_timeout' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['aws_read_timeout' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['aws_retry_maxattempts' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['splunk_admin_user' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['polling_interval' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['geopoint_bucket' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['file_suffix' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['ipv4_filename_pattern' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['ipv6_filename_pattern' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['local_root_download_directory' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['stream_content' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['delete_after_processing' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['perform_checksum_on_download' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['kvstore_batch_save_size' ]:
                    self.supportedArgs.addOptArg(arg)
                for arg in ['log_level' ]:
                    self.supportedArgs.addOptArg(arg)

                
        except:  
            e = sys.exc_info()[0]  
            logger.error("Error setting up propertys : %s" % e) 


    def handleList(self, confInfo):

        try:

            logger.info("Reading Neustar Configuration File")
            confDict = self.readConf("neustar")
            if None != confDict:
                for stanza, settings in confDict.items():
                    if stanza == "s3_download":
                        
                        for key, val in settings.items():

                            if val in [None, '']:
                                val = ''

                            confInfo["neustarapp"].append(key, val)

                        logger.info("Getting encrypted credentials")
                        entities = entity.getEntities(['storage', 'passwords'], namespace="neustar_app", owner='nobody', sessionKey=self.getSessionKey())
                        
                        access_key_id = ''
                        secret_key_id = ''
                        external_id = ''
                        aws_assumerole_arn = ''
                        for i, c in entities.items():
                            if c['username'] == "access_key_id":
                                access_key_id =  c['clear_password']
                            if c['username'] == "secret_key_id":
                                secret_key_id =  c['clear_password']
                            if c['username'] == "external_id":
                                external_id =  c['clear_password']
                            if c['username'] == "aws_assumerole_arn":
                                aws_assumerole_arn =  c['clear_password']

                        confInfo["neustarapp"].append('access_key_id', access_key_id)
                        confInfo["neustarapp"].append('secret_key_id', secret_key_id)
                        confInfo["neustarapp"].append('external_id', external_id)
                        confInfo["neustarapp"].append('aws_assumerole_arn', aws_assumerole_arn)

                        confDict = self.readConf("inputs")
                        if None != confDict:
                            for stanza, settings in confDict.items():
                                if stanza == SCRIPTED_INPUT:
                                    for key, val in settings.items():

                                        if key == "passAuth":
                                            confInfo["neustarapp"].append("splunk_admin_user", val)

                                        


        except:  
            e = sys.exc_info()[0]  
            logger.error("Error listing propertys : %s" % e) 
        

    def handleEdit(self, confInfo):

        try:

            logger.info("Writing Neustar Configuration File")

            if self.callerArgs.data['access_key_id'][0] in [None, '']:
                self.callerArgs.data['access_key_id'][0] = ''
            if self.callerArgs.data['secret_key_id'][0] in [None, '']:
                self.callerArgs.data['secret_key_id'][0] = ''
            if self.callerArgs.data['external_id'][0] in [None, '']:
                self.callerArgs.data['external_id'][0] = ''
            if self.callerArgs.data['aws_assumerole_arn'][0] in [None, '']:
                self.callerArgs.data['aws_assumerole_arn'][0] = ''
            if self.callerArgs.data['aws_assumerole_sessionname'][0] in [None, '']:
                self.callerArgs.data['aws_assumerole_sessionname'][0] = ''
            if self.callerArgs.data['aws_assumerole_duration'][0] in [None, '']:
                self.callerArgs.data['aws_assumerole_duration'][0] = ''
            if self.callerArgs.data['aws_region'][0] in [None, '']:
                self.callerArgs.data['aws_region'][0] = ''           
            if self.callerArgs.data['aws_proxy_https'][0] in [None, '']:
                self.callerArgs.data['aws_proxy_https'][0] = ''
            if self.callerArgs.data['aws_connection_timeout'][0] in [None, '']:
                self.callerArgs.data['aws_connection_timeout'][0] = ''
            if self.callerArgs.data['aws_read_timeout'][0] in [None, '']:
                self.callerArgs.data['aws_read_timeout'][0] = ''
            if self.callerArgs.data['aws_retry_maxattempts'][0] in [None, '']:
                self.callerArgs.data['aws_retry_maxattempts'][0] = ''
            if self.callerArgs.data['splunk_admin_user'][0] in [None, '']:
                self.callerArgs.data['splunk_admin_user'][0] = ''
            if self.callerArgs.data['polling_interval'][0] in [None, '']:
                self.callerArgs.data['polling_interval'][0] = ''
            if self.callerArgs.data['geopoint_bucket'][0] in [None, '']:
                self.callerArgs.data['geopoint_bucket'][0] = ''
            if self.callerArgs.data['file_suffix'][0] in [None, '']:
                self.callerArgs.data['file_suffix'][0] = ''
            if self.callerArgs.data['ipv4_filename_pattern'][0] in [None, '']:
                self.callerArgs.data['ipv4_filename_pattern'][0] = ''
            if self.callerArgs.data['ipv6_filename_pattern'][0] in [None, '']:
                self.callerArgs.data['ipv6_filename_pattern'][0] = ''
            if self.callerArgs.data['stream_content'][0] in [None, '']:
                self.callerArgs.data['stream_content'][0] = ''
            if self.callerArgs.data['local_root_download_directory'][0] in [None, '']:
                self.callerArgs.data['local_root_download_directory'][0] = ''
            if self.callerArgs.data['delete_after_processing'][0] in [None, '']:
                self.callerArgs.data['delete_after_processing'][0] = ''
            if self.callerArgs.data['perform_checksum_on_download'][0] in [None, '']:
                self.callerArgs.data['perform_checksum_on_download'][0] = ''
            if self.callerArgs.data['kvstore_batch_save_size'][0] in [None, '']:
                self.callerArgs.data['kvstore_batch_save_size'][0] = ''
            if self.callerArgs.data['log_level'][0] in [None, '']:
                self.callerArgs.data['log_level'][0] = ''
            

            access_key_id = self.callerArgs.data['access_key_id'][0]                 
            secret_key_id = self.callerArgs.data['secret_key_id'][0]
            external_id = self.callerArgs.data['external_id'][0]
            aws_assumerole_arn = self.callerArgs.data['aws_assumerole_arn'][0]

          
            #prune these out , we don't want them saved in cleartext in neustar.conf
            #they will be encrypted to passwords.conf 
            del self.callerArgs.data['access_key_id']
            del self.callerArgs.data['secret_key_id']
            del self.callerArgs.data['external_id']
            del self.callerArgs.data['aws_assumerole_arn']

            #set app context for updating conf files
            self.appName = "neustar_app"

            #update admin user to run the polling script as
            pass_auth = {"passAuth":self.callerArgs.data['splunk_admin_user'][0]}
            self.writeConf('inputs', SCRIPTED_INPUT, pass_auth)
            del self.callerArgs.data['splunk_admin_user']

            self.writeConf('neustar', 's3_download', self.callerArgs.data)

            logger.info("Setting encrypted credentials")
            # a hack to support create/update/deletes , clear out passwords.conf , and re-write it.
            try:
                entities = entity.getEntities(['storage', 'passwords'], namespace="neustar_app", owner='nobody', sessionKey=self.getSessionKey())           
                for i, c in entities.items():
                    if c['eai:acl']['app'] ==  "neustar_app":
                        entity.deleteEntity(['storage', 'passwords'],":%s:" % c['username'],namespace="neustar_app", owner='nobody', sessionKey=self.getSessionKey())           
            except:  
                e = sys.exc_info()[0]  
                logger.error("Error deleting neustar_app credential , perhaps this is the first setup run and it did not yet exist (that is ok) : %s" % e) 
            
            credential_keys = ["access_key_id","secret_key_id","external_id","aws_assumerole_arn"]
            credentials = [access_key_id,secret_key_id,external_id,aws_assumerole_arn]
            for credential_key,credential in zip(credential_keys,credentials):
                try:
                    new_credential = entity.Entity(['storage', 'passwords'], credential_key, contents={'password':credential}, namespace="neustar_app",owner='nobody')
                    entity.setEntity(new_credential,sessionKey=self.getSessionKey())
                except:  
                    e = sys.exc_info()[0]  
                    logger.error("Error creating neustar_app credential : %s" % e)


            
            #doing a restart with a disable/enable toggle

            logger.info("Restarting the Neustar S3 Polling script")
            
            logger.info("Disabling neustar_s3.py")

            uri = "/servicesNS/nobody/neustar_app/data/inputs/script/$SPLUNK_HOME%252Fetc%252Fapps%252Fneustar_app%252Fbin%252Fneustar_s3.py/disable"
            entity.controlEntity('disable',uri,sessionKey=self.getSessionKey())


            logger.info("Enabling neustar_s3.py")

            uri = "/servicesNS/nobody/neustar_app/data/inputs/script/$SPLUNK_HOME%252Fetc%252Fapps%252Fneustar_app%252Fbin%252Fneustar_s3.py/enable"
            entity.controlEntity('enable',uri,sessionKey=self.getSessionKey())

    
        except:  
                e = sys.exc_info()[0]  
                logger.error("Error editing propertys : %s" % e)  

def main():
    splunk.admin.init(ConfigHandler, splunk.admin.CONTEXT_NONE)


if __name__ == '__main__':

    main()
