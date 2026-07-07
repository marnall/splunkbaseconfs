'''
Custom search command for pushing data to Elevate via an HTTP Streaming upload

Data is exported as a JSON file

The staging filename format is splunkexport_{user}_{current_timestamp}_{random_seed}.json

October 2022

Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Elevate Security
'''

from __future__ import absolute_import, division, print_function, unicode_literals
import os,sys,random,datetime,time,copy,json
from distutils.util import strtobool
import logging
from logging.handlers import TimedRotatingFileHandler
import traceback
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, ReportingCommand, Configuration, Option, validators

SPLUNK_HOME = os.environ['SPLUNK_HOME']

#app naming constants
APP_NAME = "elevate_app"
CONF_FILE = "elevate"
STANZA_NAME = "elevate_settings"
EXPORT_STAGING_DIR = "elevate_export_staging"


#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","elevate_search_command.log")

# Set up a specific logger
logger = logging.getLogger("elevate_search_command")
logger.propagate = False

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)

@Configuration()
class ElevatePush(ReportingCommand):

    fields = Option(
        doc='''
        **Syntax:** **fields=***"field1, field2, field3"*
        **Description:** The fields to be written to the JSON file
        **Default:** All fields in the current search ''',
        require=False, validate=validators.List()) 

    stream_id = Option(
        doc='''
        **Syntax:** **stream_id=***<Stream ID>*
        **Description:** Stream ID for the Elevate Behaviour to upload data to''',
        require=True)

    #get encrypted credentials from the Splunk password store
    def get_credentials(self):

        result = []
        try:
     
           for sp in self.service.storage_passwords:
             values = {}
             values['username'] = sp.username or "none"
             values['clear_password'] = sp.clear_password or "none"
             result.append(values)

        except Exception as e:
           logger.error("Could not get credentials from Splunk. Error: %s" % str(e))
           return result

        return result

    def write_json(self,json_data, export_file):
        logger.info("Writing JSON to staging filename : %s "% export_file)
        try:
            with open(export_file, "ab") as f:
                f.writelines(json_data)
        except:
            logger.error("Error writing JSON event to file : %s " % export_file)

    def system_error(self,message):
        logger.error(message)
        self.error_print(message)
        sys.exit(1)

    def error_print(self,*args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

    #utility boolean parsing function
    def string_to_bool(self,string):
        return bool(strtobool(str(string)))

    @Configuration()
    def map(self, events):
        for e in events:
            yield(e)

    def reduce(self, records):

        try:

            logger.info("Reading in the Elevate configuration settings file") 
        
            CONF_STANZA_OBJECT = self.service.confs[CONF_FILE][STANZA_NAME]

            #prune out None values so our defaults kick in
            CONF_STANZA = {k: v for k, v in CONF_STANZA_OBJECT.content().items() if v is not None}

            #update log level with the global app level
            log_level = logging.getLevelName(CONF_STANZA.get("log_level","INFO"))
            logger.setLevel(log_level)


            dev_mode = self.string_to_bool(CONF_STANZA.get("dev_mode_for_streaming","false"))
            
            api_host = CONF_STANZA.get("api_host","api.elevatesecurity.com")

            if self.stream_id is not None and self.stream_id == "":
                self.system_error("Stream ID has not been set")

            elevate_api= f"https://{api_host}/customer-integrations/datasets/{self.stream_id}"

            logger.info("Elevate Streaming API URL : %s ", elevate_api)

            tenant_id = CONF_STANZA .get("tenant_id",None)

            if tenant_id is None:
                self.system_error("No Tenant ID has been set")


            api_key = None
            credentials_list = self.get_credentials()
         
            for c in credentials_list:
              
                username =  c['username']
                clear_password = c['clear_password']
                if username == tenant_id:
                    api_key = clear_password
            
            if api_key is None:
                self.system_error("No API Key has been set")


            if self.fields is not None and (self.fields == "" or len(self.fields) == 0):
                self.fields = None


            user = self.metadata.searchinfo.username
            sid = self.metadata.searchinfo.sid
           
            current_timestamp = str(int(time.time()))

            #add a random seed in in case of concurrent searches at same time
            random_seed = str(random.randint(10000, 99999))
            export_id=f"{current_timestamp}_{random_seed}"
            export_filename = f"splunkexport_{user}_{export_id}.json"


            staging_directory = os.path.join(SPLUNK_HOME,"etc","apps",APP_NAME,EXPORT_STAGING_DIR)

            try:
                if not os.path.exists(staging_directory):
                    os.makedirs(staging_directory)
            except:
                self.system_error("Error creating staging directory %s " % staging_directory)
                         
            export_filename = os.path.join(staging_directory, export_filename)

            logger.info("Export Filename : %s ", export_filename)


        except:
            self.system_error("Error getting Elevate settings %s " % traceback.format_exc())

 
        json_buffer = []
        max_json_buffer_size = 1000

        contains_records = False

        logger.info("Processing search events")

        for record in records:

            contains_records = True

            if self.fields is not None:
                event_keys = []
                if type(self.fields) == str:
                    self.fields = [self.fields]
                for k in list(record.keys()):
                    for f in self.fields:
                        if k == f:
                            event_keys.append(k)
            else:
                event_keys = list(record.keys())

            json_data = ''

            if self.fields is not None:
                json_event = {}
                for key in event_keys:
                    try:
                        json_event[key] = record[key]
                    except:
                        logger.error("Error reading field %s from search event" % key)
            else:
                json_event = copy.deepcopy(record)
            try:
                json_data = json.dumps(json_event)
            except:
                logger.error("Error creating json event %s " % traceback.format_exc())


            json_buffer.append((json_data + '\n').encode('utf-8'))

            if len(json_buffer) == max_json_buffer_size:

                self.write_json(json_buffer,export_filename)

                json_buffer = []
                
            yield record


        if contains_records : 
            self.write_json(json_buffer,export_filename)
            json_buffer = None

        try:
           
            #if in dev mode , skip the HTTP streaming upload and file deletion
            if dev_mode:
                logger.info("Running in Dev mode. Will only write JSON file to the staging directory and not upload it.")
            else:
                headers = {
                    'content-type': 'application/json',
                    'x-api-key': api_key,
                    'accept': 'application/json'
                }
                            
                if os.path.exists(export_filename):

                    filesize = os.path.getsize(export_filename)

                    logger.info("event=exporting export_id=%s user=%s sid=%s staging_filename=%s staging_filesize=%s stream_id=%s elevate_url=%s" % (export_id,user,sid,export_filename,filesize,self.stream_id,elevate_api))

                    #requests streaming upload logic                   
                    try:
                        with open(export_filename, newline='') as file:
                            
                            response = requests.post(elevate_api, headers=headers, data=file.read(),verify=False)
                            trimmed_response_text = response.text.replace("\n", " ")
                            if response.status_code == 200:
                                logger.info("event=exporting export_id=%s status=success response=%s http_code=%s" % (export_id,trimmed_response_text,response.status_code))

                            else:
                                logger.info("event=exporting export_id=%s status=failed response=%s http_code=%s" % (export_id,trimmed_response_text,response.status_code))

                            os.remove(export_filename)
                    except:
                        os.remove(export_filename)
                        logger.info("event=exporting export_id=%s status=error" % export_id)
                        self.system_error("Error streaming json data file to Elevate")
                    

                    
                else:
                    self.system_error("Error Exporting json data file, file to export %s can't be found  " % export_filename)
                

        except:
            self.system_error("Error exporting json data file %s " % traceback.format_exc())


dispatch(ElevatePush, sys.argv, sys.stdin, sys.stdout, __name__)