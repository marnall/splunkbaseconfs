#!/usr/bin/env/python3 
# -*- coding: utf-8 -*-

import os.path
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import commonlib

APPNAME = 'goahead_bingwebsearch'
CREDUSER = 'bingwebsearch_user1'
CREDREALM = 'bingwebsearch_realm'

@Configuration()
class binghostinfo(StreamingCommand):
  input_field = Option(require=True,doc=''' Target field name to input, ip or domain is expected.''',validate=validators.Fieldname())
  mode = Option(require=True,doc=''' Bing API's search query Operators of ip: or domain:  ''',validate=validators.Set("ip","domain"))
  mkt = Option(require=False,doc=''' One market code like en-US, ja-JP, No mkt setting is by default. ''')
  apisaver = Option(doc=''' API amount saver , default: true. This app raise exception if your event over 50. Please set apisaver=false to avoid this limit ''',require=False,default="true",validate=validators.Boolean())

  def prepare(self):
    self.configuration.required_fields = [self.input_field,self.mode]

  def stream(self, events):
    #self.logger.info('binghostinfo: %s', vars(self))
    try:
      sessionkey = self.metadata.searchinfo.session_key
      if sessionkey is None:
        raise Exception("[Session Error] Did not receive a session key from splunkd.")

      apikey = commonlib.get_credentials(sessionkey,APPNAME,CREDUSER,CREDREALM)
    except Exception as e:
      self.logger.exception("bingwebsearch raised Exception")
      raise Exception("[Credential Error] Could not retrieve credential from Splunk Entity via the API server by {}".format(str(e)))

    if self.mode=="ip":
      operator_type = "ip:"
    elif self.mode=="domain":
      operator_type = "domain:"
    else:
      self.logger.error(f"bingwebsearch command process invoke exception. the mode of {self.mode} is unexpected.")
      raise Exception(f"Unexpected mode: {self.mode}. mode=ip or mode=domain is available in current version.") 

    params = {
      'responseFilter': "Webpages",
      'count' : 50,
      'offset' : 0
    }

    if self.mkt is not None:
      params["mkt"] = self.mkt

    list_events = list(events)
    if self.apisaver and len(list_events) > 50:
      raise Exception("This execution tries to consume over 50 API query counts of Bing Web Search API. This is a kind alert because Free subscription is only 1000/month. Please set apisaver=false to avoid this limit.")

    duplicated = {}
    try:
      for event in list_events:
        result_json = {}
        bing_hostinfos = []
        try:
          if self.input_field not in event: 
            raise Exception(f"(FIELD ERROR) the fieldname '{self.input_field}' doesn't exist.")       

          target = event[self.input_field]
          if not target in duplicated:
            params["q"] = operator_type + target
            time.sleep(0.3)
            self.logger.debug(f"API Query parameters: {params}") 
            response_json = commonlib.request_bingapi(self.logger,params,apikey)
            if response_json.get("app_status")!="ok":
              result_json = { "Bing_hostinfo": None, "Bing_hostcount":None, "app_status": response_json.get("app_status") }
            else:
              webPages = response_json.get("webPages")
              if webPages is not None:
                for webpage in webPages.get("value"):
                  info = {}
                  info["title"] = webpage.get("name")
                  info["url"] = webpage.get("url")
                  info["language"] = webpage.get("language")  
                  bing_hostinfos.append(info)            
                duplicated[target] = bing_hostinfos
                result_json = { "Bing_hostinfo": bing_hostinfos, "Bing_hostcount":len(bing_hostinfos), "app_status": "ok" }
              else:
                bing_hostinfos = []
                duplicated[target] = bing_hostinfos
                result_json = { "Bing_hostinfo": bing_hostinfos, "Bing_hostcount":len(bing_hostinfos), "app_status": "no webPages hit by [" + params["q"] + "] query" }                
          else:
            bing_hostinfos = duplicated[target]
            result_json = { "Bing_hostinfo": bing_hostinfos, "Bing_hostcount":len(bing_hostinfos), "app_status": "ok" }
          
        except Exception as e:
          self.logger.exception("Unexpected")
          result_json = { "Bing_hostinfo": bing_hostinfos, "Bing_hostcount":len(bing_hostinfos), "app_status": "[Unexpected Exception] " + str(e)  }  
         
        event.update(result_json)
        yield event
    except Exception as e:
      self.logger.exception("Unexpected Exception")
      raise Exception(f"Unexpected Error {str(e)}")

dispatch(binghostinfo, sys.argv, sys.stdin, sys.stdout, __name__)