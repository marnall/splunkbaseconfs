import threatquotient_app_declare     # noqa: F401
import traceback
import splunk.admin as admin
from splunktaucclib.rest_handler import util
import splunklib.results as results
import logger_manager as log
from threatq_utils import create_service

from threatq_const import DATAMODEL_AND_ITS_SEARCH_MAP

util.remove_http_proxy_env_vars()

APP_NAME = "ThreatQAppforSplunk"

logger = log.setup_logging("threatquotient_field_tree")

class CompanyTree(admin.MConfigHandler):
    """Get the Reporting feeds data."""

    def setup(self):
        """To setup the variables to access in list."""
        self.supportedArgs.addOptArg("index_to_consider")
        self.supportedArgs.addOptArg("selected_datamodel")
        self.supportedArgs.addOptArg("match_type_custom_fields")

    def handleList(self, conf_info):
        """Populate the company multiselect dropdown."""
        splunk_session_key = self.getSessionKey()     
        spl_search = ''   
        try:
            fields_list = []
            index_list = self.callerArgs.data.get("index_to_consider")
            selected_datamodel = self.callerArgs.data.get("selected_datamodel")
            match_type = self.callerArgs.data.get("match_type_custom_fields")
            serviceobj = create_service(splunk_session_key)

            if match_type[0] == "raw":
                if index_list[0]:
                    items = index_list[0].split(',')
                    formatted_string = ', '.join(f'"{item.strip()}"' for item in items)
                    result2 = f"({formatted_string})"
                    spl_search = "search index IN {} earliest=-24h latest=now | fieldsummary | table field".format(result2) 
                device_result = serviceobj.jobs.oneshot(spl_search, count=0)
                device_reader = results.ResultsReader(device_result)
                for result in device_reader:
                    res = dict(result)
                    fields_list.append(res["field"])
            elif match_type[0] in ["tstats", "datamodel"]:
                kwargs_oneshot = {"earliest_time": "-24h", "latest_time": "now", "count": 0}
                items2 = selected_datamodel[0].split(',')
                formatted_list2 = [item.strip() for item in items2]
                for dm in formatted_list2:
                    for each_dm in DATAMODEL_AND_ITS_SEARCH_MAP[dm]:
                        try:
                            search_query = "{} | fieldsummary | table field".format(each_dm)
                            device_result2 = serviceobj.jobs.oneshot(search_query, **kwargs_oneshot)
                            device_reader2 = results.ResultsReader(device_result2)
                            for result in device_reader2:
                                res = dict(result)
                                fields_list.append(res["field"])
                        except Exception:
                            continue
        except Exception as e:
            message = "Unexpected Error : {}".format(e)
            logger.error("{} \n Traceback : {}".format(message, traceback.format_exc()))
        else:
            for each in fields_list:
                conf_info[each]
            logger.debug("Updated the dropdown options.")    

if __name__ == "__main__":
    """Driving function."""
    admin.init(CompanyTree, admin.CONTEXT_NONE)
