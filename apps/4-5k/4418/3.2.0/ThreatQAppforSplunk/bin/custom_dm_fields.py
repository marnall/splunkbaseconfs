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

logger = log.setup_logging("threatquotient_custom_dm_fields")

class CompanyTree(admin.MConfigHandler):
    """Get the Reporting feeds data."""

    def setup(self):
        """To setup the variables to access in list."""
        self.supportedArgs.addOptArg("custom_datamodels")

    def handleList(self, conf_info):
        """Populate the company multiselect dropdown."""
        splunk_session_key = self.getSessionKey()     
        try:
            fields_list = []
            selected_dm_combo = self.callerArgs.data.get("custom_datamodels")
            if isinstance(selected_dm_combo, list):
                # REST handler often gives lists
                selected_dm_combo = selected_dm_combo[0] if selected_dm_combo else None

            datamodel_name = None
            object_name = None

            if selected_dm_combo:
                parts = selected_dm_combo.split(" - ", 1)
                datamodel_name = parts[0].strip()
                if len(parts) > 1:
                    object_name = parts[1].strip()

            serviceobj = create_service(splunk_session_key)
            kwargs_oneshot = {"earliest_time": "-35m", "latest_time": "now", "count": 0}

            try:
                if datamodel_name and object_name:
                    search_query = (
                        "| datamodel {} {} search | fieldsummary | table field"
                    ).format(datamodel_name, object_name)
                    device_result2 = serviceobj.jobs.oneshot(search_query, **kwargs_oneshot)
                    device_reader2 = results.ResultsReader(device_result2)
                    for result in device_reader2:
                        res = dict(result)
                        fields_list.append(res["field"])
            except Exception:
                pass
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
