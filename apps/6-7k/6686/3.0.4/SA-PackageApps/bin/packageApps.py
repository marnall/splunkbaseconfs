import sys
import os
import logging
import splunk
import tarfile
import boto3
import time
from datetime import datetime, timedelta
import traceback
import requests
import math
try:
    import configparser
except ImportError:
    import ConfigParser as configparser  # type: ignore


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from azure.storage.blob import BlobClient

def setup_logging():
    """
     setup_logging as found on http://dev.splunk.com/view/logging/SP-CAAAFCN
    """
    logger = logging.getLogger('splunk.PackageApps')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "package_apps.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a') 
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger

logger = setup_logging()



@Configuration()
class package_Apps(GeneratingCommand):
	APP = Option(require=True)
	LOCALONLY = Option(require=False, validate=validators.Boolean(), default=False)
	AZURE = Option(require=False, validate=validators.Boolean(), default=False)
	VALID_SPLUNKBASE_APPS_FILE = 0
	def generateSplunkBaseAppsList(self):
		try:
			SPLUNK_HOME = os.environ['SPLUNK_HOME']
			if os.path.exists(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'local', 'SplunkBaseApps_UpdateTime.txt')):
				LastUpdated_time_String=open(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'local', 'SplunkBaseApps_UpdateTime.txt'), "r").read()
				LastUpdated_time = datetime.strptime(LastUpdated_time_String, '%d/%m/%Y %H:%M:%S')
				ValidFileTime=datetime.strptime((datetime.now()-timedelta(days=7)).strftime('%d/%m/%Y %H:%M:%S'),'%d/%m/%Y %H:%M:%S')
				if LastUpdated_time>ValidFileTime:
					self.VALID_SPLUNKBASE_APPS_FILE=1
					return

			SPLUNKBASE_API_URL="https://splunkbase.splunk.com/api/v1/app/"
			RETRIEVAL_LIMIT = 100
			SUCCESS_CODES = ["200", "201", "204"]
			PARAMS = {
						"limit": RETRIEVAL_LIMIT,
						"offset": 0,
						"order": "latest"
					}
			Total_pages=0
			Current_page=1

			response = requests.get(url=SPLUNKBASE_API_URL, params=PARAMS)
			if str(response.status_code) not in SUCCESS_CODES:
				logger.error("Error in invoking Splunkbase API : Response Code:" + response.status_code + " ::Response Message: " + response.content.decode("utf-8"))
				return
			apps = response.json()
			Total_pages = math.ceil(apps.get("total")/RETRIEVAL_LIMIT)
			Splunkbase_Apps_File = open(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'local','SplunkBaseApps.txt'),"w")
			results=apps.get("results",[])
			for appList in results:
				Splunkbase_Apps_File.write(appList.get("appid")+"\n")
			
			while(Total_pages>Current_page):
				Current_page = Current_page+1
				PARAMS["offset"] = PARAMS["offset"] + RETRIEVAL_LIMIT
				response = requests.get(url=SPLUNKBASE_API_URL, params=PARAMS)
				apps = response.json()
				results=apps.get("results",[])
				for appList in results:
					Splunkbase_Apps_File.write(appList.get("appid")+"\n")
			
			SplunkBaseApps_UpdateTime = open(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'local','SplunkBaseApps_UpdateTime.txt'),"w")
			SplunkBaseApps_UpdateTime.write(datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
			self.VALID_SPLUNKBASE_APPS_FILE=1
            	
		except:
			logger.error("Error Generating Splunkbase apps list using the API")


	def generate(self):
		try:
			AWS_CONF_FILE_CONTENTS = self.service.confs['aws_S3_config']['aws_creds']
			AWS_ACCESS_KEY_ID = AWS_CONF_FILE_CONTENTS['aws_access_key_id'].strip()
			BUCKET_NAME = AWS_CONF_FILE_CONTENTS['s3_bucket_name'].strip()
			AWS_SECRET_ACCESS_KEY = self.service.storage_passwords['aws_S3_config_realm:aws_access_key:'].clear_password.strip()
			SPLUNK_HOME = os.environ['SPLUNK_HOME']
			APPS = self.APP
			LOCALONLY = self.LOCALONLY
			AZURE = self.AZURE
			

			if APPS == "" or AWS_SECRET_ACCESS_KEY ==" " or BUCKET_NAME == "" or AWS_ACCESS_KEY_ID == "":
				yield {'_time': time.time(), '_raw': "Please setup the app properly" }
				return
			logger.info("All mandatory values obtained")

			if(AZURE == False):
				session = boto3.Session(aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
				s3 = session.resource('s3')
				logger.info("S3 Session established")
			else:
				azureConnString="DefaultEndpointsProtocol=https;AccountName=" + AWS_ACCESS_KEY_ID + ";AccountKey=" + AWS_SECRET_ACCESS_KEY + ";EndpointSuffix=core.windows.net"
			if not os.path.exists(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'app_packages')):
				os.makedirs(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'app_packages'))

			appsList=[]
			for appName in self.service.apps:
				appsList.append(appName['name'])
			logger.info("List of apps with access added")

			restricted_apps_file=open(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'bin', "cloud_restricted_apps.txt"),"r")
			RESTRICTED_APPS=[]
			for R_APP in restricted_apps_file:
				
				RESTRICTED_APPS.append(R_APP.strip())

			package_Apps.generateSplunkBaseAppsList(self)
			for APP in APPS.split(","):
				try:
					RESTRICTED=0
					if APP.startswith("100") or APP.startswith("0") or APP=="dmc" or APP=="dynamic-data-self-storage-app" or APP=="splunkclouduf" or APP=="cloud_administration":
						yield {'_time': time.time(), 'App_Name': APP, '_raw': "Failure: This is a Splunk Cloud restricted app and cannot be packaged"}
						continue
					for RESTRICTED_APP in RESTRICTED_APPS:
						if APP.startswith(RESTRICTED_APP.strip()):
							yield {'_time': time.time(), 'App_Name': APP, '_raw': "Failure: This is a Splunk Cloud restricted app and cannot be packaged"}
							RESTRICTED=1
							break
					if RESTRICTED==1:
						continue
						
					if not APP in appsList:
						yield {'_time': time.time(), 'App_Name': APP, '_raw': "Failure: You do not have access to this app/ app does not exist in the environment"}
						continue


					if(LOCALONLY == True):
						TAR_FILE_NAME = os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'app_packages' , APP +'_local.tar')
						APP_DIRECTORY = os.path.join(SPLUNK_HOME, 'etc' , 'apps' , APP, 'local')
						LOOKUPS_DIRECTORY = os.path.join(SPLUNK_HOME, 'etc' , 'apps' , APP, 'lookups')
						if(AZURE == True):
							Key = APP + "_local.tar"
							Bucket_Log = "Azure Container"
						else:	
							Key =  datetime.today().strftime("%d-%m-%Y") + "/" + APP + "_local_" + datetime.today().strftime("%H_%M") + ".tar"
							Bucket_Log = "S3 Bucket"
					else:
						SPLUNKBASE_CHECK=0
						if os.path.exists(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , APP , 'splunkbase.manifest')):
							yield {'_time': time.time(), 'App_Name': APP, '_raw': "Failure: This is a SplunkBase app. Export of local directory only allowed. Kindly execute with 'LOCALONLY=True'"}
							continue
						if os.path.exists(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'local', 'SplunkBaseApps.txt')) and self.VALID_SPLUNKBASE_APPS_FILE==1:
							if APP in open(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'local', 'SplunkBaseApps.txt')).read():
								FILE_PATH=os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'local', 'SplunkBaseApps.txt')
								SPLUNKBASE_CHECK=1
						elif os.path.exists(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'python_upgrade_readiness_app' , 'bin', 'libs_py3','pura_libs_utils','splunkbaseapps.csv')):
							if APP in open(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'python_upgrade_readiness_app' , 'bin', 'libs_py3','pura_libs_utils','splunkbaseapps.csv')).read():
								FILE_PATH=os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'python_upgrade_readiness_app' , 'bin', 'libs_py3','pura_libs_utils','splunkbaseapps.csv')
								SPLUNKBASE_CHECK=1						
						else:
							if APP in open(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'default', 'SplunkBaseApps.txt')).read():
								FILE_PATH=os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'default', 'SplunkBaseApps.txt')
								SPLUNKBASE_CHECK=1
						if SPLUNKBASE_CHECK==1:
							for line in open(FILE_PATH,'r').readlines():
								if line.__eq__(APP+'\n') or line.__eq__(APP) or line.__eq__('\n'+APP) or line.__eq__('\n'+APP+'\n'):
									logger.info("Splunkbase app App Name: " + APP + " not exported. LOCAL_ONLY=true not set")
									yield {'_time': time.time(), 'App_Name': APP, '_raw': "Failure: This is a SplunkBase app. Export of local directory only allowed. Kindly execute with 'LOCALONLY=True'"}
									SPLUNKBASE_CHECK=2
						if SPLUNKBASE_CHECK==2:
							continue
						app_config = configparser.ConfigParser()
						app_config.read(os.path.join(SPLUNK_HOME, 'etc' , 'apps' , APP , 'default', 'app.conf'))
						if "launcher" in app_config:
							if "author" in app_config['launcher']:
								if "splunk" in app_config['launcher']['author'].lower():
									yield {'_time': time.time(), 'App_Name': APP, '_raw': "Failure: This is a Splunk restricted app and cannot be packaged.  Kindly execute with 'LOCALONLY=True'"}
									continue

						TAR_FILE_NAME = os.path.join(SPLUNK_HOME, 'etc' , 'apps' , 'SA-PackageApps' , 'app_packages' , APP +'.tar')
						APP_DIRECTORY= os.path.join(SPLUNK_HOME, 'etc' , 'apps' , APP)

						if(AZURE == True):
							Key = APP + ".tar"
							Bucket_Log = "Azure Container"
						else:	
							Key =  datetime.today().strftime("%d-%m-%Y") + "/" + APP + "_" + datetime.today().strftime("%H_%M") + ".tar"
							Bucket_Log = "S3 Bucket"
					
					logger.info("TAR File Name" + TAR_FILE_NAME)
					logger.info("S3 File Name/ Azure BlobName=" + Key)
					if not os.path.exists(APP_DIRECTORY) and (LOCALONLY == True and not os.path.exists(LOOKUPS_DIRECTORY)):
						yield {'_time': time.time(), 'App_Name': APP, '_raw': "Failure: No App exist with the name " + APP + ", Directory=" + APP_DIRECTORY}
						continue
					with tarfile.open(TAR_FILE_NAME, "w:gz") as tar:
						if(os.path.exists(APP_DIRECTORY)):
							tar.add(APP_DIRECTORY, arcname=os.path.basename(APP_DIRECTORY))
						if(LOCALONLY == True and os.path.exists(LOOKUPS_DIRECTORY)):
							tar.add(LOOKUPS_DIRECTORY, arcname=os.path.basename(LOOKUPS_DIRECTORY))

					logger.info("Files added to TAR")

					if(AZURE == False):
						s3.meta.client.upload_file(Filename=TAR_FILE_NAME,Bucket=BUCKET_NAME,Key=Key)
					else:
						AzureBlob = BlobClient.from_connection_string(conn_str=azureConnString, container_name=BUCKET_NAME , blob_name=Key)
						with open(TAR_FILE_NAME, "rb") as data:
							AzureBlob.upload_blob(data,overwrite=True)

					os.remove(TAR_FILE_NAME)
					logger.info("Deleted generated TAR File from the Local Environment")
					
					self.logger.debug("Generating events")
					yield {'_time': time.time(), 'App_Name': APP, '_raw': "Success: App Packaged Successfully and uploaded to "+Bucket_Log+" - App Name: "+APP +" :: Directory=" + APP_DIRECTORY +" ,Package Name in "+Bucket_Log+": " + Key}
				except Exception as error:
					yield {'_time': time.time(), 'App_Name': APP, '_raw': "Failure: App packaging Unsuccessful."}
					logger.error(error)
		except Exception as error:
			yield {'_time': time.time(), '_raw': "Failure: App packaging Unsuccessful."}
			logger.error(error)
dispatch(package_Apps, sys.argv, sys.stdin, sys.stdout, __name__)


