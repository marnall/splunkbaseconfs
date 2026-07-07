import os, sys
import time
import tarfile
import logging
import splunk 
import splunk.admin
import splunk.entity as entity

import json
import requests
import urllib 

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from splunklib.six.moves import range


# python dict to kv pairs
def dict_to_kv_pairs(d):
    return ' '.join(["{}={}".format(k, v) for k, v in d.items()])

def hostname_by_splunkd(g_lconfig):
    splunkurl = g_lconfig['url'] + '/services/admin/server-info?output_mode=json'
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + g_lconfig['token']}

    r = requests.get(splunkurl, headers=headers, verify=False)

    content = json.loads(r.content)
    return content['entry'][0]['content']['serverName']

def setup_logging():
    logger = logging.getLogger('kvbackup')    
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "cloud_backup.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')

    LOGGING_FORMAT = "%(asctime)s %(levelname)-s %(process)d %(module)s %(funcName)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a') 
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    # add stdout
    stdout_log_handler = logging.StreamHandler()
    stdout_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(stdout_log_handler)
    #logger.addHandler(logging.StreamHandler())
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)

    #default logging level , can be overidden in stanza config
    logger.setLevel(logging.DEBUG)
    return logger

def make_tarfile(output_filename, source_dirs):
    with tarfile.open(output_filename, "w:gz", bufsize=10240) as tar:
        for source_dir in source_dirs:
            tar.add(source_dir, arcname=os.path.basename(source_dir))

def upload_to_s3_bucket(endpoint_url, s3_key, s3_secret, s3_region, s3_bucket_name, s3_file, s3_key_name):
    import boto3
    s3 = boto3.client('s3', endpoint_url=endpoint_url, region_name=s3_region, aws_access_key_id=s3_key, aws_secret_access_key=s3_secret)
    s3.upload_file(s3_file, s3_bucket_name, s3_key_name)

def search_foldername_recursive(path, name):
    folders = []
    for root, dirs, files in os.walk(path):
        if name in dirs:
            folders.append(os.path.join(root, name))

    return folders

def determine_latest_file_in_dir(dir):
    files = os.listdir(dir)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(dir, x)))
    return files[-1]

def determin_latest_file_in_dir_extension(dir, extension):
    files = os.listdir(dir)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(dir, x)))
    for file in files:
        if file.endswith(extension):
            return file
    return None

def read_backup_configuration(g_lconfig, configname):
    entities = entity.getEntities(['storage', 'passwords'], namespace="cloud_backup", owner='nobody', sessionKey=g_lconfig['token'])           
    for i, c in entities.items():
        if c['eai:acl']['app'] ==  "cloud_backup":
            if c['username'] == configname:
                return json.loads(c['clear_password'])

def get_unix_timestamp():
    return int(time.time())

def shasum(filename):
    import hashlib
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

@Configuration()
class runme(GeneratingCommand):

    conn = Option(require=True)

    def generate(self):
        logging = setup_logging()
        logging.debug("starting cloud kvstore")

        # # # # # debugcode
        # import sys, os
        # sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
        # import splunk_debug as dbg
        # dbg.enable_debugging(timeout=25)

        # local dev
        auth_token = self.search_results_info.auth_token
        # used as primary identifier
        sid = self.search_results_info.sid
        hostname = 'https://localhost:8089'
        url = hostname + '/services/apps/local?output_mode=json&count=0'
        ssl_verify = False
        
        # read kvstore information
        g_config  = {
            'url': 'https://localhost:8089',
            'app': 'cloud_backup',
            'token': auth_token
        }

        s3config = read_backup_configuration(g_config, self.conn)
        if  s3config == None:
            raise Exception("No configuration found for name {}".format(self.conn))
            exit(-1)

        str_backup_start = get_unix_timestamp()
        # log to kvstore backuplog
        logentries = { 
            'sid': sid,
            'type': 'kvbackup',
            'target': s3config['name'],
            'status': 'started',
            'time_start': str_backup_start
        }

        logging.info(dict_to_kv_pairs(logentries))

        if len(s3config['s3_endpoint']) == 0:
            s3config['s3_endpoint'] = "https://s3.amazonaws.com"

        s3output = []
        s3output = s3config.copy()
        del s3output['s3_secret_key']
        logging.debug("s3 parameters: " + str(s3output) ) 

        # my path
        # dp0 = os.path.dirname(__file__)
        latest_backup_filename = determine_latest_file_in_dir(os.path.join(os.environ['SPLUNK_HOME'], 'var', 'lib', 'splunk','kvstorebackup'))
        latest_backup_path = os.path.join(os.environ['SPLUNK_HOME'], 'var', 'lib', 'splunk','kvstorebackup',latest_backup_filename)
        filename_date = hostname_by_splunkd(g_config) + "-" + latest_backup_filename
        output = "backupfile: " + str(latest_backup_path)
        yield {'_time': time.time(), '_raw': output}

        filesize_in_mb = round(os.path.getsize(latest_backup_path) / 1024 / 1024,2)
        #filename_only = s3config['s3_backup_prefix'] + time.strftime("%Y%m%d-%H%M%S") + '.tar.gz'
        output = "kvstore backup determinded: " + str(latest_backup_path) + " size: " + str(filesize_in_mb) + " MB" 
        yield {'_time': time.time(), '_raw': output}
        logging.info(output)

        output = "copy to s3 bucket: " + str(latest_backup_path)
        yield {'_time': time.time(), '_raw': output}

        shasum_file = shasum(latest_backup_path)
        logging.debug("starting s3 upload")
        upload_to_s3_bucket(s3config['s3_endpoint'], s3config['s3_access_key'], s3config['s3_secret_key'], s3config['s3_region'], s3config['s3_bucket'], latest_backup_path, filename_date)
        str_backup_end = get_unix_timestamp()
        logging.debug("finished s3 upload")

        logentries = { 
            'sid': sid,
            'type': 'kvbackup',
            'target': s3config['name'],
            'status': 'done',
            'time_start': str_backup_start,
            'time_end': str_backup_end,
            'filename': filename_date,
            'shasum': shasum_file,
            'sizeMB': filesize_in_mb
        }

        logging.info(dict_to_kv_pairs(logentries))

dispatch(runme, sys.argv, sys.stdin, sys.stdout, __name__)
