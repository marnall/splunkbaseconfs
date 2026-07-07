import sys, os
import requests
import json
import time
from datetime import datetime
import logging
import csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *

TOKEN_URL = '/connect/token'
VERSION_URL = '/swagger/v2/swagger.json'
PAGE_SIZE = 100

class ASMModularInput(Script):
    def  __init__(self):
        self.api_version = '2.0'
        # initialize logger
        logging.root
        logging.root.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s %(message)s')
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(formatter)
        logging.root.addHandler(handler)

    def get_scheme(self):
        # This function is specific to Splunk modular input - Setting up UI for 
        # collecting user inputs.
        scheme = Scheme("Industrial Defender REST API")

        scheme.description = "Get data from Industrial Defender REST API."
        scheme.use_external_validation = False
        scheme.use_single_instance = False

        api_data_type = Argument("api_data_type")
        api_data_type.title = "API Data Type"
        api_data_type.data_type = Argument.data_type_string
        api_data_type.description = "The type of data to retrieve from Industrial Defender REST API. Allowed values: ActualSoftware, AdminProp, Exception, Netflow, Vulnerability."
        api_data_type.required_on_create = True
        api_data_type.required_on_edit = True
        scheme.add_argument(api_data_type)

        api_url = Argument("url")
        api_url.title = "API URL"
        api_url.data_type = Argument.data_type_string
        api_url.description = "URL of REST API. For example: https://10.10.10.10/asmdataservice."
        api_url.required_on_create = True
        api_url.required_on_edit = True
        scheme.add_argument(api_url)
        
        api_client_id = Argument("client_id")
        api_client_id.title = "API Client ID"
        api_client_id.data_type = Argument.data_type_number
        api_client_id.description = "REST API Client ID"
        api_client_id.required_on_create = True
        api_client_id.required_on_edit = True
        scheme.add_argument(api_client_id)
        
        api_client_secret = Argument("client_secret")
        api_client_secret.title = "API Client Secret"
        api_client_secret.data_type = Argument.data_type_string
        api_client_secret.description = "REST API Client Secret"
        api_client_secret.required_on_create = True
        api_client_secret.required_on_edit = True
        scheme.add_argument(api_client_secret)

        verify_ssl_cert = Argument("verify_ssl_cert")
        verify_ssl_cert.title = "Verify SSL Certificate?"
        verify_ssl_cert.data_type = Argument.data_type_boolean
        verify_ssl_cert.description = "When making rest api call, should SSL certificate be verified."
        verify_ssl_cert.required_on_create = True
        verify_ssl_cert.required_on_edit = True
        scheme.add_argument(verify_ssl_cert)
        
        return scheme

    def get_token_header(self, baseurl, client_id, secret, verifySSL):
        # Get Bearer token and return the Authorization header
        value={
            'client_id':client_id,
            'client_secret':secret,
            'grant_type':'client_credentials',
            'scope':'api' }
        tokenUrl = baseurl + TOKEN_URL

        r = requests.post(verify=verifySSL,url=tokenUrl,data=value)
        if r.status_code==200 and 'access_token' in r.json():
            access_token = r.json()['access_token']
        else:
            logging.error("Failed to obtain token.")

        header ={'Authorization':'Bearer ' + access_token}
        return(header)

    def get_api_version(self, baseurl, verifySSL):
        # Get the ASM rest api version (api 2.0 = ASM 7.3.x. api 3.0 = ASM 7.4.x)
        url = baseurl + VERSION_URL
        response = requests.get(url, verify=verifySSL)
        if response.status_code==200:
            rjson = json.loads(response.text)
            if rjson['info']:
                self.api_version = rjson['info']['version']
            else:
                logging.error("Unable to get REST API version.")
        else:
            logging.error("Unable to get REST API version.")

        return

    def vserion_compare_simple(self, v1, v2):
        # Returns True if v1 is greater or equals to v2

        v1s = v1.replace(".", "")
        v2s = v2.replace(".", "")
        v1n = int(v1s)
        v2n = int(v2s)
        return v1n >= v2n

    def make_request(self, url, verifySSL, token_header):
        # Makes a GET request
        # Returns a dict that includes json response, pagination header json and error indicator
        result = {
            "response_json": "",
            "pagination_header_json": "",
            "error": ""
        }

        response = requests.get(url, verify=verifySSL, headers=token_header)
        status_code = response.status_code
        if status_code != 200:
            logging.error('Request to ' + url + ' returns code: ' +  str(status_code))
            result["error"] = "Error occured: " + str(status_code)
            return result

        result["response_json"] = json.loads(response.text)
        page_header = response.headers['X-Pagination']
        result["pagination_header_json"] = json.loads(page_header) if page_header != '' else ''

        return result

    def get_data_20(self, baseurl, api_endpoint, client_id, secret, verifySSL):
        # Generic get request for talking to v2.0 rest api. No paging. 
        # Note, it is being used by get_vulnerability_30 since there is no paging in those responses.
        headers = self.get_token_header(baseurl, client_id, secret, verifySSL)
        url = baseurl + api_endpoint
        response = requests.get(url, verify=verifySSL, headers=headers)
        statuscode = response.status_code
        if statuscode != 200:
            logging.error('Request to ' + url + ' returns code: ' +  str(statuscode))
            exit()
        rjson = json.loads(response.text)
        return rjson

    def get_data_30(self, baseurl, api_endpoint, client_id, secret, verifySSL):
        # Generic get request for talking to v3.0 rest api. This includes pagination handling.
        token_header = self.get_token_header(baseurl, client_id, secret, verifySSL)
        # note that api_endpoint includes parameter
        url = baseurl + api_endpoint
        request_result = self.make_request(url, verifySSL, token_header)
        request_error = request_result["error"]
        if request_error == "":
            request_result_content = request_result["response_json"]
            request_result_pager = request_result["pagination_header_json"]
            result = {
                "asmName": request_result_content['asmName'],
                "asmUuid": request_result_content['asmUuid'],
                "data": request_result_content['data']
            }
            logging.info("get_data_30: data length = " + str(len(result["data"])))
            while 'nextPageLink' in request_result_pager:
                url = request_result_pager['nextPageLink']
                # request next page
                request_result = self.make_request(url, verifySSL, token_header)
                request_error = request_result["error"]
                if request_error == "": 
                    request_result_content = request_result["response_json"]
                    request_result_pager = request_result["pagination_header_json"]
                    result["data"].extend(request_result_content['data'])

                    logging.info("get_data_30: data length = " + str(len(result["data"])))
        return result

    def get_exception_20(self, baseurl, api_endpoint, client_id, secret, verifySSL):
        rjson = self.get_data_20(baseurl, api_endpoint, client_id, secret, verifySSL)
        # Get baseline exception information from v2.0 rest api.This can be removed
        # when we stop supporting ASM 7.3.x
        # From json response of the api, generate individule events, for each asset details, software and etc.
        # This means to create an json array of asset details, an array of software etc, with assetName and 
        # assetUuid, and type of baseline, within each object. Splunk automatically split the array to individual events.
        # batchId is used to differenciate multiple requests for the same data 
        combined = []
        batchId = datetime.now().isoformat()
        for asset in rjson['data']:

            assetName = asset['assetName']
            assetUuid = asset['assetUuid']

            exceptionTypes = ['assetDetailExceptions','portAndServiceExceptions','softwareExceptions','softwarePatchExceptions','firewallRuleExceptions','userAccountExceptions','fileExceptions']
            for type in exceptionTypes:
                for data in asset[type]:
                    newObj = {
                        'assetName': assetName, 
                        'assetUuid': assetUuid, 
                        'exceptionType': 'exception_' + type, 
                        'batch': batchId, 
                        'data': data
                        }
                    combined.append(newObj)

        return combined

    def get_exception_30(self, baseurl, api_endpoint, client_id, secret, verifySSL):
        # Get baseline exception information from v3.0 rest api. This includes pagination handling.
        # From json response of the api, generate individule events, for each asset details, software and etc.
        # This means to create an json array of asset details, an array of software etc, with assetName and 
        # assetUuid, and type of baseline, within each object. Splunk automatically split the array to individual events.
        # batchId is used to differenciate multiple requests for the same data 
        combined = []
        token_header = self.get_token_header(baseurl, client_id, secret, verifySSL)
        # note that api_endpoint includes parameter
        url = baseurl + api_endpoint
        request_result = self.make_request(url, verifySSL, token_header)
        request_error = request_result["error"]
        if request_error == "":
            request_result_content = request_result["response_json"]
            request_result_pager = request_result["pagination_header_json"]
            batchId = datetime.now().isoformat()
            exceptionTypes = [
                'assetDetailExceptions',
                'portAndServiceExceptions',
                'softwareExceptions',
                'softwarePatchExceptions',
                'firewallRuleExceptions',
                'userAccountExceptions',
                'deviceInterfaceExceptions',
                'fileExceptions']

            self.flatten_exception(combined, batchId, exceptionTypes, request_result_content)


            while 'nextPageLink' in request_result_pager:
                url = request_result_pager['nextPageLink']
                # request next page
                request_result = self.make_request(url, verifySSL, token_header)
                request_result_content = request_result["response_json"]
                request_result_pager = request_result["pagination_header_json"]
                self.flatten_exception(combined, batchId, exceptionTypes, request_result_content)

        return combined

    def flatten_exception(self, combined, batchId, exceptionTypes, request_result_content):

        for asset in request_result_content['data']:
            assetName = asset['assetName']
            assetUuid = asset['assetUuid']
            for type in exceptionTypes:
                if type in asset:
                    for exception_data in asset[type]:
                        newObj = {
                            'assetName': assetName, 
                            'assetUuid': assetUuid, 
                            'exceptionType': 'exception_' + type, 
                            'batch': batchId, 
                            'data': exception_data
                            }
                        combined.append(newObj)

    def get_netflow_raw_30(self, baseurl, client_id, secret, verifySSL):
        token_header = self.get_token_header(baseurl, client_id, secret, verifySSL)
        # First, query to get unique sensors
        url = baseurl + '/api/netflow/sensors'
        sensors_response = requests.get(url, verify=verifySSL, headers=token_header)
        statuscode = sensors_response.status_code
        if statuscode != 200:
            print ('Code: ' +  str(sensors_response.status_code))
            exit()
        response_obj = json.loads(sensors_response.text)
        sensors = response_obj['data']
        # write sensor UUIDs to file for ease of search later on
        sensors_file = open(os.path.join(sys.path[0],'../lookups','sensors.csv'), "w")
        with sensors_file:
            writer = csv.writer(sensors_file, delimiter='\n')
            writer.writerow(['sensors'])
            writer.writerow(sensors)

        # iterate thru sensors and make request for each
        combined = []
        # for raw data, use span of 1 hour, in milli
        span = 60 * 60 * 1000
        one_day_in_milli = 24 * 60 * 60 * 1000
        # default start to 1 day ago
        start = (int)(time.time() * 1000 - one_day_in_milli)
        # if the file exists, read start time from file.
        netflow_start_file_path = os.path.join(sys.path[0],'..','netflow_start.txt') 
        if os.path.exists(netflow_start_file_path):
            netflow_start_file = open(netflow_start_file_path, "r")
            start_in_file = int(netflow_start_file.read()) + 1
            logging.info('Read start from file netflow_start.txt: '+ str(start_in_file))
            start = start_in_file if start < start_in_file else start
            netflow_start_file.close()
        
        for i in range(len(sensors)):
            requestUrl = baseurl + '/api/netflow/flows?sTime=' + str(start) + '&batchSpan=' + str(span) + '&sensoruuid=' + sensors[i]
            logging.info('requesting ' + requestUrl)
            request_result = self.make_request(requestUrl, verifySSL, token_header)
            request_error = request_result["error"]
            if request_error == "":
                request_result_content = request_result["response_json"]
                request_result_pager = request_result["pagination_header_json"]
                combined.extend(request_result_content['data'])
                while 'nextPageLink' in request_result_pager:
                    url = request_result_pager['nextPageLink']
                    # request next page
                    request_result = self.make_request(url, verifySSL, token_header)
                    request_error = request_result["error"]
                    if request_error == "": 
                        request_result_content = request_result["response_json"]
                        request_result_pager = request_result["pagination_header_json"]
                        combined.extend(request_result_content['data'])

        #write the last record's time to file
        logging.info("Read " + str(len(combined)) + " netflow records.")
        if len(combined) > 0: 
            logging.info("Writing new start timestamp " + str(combined[len(combined) - 1]['timeStamp_millis']))
            netflow_start_file = open(netflow_start_file_path, "w")
            netflow_start_file.write(str(combined[len(combined) - 1]['timeStamp_millis']))
            netflow_start_file.close()

        return combined

    def get_netflow_data_20(self, baseurl, datatype, client_id, secret, verifySSL):
        headers = self.get_token_header(baseurl, client_id, secret, verifySSL)
        # First, query to get unique sensors
        url = baseurl + '/api/NetflowFlows/sensors'
        sensors = requests.get(url, verify=verifySSL, headers=headers)
        statuscode = sensors.status_code
        if statuscode != 200:
            logging.error ('Code: ' +  str(sensors.status_code))
            exit()
        rjson = json.loads(sensors.text)

        # iterate thru sensors and make request for each
        combined = []
        # For netflow data, we will only get data from the last day
        # If history data is desired, set the input to run on a daily basis
        span = 24 * 60 * 60 * 1000
        start = (int)(time.time() * 1000 - span)
        if datatype == 'topconversation':
            url = baseurl + '/api/netflowconversation?by=bytes&stime=' + str(start) + '&span=' + str(span) +'&count=20&sensoruuid='
        elif datatype == "topdestination":
            url = baseurl + '/api/netflowdestination?by=bytes&stime=' + str(start) + '&span=' + str(span) +'&count=20&sensoruuid='
        elif datatype == "topservice":
            url = baseurl + '/api/netflowservice?by=bytes&stime=' + str(start) + '&span=' + str(span) +'&count=20&sensoruuid='
        elif datatype == "topsource":
            url = baseurl + '/api/netflowsource?by=bytes&stime=' + str(start) + '&span=' + str(span) +'&count=20&sensoruuid='
        for i in range(len(rjson)):
            requestUrl = url + rjson[i]
            response = requests.get(requestUrl, verify=False, headers=headers)
            if response.status_code == 200:
                resultJson = json.loads(response.text)
                # append additional info
                newObj = ({'type':datatype, 'time': start, 'sensor': rjson[i], 'data':resultJson})
                combined.append(newObj)
        return combined

    def get_netflow_data_30(self, baseurl, datatype, client_id, secret, verifySSL):
        headers = self.get_token_header(baseurl, client_id, secret, verifySSL)
        # First, query to get unique sensors
        url = baseurl + '/api/netflow/sensors'
        sensors = requests.get(url, verify=verifySSL, headers=headers)
        statuscode = sensors.status_code
        if statuscode != 200:
            print ('Code: ' +  str(sensors.status_code))
            exit()
        rjson = json.loads(sensors.text)

        # iterate thru sensors and make request for each
        combined = []
        # For netflow data, we will only get data from the last day
        # If history data is desired, set the input to run on a daily basis
        span = 24 * 60 * 60 * 1000
        start = (int)(time.time() * 1000 - span)
        if datatype == 'topconversation':
            url = baseurl + '/api/netflow/conversations?by=bytes&stime=' + str(start) + '&span=' + str(span) +'&count=20&sensoruuid='
        elif datatype == "topdestination":
            url = baseurl + '/api/netflow/destinations?by=bytes&stime=' + str(start) + '&span=' + str(span) +'&count=20&sensoruuid='
        elif datatype == "topservice":
            url = baseurl + '/api/netflow/services?by=bytes&stime=' + str(start) + '&span=' + str(span) +'&count=20&sensoruuid='
        elif datatype == "topsource":
            url = baseurl + '/api/netflow/sources?by=bytes&stime=' + str(start) + '&span=' + str(span) +'&count=20&sensoruuid='
        for i in range(len(rjson['data'])):
            requestUrl = url + rjson['data'][i]
            response = requests.get(requestUrl, verify=False, headers=headers)
            if response.status_code == 200:
                resultJson = json.loads(response.text)
                # append additional info
                newObj = ({'type':datatype, 'time': start, 'sensor': rjson['data'][i], 'data':resultJson['data']})
                combined.append(newObj)
        return combined

    def get_vulnerability_20(self, baseurl, api_endpoint, client_id, secret, verifySSL):
        # Get vulnerability information from v2.0 rest api. This can be removed
        # when we stop supporting ASM 7.3.x
        rjson = self.get_data_20(baseurl, api_endpoint, client_id, secret, verifySSL)

        # iterate thru UIDs for API call for each asset
        combined = []
        batchId = datetime.now().isoformat()
        asmName = rjson['asmName']
        asmUuid = rjson['asmUuid']
        for asset in rjson['data']:
            api_endpoint = '/api/Vulnerability/' + asset['assetUUID']
            assetVulJson = self.get_data_20(baseurl, api_endpoint, client_id, secret, verifySSL)
            for vul in assetVulJson['data']['vulnerabilities']:
                combined.append(
                    {
                        'asmName': asmName,
                        'asmUuid': asmUuid,
                        'assetName': assetVulJson['assetName'], 
                        'assetUuid': assetVulJson['assetUuid'],
                        'batch': batchId,
                        'data': vul
                    })
        return combined

    def get_vulnerability_30(self, baseurl, api_endpoint, client_id, secret, verifySSL):
        # Get vulnerability information from v3.0 rest api
        # Vulnerability related api nearly did not change in 7.4.0. No paging.
        # The changes include api endpoints and field name case, assetUUID vs assetUuid. 
        rjson = self.get_data_20(baseurl, api_endpoint, client_id, secret, verifySSL)

        # iterate thru UIDs for API call for each asset
        combined = []
        batchId = datetime.now().isoformat()
        asmName = rjson['asmName']
        asmUuid = rjson['asmUuid']
        for asset in rjson['data']:
            assetName = asset['assetName']
            assetUuid = asset['assetUuid']
            api_endpoint = '/api/vulnerability/asset-details/' + assetUuid
            assetVulJson = self.get_data_20(baseurl, api_endpoint, client_id, secret, verifySSL)
            for vul in assetVulJson['data']['vulnerabilities']:
                combined.append(
                    {
                        'asmName': asmName,
                        'asmUuid': asmUuid,
                        'assetName': assetName, 
                        'assetUuid': assetUuid,
                        'batch': batchId,
                        'data': vul
                    })
        return combined

    def get_actual_software(self, baseurl, api_endpoint, client_id, secret, verifySSL):
        # Get state data, software only, information from v3.0 rest api
        result = self.get_data_30(baseurl, api_endpoint, client_id, secret, verifySSL)
        combined = []
        batchId = datetime.now().isoformat()
        self.flatten_software(combined, batchId, result)
        return combined

    def flatten_software(self, combined, batchId, request_result_content):

        for asset in request_result_content['data']:
            assetName = asset['assetName']
            assetUuid = asset['assetUuid']
            if "software" in asset:
                for software in asset["software"]:
                    newObj = {
                        'assetName': assetName, 
                        'assetUuid': assetUuid, 
                        'batch': batchId, 
                        'data': software
                        }
                    combined.append(newObj)

    def validate_input(self, validation_definition):
        pass

    def stream_events(self, inputs, ew):
        """
        {
          "input_stanza1": {"url":value,"client_id":value,"client_secret":value},
          "input_stanza2": {"url":value,"client_id":value,"client_secret":value}
        }
        """
        for input_name, input_item in inputs.inputs.items():

            event = Event()
            event.stanza = input_name

            api_data_type = input_item["api_data_type"].lower()
            base_url = input_item["url"]
            client_id = input_item["client_id"]
            client_secret = input_item["client_secret"]
            verify_ssl = False if input_item["verify_ssl_cert"] == "0" else True
            # get api version. the subsequent requesst urls differ depending on the api version
            self.get_api_version(base_url, verify_ssl)
            api_endpoint = ''

            if api_data_type == "adminprop":
                if (self.api_version == '2.0'):
                    api_endpoint = '/api/adminproperty'
                    result = self.get_data_20(base_url, api_endpoint, client_id, client_secret, verify_ssl)
                elif (self.vserion_compare_simple(self.api_version, '3.0')):
                    api_endpoint = '/api/admin-properties?limit=' + str(PAGE_SIZE)
                    result = self.get_data_30(base_url, api_endpoint, client_id, client_secret, verify_ssl)
                else:  
                    logging.warning("Unsupported REST API version")
                
                logging.info("adminprop result: data length = " + str(len(result["data"])) )
                event.data = json.dumps(result["data"])
            
            elif api_data_type == "exception":
                if (self.api_version == '2.0'):
                    api_endpoint = '/api/baselineexception'
                    result = self.get_exception_20(base_url, api_endpoint, client_id, client_secret, verify_ssl)
                elif (self.vserion_compare_simple(self.api_version, '3.0')):
                    api_endpoint = '/api/exceptions/baseline/exceptions?limit=' + str(PAGE_SIZE)
                    result = self.get_exception_30(base_url, api_endpoint, client_id, client_secret, verify_ssl)
                else:
                    logging.warning("Unsupported REST API version")
                
                event.data = json.dumps(result)
            
            elif api_data_type == "vulnerability":
                if (self.api_version == '2.0'):
                    api_endpoint = '/api/Vulnerability/GetVulnerableAssets'
                    result = self.get_vulnerability_20(base_url, api_endpoint, client_id, client_secret, verify_ssl)
                elif (self.vserion_compare_simple(self.api_version, '3.0')):
                    api_endpoint = '/api/vulnerability/assets'
                    result = self.get_vulnerability_30(base_url, api_endpoint, client_id, client_secret, verify_ssl)
                else:
                    logging.warning("Unsupported REST API version")
                
                event.data = json.dumps(result)

            elif api_data_type == "actualsoftware":
                if (self.api_version == '2.0'):
                    logging.warning ("ActualSoftware is unsupported in REST API version 2.0")
                elif (self.vserion_compare_simple(self.api_version, '3.0')):
                    api_endpoint = '/api/state/actual?type=software&limit=' + str(PAGE_SIZE)
                    result = self.get_actual_software(base_url, api_endpoint, client_id, client_secret, verify_ssl)
                else:
                    logging.warning("Unsupported REST API version")

                event.data = json.dumps(result)

            elif api_data_type == "netflow":
                if (self.api_version == '2.0'):
                    logging.warning ("Netflow raw flow unsupported in REST API version 2.0")
                elif (self.vserion_compare_simple(self.api_version, '3.0')):
                    result = self.get_netflow_raw_30(base_url, client_id, client_secret, verify_ssl)
                else:
                    logging.warning ("Unsupported REST API version")

                event.data = json.dumps(result)

            elif api_data_type == "topconversation":
                if (self.api_version == '2.0'):
                    result = self.get_netflow_data_20(base_url, api_data_type, client_id, client_secret, verify_ssl)
                elif (self.vserion_compare_simple(self.api_version, '3.0')):
                    result = self.get_netflow_data_30(base_url, api_data_type, client_id, client_secret, verify_ssl)

                event.data = json.dumps(result)

            ew.write_event(event)
            

if __name__ == "__main__":
    sys.exit(ASMModularInput().run(sys.argv))

