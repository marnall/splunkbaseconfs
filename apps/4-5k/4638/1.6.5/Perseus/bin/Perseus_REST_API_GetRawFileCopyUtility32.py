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

import Splunk_Main
import Perseus_Utility_File_Repo

class GetRawFileCopyUtility32(PersistentServerConnectionApplication):
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
            
            return {'payload': Perseus_Utility_File_Repo.getUtilityFileKvStoreEntryByKey("3c78b096-236f-4b0c-9076-9a7ac1080132", headerAuth),
                    'status': 200
                   }
            
        except Exception as err:
            
            return {'payload': {"Result" : "Get Raw File Copy Utility Failed: " + str(err)},
                    'status': 400
                   }
