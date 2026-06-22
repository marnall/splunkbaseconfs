import sys
import import_declare_test
import splunklib.client as client
from solnlib import conf_manager, log
import requests
import os
from datetime import datetime

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators
    
ADDON_NAME = "app_version_check"
API_URL="https://splunkbase.splunk.com/api/v1/app/"

#Headers for Splunkbase request to imitate a request from a browser
HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
} 

def api_call_get_app(logger, app_name):
    api_url = "https://splunkbase.splunk.com/api/v1/app/"
    params = {'appid': app_name}
      
    try:
        response = requests.get(api_url, params=params, headers=HEADERS)
        response.raise_for_status()
        
        data = response.json()
        
        return data   
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred during the API request: {e}")
        return None

def check_archived(data):
    is_archived = data["results"][0]["is_archived"]
    return is_archived

def get_app_id(data):
    app_link = data['results'][0]['path']
    app_id = app_link.strip('/').split('/')[-1]
    return app_id

def get_all_splunk_apps(logger, service):
    current_apps = []
        
    if service:
        for app in service.apps:
            app_name = app.name
            if "author" in app.content and "details" in app.content:
                app_author = app.author
                app_details = app.details
                app_version=app.version

                if "Splunk" not in app_author:
                    data = api_call_get_app(logger=logger, app_name=app_name)

                    if data and 'results' in data and len(data['results']) > 0:
                        is_archived = check_archived(data)
                        uid = get_app_id(data)

                        current_app = {
                                "name": app_name, 
                                "version": app_version, 
                                "uid": uid,
                                "is_archived": is_archived}
                        current_apps.append(current_app)
                    else:
                        logger.warning(f"App with name '{app_name}' not found on Splunkbase.")
                        continue
    return current_apps

def get_compatibility(logger, app_uid, app_name, app_version, target_version):
    api_url=f"https://splunkbase.splunk.com/api/v1/app/{app_uid}/release"
    is_compatible=False
    try:
        response = requests.get(api_url, headers=HEADERS)
        response.raise_for_status()

        data = response.json()

        if "Not found" not in data:
            for release in data:
                if release["name"] == app_version and "product_versions" in release:
                    supported_versions_list = release["product_versions"]
                    if target_version in supported_versions_list:
                        is_compatible=True                
        else:
            logger.warning(f"App with name '{app_name}' not found on Splunkbase.")
            return None  
        return is_compatible
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred during the API request: {e}")
        return None

def get_compatible_versions(logger, app_uid, app_name, target_version):
    api_url=f"https://splunkbase.splunk.com/api/v1/app/{app_uid}/release"
    try:
        response = requests.get(api_url, headers=HEADERS)
        response.raise_for_status()

        data = response.json()

        compatible_versions = []

        if "Not found" not in data:
            for release in data:
                if "product_versions" in release:
                    supported_versions_list = release["product_versions"]
                    if target_version in supported_versions_list:
                        compatible_versions.append(release["name"])               
        else:
            logger.warning(f"App with name '{app_name}' not found on Splunkbase.")
            return None 
         
        return compatible_versions
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred during the API request: {e}")
        return None

def get_data_from_api(logger, service, splunk_target_version):
    logger.info("Getting data from an external API")

    incompatible=[]
    apps = get_all_splunk_apps(logger=logger, service=service)

    if apps:
        for app in apps:
            try:
                app_uid=app["uid"]
                app_name=app["name"]
                app_version=app["version"]
                is_archived=app["is_archived"]
                host=service.host

                if not get_compatibility(logger=logger, app_uid=app_uid, 
                        app_name=app_name, 
                        app_version=app_version, 
                        target_version=splunk_target_version):
                    compatible_versions = get_compatible_versions(logger=logger, 
                                                                app_uid=app_uid, 
                                                                app_name=app_name, 
                                                                target_version=splunk_target_version)
                    incompatible.append({
                        "appid": app_name,
                        "host": host,
                        "is_archived": is_archived,
                        "current_version": app_version,
                        "compatible_versions": compatible_versions
                    })

            except Exception as e: 
                logger.error(str(e))
                incompatible.append({
                    "appid": app_name,
                    "is_archived": is_archived,
                    "current_version": app_version,
                    "error": str(e)
                })
    
    logger.info(incompatible)
    return incompatible

def get_distributed_peers(service, logger):
    try:
        peers = service.get(
            '/services/search/distributed/peers',
            output_mode='json'
        )
        data = json.loads(peers.body.read().decode('utf-8'))
        return data.get('entry', [])
    except Exception as e:
        logger.info(f"Failed to retrieve peers: {e}")
        return []

def get_service(session_key, splunkd_uri):
    return client.Service(
            token=session_key,
            splunkd_uri=splunkd_uri,
            app='app_version_check',
            owner='nobody')

def get_peer_services(session_key, logger, peers):
    services=[]

    if not peers:
        logger.info("No distributed peers found.")
    else: 
        for entry in peers:
            peer_uri = entry['content']['peerName']
            service = client.Service(
                token=session_key,
                host=peer_uri,
                port=8089
            )
            services.append(service)

    return services

@Configuration()
class CompatibilitycheckCommand(GeneratingCommand):
    tgt_splunk_version = Option(name='tgt_splunk_version', require=True)

    def generate(self):

        session_key = self._metadata.searchinfo.session_key
        splunkd_uri = self._metadata.searchinfo.splunkd_uri
        service = get_service(session_key, splunkd_uri) #current instance (SH)

        logger = log.Logs().get_logger("compatibility_check_command")
        log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="app_version_check_settings",
            )
        logger.setLevel(log_level)

        peers = get_distributed_peers(service, logger) 
        peer_services = get_peer_services(session_key, logger, peers) #distributed search peers
        services= []
        services.append(service)
        services.append(peer_services)

        try: 
            
            logger.info("Starting command search")

            result = []

            for serv in services:
                incompatible_apps = get_data_from_api(
                    logger=logger,
                    service=serv,
                    splunk_target_version=self.tgt_splunk_version,)
                for app in incompatible_apps:
                    result.append(app)

            event_time = datetime.now().timestamp()

            for app in result:
                if app:
                    logger.info(app)
                    yield {
                        "_time": event_time,
                        "appid": app.get("appid"),
                        "host": app.get("host"),
                        "is_archived": app.get("is_archived"),
                        "current_version": app.get("current_version"),
                        "compatible_versions": app.get("compatible_versions"),
                        "target_splunk_version": self.tgt_splunk_version,
                }

        except Exception as e:
            log.log_exception(logger, e, "my custom error type", msg_before="Exception raised while ingesting data for demo_input: ") 


dispatch(CompatibilitycheckCommand, sys.argv, sys.stdin, sys.stdout, __name__)