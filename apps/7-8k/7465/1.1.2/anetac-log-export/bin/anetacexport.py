# encoding = utf-8
import gzip
import json
import shutil
import sys
import os
from datetime import datetime
import boto3
import logging

# Need this to find splunklib module
splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'anetac-log-export', 'lib'))
from splunklib.searchcommands import EventingCommand, Configuration, dispatch

logger = logging.getLogger() # Root-level logger
logger.setLevel(logging.INFO)
logfile = logging.StreamHandler(open(os.path.join(splunkhome, 'var', 'log', 'anetac-log-export.log'), "a"));
logfile.setLevel(logging.INFO)
logfile.setFormatter(logging.Formatter('%(asctime)s [%(process)06d] %(levelname)-8s %(name)s:  %(message)s'))
logger.addHandler(logfile)

# Define class and type for Splunk command
@Configuration()
class anetacexport(EventingCommand):
    '''
    **Syntax:**
    search | send_to_anetac

    **Description:
    Export Splunk events to AWS S3 bucket in Anetac SaaS in newline delimited JSON format
    '''

    def transform(self, events):
        logger.info('Starting anetacexport command')
        try:
            secrets = self.service.storage_passwords
            for secret in secrets:
                if secret.realm.find("anetac-log-export") > -1:
                    secret_json = json.loads(secret.clear_password)
                    aws_secret_key = secret_json['aws_secret_key']
                    break

            aws_key_id = self.service.confs['anetac_log_export_settings']['additional_parameters'].aws_key_id
            bucket_name = self.service.confs['anetac_log_export_settings']['additional_parameters'].bucket_name
            aws_region = self.service.confs['anetac_log_export_settings']['additional_parameters'].aws_region

            timenow = datetime.now()
            folder_sfx = timenow.strftime("%Y-%m-%d")
            file_name = timenow.strftime("%H-%M-%S")
            object_key = f"datadrop/{folder_sfx}/splunk_cmd_{file_name}.json"

            app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
            tmp_file = os.path.join(app_dir, f"temp-{folder_sfx}-{file_name}.json")

            logger.info(f"Writing events to file {tmp_file}")
            with open(tmp_file, 'w') as f:
                for result in events:
                    f.write(json.dumps(result) + "\n")
                    yield result

            s3 = boto3.client('s3',
                              aws_access_key_id=aws_key_id,
                              aws_secret_access_key=aws_secret_key,
                              region_name=aws_region)


            # gzip the temp file using python gzip module
            tmp_file_gz = tmp_file + '.gz'
            logger.info(f"Compressing file {tmp_file} to {tmp_file_gz}")
            with open(tmp_file, 'rb') as f_in:
                with gzip.open(tmp_file_gz, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            os.remove(tmp_file)
            object_key += ".gz"
            s3.upload_file(tmp_file_gz, bucket_name, object_key)
            os.remove(tmp_file_gz)

            logger.info(f"anetacexport completed. File uploaded to {object_key}")

        except Exception as e:
            logger.error(f"Error while uploading file to S3: {str(e)}")

dispatch(anetacexport, sys.argv, sys.stdin, sys.stdout, __name__)