#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import galib

APPNAME = "goahead_hatching_triage_utils"
CREDUSER = 'triageapp_user1'
CREDREALM = 'triage_realm'
COMMANDNAME = 'triagereport'

logger = galib.setup_logging(APPNAME)

@Configuration()
class triagereport(GeneratingCommand):
  instance = Option(doc=''' triage sandbox instance whether "public" or "private" or "recordedfuture" ''',require=True,validate=validators.Set('public','private','recordedfuture'))
  report = Option(doc=''' report kind to get ''',require=True,validate=validators.Set("base","summary","static","overview","dynamic","onemon","pcap","pcapng","magic","ioc_extracted","proc_tree")) 
  sampleID = Option(doc=''' sampleID of the report ''',require=True)
  taskID = Option(doc=''' (Optional) taskID of the report ''',require=False)

  # pcap and pcapng is just show the download url path

  # dangerous path
  # GET /samples/{sampleID}/{taskID}/files/{fileName}
  # GET /samples/{sampleID}/sample

  # out of scope: GET /samples/events GET /samples/{sampleID}/events

  def generate(self):
    try:
      #logger.debug('triagereport: %s', vars(self))
      try:
        sessionkey = self.metadata.searchinfo.session_key
        if sessionkey is None:
          raise Exception("[Session Error] Did not receive a session key from splunkd.")
        apikey = galib.get_credentials(sessionkey,APPNAME,CREDUSER,CREDREALM)
      except Exception as e:
        raise Exception("[Credential Error] Could not retrieve credential from Splunk Entity via the API server by '{}'".format(str(e)))

      if self.instance == "public":
        baseUrl = "https://api.tria.ge/v0/"
      elif self.instance == "private":
        baseUrl = "https://private.tria.ge/api/v0/"   
      elif self.instance == "recordedfuture":
        baseUrl = "https://sandbox.recordedfuture.com/api/v0/" 
      else:
        raise Exception("[Option Error] Please specify 'public' or 'private' or 'recordedfuture' in order to choose which Hatching Triage sandbox instance to access.")
        return 0

      if not self.taskID: self.taskID = None

      # run query 
      try:
        from triagelib import getreport
        jsonResponse = getreport(baseUrl,apikey,self.report,self.sampleID,self.taskID,logger)
      except Exception as e:
        raise Exception("[API Error] Could not retrieve a valid json results by '{}'".format(str(e)))
        return 0

      if self.report == "onemon":
        if isinstance(jsonResponse,dict):
          if "triage_json_error" in jsonResponse:
            logger.info("({}) data:{}".format(type(jsonResponse["triage_json_error"]),jsonResponse["triage_json_error"]))
            yield { "onemon_data": jsonResponse["triage_json_error"] }
        elif isinstance(jsonResponse,list):
          ndjson = jsonResponse
          for result in ndjson:
            yield result
        else:
          raise Exception("[Response Error] Onemon option is not worked, unavailable. Please check whether the standalone api access is fine.")

      elif self.report == "ioc_extracted":
        extractedJson = { "config_c2": [], "dropper_source": [] }
        extracted = jsonResponse.get("extracted")
        for entry in extracted:
          if "config" in entry:
            c2_data = entry.get("config").get("c2")
            if c2_data:
              if isinstance(c2_data,list): 
                extractedJson["config_c2"].extend(c2_data)
              else:
                extractedJson["config_c2"].append(c2_data)
          elif "dropper" in entry:
            source_data = entry.get("dropper").get("source")
            if source_data:
              if isinstance(source_data,list): 
                extractedJson["dropper_source"].extend(source_data)
              else:
                extractedJson["dropper_source"].append(source_data)
        yield extractedJson
      
      elif self.report == "proc_tree":
        from triagelib import maketree,appendfamily_sig,appendfamily_extracted,appendhash,appendnetwork
        resultTree = []
        try: 
          resultTree = maketree(jsonResponse["processes"])
          if len(resultTree)==len(jsonResponse["processes"]):
            logger.info("[maketree] resultTree was created successfully. process count: %d, orig_processes: %d"%(len(resultTree),len(jsonResponse["processes"])))
          else:
            logger.warning("[maketree] resultTree was created, but not enough processes to reproduce the tree. process count in tree: %d, orig_processes: %d"%(len(resultTree),len(jsonResponse["processes"])))
        except Exception as e:
          logger.exception("Fail to create process tree !")
          yield { "proc_tree_response_status": "Parse Error by %s"%str(e) }

        try:  
          resultTree = appendfamily_sig(resultTree,jsonResponse['signatures'])
        except Exception as e:
          logger.warning("(%s) Fail to complete appending malware family from signature"%str(e))
        try:
          resultTree = appendfamily_extracted(resultTree,jsonResponse['extracted'])
        except Exception as e:
          logger.warning("(%s) Fail to complete appending malware family from extracted"%str(e))
        try:
          resultTree = appendhash(resultTree,jsonResponse['dumped'])
        except Exception as e:
          logger.warning("(%s) Fail to complete appending process image file hash from dumped"%str(e))
        try:
          resultTree = appendnetwork(resultTree,jsonResponse['network'])   
        except Exception as e:
          logger.warning("(%s) Fail to complete appending network flow c2 from network flow"%str(e))
        
        logger.info("Final resultTree length: %s"%len(resultTree))
        for result in resultTree:
          yield result

      else:
        # return the results to splunk output
        yield jsonResponse
      
    except Exception as e:
      logger.exception("Unexpected Error: {}".format(str(e)))
      raise Exception("[Unexpected Error]: Please see the error detail in app log or search log. '{}'".format(str(e)))
      return 1
      
dispatch(triagereport, sys.argv, sys.stdin, sys.stdout, __name__)
