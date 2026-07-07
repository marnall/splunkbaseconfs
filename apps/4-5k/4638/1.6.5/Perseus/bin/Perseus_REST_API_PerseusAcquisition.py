#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import os
import sys
import json

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application import PersistentServerConnectionApplication

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'Perseus', 'bin']))

import Splunk_KV_Store
import Splunk_Main

class PerseusAcquisition(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, requestIn):

        try:

            #We create a system-level authorization header for completing the KV Store lookup since this would otherwise be an unauthorized attempt at accessing it
            try:
                jsonRequest = json.loads(requestIn)
                headerAuth = Splunk_Main.getAuthorizationHeader(jsonRequest["system_authtoken"])
            except:
                raise Exception("Invalid Json Request")
            
            jsonPayload = json.loads(jsonRequest["payload"])

            #!TFinish - OPTIONAL - Add in some sort of rate-limiting or other means of filtering out malicious uploads
            #This checks to make sure the json passed in is as expected
            
            try:
                #We convert strUploadGuid to _key
                jsonPayload["_key"] = jsonPayload.pop("strUploadGuid")
                strCheck = jsonPayload["strBase64FileContent"]
                strCheck = jsonPayload["strFileName"]
                strCheck = jsonPayload["strUploadType"]
                
            except:
                raise Exception("Invalid Upload Json")            
            
            kvFileRepo = Splunk_KV_Store.SplunkKVStore("PerseusFileRepo", headerAuth)
            kvFileRepo.addEntry(jsonPayload)

            return {'payload': {"Result" : "Acquisition Successfully Uploaded"},
                    'status': 200
                   }

        except Splunk_KV_Store.SplunkAddEntryMaxSizeExceededKVStoreException:

            return {'payload': {"Result" : "Acquisition Upload Failed: The acquisition is larger than the maximum file size that is supported for upload. In order to process this acquisition, you will need to manually transfer the acquisition to the 'Acquisitions' directory of the Perseus Engine"},
                    'status': 422
                   }
        
        except Exception as err:
            
            return {'payload': {"Result" : "Acquisition Upload Failed: " + str(err)},
                    'status': 400
                   }

