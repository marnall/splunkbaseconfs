from datetime import datetime,timedelta
import os

from solnlib.modular_input import checkpointer
import sb_consts as sc
import sb_report_violation
import sb_utils as utils
from sb_utils import get_account_details
import sys

APP_NAME = __file__.split(os.path.sep)[-3]
CP_ID="l_info"

def flv(self, input_item, id):
    l_info_checkpoint_name = input_item["sb_license"]+"_"+CP_ID
    l_info = utils.get_check_point(self, l_info_checkpoint_name, CP_ID)
    if not l_info:
        self.logger.warning("License info not found. Skipping data collection")
        return
    # Convert the given datetime string to a datetime object
    dt_format = "%a, %d %b %Y %H:%M:%S %Z"

    validation_time = l_info.get("validation_time")
    if not validation_time:
        self.logger.warning("License validation info not found. Skipping data collection")
        return
    v_time = datetime.strptime(validation_time, dt_format)
   
    current_utc = datetime.utcnow()

    difference = current_utc - v_time
   
    seven_days = timedelta(days=7)
    if difference > seven_days and l_info.get("pricing_plan") == "1":
        message = f"""Your license has expired. Please renew your license at {sc.SB_DOMAIN}{sc.SB_BUYLICENSE_URL}"""
        self.logger.warning(message)
        license_info = get_account_details(self.session_key, self.logger, "license", input_item["sb_license"])
        response = sb_report_violation.report_violation(id,license_info.get("licensekey"))
        if response.status_code == 200:
            utils.delete_check_point(self, l_info_checkpoint_name, CP_ID)
        return 0 
    else:
        """write out the events"""
        return 1

