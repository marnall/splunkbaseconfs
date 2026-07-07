import re
import json
import requests
import os
import platform
from Constants import *
from urllib.parse import urlparse
from urllib.parse import urlencode, urljoin
from splunktaucclib.rest_handler.error import RestError


import logging
import os
from logging.handlers import RotatingFileHandler


# Setup logger for validator
def setup_validator_logger():
    current_working_directory = os.path.dirname(os.path.abspath(__file__))
    log_file_path = os.path.join(current_working_directory, "validator.log")
    
    logger = logging.getLogger("validator_logger")
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    return logger

# Initialize logger
validator_logger = setup_validator_logger()


class ServerURLValidator:

    def __init__(self) -> None:
        validator_logger.info("ServerURLValidator initialized")
        pass

    def ensure_endpointcentral_stanzas(self, file_path, global_account, required_types):
        validator_logger.info(f"Starting ensure_endpointcentral_stanzas for global_account: {global_account}, required_types: {required_types}")
        try:            
            
            required_stanzas_config = {}
            if "vulnerability" in required_types:
                vulnname = "Vulnerability_" + global_account
                required_stanzas_config[f"[endpointcentral_vulnerability://{vulnname}]"] = [
                    f"global_account = {global_account}",
                    "interval = 3600",
                    "disabled = 1"
                ]
                validator_logger.info(f"Added vulnerability stanza configuration for {vulnname}")
                
            if "actionlogdata" in required_types:
                actionlogname = "ActionLog_" + global_account
                required_stanzas_config[f"[endpointcentral_actionlog://{actionlogname}]"] = [
                    f"global_account = {global_account}",
                    "interval = 300",
                    "disabled = 1"
                ]
                validator_logger.info(f"Added actionlogdata stanza configuration for {actionlogname}")

            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                validator_logger.info(f"Successfully read file: {file_path}")
                
            except FileNotFoundError:
                # If the file doesn't exist, start with empty content
                content = ""
                validator_logger.info(f"File not found, will create new file: {file_path}")
                

            # Check which stanzas already exist
            stanza_found_in_file = {}
            for stanza_header in required_stanzas_config.keys():
                stanza_found_in_file[stanza_header] = stanza_header in content
                validator_logger.info(f"Stanza {stanza_header} found in file: {stanza_found_in_file[stanza_header]}")

            # Only add missing stanzas
            missing_stanzas = []
            for stanza_header, stanza_content_lines in required_stanzas_config.items():
                if not stanza_found_in_file[stanza_header]:
                    validator_logger.info(f"Adding missing stanza: {stanza_header}")
                    missing_stanzas.append(f"\n{stanza_header}\n")
                    for content_line in stanza_content_lines:
                        missing_stanzas.append(f"{content_line}\n")
                    missing_stanzas.append("\n")

            # If there are missing stanzas, append them to the file
            if missing_stanzas:
                validator_logger.info(f"Writing {len(missing_stanzas)} missing stanza entries to file")
                try:
                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    with open(file_path, 'a') as f:
                        f.writelines(missing_stanzas)
                    validator_logger.info(f"Successfully appended missing stanzas to file: {file_path}")
                    
                except IOError as e:
                    validator_logger.error(f"IOError while writing to file {file_path}: {str(e)}")
                    return
            
            
            # If file was empty and we added content, create the file
            if not content and missing_stanzas:
                try:
                    with open(file_path, 'w') as f:
                        f.writelines(missing_stanzas)
                    validator_logger.info(f"Successfully created new file with stanzas: {file_path}")
                    
                except IOError as e:
                    validator_logger.error(f"IOError while creating new file {file_path}: {str(e)}")
                    return
                    
            validator_logger.info("ensure_endpointcentral_stanzas completed successfully")
            
        except Exception as e:
            validator_logger.error(f"Exception in ensure_endpointcentral_stanzas: {str(e)}")
            return
    
    def saveDefaultInputInSplunk(self,values,global_account):
        validator_logger.info(f"Starting saveDefaultInputInSplunk for values: {values}, global_account: {global_account}")
        try:
            
            
            current_working_directory = os.path.dirname(os.path.abspath(__file__))
            inputconf_path = None

            if os.name == 'nt' or platform.system() == 'Windows':
                inputconf_path = os.path.join(current_working_directory, "..", "local", "inputs.conf")
                validator_logger.info("Detected Windows OS for inputs.conf path")
                
            elif os.name == 'posix' or platform.system() == 'Linux':
                inputconf_path = os.path.join(current_working_directory, "..", "local", "inputs.conf")
                validator_logger.info("Detected Linux OS for inputs.conf path")
                
            else:
                validator_logger.error(f"Unrecognized operating system: {os.name} / {platform.system()}")
                return  
  
            inputconf_path = os.path.abspath(inputconf_path)
            validator_logger.info(f"Resolved inputs.conf path: {inputconf_path}")
            
            self.ensure_endpointcentral_stanzas(inputconf_path,global_account,values)
            validator_logger.info("saveDefaultInputInSplunk completed successfully")
            
        except Exception as e:
            validator_logger.error(f"Exception in saveDefaultInputInSplunk: {str(e)}")
            return

    def fetch_zoho_accounts_server_uri(self, data):
        """
        Fetches the Zoho Accounts server URI from the provided data.
        If not found, returns None.
        """        
        validator_logger.info("Starting fetch_zoho_accounts_server_uri")
        
        
        managed_domains = [
        "endpointcentral.manageengine.com",
        "endpointcentral.manageengine.in",
        "endpointcentral.manageengine.eu",
        "endpointcentral.manageengine.com.au",
        "endpointcentral.manageengine.uk",
        "endpointcentral.manageengine.jp",
        "endpointcentral.manageengine.cn",
        "endpointcentral.manageengine.ca",
        ]
        
        
            
        servertype = data.get("endpointcenteralserver")
        validator_logger.info(f"Server type: {servertype}")
        
        if servertype == "endpointcentral_cloud":
            server_url = data.get("server_url")
           
            
            if server_url and server_url != "dummy":
                try:
                    hostname = urlparse(server_url).hostname
                    
                except Exception as e:
                    validator_logger.error(f"Exception parsing server URL: {str(e)}")
                    return False, data.get("zoho_accounts_server_uri")
                    
                if hostname in managed_domains:
                    parts = hostname.split(".")
                    ext = parts[-1]
                    zoho_uri = f"https://accounts.zoho.{ext}"
                    validator_logger.info(f"Found managed domain, generated Zoho URI: {zoho_uri}")
                    return True, zoho_uri
                else:
                    validator_logger.info(f"Hostname {hostname} not in managed domains")
                    return False, data.get("zoho_accounts_server_uri")
            else:
                validator_logger.info("Server URL is empty or dummy")
                return False, data.get("zoho_accounts_server_uri")
        else:
            validator_logger.info("Server type is not endpointcentral_cloud")
            
            return False, "dummy"

    def validate(self,value, data):
    
      
        
        server_url_pattern = r"^(ht)tp(s?)\:\/\/[-.\w]*(\/?)([a-zA-Z0-9\-\.\?\,\:\'\/\\\+=&amp;%\$#_@]*)?"
        server_type = data.get("endpointcenteralserver")
        server_url = data.get("server_url")
        auth_token = data.get("auth_token")
        op_server_url = data.get("op_server_url")
        
        validator_logger.info(f"Server type: {server_type}, Server URL: {server_url}, OP Server URL: {op_server_url}")
        
        default_accounts_uri,zoho_accounts_server_uri = self.fetch_zoho_accounts_server_uri(data)
        validator_logger.info(f"Default accounts URI: {default_accounts_uri}, Zoho accounts server URI: {zoho_accounts_server_uri}")

        # Inputs Validation
        if server_type == None or server_type == "dummy":
            validator_logger.error("Server Type is None or dummy")
            raise RestError(400,"Server Type in None")

        if server_type == "endpointcentral_op":
            validator_logger.info("Validating endpointcentral_op server type")
            
            if op_server_url == None or op_server_url == "dummy":
                validator_logger.error("OP Server URL is None or dummy")
                
                raise RestError(400,"Server URL is None")
        
            if auth_token == None or auth_token == "dummy":
                validator_logger.error("Auth Token is None or dummy")
                raise RestError(400,"Auth Token is None")
            
            if re.match(server_url_pattern, op_server_url) == None:
                validator_logger.error(f"OP Server URL is invalid: {op_server_url}")
                raise RestError(400,"Server URL is invalid")
            
        elif server_type == "endpointcentral_cloud":
            validator_logger.info("Validating endpointcentral_cloud server type")
            
            if server_url == None or server_url == "dummy":
                validator_logger.error("Server URL is None or dummy")
                raise RestError(400,"Server URL is None")
            
            if not default_accounts_uri and ( zoho_accounts_server_uri == None or zoho_accounts_server_uri == "dummy"):
                validator_logger.error("Zoho Account Server URL is None")
                raise RestError(400,"Zoho Account Server URL is None")
            if re.match(server_url_pattern, zoho_accounts_server_uri) == None:
                raise RestError(400, "Zoho Accounts Server URL is invalid")
            if data.get("service_account",None):
                validator_logger.info("Processing service account from JSON")
                try:
                    service_account= json.loads(data.get("service_account"))
                    client_id = service_account.get("client_id")
                    client_secret = service_account.get("client_secret")
                    code = service_account.get("code")
                    validator_logger.info("Successfully parsed service account JSON")
                    
                except Exception as e:
                    validator_logger.error(f"Exception parsing service account JSON: {str(e)}")
                    raise RestError(400,"Service Account is not in valid JSON format, Error: " + str(e))
            else:
                validator_logger.info("Processing individual auth parameters")
                code = data.get("code")
                client_id = data.get("client_id")
                client_secret = data.get("client_secret")
                    
            for param_name, param_value in {
                "Code": code,
                "Client ID": client_id,
                "Client Secret": client_secret
            }.items():
                if param_value is None or param_value == "dummy":
                    validator_logger.error(f"{param_name} is not valid")
                    raise RestError(400, f"Upload a valid Authentication File: {param_name} is not valid")

            if re.match(server_url_pattern, server_url) == None:
                validator_logger.error(f"Server URL is invalid: {server_url}")
                raise RestError(400,"Server URL is invalid")
        else:
            validator_logger.error(f"Invalid server type: {server_type}")
            raise RestError(400,"Server Type is invalid")

        delimiter = "/"
        configuration_api = delimiter.join([EC_API_CATEGORY, INTEGRATIONS, SPLUNK, CONFIGURATION])
        validator_logger.info(f"Configuration API endpoint: {configuration_api}")

        if server_type == "endpointcentral_op":    
            if value != op_server_url:
                validator_logger.info("Value differs from OP server URL, returning True")
                return True
                
            validator_logger.info("Processing endpointcentral_op validation")
            
            current_working_directory = os.path.dirname(os.path.abspath(__file__))
            os_name = os.name
            system_name = platform.system()
            ca_bundle_file_path = None
            
            # Checking the OS to set certificate in ec.ca-bundle
            if os_name == 'nt' or system_name == 'Windows':
                ca_bundle_file_path = str(current_working_directory) + "\\..\\certificates\ec.ca-bundle"
                validator_logger.info(f"Windows OS detected, CA bundle path: {ca_bundle_file_path}")
                
            elif os_name == 'posix' or system_name == 'Linux':
                ca_bundle_file_path = str(current_working_directory) + "/../certificates/ec.ca-bundle"
                validator_logger.info(f"Linux OS detected, CA bundle path: {ca_bundle_file_path}")
                
            else:
                validator_logger.error(f"Unrecognized operating system: {system_name}")
                
                raise RestError(400,'This is an unrecognized operating system: ' + str(system_name))
           
            os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(ca_bundle_file_path)
            validator_logger.info(f"Set REQUESTS_CA_BUNDLE environment variable to: {ca_bundle_file_path}")
            
            url = op_server_url  + "/" + configuration_api
            validator_logger.info(f"Constructed request URL: {url}")
            
            headers = {}
            headers["Content-Type"] = "application/json"
            headers["Authorization"] = auth_token
            payload = {}
            payload["productCode"] = "DCEE"
            data["isNewConfiguration"] = True
            verifyCert = bool(data.get("verify_cert", True))
            
            validator_logger.info(f"Request headers (auth token masked): Content-Type: {headers.get('Content-Type')}, Authorization: ***masked***")
            validator_logger.info(f"Request payload: {payload}")
            validator_logger.info(f"SSL verification enabled: {verifyCert}")
            
            global_account = data.get("zoho_accounts_server_uri",None)
            
            data["zoho_accounts_server_uri"]= "dummy"

            validator_logger.info("Sending POST request to configuration API")
            
            try:
                response = requests.request(method=METHOD_POST, url=url, headers=headers, json=payload, verify=verifyCert)
                validator_logger.info(f"Received response with status code: {response.status_code}")
                validator_logger.info(f"Response content length: {len(response.content) if response.content else 0} bytes")
                
            except requests.exceptions.SSLError as ssl_error:
                validator_logger.error(f"SSL error occurred: {str(ssl_error)}")
                raise RestError(400, "SSL validation failed. Please upload a valid Endpoint Central SSL certificate in Splunk.")
            except requests.exceptions.ConnectionError:
                validator_logger.error("Connection error occurred")
                raise RestError(400, "Unable to connect to the Endpoint Central server. Please verify the server URL and network connectivity.")
            except requests.exceptions.RequestException as e:
                validator_logger.error(f"Request exception occurred: {str(e)}")
                raise RestError(400, "Unable to connect to the Endpoint Central server. Please verify the server URL and network connectivity.")
            except OSError as e:
                error_message = str(e).lower()
                validator_logger.error(f"OS error occurred: {str(e)}")
                if "certificate" in error_message or "ssl" in error_message:
                    raise RestError(400, "SSL validation failed. Please upload a valid Endpoint Central SSL certificate in Splunk."+ str(e))
                elif "certificate bundle" in error_message or "invalid path" in error_message:
                    raise RestError(400,"Certificate verification failed. Please check the CA bundle path and ensure the file exists. ")
                else:
                    raise RestError(400, f"Unexpected OS error: {str(e)}")
           
            if response.status_code == 200:
                    validator_logger.info("Received successful response (200)")
                    response = json.loads(response.content.decode())
                    validator_logger.info(f"Parsed response JSON successfully")
                    try:
                        input_data = data.get("input_data", None)   
                    except Exception as e:
                         validator_logger.info(f"Exception parsing input_data: {str(e)}")
                         input_data = None                 
                    
                    if input_data:
                        values = input_data.split("|")
                        validator_logger.info(f"Input data values: {values}")
                        
                        if "actionlogdata" in values:
                            validator_logger.info("Processing actionlogdata validation")
                            if "status" in response and "buildNumber" not in response:
                                validator_logger.error("Audit Log input not supported in current EC version")
                                raise RestError(400,"Action Log input is not supported in your Endpoint Central version. Please upgrade to version 11.4.2530.1 or higher.")
                            else:                                
                                #check whether the api key is having valid permissions
                                params = {
                                    START_TIME: 0,
                                    END_TIME: 0,
                                    PAGE: 0
                                }
                                actionlogurl = op_server_url+ "/"+ AUDIT_API
                                fullurl = urljoin(actionlogurl, '?' + urlencode(params))
                                validator_logger.info(f"Sending audit API request to: {fullurl}")
                            
                                try:                           
                                    auditresponse = requests.request(method=METHOD_GET, url=fullurl, headers=headers, json=None,verify=verifyCert)
                                    audit_status_code = auditresponse.status_code
                                    validator_logger.info(f"Audit API response status code: {audit_status_code}")
                                    


                                    if audit_status_code ==401 or audit_status_code == 403:
                                        validator_logger.error(f"Audit API permission denied - status code: {audit_status_code}")
                                        raise RestError(400, "The API key lacks Action Log permission. Generate a new API key with Action Log permissions")
                                    
                                    validator_logger.info("Audit API validation successful")
                                    self.saveDefaultInputInSplunk(values,global_account) 
                                    return True

                                except requests.exceptions.RequestException as e:
                                    validator_logger.error(f"Exception during audit API request: {str(e)}")
                                    raise RestError(400,"Unable to connect to the Endpoint Central server. Please verify the server URL and network connectivity.")
                        else:
                            validator_logger.info("No actionlogdata in values, saving default input")
                            self.saveDefaultInputInSplunk(values,global_account) 
                            return True
                    else:
                         return True

            elif response.status_code ==400 and  ("requires TLS" in response.text or "HTTP request was sent to HTTPS port" in response.text):
                        validator_logger.error(f"TLS/HTTPS error - status code: {response.status_code}, response: {response.text}")
                        raise RestError(400,"Secure connection required. Use HTTPS in the Endpoint Central server URL.")
            else:
                validator_logger.info(f"Processing non-200 response - status code: {response.status_code}")

                if response.status_code == 401 or response.status_code == 403:
                    validator_logger.error(f"Authentication/authorization error - status code: {response.status_code}")
                    raise RestError(400, "The API key is invalid or lacks sufficient permissions. Please enter a valid key with required permissions.")
                              
                if "status" not in response:
                                validator_logger.error("Response does not contain 'status' field")
                                raise RestError(400,"Kindly verify the server URL is valid or Generated API key has required permissions " )
                if response["status"] == ERROR and MESSAGE in response:
                                validator_logger.error(f"Response contains error: {response[MESSAGE]}")
                                raise RestError(400,"Error: " + response[MESSAGE])
                elif response["status"] == SUCCESS:
                                validator_logger.info("Response indicates success")
                                return True
                else:
                                validator_logger.error(f"Unexpected response status: {response.get('status', 'unknown')}")
                                raise RestError(400,response[ERROR_MSG])
                           
        
        elif server_type == "endpointcentral_cloud":
            validator_logger.info("Processing endpointcentral_cloud validation")
            if value != server_url:
                validator_logger.info("Value differs from server URL, returning True")
                return True                
            
            if zoho_accounts_server_uri[-1] == "/":
                zoho_accounts_server_uri = zoho_accounts_server_uri[:-1]
                validator_logger.info("Removed trailing slash from zoho_accounts_server_uri")
            
            authorization_url = zoho_accounts_server_uri + "/oauth/v2/token?" + "code=" + code + "&client_id=" + client_id + "&client_secret=" + client_secret + "&grant_type=authorization_code"
            validator_logger.info(f"Constructed authorization URL (credentials masked): {zoho_accounts_server_uri}/oauth/v2/token?code=***&client_id=***&client_secret=***&grant_type=authorization_code")
            
            try:
                validator_logger.info("Sending POST request to authorization URL")
                response = requests.request(url=authorization_url, method = "POST")
                if response.status_code !=200 :
                    validator_logger.error(f"Authorization response status code: {response.status_code}")
                    raise RestError(400,"Unable to connect to Endpoint Central Cloud. Please verify your instance details and internet connectivity.")
                else:
                    response = json.loads(response.content.decode())
                    #validator_logger.info(response)
            except requests.exceptions.ConnectionError:
                validator_logger.error("Connection error during authorization request")
                raise RestError(400,"Unable to connect to Endpoint Central Cloud. Please verify your instance details and internet connectivity.")
            except Exception as e:
                validator_logger.error(f"Exception during authorization request: {str(e)}")
                raise RestError(400,f"Unable to connect to Endpoint Central Cloud. Please verify your instance details and internet connectivity {str(e)}")
            
            
            if "refresh_token" not in response or "access_token" not in response:
                validator_logger.error("Authorization response missing required tokens")
                raise RestError(400,"The uploaded authentication file is invalid. Please upload a valid authentication file.")
            else:
                validator_logger.info("Successfully obtained access and refresh tokens")
                
            access_token = response["access_token"]

            data["refresh_token"] = response["refresh_token"]
        

            if server_url[-1] == "/":
                server_url = server_url[:-1]
                validator_logger.info("Removed trailing slash from server_url")

            config_url = server_url + "/" + configuration_api
            validator_logger.info(f"Constructed config URL: {config_url}")
            
            
            headers = {}
            headers["Content-Type"] = "application/json"
            headers["Authorization"] = "Zoho-oauthtoken " + access_token
            payload = {}
            payload["productCode"] = "DCODEE"
            
            
            try:
                validator_logger.info("Sending POST request to cloud configuration API")
                response = requests.request(method=METHOD_POST, url=config_url, headers=headers, json=payload)
                validator_logger.info(f"Cloud config response status code: {response.status_code}")
                statuscode = response.status_code
                response = json.loads(response.content.decode())
                validator_logger.info(response)
            except requests.exceptions.ConnectionError:
                validator_logger.error("Connection error during cloud config request")
                raise RestError(400,"Unable to connect to the Endpoint Central server. Please verify the server URL and network connectivity.")
            except requests.exceptions.RequestException as e:
                validator_logger.error(f"Request exception during cloud config request: {str(e)}")
                raise RestError(400, "Unable to connect to the Endpoint Central server. Please verify the server URL and network connectivity.")
                
            input_data = data.get("input_data", None)
            global_account = data.get("op_server_url",None)
            
            data["op_server_url"]= "dummy"
            data["isNewConfiguration"] = True
            data["zoho_accounts_server_uri"]= zoho_accounts_server_uri
            
            if statuscode == 200 and response["status"]==SUCCESS:
                validator_logger.info("Cloud config request successful")
                if input_data:
                    values = input_data.split("|")
                    validator_logger.info(f"Cloud input data values: {values}")
                    if "actionlogdata" in values:
                                params = {
                                        START_TIME: 0,
                                        END_TIME: 0,
                                        PAGE: 0
                                    }
                                actionlogurl = server_url+ "/"+ AUDIT_API
                                validator_logger.info(f"Cloud audit API URL: {actionlogurl}")
                                fullurl = urljoin(actionlogurl, '?' + urlencode(params))
                                try:                           
                                    auditresponse = requests.request(method=METHOD_GET, url=fullurl, headers=headers, json=None)
                                    audit_status_code = auditresponse.status_code
                                        
                                    if audit_status_code ==401 or audit_status_code == 403:
                                            
                                        raise RestError(400, "The authentication file lacks Audit permission. Generate a new file with Audit permissions.")

                                    

                                except requests.exceptions.RequestException as e:                                        
                                    raise RestError(400,"Unable to connect to the Endpoint Central server. Please verify the server URL and network connectivity.")
                    if "vulnerability" in values:
                                vuln_url = server_url+ "/"+ VULN_API
                                validator_logger.info(f"Cloud vulnerability API URL: {vuln_url}")

                                try:
                                    vuln_response = requests.request(method=METHOD_GET, url=vuln_url, headers=headers, json=None)
                                    vuln_status_code = vuln_response.status_code

                                    if vuln_status_code == 401 or vuln_status_code == 403:
                                        raise RestError(400, "The authentication file lacks Vulnerability permission. Generate a new file with Vulnerability permissions.")


                                except requests.exceptions.RequestException as e:                                        
                                    raise RestError(400,"Unable to connect to the Endpoint Central server. Please verify the server URL and network connectivity.")
                                
                    self.saveDefaultInputInSplunk(values,global_account)
                    return True
                    
                else:
                     return True
                
                

            else:
                if statuscode==401 or statuscode == 403:
                    raise RestError(400,"The authentication file is invalid or lacks sufficient permissions. Please enter a valid file with required permissions.")
            
                if "status" not in response:               
                    raise RestError(400,"Server URL is invalid or Generated code dosen't have required permissions " + str(response))
                if response["status"] == ERROR and MESSAGE in response:                
                    raise RestError(400,"Error: " + response[MESSAGE])
                elif response["status"] == SUCCESS:                
                    return True
                else:
                    raise RestError(400,str(response))
        
        