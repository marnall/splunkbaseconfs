#!/usr/bin/python

"""
This is the main entry point for TA-QualysCloudPlatform
"""

# Standard imports
from __future__ import print_function
import time
import sys, os
import signal

# dynamically load all the .whl files
TA_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
WHL_DIR = TA_ROOT + "/bin/whl/"
for filename in os.listdir(WHL_DIR):
	if filename.endswith(".whl"):
		sys.path.insert(0, WHL_DIR + filename)

import re
from datetime import datetime, timedelta
import traceback
import logging
import fcntl, sys
import json
from six.moves.urllib.parse import urlparse
from io import open
from file_read_backwards import FileReadBackwards

from defusedxml import ElementTree as ET

# Splunk imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.splunklib.modularinput import *
import splunk.clilib.cli_common as scc
import splunk.entity as entity
from splunk_cluster import ServerInfo

# Qualys imports
import qualysModule.qualys_log_populator
import qualysModule.splunkpopulator.utils
from qualysModule.splunkpopulator.utils import get_password
from qualysModule.application_configuration import *
from qualysModule import qlogger
import qualysModule.lib.api as qapi
from qualysModule.splunkpopulator.utils import bool_value
from qualysModule.Constants import *


# Import modules coming from those egg files.
from croniter import croniter

qualysModule.enableLogger()
qlogger = logging.getLogger(QUALYS_APP_NAME)
ew = EventWriter()

#CONSTANTS
SERVICES_BEHIND_GATEWAY = ['fim_events', 'fim_ignored_events', 'fim_incidents', 'edr_events','cs_container_vulns','cs_image_vulns','sem_detection','pcrs_posture_info','cyber_security_asset_management','certview_certificates']
TOTALCLOUD_CSPM_DATA_INPUT = ['aws_cspm_events','gcp_cspm_events','azure_cspm_events']
GATEWAY_URL_PREFIX = "https://gateway"
GUARD_URL_PREFIX = "https://qualysguard"
API_SERVER_URL_PREFIX = "https://qualysapi"
#qualys_platforms_url_map is a map of urls not having 'apps' in url; new pods apis are having apps in name
#e.g. https://qualysapi.qg1.apps.qualys.in, https://qualysapi.qg2.apps.qualys.eu
QUALYS_PLATFORMS_URLS_NOT_HAVING_apps = [
	"https://gateway.qg1.apps.qualys.com", "https://qualysapi.qualys.com", "https://qualysguard.qualys.com",
	"https://gateway.qg1.apps.qualys.eu", "https://qualysguard.qualys.eu","https://qualysapi.qualys.eu"
]

class QualysScript(Script):
	def get_scheme(self):
		scheme = Scheme("Qualys Technology Add-On")
		scheme.description = "Add-On for Qualys"
		scheme.use_external_validation = True
		# scheme.streaming_mode = "xml"
		scheme.use_single_instalce = False

		name_argument = Argument("name")
		name_argument.description = "Qualys Sources"
		scheme.add_argument(name_argument)

		duration_argument = Argument("duration")
		duration_argument.description = "Interval between subsequent runs (in seconds)"
		duration_argument.required_on_create = False
		duration_argument.required_on_edit = False
		scheme.add_argument(duration_argument)

		start_date_argument = Argument("start_date")
		start_date_argument.description = "Fetch data after this date"
		start_date_argument.required_on_create = False
		start_date_argument.required_on_edit = False
		scheme.add_argument(start_date_argument)

		return scheme

	def validate_input(self, validation_definition):
		if validation_definition.metadata.get("name") != "knowledge_base" and qualysModule.splunkpopulator.utils.is_valid_data_input_startDate(validation_definition.parameters.get("start_date"),validation_definition.metadata.get("name")): pass
		if qualysModule.splunkpopulator.utils.is_valid_cron(validation_definition.metadata.get("name"),validation_definition.parameters.get("duration")):
			pass
		return

	def stream_events(self, inputs, ew):
		session_key = inputs.metadata.get('session_key')
		server_uri = inputs.metadata.get('server_uri')
		checkpoint_dir = inputs.metadata.get("checkpoint_dir", "./")
		server_info = ServerInfo(server_uri, session_key)
		ta_version = "Unidentified"

        # Enable debug mode if set in TA setup form
		try:
			qualysConf = scc.getMergedConf("qualys")
			if qualysConf['setupentity']['enable_debug'] == '1':
				qualysModule.enableDebug(True)
				qlogger.setLevel(logging.DEBUG)
				for handler in qlogger.handlers:
					handler.setLevel(logging.DEBUG)
		except Exception as e:
			pass

		for input_name, input_item in list(inputs.inputs.items()):
			pure_input_name = input_name.replace("qualys://", "")
			qualysModule.enableLogger(pure_input_name)
			host = input_item.get('host', 'localhost')
			index = input_item.get('index', 'main')
			duration = input_item.get('duration', '0 9 * * *')
			start_date = input_item.get('start_date', '1999-01-01T00:00:00Z')

			fimDataInputs = ["fim_events","fim_incidents","fim_ignored_events"]

			find_splunk_version()
			try:
				if os.path.exists('/opt/splunk/var/log/splunk/configuration_change.log'):
					with FileReadBackwards("/opt/splunk/var/log/splunk/configuration_change.log", encoding="utf-8") as frb:
						count = 0
						for l in frb:
							if input_name in l:
								if count == 1:
									qlogger.info("Last disable details for %s  data input - %s",pure_input_name,l)
								else:
									qlogger.info("Last enable details for %s data input - %s",pure_input_name,l)
								count += 1
								if count == 2:
									break

			except:
				qlogger.error("Error occured while knowing the data input enable/disable details")

			try:
				if pure_input_name in fimDataInputs:
					datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%S.%fZ')
			except ValueError:
				start_date = start_date[:-1]+".000Z"
				qlogger.info("default Start Date mentioned for %s is converted to include milliseconds. Updated value is %s",pure_input_name , start_date)

			try:
				if pure_input_name != "knowledge_base" and not qualysModule.splunkpopulator.utils.is_valid_data_input_startDate(start_date, pure_input_name):
					qlogger.error("Invalid Start Date for %s data input.", pure_input_name)
					sys.exit(1)
			except Exception as exc:
				if hasattr(exc, 'message'):
					excMessage = exc.message
				else:
					excMessage = exc
				qlogger.error("Invalid Start Date for %s data input. Error: %s", pure_input_name, excMessage)
				sys.exit(1)

			current_dt = datetime.now()
			cron_seed_dt = current_dt - timedelta(minutes=1)  # time 1 min ago
			current_dt_str = current_dt.strftime("%Y-%m-%d %H:%M:00")

			sleep_old_way = False

			try:
				iter = croniter(duration, cron_seed_dt)
				next_run = iter.get_next(datetime).strftime("%Y-%m-%d %H:%M:00")
				if next_run != current_dt_str:
					qlogger.debug(
						"Current time (%s) does not match cron format (%s) defined for %s. Will not run. Next run is on %s",
						current_dt_str, duration, pure_input_name, next_run)
					exit(0)
				else:
					qlogger.info("Current time (%s) matches cron format (%s) defined for %s. Running now.",
								 current_dt_str, duration, pure_input_name)
			except ValueError as ve:
				qlogger.warning(
					"Old style interval found! '%s' is not a valid cron format. TA will sleep for %s in old-fashioned way after this %s job is done.",
					duration, duration, pure_input_name)
				qlogger.warning(
					"Qualys recommends you to switch to cron format for more control on data input execution.")
				sleep_old_way = True
			except Exception as exc:
				qlogger.error("Invalid cron format - %s", duration)
				sys.exit(1)

			#TA_VERSION variable used to print version number in logs
			try:
				qlogger.info("Python interpreter version = %s", sys.version_info[0])
				appConf = scc.getAppConf("app", QUALYS_APP_NAME)
				ta_version = appConf['launcher']['version']
				qlogger.info("Qualys TA version=%s", ta_version)
			except Exception as e:
				pass

			if pure_input_name == "ioc_events":
				qlogger.warning("Data input %s is deprecated. Configure edr_events data input instead of %s on Settings >> Data inputs >> Qualys.", pure_input_name , pure_input_name)
				sys.exit(1)

			qlogger.info("Running for %s. Host name to be used: %s. Index configured: %s. "
						 "Run duration: %s. Default start date: %s.", pure_input_name, host, index, duration, start_date)

			apiConfig = makeAPIConfigObject(session_key, pure_input_name)
			apiConfig.ta_version = ta_version
			runLogPopulator(pure_input_name, checkpoint_dir, host, index, start_date, apiConfig, ew, server_info)

			if sleep_old_way:
				qlogger.info("%s run completed. Sleeping for %s", pure_input_name, duration)
				durationSeconds = qualysModule.splunkpopulator.utils.timeStringToSeconds(duration)
				time.sleep(int(durationSeconds))

			try:
				removePIDFile(pure_input_name)
			except IOError as e:
				sys.stderr.write(e)
				exit(1)
		# end of for loop on inputs


def makeAPIConfigObject(session_key, data_input_running):
	"""

	:param session_key:
	:return:
	"""
	qualysConf = scc.getMergedConf("qualys")
	creds = qualysModule.splunkpopulator.utils.getCredentials(session_key,qualysConf['setupentity'].get("authentication_type","basic"))
	#if bool_value(qualysConf['setupentity']['is_pcp']):
	api_server = qualysConf['setupentity']['api_server']
	token_added = False
	if qualysConf['setupentity'].get("authentication_type","basic") == "basic":
		api_user = creds["basic"]["username"]
		api_password = creds["basic"]["password"]
		if data_input_running == 'edr_events' and "jwt_basic" in creds:
			token_added = True
	elif qualysConf['setupentity'].get("authentication_type") == "oidc":
		client_id = creds["client"]["client_id"]
		client_secret = creds["client"]["client_secret"]
		if data_input_running == 'edr_events' and "jwt_oidc" in creds:
			token_added = True
	#qlogger.error("Fetcsddhed client credentials for client_id %s and password -%s ", client_id,client_secret)
	api_server = api_server.strip(" / \ ")
	check_protocol = urlparse(api_server)
	if not check_protocol.scheme == "https":
		qlogger.error("User have provided the Qualys API Server with \'http\'. The URL scheme has to be HTTPS. Exiting...")
		exit(1)
	useProxy = qualysConf['setupentity']['use_proxy']
	_proxy = qualysConf['setupentity']['proxy_server']
	proxy_server = _proxy
	if re.match('(?:https?:\/\/)?(\w+:)(.*)(?=@)', _proxy):
		proxy_pass = get_password(session_key, "qualys_proxypass", QUALYS_PROXY_REALM)
		proxy = _proxy.replace("****", proxy_pass)
	else:
		proxy = _proxy

	use_ca = qualysConf['setupentity']['use_ca']
	api_timeout = qualysConf['setupentity']['api_timeout']
	retry_interval = qualysConf['setupentity']['retry_interval_seconds']
 

	if qualysConf['setupentity'].get("authentication_type","basic") == "basic":
		if (api_user is None or api_user == '' or \
						api_password is None or api_password == '' or \
						api_server is None or api_server == ''):
			qlogger.error("API Server/Username/Password not configured. Exiting.")
			exit(1)
   
	elif qualysConf['setupentity'].get("authentication_type") == "oidc":
		if (client_id is None or client_id == '' or \
						client_secret is None or client_secret == '' or \
						api_server is None or api_server == ''):		
			qlogger.error("API Server/Client ID/Client Secret not configured. Exiting.")
			exit(1)

	if not bool_value(qualysConf['setupentity'].get("is_pcp", "0")):
		if data_input_running in SERVICES_BEHIND_GATEWAY or (qualysConf['setupentity'].get("authentication_type","basic") == "oidc" and data_input_running in TOTALCLOUD_CSPM_DATA_INPUT):
			if not api_server.startswith(GATEWAY_URL_PREFIX):
				#make it gateway url
				if api_server in list(QUALYS_PLATFORMS_URLS_NOT_HAVING_apps):
					api_server = re.sub(r"https:\/\/(qualysapi|qualysguard)", "https://gateway.qg1.apps", api_server)
				else:
					api_server = re.sub(r"https:\/\/(qualysapi|qualysguard)", GATEWAY_URL_PREFIX, api_server)
				qlogger.info("API URL changed to %s for %s data input", api_server, data_input_running)


		elif data_input_running in TOTALCLOUD_CSPM_DATA_INPUT and qualysConf['setupentity'].get("authentication_type","basic") == "basic":
			if api_server.startswith(GATEWAY_URL_PREFIX):
				#make it guard url
				if api_server in QUALYS_PLATFORMS_URLS_NOT_HAVING_apps:
					api_server = re.sub(r"https:\/\/(qualysapi|gateway.qg1.apps)", GUARD_URL_PREFIX, api_server)
				else:
					api_server = re.sub(r"https:\/\/(qualysapi|gateway)", GUARD_URL_PREFIX, api_server)
				qlogger.info("API URL changed to %s for %s data input", api_server, data_input_running)	
	
			else:
				if re.search(r"^https:\/\/(qualysapi|gateway)", api_server):
					api_server = re.sub(r"https:\/\/(qualysapi|gateway)", GUARD_URL_PREFIX, api_server)
					qlogger.info("API URL changed to %s for %s data input", api_server, data_input_running)	
	
		else:
			#not a gateway service
			if re.search(r"^https:\/\/qualysguard", api_server):
				api_server = re.sub(r"https:\/\/qualysguard", API_SERVER_URL_PREFIX, api_server)
				qlogger.info("API URL changed to %s for %s data input", api_server, data_input_running)

			elif api_server.startswith(GATEWAY_URL_PREFIX):
				if api_server in QUALYS_PLATFORMS_URLS_NOT_HAVING_apps:
					api_server = re.sub(r"https:\/\/gateway.qg1.apps", API_SERVER_URL_PREFIX, api_server)
				else:
					api_server = re.sub(r"https:\/\/gateway", API_SERVER_URL_PREFIX, api_server)
				qlogger.info("API URL changed to %s for %s data input", api_server, data_input_running)

	elif bool_value(qualysConf['setupentity'].get("is_pcp", "0")) and data_input_running in SERVICES_BEHIND_GATEWAY:
			api_server = qualysConf['setupentity'].get("gateway_server_url_pcp")
			if api_server:
				api_server = api_server.strip(" / \ ")
				check_protocol = urlparse(api_server)
				if not check_protocol.scheme == "https":
					qlogger.error("User have provided the Qualys Gateway Server with \'http\'. The URL scheme has to be HTTPS. Exiting...")
					exit(1)
			else:
				qlogger.error("User has not provided the Qualys Gateway Server. Exiting...")
				exit(1)
 
	elif bool_value(qualysConf['setupentity'].get("is_pcp", "0")) and data_input_running in TOTALCLOUD_CSPM_DATA_INPUT:
			api_server = qualysConf['setupentity'].get("qualysguard_server_url_pcp")
			if api_server:
				api_server = api_server.strip(" / \ ")
				check_protocol = urlparse(api_server)
				if not check_protocol.scheme == "https":
					qlogger.error("User have provided the Qualys Guard URL with \'http\'. The URL scheme has to be HTTPS. Exiting...")
					exit(1)
			else:
				qlogger.error("User has not provided the Qualys Guard URL. Exiting...")
				exit(1)

	apiConfig = qapi.Client.APIConfig()
	if qualysConf['setupentity'].get("authentication_type","basic") == "basic":
		apiConfig.username = api_user
		apiConfig.password = api_password
		if data_input_running == 'edr_events':
			apiConfig.jwt_token = tokens = creds.get("jwt_basic",{}).get("token")
	elif qualysConf['setupentity'].get("authentication_type") == "oidc":
		apiConfig.client_id = client_id
		apiConfig.client_secret = client_secret
		if data_input_running == 'edr_events':
			apiConfig.jwt_token = creds.get("jwt_oidc",{}).get("token")
   
	if bool_value(qualysConf['setupentity'].get("is_pcp", "0")) and data_input_running:#  not in SERVICES_BEHIND_GATEWAY and data_input_running not in TOTALCLOUD_CSPM_DATA_INPUT:
		if qualysConf['setupentity'].get("gateway_server_url_pcp"):
			pcp_gateway_url = qualysConf['setupentity'].get("gateway_server_url_pcp")
		else:
			qlogger.error("User has not provided the Qualys Gateway Server. Exiting... and PCP is enabled")
			exit(1)
		apiConfig.pcp_gateway_url = pcp_gateway_url
	apiConfig.pcp_enabled = bool_value(qualysConf['setupentity'].get("is_pcp", "0"))

	apiConfig.serverRoot = api_server
	if data_input_running in TOTALCLOUD_CSPM_DATA_INPUT and bool_value(qualysConf['setupentity'].get("is_pcp", "0")) and qualysConf['setupentity'].get("authentication_type","basic") == "oidc":
		apiConfig.serverRoot = apiConfig.pcp_gateway_url
	else: 
		apiConfig.serverRoot = api_server
	apiConfig.api_timeout = api_timeout
	apiConfig.retry_interval = retry_interval
	apiConfig.proxy_server = proxy_server
	apiConfig.auth_type = qualysConf['setupentity'].get("authentication_type","basic")
	apiConfig.session_key = session_key

	if useProxy == '1':
		apiConfig.useProxy = True
		if proxy != '':
			apiConfig.proxyHost = proxy
		else:
			qlogger.error('You have enabled Proxy but Host field is empty. Cannot proceed further.')
			exit(1)
			
	apiConfig.use_ca, apiConfig.ca_path, apiConfig.ca_key, apiConfig.ca_pass = None, None, None, None
	if use_ca == '1':
		ca_path = qualysConf['setupentity']['ca_path']
		ca_key = qualysConf['setupentity']['ca_key']
		ca_pass = get_password(session_key, "qualys_ca_passphrase", QUALYS_APP_NAME)
		apiConfig.use_ca = True
		error = False
		error_msg = ""
		if ca_path:
			if not os.path.isfile(ca_path): 
				error = True
				error_msg = 'CA certificate file path is not valid, please make sure file path is correct. Cannot proceed further.'
			if ca_key and not os.path.isfile(ca_key): 
				error = True
				error_msg = 'CA Certificate key file path is not valid, please make sure file path is correct. Cannot proceed further.'

			apiConfig.ca_path, apiConfig.ca_key, apiConfig.ca_pass = ca_path,  ca_key or None, ca_pass or None
		else:
			error = True
			error_msg = 'You have enabled Client certificate but Certificate file path field is empty. Cannot proceed further.'
		if error:
			qlogger.error(error_msg)
			exit(1)

	return apiConfig
	

def runLogPopulator(pureName, checkpoint_dir, host, index, start_date, apiConfig, ew, server_info):
	"""

	:param pureName: String
	:param checkpoint_dir: String
	:param host: String
	:param index: String
	:param start_date: String
	:param apiConfig: qapi.Client.APIConfig
	:return:
	"""
	appConfig = ApplicationConfiguration()
	appConfig.load()
	
	cp = os.path.join(checkpoint_dir, pureName)

	qualysConf = scc.getMergedConf("qualys")
	createPIDFile(pureName)

	# if bool(qualysConf['setupentity'].get("is_pcp", "0")) and pureName in TOTALCLOUD_CSPM_DATA_INPUT:
	#is_behind_gateway = False
	# #if  not bool(qualysConf['setupentity'].get("is_pcp", "0")):
	# else:
	is_behind_gateway = pureName in SERVICES_BEHIND_GATEWAY or (qualysConf['setupentity'].get("authentication_type","basic") == "oidc" and pureName in TOTALCLOUD_CSPM_DATA_INPUT)
	#if program is not exited or still running at this point; means some of the cron format/s is matching and PID file is created and populator is going to run.
	#now, call API client validate() method
	apiConfig.pure_input_name = pureName
	qapi.setupClient(apiConfig, is_behind_gateway)
	qapi.pure_input_name = pureName
	if pureName == "edr_events" and qualysConf['setupentity'].get("authentication_type","basic") == "basic":
		qapi.client.validate_jwt()
	elif pureName == "edr_events" and qualysConf['setupentity'].get("authentication_type","oidc") == "oidc":
		qapi.client.validate_oidc()
	else:
		qapi.client.validate()

	if pureName == "knowledge_base":
		kbPopulator = qualysModule.qualys_log_populator.QualysKBPopulator(
											settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer=ew)
		kbPopulator.run()

	if pureName == "host_detection":
		detectionPopulator = qualysModule.qualys_log_populator.QualysDetectionPopulator(
											settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer=ew,
											server_info=server_info)
		detectionPopulator.run()

	if pureName == "was_findings":
		wasFindingsPopulator = qualysModule.qualys_log_populator.QualysWasDetectionPopulator(
											settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer = ew)
		wasFindingsPopulator.run()

	if pureName == "policy_posture_info":
		pcPosturePopulator = qualysModule.qualys_log_populator.QualysPCPosturePopulator(
											settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer = ew)
		pcPosturePopulator.run()

	if pureName == "cs_image_vulns":
		csImagePopulator = qualysModule.qualys_log_populator.QualysCSImagePopulator(
											settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer=ew)
		csImagePopulator.run()

	if pureName == "cs_container_vulns":
		csContainerPopulator = qualysModule.qualys_log_populator.QualysCSContainerPopulator(
											settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer=ew)
		csContainerPopulator.run()

	if pureName == "edr_events":
		ioc_cp_file = os.path.join(checkpoint_dir, "ioc_events")
		edr_cp_folder = os.path.join(checkpoint_dir, "edr_events_cp_folder")

		# Check IOC events checkpoint file exists or not
		is_ioc_cp_file = os.path.isfile(ioc_cp_file)

		# Check EDR events checkpoint file and folder exists or not
		is_edr_cp_file = os.path.isfile(cp)
		is_edr_cp_folder = os.path.isdir(edr_cp_folder)

		if is_ioc_cp_file == True and is_edr_cp_file == False:
			try:
				os.rename(ioc_cp_file, cp)
				qlogger.info("ioc_events checkpoint file renamed to edr_events for delta pull.")
			except:
				qlogger.warning("Unable to rename ioc_events checkpoint file to edr_events.")

		iocEventsPopulator = qualysModule.qualys_log_populator.QualysIOCEventsPopulator(
											settings=appConfig,
											checkpoint=cp,
                                            checkpoint_folder=edr_cp_folder,
											host=host,
											index=index,
											start_date=start_date,
											event_writer=ew)
		iocEventsPopulator.run()
	
	if pureName == "fim_events":
		fimEventsPopulator = qualysModule.qualys_log_populator.QualysFimEventsPopulator(
											settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer=ew)
		fimEventsPopulator.run()

	if pureName == "fim_ignored_events":
		fimIgnoredEventsPopulator = qualysModule.qualys_log_populator.QualysFimIgnoredEventsPopulator(
											settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer=ew)
		fimIgnoredEventsPopulator.run()

	if pureName == "fim_incidents":
		fimIncidentsPopulator = qualysModule.qualys_log_populator.QualysFimIncidentsPopulator(
											settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer = ew)
		fimIncidentsPopulator.run()

	if pureName == "activity_log":
		activityLogPopulator = qualysModule.qualys_log_populator.QualysActivityLogPopulator(
											settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer = ew)
		activityLogPopulator.run()

	if pureName == "sem_detection":
		semDetectionPopulator = qualysModule.qualys_log_populator.QualysSemDetectionPopulator(
											settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer=ew,
											server_info=server_info)
		semDetectionPopulator.run()

	if pureName == "pcrs_posture_info":
		pcrsPopulator = qualysModule.qualys_log_populator.QualysPCRSPopulator(
										    settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer = ew)
		pcrsPopulator.run()

	if pureName == "cyber_security_asset_management":
		csamPopulator = qualysModule.qualys_log_populator.QualysCSAMPopulator(
										    settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer = ew)
		csamPopulator.run()			

	if pureName == "certview_certificates":
		certviewPopulator = qualysModule.qualys_log_populator.QualysCertViewPopulator(
										    settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer = ew)
		certviewPopulator.run()
  
	if pureName == "aws_cspm_events":
		awscspmPopulator = qualysModule.qualys_log_populator.QualysAWSCSPMEventsPopulator(
										    settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer = ew)
		awscspmPopulator.run()
 
	if pureName == "azure_cspm_events":
		azurecspmPopulator = qualysModule.qualys_log_populator.QualysAZURECSPMEventsPopulator(
										    settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer = ew)
		azurecspmPopulator.run() 
  
	if pureName == "gcp_cspm_events":
		gcpcspmPopulator = qualysModule.qualys_log_populator.QualysGCPCSPMEventsPopulator(
										    settings=appConfig,
											checkpoint=cp,
											host=host,
											index=index,
											start_date=start_date,
											event_writer = ew)
		gcpcspmPopulator.run()

def is_ta_input_running(pid):
	if os.path.exists('/proc/' + pid):
		try:
			with open('/proc/' + pid + '/cmdline') as f:
				process_name = f.readline()
				if TA_ROOT + '/bin/qualys.py' in process_name :
					return True
		except:
			return False
	return False

def createPIDFile(basename):
	global TA_ROOT

	pid_file = TA_ROOT + '/' + basename + '.pid'

	current_pid = os.getpid()
	qualysConf = scc.getMergedConf("qualys")
	is_kill = bool_value(qualysConf['setupentity']['is_kill'])
	if qualysConf['setupentity']['kill_process_id'].isnumeric() and is_kill:
		qlogger.info("Configured Process Id in TA setup page: %s",qualysConf['setupentity']['kill_process_id'])
	elif is_kill:
		qlogger.info("Configured Process Id is not a number and the value of the Process Id is %s",qualysConf['setupentity']['kill_process_id'])

	if os.path.isfile(pid_file):
		fp2 = None
		try:
			fp2 = open(pid_file, 'r')
			running_pid = fp2.readline()
			kill_process_id = qualysConf['setupentity']['kill_process_id']
			if  running_pid and is_ta_input_running(running_pid):
				qlogger.info("Earlier Running PID: %s",running_pid)
				if is_kill and kill_process_id.isnumeric() and int(running_pid) == int(kill_process_id):
					try:
						qlogger.info("Killing already existing running process Id %s for %s",kill_process_id,basename)
						os.kill(int(kill_process_id), signal.SIGKILL)
						fp2.close()
					except Exception as e:
						qlogger.error("Error while killing Process Id %s and Reason: %s", kill_process_id,str(e))
						qlogger.info("Not able to kill the given process Id but Removing PID File in its name as user wants kill PID intentionally")
						removePIDFile(basename)
						fp2.close()
				else:
					qlogger.error("Another instance of %s is already running with PID %s. I am exiting.", basename, running_pid)
					fp2.close()
					exit(0)
			else:
				qlogger.info("Removing earlier PID File for %s", basename)
				removePIDFile(basename)
		except IOError as e:
			if fp2:
				qlogger.error("IOError while creating PID file: %s", e)
				fp2.close()
			else:
				qlogger.error(e)
			exit(1)
		finally:
			fp2 and fp2.close()

	fp = None
	try:
		fp = open(pid_file, 'w')
		fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
		if sys.version_info[0] < 3:
			fp.write(str(current_pid).decode('utf-8'))
		else:
			fp.write(str(current_pid))
	except IOError:
		if fp:
			qlogger.info('Another instance of %s already running. Exiting...', basename)
			fp.close()
		else:
			qlogger.error(e)
		exit(0)
	finally:
		fp and fp.close()


# end of createPIDFile

def removePIDFile(basename):
	global TA_ROOT
	try:
		pid_file = TA_ROOT + '/' + basename + '.pid'
		os.remove(pid_file)
	except IOError:
		raise IOError("Cannot remove %s PID file." % basename)

def find_splunk_version():
   if os.path.exists('/opt/splunk/etc/splunk.version'):
       try:
          fp2 = open('/opt/splunk/etc/splunk.version', 'r')
          splunk_version = fp2.readline().split("=")[1]
          qlogger.info("splunk version = %s",splunk_version)
       except:
           qlogger.error("Error occured while reading splunk version file to know the splunk version") 
       finally:    
          fp2.close()    


# end of removePIDFile

def usage():
	"""
	Print usage of this binary
	"""

	hlp = "%s --scheme|--validate-arguments|-h"
	print(hlp % sys.argv[0], file=sys.stderr)
	sys.exit(1)

if __name__ == "__main__":
	sys.exit(QualysScript().run(sys.argv))


