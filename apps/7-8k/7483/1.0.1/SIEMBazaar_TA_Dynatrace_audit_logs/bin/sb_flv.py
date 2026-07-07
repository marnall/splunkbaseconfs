from datetime import datetime,timedelta
import os

from solnlib.modular_input import checkpointer
import sb_consts as sc
import sb_report_violation

APP_NAME = __file__.split(os.path.sep)[-3]

def flv(self):
    checkpoint = checkpointer.KVStoreCheckpointer(
            f"{APP_NAME}_l_info",
                self._input_definition.metadata["session_key"],
                APP_NAME
            )
    l_info = checkpoint.get("l_info")
    if not l_info:
        self.log_warning("License info not found. Skipping data collection")
        return
    # Convert the given datetime string to a datetime object
    dt_format = "%a, %d %b %Y %H:%M:%S %Z"

    validation_time = l_info.get("validation_time")
    if not validation_time:
        self.log_warning("License validation info not found. Skipping data collection")
        return
    v_time = datetime.strptime(validation_time, dt_format)
   
    current_utc = datetime.utcnow()

    difference = current_utc - v_time
   
    seven_days = timedelta(days=7)
    if difference > seven_days and l_info.get("pricing_plan") == "1":
        message = f"""Your license has expired. Please renew your license at {sc.SB_DOMAIN}{sc.SB_BUYLICENSE_URL}"""
        self.log_warning(message)
        response = sb_report_violation.report_violation("1",self.get_arg('dynatrace_license')["licensekey"])
        if response.status_code == 200:
            checkpoint.delete("l_info")
        return 0 
    else:
        """write out the events"""
        return 1

