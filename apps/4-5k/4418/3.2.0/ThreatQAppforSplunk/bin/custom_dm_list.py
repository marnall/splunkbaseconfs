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

logger = log.setup_logging("threatquotient_custom_dms")

class CompanyTree(admin.MConfigHandler):
    """Get the Reporting feeds data."""

    def setup(self):
        """To setup the variables to access in list."""
        pass

    def handleList(self, conf_info):
        """Populate the company multiselect dropdown."""
        splunk_session_key = self.getSessionKey()     
        spl_search = ''   
        try:
            fields_list = []
            spl_search = (
                '| rest /services/datamodel/model splunk_server=local '
                '| search eai:acl.app!=Splunk_SA_CIM '
                '| rex field=description "\\\"objects\\\":\\[\\{\\"objectName\\\":\\"(?<objectName>[^\\"]+)\\"" '
                '| table objectName title '
                '| rename title as display_name objectName as object_Name'
            )
            kwargs_oneshot = {"earliest_time": "-35m", "latest_time": "now", "count": 0}
            serviceobj = create_service(splunk_session_key)
            device_result = serviceobj.jobs.oneshot(spl_search, **kwargs_oneshot)
            device_reader = results.ResultsReader(device_result)
            for result in device_reader:
                res = dict(result)
                if isinstance(res["object_Name"], list):
                    if res["object_Name"]:
                        object_name = str(res["object_Name"][0])
                    else:
                        object_name = None
                else:
                    object_name = res["object_Name"]
                if res["display_name"] and object_name:
                    display_name_and_object_name = res["display_name"] + " - " + object_name
                    fields_list.append(display_name_and_object_name)
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
