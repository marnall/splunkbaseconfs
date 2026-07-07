'''
Custom Scripted Input for retrieving Geopoint CSV files from AWS S3 and loading them
into KVStore collections.

May 2021

Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Neustar
'''

import sys
import os
import re
import logging
import hashlib
import time
import traceback
import json
import gzip
import csv
from splunklib.client import connect
from splunklib.client import Service
from croniter import croniter
from datetime import datetime,timedelta
import splunk.entity as entity
import splunk.rest as rest
from logging.handlers import TimedRotatingFileHandler
import boto3
import botocore
from botocore.config import Config
from distutils.util import strtobool
from operator import attrgetter


#environment variables
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

#static app settings
APP_NAME = "neustar_app"
CONF_FILE = "neustar"
STANZA_NAME = "s3_download"

#for connecting to the Splunk REST API
SESSION_KEY = None
SPLUNK_SERVICE = None

#for interacting with the neustar.conf file
CONF_STANZA = None
CONF_STANZA_OBJECT = None


#default management port/host , but may be different sometimes
SPLUNK_PORT = 8089 
SPLUNK_HOST = "localhost"

#collections
KVSTORE_V4_COLLECTION = "geopoint_csv_ipv4" 
KVSTORE_V6_COLLECTION  = "geopoint_csv_ipv6"

#schemas
KVSTORE_V4_COLLECTION_SCHEMA = json.loads('{"field.anonymizer_status": "string", "field.area_code": "string", "field.asn": "string", "field.carrier": "string", "field.city": "string", "field.city_cf": "string", "field.city_ref_id": "string", "field.connection_type": "string", "field.continent": "string", "field.country": "string", "field.country_cf": "string", "field.country_code": "string", "field.dma": "string", "field.end_ip_int": "number", "field.end_ip_oct": "string", "field.geonames_id": "string", "field.home": "string", "field.hosting_facility": "string", "field.ip_routing_type": "string", "field.isic_code": "string", "field.latitude": "string", "field.line_speed": "string", "field.longitude": "string", "field.msa": "string", "field.naics_code": "string", "field.organization": "string", "field.organization_type": "string", "field.postal_code": "string", "field.postal_code_cf": "string", "field.proxy_last_detected": "string", "field.proxy_level": "string", "field.proxy_type": "string", "field.region": "string", "field.region_ref_id": "string", "field.sld": "string", "field.start_ip_int": "number", "field.start_ip_oct": "string", "field.state": "string", "field.state_cf": "string", "field.state_code": "string", "field.state_ref_id": "string", "field.time_zone": "string", "field.tld": "string"}')
KVSTORE_V6_COLLECTION_SCHEMA = json.loads('{"field.anonymizer": "string", "field.anonymizer_status": "string", "field.area_code": "string", "field.asn": "string", "field.carrier": "string", "field.city": "string", "field.city_cf": "string", "field.connection_type": "string", "field.continent": "string", "field.country": "string", "field.country_cf": "string", "field.country_code": "string", "field.dma": "string", "field.end_ip_2long_1": "string", "field.end_ip_2long_2": "string", "field.end_ip_3long_1": "number", "field.end_ip_3long_2": "number", "field.end_ip_3long_3": "number", "field.end_ip_full": "string", "field.end_ip_raw": "string", "field.end_ip_shortened": "string", "field.geonames_id": "string", "field.home": "string", "field.hosting_facility": "string", "field.ip_routing_type": "string", "field.isic_code": "string", "field.latitude": "string", "field.longitude": "string", "field.msa": "string", "field.naics_code": "string", "field.organization": "string", "field.organization_type": "string", "field.postal_code": "string", "field.proxy_last_detected": "string", "field.proxy_level": "string", "field.proxy_type": "string", "field.reg_area_code": "string", "field.reg_city": "string", "field.reg_continent": "string", "field.reg_country": "string", "field.reg_country_code": "string", "field.reg_dma": "string", "field.reg_latitude": "string", "field.reg_longitude": "string", "field.reg_msa": "string", "field.reg_postal_code": "string", "field.reg_region": "string", "field.reg_state": "string", "field.reg_time_zone": "string", "field.region": "string", "field.start_ip_2long_1": "string", "field.start_ip_2long_2": "string", "field.start_ip_3long_1": "number", "field.start_ip_3long_2": "number", "field.start_ip_3long_3": "number", "field.start_ip_full": "string", "field.start_ip_raw": "string", "field.start_ip_shortened": "string", "field.state": "string", "field.state_code": "string", "field.time_zone": "string"}')

#schema accelerations
KVSTORE_V4_COLLECTION_SCHEMA["accelerated_fields.ipv4_end_range"] = '{"end_ip_int": 1}'
KVSTORE_V4_COLLECTION_SCHEMA["accelerated_fields.ipv4_start_range"] = '{"start_ip_int": 1}'

KVSTORE_V6_COLLECTION_SCHEMA["accelerated_fields.ipv6_end_range"] = '{"end_ip_3long_1": 1, "end_ip_3long_2": 1, "end_ip_3long_3": 1}'
KVSTORE_V6_COLLECTION_SCHEMA["accelerated_fields.ipv6_start_range"] = '{"start_ip_3long_1": 1, "start_ip_3long_2": 1, "start_ip_3long_3": 1}'

#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","neustar_s3.log")

# Set up a specific logger
logger = logging.getLogger("neustar_s3")
logger.propagate = False

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)



#get the current datetime for cron based polling
def get_current_datetime_for_cron():
    current_dt = datetime.now()
    #dont need seconds/micros for cron
    current_dt = current_dt.replace(second=0, microsecond=0)
    return current_dt
            

#get encrypted credentials from the Splunk password store
def get_credentials():

   result = []
   try:
 
      for sp in SPLUNK_SERVICE.storage_passwords:
        values = {}
        values['username'] = sp.username or "none"
        values['clear_password'] = sp.clear_password or "none"
        result.append(values)

   except Exception as e:
      logger.error("Could not get credentials from splunk. Error: %s" % str(e))
      return result

   return result

#utility boolean parsing function
def string_to_bool(string):
    return bool(strtobool(str(string)))



#check if the CSV file on AWS S3 has updated from the currently loaded file   
def check_if_s3file_updated(file_ip_type,file_lastmod,file_version,file_date,file_category):

    #just testing based on version , but could extend to test on date and last modified also
    #also testing based on file_category ie: if user gets issued a different role and needs to update

    current_version = None
    current_category = None

    if file_ip_type == "v4":
        current_category = CONF_STANZA.get("ipv4_current_category",None)
        #current_date = CONF_STANZA.get("ipv4_current_date",None)
        current_version = CONF_STANZA.get("ipv4_current_version",0)
        #current_lastmodified = CONF_STANZA.get("ipv4_current_lastmodified",None)

    if file_ip_type == "v6":
        current_category = CONF_STANZA.get("ipv6_current_category",None)
        #current_date = CONF_STANZA.get("ipv6_current_date",None)
        current_version = CONF_STANZA.get("ipv6_current_version",0)
        #current_lastmodified= CONF_STANZA.get("ipv6_current_lastmodified",None)

    if current_version is None or current_category is None:
        return True
    elif int(file_version) > int(current_version):
        return True
    elif file_category != current_category:
        return True
    else:
        return False

#Read rows as dicts from a Gzipped CSV file
def gzipped_csv(filename):

    #will close file after "with" block ends
    with gzip.open(filename,'rt') as f:
        r = csv.DictReader(f, delimiter=',')
        for row in r:
            yield row

#Run the scripted input core logic
def run_script():

  try:

    logger.info("Getting AWS encrypted credentials")

    credentials_list = get_credentials()

    accessKeyId = None
    secretKeyId = None
    externalId = None
    awsAssumeRoleARN = None

    for c in credentials_list:
        if c['username'] == "access_key_id":
            accessKeyId = c['clear_password']
        if c['username'] == "secret_key_id":
            secretKeyId = c['clear_password']
        if c['username'] == "external_id":
            externalId = c['clear_password']
        if c['username'] == "aws_assumerole_arn":
            awsAssumeRoleARN = c['clear_password']

    if accessKeyId is None: 
        logger.error("AWS Access Key ID could not be found or has not been setup")
        return False
    if secretKeyId is None: 
        logger.error("AWS Secret Key ID could not be found or has not been setup")
        return False
    if externalId is None: 
        logger.error("AWS External ID could not be found or has not been setup")
        return False
    if awsAssumeRoleARN is None: 
        logger.error("AWS AssumeRole ARN could not be found or has not been setup")
        return False


    #defaults to 1 week
    polling_interval_string = CONF_STANZA.get("polling_interval","604800")
    
    if polling_interval_string.isdigit():
        polling_type = 'interval'
        polling_interval=int(polling_interval_string)   
    else:
        polling_type = 'cron'
        cron_start_date = datetime.now()
        cron_iter = croniter(polling_interval_string, cron_start_date)

    logger.info("Polling type is %s" % polling_type)


    logger.info("Getting AWS Connection settings")

    
    aws_proxy_https = CONF_STANZA.get("aws_proxy_https",None)
    aws_region = CONF_STANZA.get("aws_region",None)
    aws_connection_timeout = int(CONF_STANZA.get("aws_connection_timeout",60))
    aws_read_timeout = int(CONF_STANZA.get("aws_read_timeout",60)) 
    aws_retry_maxattempts = int(CONF_STANZA.get("aws_retry_maxattempts",10))
    aws_retry_mode = CONF_STANZA.get("aws_retry_mode","standard")
    aws_assumerole_duration = int(CONF_STANZA.get("aws_assumerole_duration",3600))
    aws_assumerole_sessionname = CONF_STANZA.get("aws_assumerole_sessionname","NeustarGeopointAssumeRole")

  

    s3_config = Config(
        region_name=aws_region,
        connect_timeout= aws_connection_timeout,
        read_timeout= aws_read_timeout,
        proxies={
        'https': aws_proxy_https
        },
        retries= {
            'max_attempts': aws_retry_maxattempts,
            'mode': aws_retry_mode
        }
        
    )


    geopoint_bucket = CONF_STANZA.get("geopoint_bucket","geopoint")
    file_suffix = CONF_STANZA.get("file_suffix","csv.gz")
    ipv4_filename_pattern = CONF_STANZA.get("ipv4_filename_pattern","v(.*)_(\\d*)\\.(.*)")
    ipv6_filename_pattern = CONF_STANZA.get("ipv6_filename_pattern","IPv6_v(.*)_(\\d*)\\.(.*)")
    stream_content = string_to_bool(CONF_STANZA.get("stream_content","false"))
    local_root_download_directory = CONF_STANZA.get("local_root_download_directory","s3_downloads")
    delete_after_processing = string_to_bool(CONF_STANZA.get("delete_after_processing","true"))
    perform_checksum_on_download = string_to_bool(CONF_STANZA.get("perform_checksum_on_download","false"))
    kvstore_batch_save_size  = int(CONF_STANZA.get("kvstore_batch_save_size",500))
    #internal dev/test settings
    dev_mode = string_to_bool(CONF_STANZA.get("dev_mode","false"))
    dev_mode_limit  = int(CONF_STANZA.get("dev_mode_limit",100))

    if dev_mode:
        logger.info("Running in Dev Mode")
                                        


    while True:
             
        logger.info("Entered Execution Loop")

        if polling_type == 'cron':
            next_cron_firing = cron_iter.get_next(datetime)
            CONF_STANZA_OBJECT.update(polling_script_current_status="Waiting until next CRON execution at %s" % next_cron_firing.strftime("%d-%m-%Y %H:%M:%S"))
            while get_current_datetime_for_cron() != next_cron_firing:
                time.sleep(float(10))
        try:

            logger.info("Executing.....")

            logger.info("Creating AWS STS client")
            # create an STS client object that represents a live connection to the STS service
            try:
                sts_client = boto3.client('sts',aws_access_key_id=accessKeyId,aws_secret_access_key=secretKeyId,config=s3_config)
            except botocore.exceptions.ClientError as error:
                CONF_STANZA_OBJECT.update(polling_script_last_execution_status="AWS STS connection failed")
                logger.error("Couldn't instantiate AWS STS Client %s " % error)
                time.sleep(float(30))
                continue

            # Call the assume_role method of the STSConnection object and pass the role ARN and a role session name.
            logger.info("Assuming role")

            try:
                assumed_role_object=sts_client.assume_role(
                    DurationSeconds=aws_assumerole_duration,
                    RoleArn=awsAssumeRoleARN,
                    RoleSessionName=aws_assumerole_sessionname,
                    ExternalId=externalId
                )
            except botocore.exceptions.ClientError as error:
                CONF_STANZA_OBJECT.update(polling_script_last_execution_status="AWS STS Assume Role failed")
                logger.error("Couldn't AssumeRole %s " % error)
                time.sleep(float(30))
                continue


            # From the response that contains the assumed role, get the temporary 
            # credentials that can be used to make subsequent API calls
            credentials=assumed_role_object['Credentials']

            # Use the temporary credentials that AssumeRole returns to make a 
            # connection to Amazon S3 
            logger.info("Getting AWS S3 Resource")

            try:
                s3_resource=boto3.resource(
                    's3',
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken'],
                )
                s3_resource_client = s3_resource.meta.client
            except botocore.exceptions.ClientError as error:
                CONF_STANZA_OBJECT.update(polling_script_last_execution_status="AWS S3 connection failed")
                logger.error("Couldn't Get AWS S3 Resource %s " % error)
                time.sleep(float(30))
                continue


            logger.info("Getting AWS S3 Bucket %s" % geopoint_bucket)

            try : 
                my_bucket = s3_resource.Bucket(geopoint_bucket)
            except botocore.exceptions.ClientError as error:
                CONF_STANZA_OBJECT.update(polling_script_last_execution_status="AWS S3 %s bucket not accessible " % geopoint_bucket)
                logger.error("Couldn't Get AWS S3 Bucket %s " % error)
                time.sleep(float(30))
                continue

            logger.info("Getting Bucket Objects")
            #for file in my_bucket.objects.all():
            for file in sorted(my_bucket.objects.all(), key=attrgetter('size')):
                #file metadata
                file_key = file.key
                file_lastmod = file.last_modified
                file_size = file.size

                #we only want the CSV files
                if file_key.endswith(file_suffix):
                    
                    logger.info("Inspecting file name : %s , size : %s , last_modified : %s" % (file_key,file_size,file_lastmod))
                    dir_name = os.path.dirname(file_key)
                    file_name = os.path.basename(file_key)

                    file_category = dir_name.split("/",1)[0]
                    if dir_name.endswith("v4"):
                        file_ip_type="v4"
                        filename_search = re.search(ipv4_filename_pattern, file_name, re.IGNORECASE)
                        if filename_search:
                            file_version = filename_search.group(1)
                            file_date = filename_search.group(2)

                    if dir_name.endswith("v6"):
                        file_ip_type="v6"
                        filename_search = re.search(ipv6_filename_pattern, file_name, re.IGNORECASE)

                        if filename_search:
                            file_version = filename_search.group(1)
                            file_date = filename_search.group(2)
                    
                    
                    
                    if check_if_s3file_updated(file_ip_type,file_lastmod,file_version,file_date,file_category):               
                        
                        logger.info("File on S3 is an updated version of currently loaded file")


                        if not stream_content:    
                        
                            output_directory = os.path.join(SPLUNK_HOME,"etc","apps","neustar_app",local_root_download_directory,dir_name)
                         
                            logger.info("Downloading file %s to %s" % (file_name,output_directory))


                            if not os.path.exists(output_directory):
                                os.makedirs(output_directory)

                            output_file = os.path.join(output_directory,file_name)

                            logger.info("Starting download....")

                            #CSV file download
                            try:
                                CONF_STANZA_OBJECT.update(polling_script_current_status="Downloading new dataset %s" % file_key)
                                my_bucket.download_file(file_key,output_file)

                            except botocore.exceptions.ClientError as error:
                                CONF_STANZA_OBJECT.update(polling_script_last_execution_status="Couldn't download CSV file %s " % file_key)
                                logger.error("Couldn't download CSV file %s %s " % (file_key,error))
                                time.sleep(float(30))
                                continue

                            if perform_checksum_on_download:
                                #checksum file
                                logger.info("Performing MD5 checksum")
                                CONF_STANZA_OBJECT.update(polling_script_current_status="Performing checksum on new dataset %s" % file_key)
                                try:
                                    logger.info("Downloading checksum file")
                                    my_bucket.download_file(file_key+".MD5",output_file+".MD5")

                                    with open(output_file+".MD5", 'r') as md5_file:
                                        md5_file_digest = md5_file.read().replace('\n', '')
                                        md5_file_digest = md5_file_digest.split()[0]


                                    logger.info("Calculating hash on CSV file")
                                    md5_hash = hashlib.md5()
                                    with open(output_file,"rb") as f:
                                        # Read and update hash in chunks of 4K
                                        for byte_block in iter(lambda: f.read(4096),b""):
                                            md5_hash.update(byte_block)
                                        csv_file_digest = md5_hash.hexdigest()

                                    logger.info("Comparing MD5 digest")
                                    if md5_file_digest.lower() == csv_file_digest.lower():
                                        logger.info("File download MD5 checksum passed")
                                    else:
                                        CONF_STANZA_OBJECT.update(polling_script_last_execution_status="MD5 Checksum failed for file %s " % file_key)
                                        logger.error("File download MD5 checksum failed")
                                        time.sleep(float(30))
                                        continue


                                except botocore.exceptions.ClientError as error:
                                    logger.error("Couldn't download MD5 checksum file %s " % error)
                                    #skip the checksum if the file couldn't be downloaded
                                    #time.sleep(float(30))
                                    #continue

                            
                            logger.info("Download completed")

                            
                        logger.info("Loading data into KVStore Collection")

                        #KVStore processing
                        collection_obj = None

                        if file_ip_type == "v4":
                            logger.info("Loading an IPV4 KVStore Collection")
                            CONF_STANZA_OBJECT.update(polling_script_current_status="Loading new IPV4 KVStore Collection")

                            if KVSTORE_V4_COLLECTION in SPLUNK_SERVICE.kvstore:
                                logger.info("Dropping previous IPV4 data collection")
                                SPLUNK_SERVICE.kvstore.delete(KVSTORE_V4_COLLECTION)

                            logger.info("Creating new IPV4 data collection")
                            SPLUNK_SERVICE.kvstore.create(KVSTORE_V4_COLLECTION,**KVSTORE_V4_COLLECTION_SCHEMA)

                            try:
                                #set ACL permissions on the collection
                                logger.info("Setting access permissions on IPV4 data collection")
                                aclUrl = "/servicesNS/nobody/"  + APP_NAME + "/storage/collections/config/"+ KVSTORE_V4_COLLECTION + "/acl"
                                postArgs = {"perms.write": "*", "perms.read":  "*", "sharing": "global", "owner": "nobody"}
                                rest.simpleRequest(aclUrl, sessionKey=SESSION_KEY, postargs=postArgs, method='POST', raiseAllErrors=True)
                            except:   
                                logger.error("Error setting access permissions on IPV4 data collection : %s" % traceback.format_exc())

 
                            collection_obj = SPLUNK_SERVICE.kvstore[KVSTORE_V4_COLLECTION]


                        if file_ip_type == "v6":
                            logger.info("Loading an IPV6 KVStore Collection")
                            CONF_STANZA_OBJECT.update(polling_script_current_status="Loading new IPV6 KVStore Collection")

                            if KVSTORE_V6_COLLECTION in SPLUNK_SERVICE.kvstore:
                                logger.info("Dropping previous IPV6 data collection")
                                SPLUNK_SERVICE.kvstore.delete(KVSTORE_V6_COLLECTION)

                            logger.info("Creating new IPV6 data collection")
                            SPLUNK_SERVICE.kvstore.create(KVSTORE_V6_COLLECTION,**KVSTORE_V6_COLLECTION_SCHEMA)

                            try:
                                #set ACL permissions on the collection
                                logger.info("Setting access permissions on IPV6 data collection")
                                aclUrl = "/servicesNS/nobody/"  + APP_NAME + "/storage/collections/config/"+ KVSTORE_V6_COLLECTION + "/acl"
                                postArgs = {"perms.write": "*", "perms.read":  "*", "sharing": "global", "owner": "nobody"}
                                rest.simpleRequest(aclUrl, sessionKey=SESSION_KEY, postargs=postArgs, method='POST', raiseAllErrors=True)
                            except:   
                                logger.error("Error setting access permissions on IPV6 data collection : %s" % traceback.format_exc())

                            collection_obj = SPLUNK_SERVICE.kvstore[KVSTORE_V6_COLLECTION]


                        
                        logger.info("Starting Batch Save operation on KVStore")
                        #perform batch save
                        if not collection_obj is None:
                            batch = []
                            current_batch_size=0;
                            total_rows_read_from_csv=0
                            total_rows_saved_to_kvstore=0

                            #for calculating IPv4 missing ranges
                            current_start_int = 0
                            current_end_int = 0
            

                            if stream_content:

                                logger.info("Streaming CSV Content from AWS S3")


                                try:
                                    select_query = "SELECT * FROM s3object"
                                    if dev_mode:
                                        select_query = select_query+" limit "+str(dev_mode_limit)

                                    #need to use the resource object's underlying low level client
                                    resp = s3_resource_client.select_object_content(
                                        Bucket=geopoint_bucket,
                                        Key=file_key,
                                        ExpressionType='SQL',
                                        RequestProgress={'Enabled': True},
                                        Expression=select_query,
                                        InputSerialization = {'CSV': {"FileHeaderInfo": "Use"}, 'CompressionType': 'GZIP'},
                                        OutputSerialization = {'JSON': {}},
                                    )
                                except botocore.exceptions.ClientError as error:
                                    CONF_STANZA_OBJECT.update(polling_script_last_execution_status="Couldn't stream CSV content %s " % file_key)
                                    logger.error("Couldn't stream S3 Object Content %s " % error)
                                    time.sleep(float(30))
                                    continue


                                # This is the event stream in the response
                                event_stream = resp['Payload']
                                end_event_received = False
                                carryover_json_chunk = ""
                                # Iterate over events in the event stream as they come
                                for event in event_stream:
                                    # If we received a records event, write the data to a file
                                    if 'Records' in event:
                                        records = event['Records']['Payload'].decode('utf-8')
                                        record_items = (carryover_json_chunk+records).splitlines()

                                        for record_item in record_items:
                                            
                                            try:
                                                json_record_item = json.loads(record_item)

                                                if file_ip_type == "v4":
                                                    #calculate missing ranges
                                                    if current_start_int == 0:
                                                        current_start_int = int(json_record_item["end_ip_int"])
                                                    else:
                                                        current_end_int = int(json_record_item["start_ip_int"])

                                                        if current_end_int - current_start_int > 1:
                                                            missing_batch_row = {}
                                                            missing_batch_row["start_ip_int"] = current_start_int + 1
                                                            missing_batch_row["end_ip_int"] = current_end_int - 1

                                                            batch.append(missing_batch_row)
                                                            current_batch_size += 1

                                                            if current_batch_size >= kvstore_batch_save_size:
                                                                #batch save 
                                                                logger.info("Performing Batch Save operation on KVStore ,  current_batch_size=%s " % current_batch_size)
                                                                
                                                                collection_obj.data.batch_save(*batch)
                                                                total_rows_saved_to_kvstore += current_batch_size
                                                                logger.info("Batch Save operation complete,  total_rows_read_from_csv=%s total_rows_saved_to_kvstore=%s" % (total_rows_read_from_csv,total_rows_saved_to_kvstore))
                                                                
                                                                #reset counters and batch dict array
                                                                batch = []
                                                                current_batch_size=0;

                                                        current_start_int = int(json_record_item["end_ip_int"])



                                                batch.append(json_record_item)
                                            except ValueError as e:
                                                carryover_json_chunk = record_item.strip()
                                                continue
                                            

                                            current_batch_size += 1
                                            total_rows_read_from_csv += 1

                                            if current_batch_size >= kvstore_batch_save_size:
                                                #batch save 
                                                logger.info("Performing Batch Save operation on KVStore ,  current_batch_size=%s " % current_batch_size)
                                                
                                                collection_obj.data.batch_save(*batch)
                                                total_rows_saved_to_kvstore += current_batch_size
                                                logger.info("Batch Save operation complete,  total_rows_read_from_csv=%s total_rows_saved_to_kvstore=%s" % (total_rows_read_from_csv,total_rows_saved_to_kvstore))
                                                
                                                #reset counters and batch dict array
                                                batch = []
                                                current_batch_size=0;
                                    # If we received a progress event, print the details
                                    elif 'Progress' in event:
                                        logger.info('Streaming progress %s ' % event['Progress']['Details'])
                                    # End event indicates that the request finished successfully
                                    elif 'End' in event:
                                        logger.info('Streaming is complete')
                                        end_event_received = True
                                if not end_event_received:
                                    logger.error("Streaming end event not received, request incomplete")
                                else:
                                    logger.info('Streaming end event received, closing event stream')
                                    event_stream.close()


                            else:

                                logger.info("Reading in downloaded CSV Content")

                                for row in gzipped_csv(output_file):

                                    if file_ip_type == "v4":
                                        #calculate missing ranges
                                        if current_start_int == 0:
                                            current_start_int = int(row["end_ip_int"])
                                        else:
                                            current_end_int = int(row["start_ip_int"])

                                            if current_end_int - current_start_int > 1:
                                                missing_batch_row = {}
                                                missing_batch_row["start_ip_int"] = current_start_int + 1
                                                missing_batch_row["end_ip_int"] = current_end_int - 1

                                                batch.append(missing_batch_row)
                                                current_batch_size += 1

                                                if current_batch_size >= kvstore_batch_save_size:
                                                    #batch save 
                                                    logger.info("Performing Batch Save operation on KVStore ,  current_batch_size=%s " % current_batch_size)
                                                    
                                                    collection_obj.data.batch_save(*batch)
                                                    total_rows_saved_to_kvstore += current_batch_size
                                                    logger.info("Batch Save operation complete,  total_rows_read_from_csv=%s total_rows_saved_to_kvstore=%s" % (total_rows_read_from_csv,total_rows_saved_to_kvstore))
                                                    
                                                    #reset counters and batch dict array
                                                    batch = []
                                                    current_batch_size=0;

                                            current_start_int = int(row["end_ip_int"])



                                    batch.append(row)
                                    current_batch_size += 1
                                    total_rows_read_from_csv += 1

                                    if dev_mode:
                                        if total_rows_read_from_csv >= dev_mode_limit:
                                            break

                                    if current_batch_size >= kvstore_batch_save_size:
                                        #batch save 
                                        logger.info("Performing Batch Save operation on KVStore ,  current_batch_size=%s " % current_batch_size)
                                        
                                        collection_obj.data.batch_save(*batch)
                                        total_rows_saved_to_kvstore += current_batch_size
                                        logger.info("Batch Save operation complete,  total_rows_read_from_csv=%s total_rows_saved_to_kvstore=%s" % (total_rows_read_from_csv,total_rows_saved_to_kvstore))
                                        
                                        #reset counters and batch dict array
                                        batch = []
                                        current_batch_size=0;
                                


                            #batch save any remaining items
                            if len(batch) > 0:
                                logger.info("Performing Batch Save operation on KVStore ,  current_batch_size=%s " % current_batch_size)                               
                                collection_obj.data.batch_save(*batch)
                                total_rows_saved_to_kvstore += current_batch_size
                                logger.info("Batch Save operation complete,  total_rows_read_from_csv=%s total_rows_saved_to_kvstore=%s" % (total_rows_read_from_csv,total_rows_saved_to_kvstore))
                                batch = []
                                current_batch_size=0;
                                        

                            FILE_STATE = {}
                            current_dt = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                            FILE_STATE["polling_script_last_execution_status"] = "Succeeded loading new dataset %s" % file_key
                            #once all has succeeded , persist stateful settings about the currently loaded data
                            
                            if file_ip_type == "v4":
                                FILE_STATE["ipv4_current_category"] =  file_category
                                FILE_STATE["ipv4_current_filename"] = file_key
                                FILE_STATE["ipv4_current_date"] = file_date
                                FILE_STATE["ipv4_current_version"] = file_version
                                FILE_STATE["ipv4_current_lastmodified"] = file_lastmod
                                FILE_STATE["ipv4_current_kvstore_load_date"] = current_dt
                                FILE_STATE["ipv4_current_filesize"] = file_size
                                FILE_STATE["ipv4_current_source"] = "streamed" if stream_content else "file downloaded"


                            if file_ip_type == "v6":
                                FILE_STATE["ipv6_current_category"] =  file_category
                                FILE_STATE["ipv6_current_filename"] = file_key
                                FILE_STATE["ipv6_current_date"] = file_date
                                FILE_STATE["ipv6_current_version"] = file_version 
                                FILE_STATE["ipv6_current_lastmodified"] = file_lastmod
                                FILE_STATE["ipv6_current_kvstore_load_date"] = current_dt
                                FILE_STATE["ipv6_current_filesize"] = file_size
                                FILE_STATE["ipv6_current_source"] = "streamed" if stream_content else "file downloaded"
                                


                            CONF_STANZA_OBJECT.update(**FILE_STATE)

                            CONF_STANZA.update(FILE_STATE)


                            logger.info("File loading into KVStore has completed successfully")

                        else:
                            CONF_STANZA_OBJECT.update(polling_script_last_execution_status= "No KVStore Collection for the file type %s could be found " % file_ip_type)
                            logger.error("No KVStore Collection for the file type %s could be found " % file_ip_type)
                            
                      

                        if not stream_content and delete_after_processing:
                            if os.path.exists(output_file):
                                logger.info("Deleting file %s " % output_file)
                                os.remove(output_file)
                            if os.path.exists(output_file+".MD5"):
                                logger.info("Deleting file %s " % output_file+".MD5")
                                os.remove(output_file+".MD5")
                    else:
                        CONF_STANZA_OBJECT.update(polling_script_last_execution_status="No new datasets found to load")
                        logger.info("File on S3 is not an updated version of currently loaded file")

        except:  
            CONF_STANZA_OBJECT.update(polling_script_last_execution_status="Failed (refer to logs)")                                  
            #e = sys.exc_info()[0]  
            logger.error("Error : %s" % traceback.format_exc())

        if polling_type == 'interval': 
            logger.info("Sleeping until next Interval time firing")
            current_dt = datetime.now()
            added_seconds = timedelta(seconds=polling_interval)
            next_firing_time = current_dt + added_seconds
            CONF_STANZA_OBJECT.update(polling_script_current_status="Waiting until next execution at %s" % next_firing_time.strftime("%d-%m-%Y %H:%M:%S"))                        
            time.sleep(float(polling_interval))
    
 
  except:  
    CONF_STANZA_OBJECT.update(polling_script_last_execution_status="Failed (refer to logs)")
    #e = sys.exc_info()[0]  
    logger.error("Error : %s" % traceback.format_exc())
    return False

  


if __name__ == '__main__':

    logger.info("Running Neustar S3 Download script")
   
    try:
        sk = sys.stdin.readline().strip()

        logger.info("Getting the session key")

        SESSION_KEY = re.sub(r'sessionKey=', "", sk)

        logger.info("Getting the Splunk management port and host")

        server_settings = entity.getEntity('/server','settings', namespace=APP_NAME, owner='nobody', sessionKey=SESSION_KEY)

        SPLUNK_PORT = server_settings['mgmtHostPort']
        SPLUNK_HOST = server_settings['host']

        logger.info("Port %s " % SPLUNK_PORT)
        logger.info("Host %s " % SPLUNK_HOST)

        logger.info("Getting the Splunk SDK Service")

        service_args = {'host':SPLUNK_HOST,'port':SPLUNK_PORT,'token':SESSION_KEY,'owner':'nobody','app':APP_NAME,'sharing':'global'}
        SPLUNK_SERVICE = Service(**service_args)  

     
        logger.info("Reading in the settings stanza from neustar.conf")

        CONF_STANZA_OBJECT = SPLUNK_SERVICE.confs[CONF_FILE][STANZA_NAME]

        #prune out None values so our defaults kick in
        CONF_STANZA = {k: v for k, v in CONF_STANZA_OBJECT.content().items() if v is not None}

        #change log level from configuration stanza if present
        log_level = logging.getLevelName(CONF_STANZA.get("log_level","INFO"))
        logger.setLevel(log_level)

        run_status = run_script()

        if not run_script:
            raise Exception("Polling script failed to initialize")
    except: 
        if not CONF_STANZA_OBJECT is None:
            CONF_STANZA_OBJECT.update(polling_script_last_execution_status="Failed to initialize script (refer to logs)") 
        #e = sys.exc_info()[0]  
        logger.error("Error : %s" % traceback.format_exc())