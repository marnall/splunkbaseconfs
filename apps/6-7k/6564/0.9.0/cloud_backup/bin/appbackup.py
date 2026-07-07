import os, sys
import time
import tarfile
import requests
import logging
import splunk 
import splunk.admin
import splunk.entity as entity

import re 

import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
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
    logger = logging.getLogger('appbackup')    
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
            #tar.add(source_dir, arcname=os.path.basename(source_dir))
            tar.add(source_dir, arcname=source_dir)

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

def shasum(filename):
    import hashlib
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def read_backup_configuration(g_lconfig, configname):
    entities = entity.getEntities(['storage', 'passwords'], namespace="cloud_backup", owner='nobody', sessionKey=g_lconfig['token'])           
    for i, c in entities.items():
        if c['eai:acl']['app'] ==  "cloud_backup":
            if c['username'] == configname:
                return json.loads(c['clear_password'])
            

def get_unix_timestamp():
    return int(time.time())

@Configuration()
class runme(GeneratingCommand):

    apps = Option(require=True)
    conn = Option(require=True)
    userdirs = Option(require=False)

    def generate(self):

        # # # # # # # # debugcode
        # import sys, os
        # sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
        # import splunk_debug as dbg
        # dbg.enable_debugging(timeout=25)

        apps = self.apps.split(",")
        logging = setup_logging()
        logging.debug("starting backup for apps: " + self.apps)

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
        #logging.debug("s3config: " + str(s3config))
        # response = kv_search(g_config, 'backupconfig', {'name': self.conn})
        
        try:
            test = s3config["name"]
        
        except:
            output = "no backup config found for connection: " + self.conn
            logging.error("no backup config found for " + self.conn)
            yield {'_time': time.time(), '_raw': output}
            exit(-1)

        str_backup_start = get_unix_timestamp()
        # log to kvstore backuplog
        logentries = { 
            'sid': sid,
            'type': 'appbackup',
            'status': "started",
            'target': s3config['name'],
            'time_start': str_backup_start
        }

        logging.info(dict_to_kv_pairs(logentries))

        if self.userdirs == None:
            userdirs = False
        else:
            if self.userdirs.lower() == "t" or self.userdirs.lower() == "true":
                userdirs = True
            else:
                userdirs = False
        
        logging.debug("userdirs should be backuped: " + str(userdirs))

        if len(s3config['s3_endpoint']) == 0:
            s3config['s3_endpoint'] = "https://s3.amazonaws.com"
    
        if apps[0] == '*':
            apps = os.listdir(os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps'))
            self.logger.debug("backup all apps: " + str(apps))


        splunk_home = os.environ.get('SPLUNK_HOME')
        
        s3output = []
        s3output = s3config.copy()
        del s3output['s3_secret_key']
        logging.debug("s3 parameters: " + str(s3output) ) 

        filename_date =  hostname_by_splunkd(g_config) + "-" + time.strftime("%Y%m%d-%H%M%S")
        
        # # if not os.path.isdir(os.path.join(splunk_home, 'var', 'run', 'tmp')):
        # #     os.path.os.mkdir(os.path.join(splunk_home, 'var', 'run', 'tmp'))
        
        # # we have to backup to /tmp as /splunk/var/run/tmp is read only fs
        file_path = os.path.join('/','tmp', filename_date +'.tar.gz')

        appdirs = []
        for app in apps:
            if not os.path.join(splunk_home, 'etc', 'apps', app ):
                logging.error("directory "  + os.path.join(splunk_home, 'etc', 'apps', app ) + " does not exist. please check appname")

            # do not include splunk cloud specific apps
            if re.search("^[^1][^1-9]",app):
                appdirs.append(os.path.join(splunk_home, 'etc', 'apps', app))

            if userdirs == True:
                subfolders = search_foldername_recursive(os.path.join(splunk_home, 'etc', 'users'), app)
                for subfolder in subfolders:
                    appdirs.append(subfolder)
        
        os.chdir(os.path.join(splunk_home, 'etc'))
        relfolders = []
        for appdir in appdirs:
            relfolders.append(appdir.replace(os.path.join(splunk_home, 'etc'), "."))


        output = "backup folders:" + str(relfolders)
        yield {'_time': time.time(), '_raw': output}

        make_tarfile(file_path, relfolders)  
        #make_tarfile_no_scpfiles(file_path, relfolders)      

        filesize_in_mb = round(os.path.getsize(file_path) / 1024 / 1024,2)
        filename_only = os.path.basename(file_path) 
        output = "filesystem tar for apps: " + str(apps) + " size: " + str(filesize_in_mb) + " MB" 
        logging.info(output)
        yield {'_time': time.time(), '_raw': output}

        output = "local backup file: " + file_path
        yield {'_time': time.time(), '_raw': output}
        logging.info(output)

        shasum_file = shasum(file_path)
        logging.debug("starting s3 upload")
        upload_to_s3_bucket(s3config['s3_endpoint'], s3config['s3_access_key'], s3config['s3_secret_key'], s3config['s3_region'], s3config['s3_bucket'], file_path, filename_only)
        logging.info("finished s3 upload")

        str_backup_end = get_unix_timestamp()
        
        #get key of try 
        #response_key = kv_search(g_config, 'backuplog', {'sid': sid})
        
        logentries = { 
            'sid': sid,
            'type': 'appbackup',
            'status': "done",
            'target': s3config['name'],
            'time_start': str_backup_start,
            'time_end': str_backup_end,
            'filename': filename_only,
            'shasum': shasum_file,
            'sizeMB': filesize_in_mb
        }
        
        logging.info(dict_to_kv_pairs(logentries))
        os.remove(file_path)


dispatch(runme, sys.argv, sys.stdin, sys.stdout, __name__)
