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

CP_ID = "checkpointer"

def get_start_date(self, opt_since_date, input_checkpoint_name):

    # Try to get a date from the check point first
    d = utils.get_check_point(self, input_checkpoint_name, CP_ID)
    self.logger.debug("input_checkpoint_value={}".format(d))

    # If there was a check point date, retun it.
    if (d not in [None,'']):
        iso_format = parser.parse(d["since_date"]).strftime('%Y-%m-%dT%H:%M:%SZ')
        return iso_format
    else:
        # No check point date, so look if a start date was specified as an argument
        self.logger.debug("No saved checkpoint for 'Since Date'")
        d = opt_since_date
        if (d not in [None,'']):
            dt = parser.parse(d)
            self.logger.debug("user input of since_date={}".format(dt))
            iso_format = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            return iso_format

        else:
            # If there was no start date specified, default to 7 days ago
            past_date =  datetime.datetime.utcnow() - datetime.timedelta(days=7)
            iso_format = past_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            return iso_format
        
def isAccessTokenValid(self,acessstoken_checkpoint_name):
    acstok = utils.get_check_point(self, acessstoken_checkpoint_name, CP_ID)
    self.logger.debug("get access token called")
    
    # If there was a check point access token, return it.
    if (acstok not in [None,'']):
        self.logger.debug("access token is found")
        
        gentime,access_token = acstok.split("::")
        gentimeconvert = parser.parse(gentime)
        self.logger.debug("Token genrated last time:{}".format(gentimeconvert))
        self.logger.debug("Token elapsed time(in seconds): {}".format((datetime.datetime.now() - gentimeconvert).seconds))
        if int((datetime.datetime.now() - gentimeconvert).seconds) < int(3500):
            self.logger.debug("access token is valid from last rest call, hence using it")
            return access_token

def get_access_token(self,login_url,tenant_id,resource,client_id,client_secret,acessstoken_checkpoint_name):
    try:
        access_token=isAccessTokenValid(self,acessstoken_checkpoint_name)
        
        if access_token:
            self.logger.debug("access token is found from method:isAccessTokenValid")
            return access_token
        else:
            self.logger.debug("access token is not found, hence requesting")

            url = login_url+"/"+tenant_id+"/oauth2/token"
            auth_body="""grant_type=client_credentials&client_secret="""+client_secret+"""&client_id="""+client_id+"""&resource="""+resource
            auth_headers = { "content-type": "application/x-www-form-urlencoded"}

            proxy_settings = utils.get_proxy_settings(self.session_key, self.logger)
            self.logger.debug("proxy_settings:{}".format(proxy_settings))
                                
            response = requests.post(url, data=auth_body, headers=auth_headers, cookies=None, verify=True, cert=None, timeout=None, proxies=proxy_settings)

            time_now = str(datetime.datetime.now())
            access_token  = json.loads(response.content)['access_token']
            
            utils.save_check_point(self, acessstoken_checkpoint_name, time_now+"::"+str(access_token), CP_ID)
            return access_token
        
    except Exception as e:
            self.logger.error("get_access_token. exception={}".format(e))
            sys.exit(1)


def validate_input(definition: smi.ValidationDefinition):
    since_date = definition.parameters.get('since_date', None)
    if since_date is not None:
        try:
            parser.parse(since_date)
        except Exception as e:
            error_message = f"Invalid date format specified for 'Since Date={since_date}'"
            raise ValueError(error_message) 
    
    pass


def collect_events(self, input_name, input_item, ew: smi.EventWriter):

    try:
        self.logger.debug(f"Starting data collection for {input_item}")

        account_information = get_account_details(self.session_key, self.logger, "account", input_item["azure_account"])
        opt_tenant_id = account_information.get('tenant_id')
        self.logger.debug(f"opt_tenant_id={opt_tenant_id}")

        opt_client_id = account_information.get('client_id')
        self.logger.debug(f"opt_client_id={opt_client_id}")

        opt_client_secret = account_information.get('client_secret')

        opt_workspace_id = account_information.get('workspace_id')
        self.logger.debug(f"opt_workspace_id={opt_workspace_id}")

        opt_query = input_item.get('query')
        self.logger.debug(f"opt_query={opt_query}")

        opt_event_delay = input_item.get('event_delay')
        self.logger.debug(f"opt_event_delay={opt_event_delay}")

        opt_since_date = input_item.get('since_date')

        opt_source_type = input_item.get('sourcetype')

        input_name = input_name.split("/")[-1]

        input_checkpoint_name = "%s_input" % input_name
        self.logger.debug(f"input_checkpoint_name={input_checkpoint_name}")
    
        self.logger.debug(f"normalized_input_name={input_name}")
            
        auth_url = "https://login.microsoftonline.com/"
        self.logger.debug(f"auth_url={auth_url}")
        
        resource = """https%3A%2F%2Fapi.loganalytics.io%2F"""
        self.logger.debug(f"resource={resource}")

        acessstoken_checkpoint_name = "%s_accesstoken" % input_name
        self.logger.debug(f"acessstoken_checkpoint_name={acessstoken_checkpoint_name}")

        access_token = ""
        access_token=get_access_token(self, auth_url, opt_tenant_id, resource, opt_client_id, opt_client_secret, acessstoken_checkpoint_name)

        data_headers = {
                            "Authorization": 'Bearer ' + access_token,
                            "Content-Type":'application/json'
                    }
        data_url = """https://api.loganalytics.io/v1/workspaces/"""+opt_workspace_id+"""/query"""
        self.logger.debug("data_url={}".format(data_url))

        if opt_source_type:
            sourcetype=opt_source_type 
        else:
            sourcetype="azure:log_analytics"

        proxy_settings = utils.get_proxy_settings(self.session_key, self.logger)
        self.logger.debug("proxy_settings:{}".format(proxy_settings))
        
        start_date = ""
        date_format_str="%Y-%m-%dT%H:%M:%SZ"
        
        end_date = datetime.datetime.utcnow() - datetime.timedelta(minutes=int(opt_event_delay))
        end_date_str=end_date.strftime(date_format_str)
        
        end_date_epoch=math.floor(end_date.timestamp())
        self.logger.debug("end_date_epoch={}".format(end_date_epoch))

        checkpoint_data = {}

             
        start_date = get_start_date(self, opt_since_date, input_checkpoint_name)
        self.logger.debug("start_date_str={} before getting events".format(str(start_date)))
        start_date_str = datetime.datetime.strptime(str(start_date),date_format_str)
        start_date_epoch=math.floor(start_date_str.timestamp())
        self.logger.debug("start_date_epoch={} before getting events".format(start_date_epoch))
        self.logger.debug("end_date_str={} before getting events".format(str(end_date_str)))



        data_body = json.dumps({
                                "query": opt_query,
                                "timespan": str(start_date)+"/"+str(end_date_str),
            })
        self.logger.debug("data_body:{}".format(data_body))

        response = requests.post(data_url, data=data_body, headers=data_headers, cookies=None, verify=True, cert=None, timeout=300, proxies=proxy_settings)

        if response.status_code == 200:
            response_json=response.json()
            # for loop to find number of events returned
            for i in range(len(response_json["tables"][0]["rows"])):
                event = "{"
                #combine field name and value for all rows
                for n in range(len(response_json["tables"][0]["rows"][i])):
                    field = str(response_json["tables"][0]["columns"][n]["name"])
                    value = str(response_json["tables"][0]["rows"][i][n]).replace('"',"'").replace("\\", "\\\\").replace("None", "").replace("\r\n","")
                    if value == "":
                        continue
                    else:
                        event += '"%s":"%s",' % (field, value)
                event += "}"
                event = event.replace(",}", "}")
                ew.write_event(
                        smi.Event(
                            data=event,
                            #time=event_time,
                            index=input_item["index"],
                            sourcetype=sourcetype,
                        )
                    )
                
            checkpoint_data["since_date"]=str(end_date_str)
            utils.save_check_point(self,input_checkpoint_name,checkpoint_data, CP_ID)
            self.logger.debug('checkpoint set is : {}'.format(checkpoint_data))
            self.logger.info("Data collection completed for input={}".format(input_name))
        
        elif response.status_code == 504:
            self.logger.info("gateway response timeout. specify the Since Date in the input configuration")
            
        else:
            self.logger.error("Failed to fetch events. response={}".format(response.text))
            sys.exit(0)
                            
    except Exception as e:
            self.logger.error("collect_events exception={}".format(e))
            sys.exit(1)
