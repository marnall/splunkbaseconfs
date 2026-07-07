import os
import sys
import json
import time

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", "ReloadDeploymentServer", "lib")
)
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration()
class ReloadCommand(GeneratingCommand):
    """ 

    ##Syntax

    | reloadds

    ##Description

    POSTs to the /services/deployment/server/config/_reload endpoint

    """
    def generate(self):
       # Put your event  code here

       # To connect with Splunk, use the instantiated service object which is created using the server-uri and
       # other meta details and can be accessed as shown below
       # Example:-
       #    service = self.service
       service = self.service
       if not service:
           raise ValueError("Could not find instantiated service object")
       service.post("/services/deployment/server/config/_reload")
       yield {"_time": time.time(), "_raw": json.dumps({"message": "Successfully reloaded /services/deployment/server/config endpoint"})}

dispatch(ReloadCommand, sys.argv, sys.stdin, sys.stdout, __name__)
