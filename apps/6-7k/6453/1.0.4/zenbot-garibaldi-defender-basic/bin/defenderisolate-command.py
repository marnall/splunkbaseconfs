#!/usr/bin/env python
# coding=utf-8
#
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))  

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import re
import requests
import json

from configparser import SafeConfigParser
import logging

from datetime import datetime, timezone

@Configuration(type="reporting")
class DefenderIsolateCommand(GeneratingCommand):

    stanza = Option(require=True)
    log_level = Option(require=False, default="INFO")
    testmode = Option(require=False, default=False, validate=validators.Boolean())
   
    comment=Option(require=True)
    isolationType=Option(require=True)
    id=Option(require=True)

    def generate(self):

        ntt_logger = logging.getLogger('defenderisolate')
        ntt_logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
        ntt_logger.setLevel(self.log_level)    
        file_handler = logging.handlers.RotatingFileHandler(os.path.join(os.environ['SPLUNK_HOME'], 'var','log','splunk','defenderisolate.log'), maxBytes=5000000, backupCount=5) 
        format = '%(asctime)s Level=%(levelname)s zenBOT=garibaldi-defender Pid=%(process)s Logger=%(name)s File=%(filename)s, Line=%(lineno)s, %(message)s'
        file_handler.setFormatter(logging.Formatter(format))
        ntt_logger.addHandler(file_handler)

        try:

            ntt_logger.info("START GARIBALDI DEFENDER!!")
            ntt_logger.setLevel(logging.INFO if self.log_level == "INFO" else logging.DEBUG)

            scriptDir = sys.path[0]
            ntt_logger.debug(f"scriptDir={scriptDir}")
            configDefaultFileName = os.path.join(scriptDir,'..','default','ntt_data_defender_settings.conf')
            cfg = SafeConfigParser()
            cfg.read(configDefaultFileName)
            configLocalFileName = os.path.join(scriptDir,'..','local','ntt_data_defender_settings.conf')
            cfg.read(configLocalFileName)

            auth_tenantId = cfg.get(self.stanza,'auth_tenantId')
            auth_appId = cfg.get(self.stanza,'auth_appId')
            auth_appSecret = cfg.get(self.stanza,'auth_appSecret')
            auth_url = cfg.get(self.stanza,'auth_url')
            auth_url = f"{auth_url}/{auth_tenantId}/oauth2/token"
            auth_resourceAppIdUri = cfg.get(self.stanza,'auth_resourceAppIdUri')

            ntt_logger.debug(auth_tenantId)
            ntt_logger.debug(auth_appId)
            ntt_logger.debug(auth_appSecret)
            ntt_logger.debug(auth_url)
            ntt_logger.debug(auth_resourceAppIdUri)
            ntt_logger.debug(f'self.testmode={self.testmode}')

            record = {}
            if not self.testmode:
                ntt_logger.info("Authentication Start")
                body = {
                    'resource' : auth_resourceAppIdUri,
                    'client_id' : auth_appId,
                    'client_secret' : auth_appSecret,
                    'grant_type' : 'client_credentials'
                }
                req = requests.Request('GET',auth_url,data=body)
                prepared = req.prepare()

                ntt_logger.debug(f"method={prepared.method}")
                ntt_logger.debug(f"headers={prepared.headers}")
                ntt_logger.debug(f"body={prepared.body}")
                ntt_logger.debug(f"path_url={prepared.path_url}")

                session = requests.Session()
                response = session.send(prepared,timeout=120)
                #ntt_logger.debug(response.status_code)

                if re.search('[1345]\d+', str(response.status_code), re.IGNORECASE):
                    record['_time'] = (int(datetime.now(timezone.utc).timestamp()))
                    record['aadToken']=aadToken
                    record['response_status_code'] = response.status_code
                    record['response_text'] = response.text
                    ntt_logger.error('Authentication Failed')
                    yield record
                    raise Exception("Authentication Failed")

                try:
                    json_data = response.json()
                    aadToken = json_data["access_token"]
                    record['aadToken']=aadToken
                    ntt_logger.info("Authentication Complete")
                except:
                    record['_time'] = (int(datetime.now(timezone.utc).timestamp()))
                    record['aadToken']=''
                    record['error'] = 'Authentication Failed. access_token not in response. Check access paramters in ntt_data_defender_settings.conf'
                    ntt_logger.error('Authentication Failed. access_token not in response. Check access paramters in ntt_data_defender_settings.conf')
                    yield record
                    return 
            else:
                aadToken = 'aadTestToken'
                record['aadToken']=aadToken
                ntt_logger.info("Authentication Complete Testmode ON")
            ntt_logger.debug(f'aadToken={aadToken}')
            

            headers = { 
                    'Content-Type' : 'application/json',
                    'Accept' : 'application/json',
                    'Authorization' : f"Bearer {aadToken}" 
                }
                
            payload = {
                "Comment": self.comment,
                "IsolationType": self.isolationType 
            }

            if self.log_level == 'DEBUG':
                record['payload'] = payload
            
            if not self.testmode:
                ntt_logger.info("Isolate Start")
                api_url=f"{auth_resourceAppIdUri}/api/machines/{self.id}/isolate"
                response = requests.post(api_url,headers=headers,data=json.dumps(payload),verify=False)
                if re.search('[1345]\d+', str(response.status_code), re.IGNORECASE):
                    record['response_status_code'] = response.status_code
                    record['response_text'] = response.text
                    ntt_logger.error("Isolate Error")
                else:
                    record['response_status_code'] = response.status_code
                    ntt_logger.info("Isolate Complete")
            else:
                record['response_status_code'] = '200'
                record['testmode'] = 'true'    
                ntt_logger.info("Isolate Complete Testmode ON")

            yield record
            
            ntt_logger.info("END GARIBALDI DEFENDER!!")

        except Exception as ex:
            ntt_logger.info("END GARIBALDI DEFENDER WITH EXCEPTION!!")
            ntt_logger.error(str(ex), exc_info=1)
            record = {}
            record["call_result"] = f"Exception: {ex}"
            yield record
            raise ex

dispatch(DefenderIsolateCommand, sys.argv, sys.stdin, sys.stdout, __name__)
