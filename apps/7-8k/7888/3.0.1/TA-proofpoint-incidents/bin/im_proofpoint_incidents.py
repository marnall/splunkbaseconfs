import json

from splunklib import modularinput as smi

#manual imports
from sb_utils import get_account_details
import sb_utils as utils
import sys
import datetime
from dateutil import parser
import math
import requests
from urllib.parse import quote
import gzip
import io

CP_ID = "checkpointer"

def get_start_date(self, opt_since_date, input_checkpoint_name):

    # Try to get a date from the check point first
    d = utils.get_check_point(self, input_checkpoint_name, CP_ID)
    self.logger.debug("input_checkpoint_value={}".format(d))

    # If there was a check point date, retun it.
    if (d not in [None,'']):
        iso_format = parser.parse(d["start_date"]).strftime('%Y-%m-%dT%H:%M:%S')
        return iso_format
    else:
        # No check point date, so look if a start date was specified as an argument
        self.logger.debug("No saved checkpoint for 'Start Date'")
        d = opt_since_date
        if (d not in [None,'']):
            dt = parser.parse(d)
            self.logger.debug("user input of start_date={}".format(dt))
            iso_format = dt.strftime('%Y-%m-%dT%H:%M:%S')
            return iso_format

        else:
            # If there was no start date specified, default to 7 days ago
            past_date =  datetime.datetime.utcnow() - datetime.timedelta(days=7)
            iso_format = past_date.strftime('%Y-%m-%dT%H:%M:%S')
            return iso_format
        
def isAccessTokenValid(self,acessstoken_checkpoint_name):
    acstok = utils.get_check_point(self, acessstoken_checkpoint_name, CP_ID)
    self.logger.debug("get access token called")
    
    # If there was a check point access token, return it.
    if (acstok not in [None,'']):
        self.logger.debug("access token is found")
        
        gentime,access_token = acstok.get("access_token").split("::")
        gentimeconvert = parser.parse(gentime)
        self.logger.debug("Token genrated last time:{}".format(gentimeconvert))
        self.logger.debug("Token elapsed time(in seconds): {}".format((datetime.datetime.now() - gentimeconvert).seconds))
        if int((datetime.datetime.now() - gentimeconvert).seconds) < (int(acstok.get("expires_in")) - 300):
            self.logger.debug("access token is valid from last rest call, hence using it")
            return access_token

def get_access_token(self,proofpoint_endpoint,client_id,client_secret, acessstoken_checkpoint_name):
    try:
        #access_token=isAccessTokenValid(self,acessstoken_checkpoint_name)
        access_token = ""
        
        if access_token:
            self.logger.debug("access token is found from method:isAccessTokenValid")
            return access_token
        else:
            self.logger.debug("access token is not found or expired, hence requesting")

            uri = "/v2/apis/auth/oauth/token"
            url = "https://"+proofpoint_endpoint+uri
            auth_body="""grant_type=client_credentials&client_secret="""+client_secret+"""&client_id="""+client_id+"""&scope=*"""
            auth_headers = { "content-type": "application/x-www-form-urlencoded"}

            proxy_settings = utils.get_proxy_settings(self.session_key, self.logger)
            self.logger.debug("proxy_settings:{}".format(proxy_settings))
                                
            response = requests.post(url, data=auth_body, headers=auth_headers, cookies=None, verify=True, cert=None, timeout=None, proxies=proxy_settings)
            if response.status_code == 200:
                #self.logger.debug("token response={}".format(response.text))
                time_now = str(datetime.datetime.now())
                access_token  = json.loads(response.content)['access_token']
                expires_in = json.loads(response.content)['expires_in']

                acessstoken_checkpoint_value = {"access_token":time_now+"::"+str(access_token),"expires_in":expires_in}

                #self.logger.debug("acessstoken_checkpoint_value={}".format(acessstoken_checkpoint_value))
                
                utils.save_check_point(self, acessstoken_checkpoint_name, acessstoken_checkpoint_value, CP_ID)
                return access_token
            else:
                self.logger.error("error in getting access token. error={}".format(response.json()))
        
    except Exception as e:
            self.logger.error("get_access_token. exception={}".format(e))
            return False


def collect_events(self, input_name, input_item, ew: smi.EventWriter):


    try:
        self.logger.debug(f"Starting data collection for {input_item}")

        account_information = get_account_details(self.session_key, self.logger, "account", input_item["account"])
        client_id = account_information.get('client_id')
        self.logger.debug(f"client_id={client_id}")

        client_secret = account_information.get('client_secret')
        proofpoint_endpoint = account_information.get('proofpoint_endpoint')

        if '/' not in proofpoint_endpoint:
            self.logger.error(f"Invalid proofpoint_endpoint format: {proofpoint_endpoint}")
            sys.exit(1)  # Exit program with non-zero code (indicates failure)

        proofpoint_endpoint, data_uri = proofpoint_endpoint.split('/', 1)

        self.logger.debug(f"proofpoint_endpoint={proofpoint_endpoint}")
        self.logger.debug(f"data_uri={data_uri}")


        start_date = input_item.get('start_date')
        # end_date = input_item.get('end_date')

        source_type = input_item.get('custom_sourcetype')
        collection_method = input_item.get('collection_method')

        input_name = input_name.split("/")[-1]

        input_checkpoint_name = "%s_input" % input_name
        self.logger.debug(f"input_checkpoint_name={input_checkpoint_name}")
    
        self.logger.debug(f"normalized_input_name={input_name}")
            
       
        acessstoken_checkpoint_name = "%s_accesstoken" % input_name
        self.logger.debug(f"acessstoken_checkpoint_name={acessstoken_checkpoint_name}")

        access_token = ""
        access_token=get_access_token(self, proofpoint_endpoint, client_id, client_secret, acessstoken_checkpoint_name)


        if access_token:

            if collection_method=="continuous":
        
                data_headers = {
                                    "Authorization": 'Bearer ' + access_token,
                                    "Content-Type":'application/json'
                            }
                proxy_settings = utils.get_proxy_settings(self.session_key, self.logger)
                self.logger.debug("proxy_settings:{}".format(proxy_settings))
                
                #start_date = ""
                date_format_str="%Y-%m-%dT%H:%M:%S"

                checkpoint_data = {}

                job_start_time = datetime.datetime.utcnow()

                start_date = get_start_date(self, start_date, input_checkpoint_name)
                self.logger.debug("start_date_str={} before getting events".format(str(start_date)))
                start_date_str = datetime.datetime.strptime(str(start_date),date_format_str)
                start_date_epoch=math.floor(start_date_str.timestamp())
                self.logger.debug("start_date_epoch={} before getting events".format(start_date_epoch))

                if math.floor(job_start_time.timestamp()) - start_date_epoch > 3600:
                    end_date = parser.parse(start_date) + datetime.timedelta(seconds=3600)
                    self.logger.debug("start_date is older than 1 hour, setting end_date to start_date+1hour to handle api calls effectively")
                
                else:
                    end_date = job_start_time
                
                end_date_str=end_date.strftime(date_format_str)

                self.logger.debug("end_date_str={} before getting events".format(str(end_date_str)))
                end_date_epoch=math.floor(end_date.timestamp())
                self.logger.debug("end_date_epoch={}".format(end_date_epoch))

                encoded_startTime = quote(start_date_str.strftime(date_format_str), safe='')
                encoded_endTime = quote(end_date_str, safe='')

                #data_uri = "/v2/apis/data-delivery/collections/activity/feeds/oitactivity/objects?"
                #url=f"https://{proofpoint_endpoint}{data_uri}"
                url = f"https://{proofpoint_endpoint}/{data_uri.lstrip('/')}?"

                limit="1"
                offset="0"



                CONTINUE = True 
                cursor = ""
                COUNTER=0

                while(CONTINUE):


                    if end_date_epoch >  math.floor(job_start_time.timestamp()) or end_date_epoch == start_date_epoch:
                        self.logger.debug("events collected until job scheduled start time. exiting")
                        sys.exit(0)


                    if cursor=="":
                        self.logger.debug("cursor is empty, mostly this is the first call in the schedule or no more pages to fetch in the last call.")
                        query_string = f"offset={offset}&limit={limit}&startTime={encoded_startTime}&endTime={encoded_endTime}"
                        data_url = f"{url}{query_string}"
                    else:
                        query_string = f"offset={offset}&limit={limit}&startTime={encoded_startTime}&endTime={encoded_endTime}&cursor={cursor}"
                        data_url = f"{url}{query_string}"

                    data_headers = {"Authorization": 'Bearer ' + access_token,
                                                        "Content-Type":'application/json'
                                                }

                    proxy_settings = {}
                    response = requests.request("GET",data_url, data=None, headers=data_headers, cookies=None, verify=True, cert=None, timeout=300, proxies=proxy_settings)

                    if response.status_code == 200:
                        response_json=response.json()
                        #print(json.dumps(response_json))
                        # response_json_meta = response_json.get("_meta")
                        data_list = response_json.get("data", [])
                        cursor = response_json.get("_meta", {}).get("next", {}).get("cursor")
                        #print(cursor)
                        # print(response_json_meta)

                        self.logger.debug("found length of data_list={}".format(len(data_list)))
                        

                        if data_list:

                            for item in data_list:
                                href = item.get("links", {}).get("access", {}).get("href")
                                self.logger.debug("href={}".format(href))
                                final_response = requests.request("GET",href,headers="",data="")
                                file_compression = item.get("format",{}).get("compression")
                                if file_compression == "gzip":
                                    #print(final_response.content)
                                    with gzip.GzipFile(fileobj=io.BytesIO(final_response.content)) as gz:
                                        decompressed_data = gz.read().decode("utf-8", errors="replace")
                                        ew.write_event(
                                            smi.Event(
                                            data=decompressed_data,
                                            #time=event_time,
                                            index=input_item["index"],
                                            sourcetype=source_type,
                                            )
                                        )
                                access_token=get_access_token(self, proofpoint_endpoint, client_id, client_secret, acessstoken_checkpoint_name)

                        else:
                            checkpoint_data["start_date"]=str(end_date_str)
                            utils.save_check_point(self,input_checkpoint_name,checkpoint_data, CP_ID)
                            self.logger.debug('checkpoint set is : {}'.format(checkpoint_data))
                            

                            start_date = get_start_date(self, start_date, input_checkpoint_name)
                            self.logger.debug("start_date_str={} before getting events".format(str(start_date)))
                            start_date_str = datetime.datetime.strptime(str(start_date),date_format_str)
                            start_date_epoch=math.floor(start_date_str.timestamp())
                            self.logger.debug("start_date_epoch={} before getting events".format(start_date_epoch))

                            if math.floor(job_start_time.timestamp()) - start_date_epoch > 3600:
                                end_date = parser.parse(start_date) + datetime.timedelta(seconds=3600)
                                self.logger.debug("start_date is older than 1 hour, setting end_date to start_date+1hour to handle api calls effectively")
                            
                            else:
                                end_date = job_start_time
                            
                            end_date_str=end_date.strftime(date_format_str)

                            self.logger.debug("end_date_str={} before getting events".format(str(end_date_str)))
                            end_date_epoch=math.floor(end_date.timestamp())
                            self.logger.debug("end_date_epoch={}".format(end_date_epoch))

                            encoded_startTime = quote(start_date_str.strftime(date_format_str), safe='')
                            encoded_endTime = quote(end_date_str, safe='')
                            #CONTINUE = False
                    else:
                        self.logger.error("error in api response of collect_events. error={}".format(response.text))
                        CONTINUE = False
                        sys.exit(1)
            else:
                self.logger.info("only continuous data collection method is supported by the app for input={}.exiting".format(input_name))
        else:
            self.logger.info("no access token found for input={}.exiting".format(input_name))
        self.logger.info("Data collection completed for input={}".format(input_name))
    except Exception as e:
            self.logger.error("error in collect_events. error={}".format(e))
                
