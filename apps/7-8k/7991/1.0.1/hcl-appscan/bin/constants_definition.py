import subprocess
import requests
import json
import platform
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hcl_appscan")

def header(keyID, secretID, appScanUrl,allowUntrustedConnection):
	if "local" in appScanUrl.lower():
		client_type = 'splunk-1.0.1'
	else:
		client_type = 'splunk-' + platform.system().lower() + '-1.0.1'

	session_command = [
		"curl", "-s", "-X", "POST",
		"--header", "Content-Type: application/json",
		"--header", "Accept: application/json",
		"-d", json.dumps({"KeyId": keyID, "KeySecret": secretID, "clientType": client_type}),
		appScanUrl + "/api/v4/Account/ApiKeyLogin"
	]

	if allowUntrustedConnection:
		session_command.append("--insecure")


	session_output = subprocess.check_output(session_command).decode("utf-8")
	session_result = json.loads(session_output)
	sessionId = session_result["Token"]

	return {
		'accept': 'application/json',
		'authorization': 'Bearer ' + sessionId,
		'accept-language': 'en-US,en;q=0.9,ro;q=0.8,cs;q=0.7,es;q=0.6,fr;q=0.5',
		'cookie': 'fs_uid=#12N5F4#942c9d4d-7021-4887-a4eb-25646acf1c43:ef8faaed-fb82-4b85-a430-bf2bf6df4377:1717582144903::1#c0cbd4de#/1748426917; fs_lua=1.1717582197676',
		'dnt': '1',
		'priority': 'u=1, i',
		'referer': appScanUrl + '/swagger/index.html',
		'sec-ch-ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
		'sec-ch-ua-mobile': '?0',
		'sec-ch-ua-platform': '"Windows"',
		'sec-fetch-dest': 'empty',
		'sec-fetch-mode': 'cors',
		'sec-fetch-site': 'same-origin',
		'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
	}

def fetch_applications(keyID, secretID,appScanUrl,allowUntrustedConnection, skip, count, top):
	headers = header(keyID, secretID,appScanUrl,allowUntrustedConnection)
	params = {
		"orderby": "Id",
		"skip": skip,
		"count": count,
		"top": top
	}
	url = appScanUrl + '/api/v4/Apps'
	response = requests.get(url, headers=headers, params=params, verify=not allowUntrustedConnection)
	response.raise_for_status()
	return response.json()['Items']
	
def fetch_issues(keyID, secretID,appScanUrl,allowUntrustedConnection, app_id, skip, count, top):
	headers = header(keyID, secretID,appScanUrl,allowUntrustedConnection)
	params = {
		"orderby": "Id",
		"skip": skip,
		"count": count,
		"top": top
	}
	url = f'{appScanUrl}/api/v4/Issues/Application/{app_id}'
	response = requests.get(url, headers=headers, params=params, verify=not allowUntrustedConnection)
	response.raise_for_status()
	return response.json()['Items']

def fetch_scans(keyID, secretID,appScanUrl,allowUntrustedConnection, skip, count, top):
	logger.info(f"Fetching scans with skip={skip}, count={count}, top={top}, appScanUrl={appScanUrl}, allowUntrustedConnection={allowUntrustedConnection}")
	headers = header(keyID, secretID,appScanUrl,allowUntrustedConnection)
	params = {
		"orderby": "Id",
		"skip": skip,
		"count": count,
		"top": top
	}
	logger.info(f"Params: {params}")
	url = f'{appScanUrl}/api/v4/Scans/'
	logger.info(f"URL: {url}")

	response = requests.get(url, headers=headers, params=params, verify=not allowUntrustedConnection)
	response.raise_for_status()
	return response.json()['Items']