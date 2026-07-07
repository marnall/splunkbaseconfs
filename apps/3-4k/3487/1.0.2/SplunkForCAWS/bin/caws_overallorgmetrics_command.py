import sys, os, time
import json
from datetime import datetime, timedelta
from caws.cawsmetricssearchcommand import CawsMetricsSearchCommand
import caws.cawsutility as cawsutility
from splunklib.searchcommands import dispatch

class OverallOrgMetricsCommand(CawsMetricsSearchCommand):
    """  
    A custom search command to get overall organization metrics from the CAWS API.
    """

    @property
    def api_endpoint(self):
        return "statistics/global"

    def __init__(self):
        """
        Initializes an instance of the CawsSearchCommand class.
        """
        super(OverallOrgMetricsCommand, self).__init__()

    def parseApiResponse(self, response):
        #Parse each daily exploit
        if response != None:                        
            metrics = json.loads(response)

            result = {
                "applicationsTested": int(metrics["Applications"]["Tested"]),
                "applicationsCompromised": int(metrics["Applications"]["Compromised"]),
                "exploits": int(metrics["Exploits"]["Total"]),
                "urlsScanned": int(metrics["Urls"]["Scanned"]),
                "maliciousUrls": int(metrics["Urls"]["Malicious"]),
                "averageUrlTtl": float(metrics["Urls"]["AverageTtl"])
            }

            return [result]

        return []            

dispatch(OverallOrgMetricsCommand, sys.argv, sys.stdin, sys.stdout, __name__)