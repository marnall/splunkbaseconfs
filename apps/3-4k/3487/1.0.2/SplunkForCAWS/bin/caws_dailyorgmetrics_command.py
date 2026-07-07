import sys, os, time
import json
from datetime import datetime, timedelta
from caws.cawsmetricssearchcommand import CawsMetricsSearchCommand
import caws.cawsutility as cawsutility
from splunklib.searchcommands import dispatch

class DailyOrgMetricsCommand(CawsMetricsSearchCommand):
    """  
    A custom search command to get daily organization metrics from the CAWS API.
    """

    @property
    def api_endpoint(self):
        return "statistics/global"

    def __init__(self):
        """
        Initializes an instance of the CawsSearchCommand class.
        """
        super(DailyOrgMetricsCommand, self).__init__()

    def parseApiResponse(self, response):
        results = []
        dailyResults = {}
                
        #Parse each daily exploit
        if response != None:                        
            metrics = json.loads(response)
            dailyExploits = metrics["Exploits"]["Daily"]
            for item in dailyExploits:                
                date = str(item["Date"])
                timestamp = cawsutility.get_iso_date(date)
                if dailyResults.has_key(date) == False:
                    dailyResults[date] = {
                        "_time": date
                    }

                dailyResults[date]["Exploits"] = int(item["Count"])

            dailyUrls = metrics["Urls"]["Daily"]
            for item in dailyUrls:
                date = str(item["Date"])
                timestamp = cawsutility.get_iso_date(date)
                if dailyResults.has_key(date) == False:
                    dailyResults[date] = {
                        "_time": date
                    }

                dailyResults[date]["MaliciousUrls"] = int(item["Count"])
                dailyResults[date]["AverageUrlTtl"] = int(item["AverageTtl"])
                
            results = [value for key, value in dailyResults.items()]

        for result in results:
            yield result

dispatch(DailyOrgMetricsCommand, sys.argv, sys.stdin, sys.stdout, __name__)