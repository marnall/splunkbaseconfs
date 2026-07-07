import splunk
import os
import sys
import json

import logging as logger
from io import open
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

splunkHome=os.environ.get('SPLUNK_HOME')
tmpDir=splunkHome + "/etc/apps/bv_xv/scm/temp"
logger.info("custom_endpoint file loaded")

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application import PersistentServerConnectionApplication

class Upload(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):

        try:
            python3 = sys.version_info[0] >= 3
            if python3:
                in_string = str(in_string, 'utf-8')

            filename = "default"
            content = "none"

            data = json.loads(str(in_string))

            form = data['form']
            filename = form[0][1]
            content = form[1][1]

            resp = ""

            #logger.info("checking if directory exists: " + tmpDir)
            if not os.path.exists(tmpDir):
                os.makedirs(tmpDir);

            if filename and content:
                filenameFullPath = tmpDir + "/" + filename
                #logger.info("Open file for write: " + filenameFullPath)
                f = open(filenameFullPath, 'w')
                f.write(content);
                #logger.info("Successfully wrote content")
                resp = 'successfuly saved content to file: ' + filenameFullPath
            else:
                logger.info("Bad Request -= parameters filename and/or content are missing")
                status=403
                resp = 'Bad Request - parameters filename and/or content are missing.'

            return {'payload': resp,  # Payload of the request.
                    'status': 200          # HTTP status code
            }
        except Exception as e:
            logger.info(e)
            resp = "Exception Occurred";
            return {'payload': resp,  # Payload of the request.
                    'status': 403          # HTTP status code
            }

