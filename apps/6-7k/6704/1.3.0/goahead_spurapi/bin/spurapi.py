#!/usr/bin/env/python3 
# -*- coding: utf-8 -*-

from ipaddress import ip_address
import os.path
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import commonlib

APPNAME = "goahead_spurapi"
CREDUSER = 'spur_api_user1'
CREDREALM = 'spur_api_realm'

def format_output(context):
    output = {}
    for key, value in context.items():
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        output[key+"."+k+"."+k2] = v2
                else:
                    output[key+"."+k] = v
        elif key == "tunnels":
            for i in value:
                for k, v in i.items():
                    output["tunnels["+str(value.index(i))+"]."+k] = v
        else:
            output[key] = value
    return output

@Configuration()
class spurapi(StreamingCommand):
  ip_field = Option(require=True,doc=''' target_ip ip field name to input ''',validate=validators.Fieldname())
  apisaver = Option(doc=''' API amount saver , default: true. This app raise exception if your event over 50. Please set apisaver=false to avoid this limit ''',require=False,default="true",validate=validators.Boolean())

  def prepare(self):
    self.configuration.required_fields = [self.ip_field]

  def stream(self, events):
    #self.logger.info('spurapi: %s', vars(self))
    try:
      sessionkey = self.metadata.searchinfo.session_key
      if sessionkey is None:
        raise Exception("[Session Error] Did not receive a session key from splunkd.")

      apitoken = commonlib.get_credentials(sessionkey,APPNAME,CREDUSER,CREDREALM)
    except Exception as e:
      self.logger.exception("spurapi raised Exception")
      raise Exception("[Credential Error] Could not retrieve credential from Splunk Secret Storage by {}".format(str(e)))

    list_events = list(events)
    if self.apisaver and len(list_events) > 50:
      raise Exception("This execution tries to consume over 50 API query counts of Spur API. This is a kind alert. Please set the argument option of apisaver=false to avoid this limit.")

    duplicated = {}
    try:
      for event in list_events:
        spur_context = {}
        response_json = {}
        try:
          if self.ip_field not in event: 
            raise Exception(f"(FIELD ERROR) the fieldname '{self.ip_field}' doesn't exist.")       

          target_ip = event[self.ip_field]

          # check target_ip is a public ip address which is worth for Spur API. 
          if not commonlib.is_valid_external_ipaddress(self.logger,target_ip):
            spur_context["app_status"] = "Not Valid Public IP address."  
            event.update(spur_context)
            yield event
            continue

          if not target_ip in duplicated:
            time.sleep(0.3)
            response_json = commonlib.request_spurapi(self.logger,target_ip,apitoken)
            if response_json.get("app_status")=="ok":
              spur_context = format_output(response_json)
              duplicated[target_ip] = spur_context                 
            else:
              spur_context = response_json
          else:
            spur_context = duplicated[target_ip]
        except Exception as e:
          self.logger.exception("Unexpected")
          if len(response_json) > 0: 
            response_json["app_status"] = "[Unexpected Exception] " + str(e) 
            spur_context = response_json
          else:
            spur_context["app_status"] = "[Unexpected Exception] " + str(e)  

        prefix_context = {}
        for key,value in spur_context.items():
            prefix_context["Spur_%s"%key] = value
             
        event.update(prefix_context)
        yield event

    except Exception as e:
      self.logger.exception("Unexpected Exception")
      raise Exception(f"Unexpected Error {str(e)}")

dispatch(spurapi, sys.argv, sys.stdin, sys.stdout, __name__)