#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import six

import os
import sys
import json

import uuid
import base64
import zipfile
            
if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application import PersistentServerConnectionApplication

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'Perseus', 'bin']))

import Splunk_Main
import Perseus_Cache

class PerseusAcquisition_Demo_Upload_Results(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, requestIn):

        try:

            #!TFinish - OPTIONAL - Add in some sort of rate-limiting or other means of filtering out malicious uploads
            
            #We create a system-level authorization header for completing the KV Store lookup since this would otherwise be an unauthorized attempt at accessing it
            try:
                jsonRequest = json.loads(requestIn)
                headerAuth = Splunk_Main.getAuthorizationHeader(jsonRequest["system_authtoken"])
            except:
                raise Exception("Invalid Json Request")
            
            jsonPayload = json.loads(jsonRequest["payload"])
            strHostGuid = jsonPayload["strHostGuid"]

            #Parse the Acquisition Results Json out of the Encoded Zip File In Memory
            strEventsJson = None

            strExpectedFileNameLC = (strHostGuid + ".json").lower()
            inFile = six.BytesIO(base64.b64decode(jsonPayload["strBase64FileContent"]))
            zipFile = zipfile.ZipFile(inFile)
            for strFileName in zipFile.namelist():
                if (strFileName.lower() == strExpectedFileNameLC):
                    strEventsJson = zipFile.read(strFileName)
                
            inFile.close()

            if (strEventsJson is None):
                raise Exception("Invalid Acquisition Results Zip File")

            cache = Perseus_Cache.RecollectionModsCache(headerAuth)

            #We clear the Cache/Cache Info in case there were previous entries present in the demo
            cache.removeAllEntries()
            cache.kvCacheInfo.removeAllEntries()

            cache.createCacheForHostFromJsonEventsString(None, strHostGuid, strEventsJson)

            return {'payload': {"Result" : "Acquisition Results Uploaded" },
                    'status': 200
                   }

        except Exception as err:
            
            return {'payload': {"Result" : "Acquisition Results Upload Failed: " + str(err)},
                    'status': 400
                   }

