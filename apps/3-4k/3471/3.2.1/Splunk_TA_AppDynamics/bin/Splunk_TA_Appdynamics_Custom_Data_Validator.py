from solnlib import log
from splunktaucclib.rest_handler import error

from Splunk_TA_Appdynamics_BaseRestHandler import BaseRestHandler

logger = log.Logs().get_logger("appdynamics_custom_data_validation")


def _validate_credentials(global_account_name, session_key, applications, metric_list):
    if global_account_name is None:
        return
    logger.info("Validating Custom Data Metrics: account=%s, applications=%s, metric_list=%s", global_account_name,
                applications, metric_list)
    from controller_service import ControllerService
    controller = ControllerService(global_account_name=global_account_name, session_key=session_key,
                                   throw_exceptions=True, logger=logger)
    error_messages = []
    for application in applications:
        app_id = application.split("|")[1]
        app_name = application.split("|")[2]
        for metric in metric_list:
            try:
                data = controller.get_metric_data(app_id, metric, just_verify=True)
                logger.info(f"{app_name} metric '{metric}' data = '{data}'")
            except Exception as e:
                error_messages.append(f"{app_name} metric '{metric}' not found")
    if error_messages != []:
        raise error.RestError(400, "; ".join(error_messages))
    return


class CustomRestHandler(BaseRestHandler):
    def get_payload_as_list(self, parameter, delimiter='~'):
        data = self.payload.get(parameter)
        if data is None:
            logger.debug(f"Parameter {parameter} not found")
            return []
        data = data.split(delimiter)
        if not isinstance(data, list):
            data = [data]
        return data

    def handleEdit(self, confInfo):
        _validate_credentials(
            self.payload.get("global_account"),
            self.getSessionKey(),
            self.get_payload_as_list("application_list"),
            self.get_payload_as_list("metrics_to_collect", ',')
        )
        super().handleEdit(confInfo)

    def handleCreate(self, confInfo):
        _validate_credentials(
            self.payload.get("global_account"),
            self.getSessionKey(),
            self.get_payload_as_list("application_list"),
            self.get_payload_as_list("metrics_to_collect", ',')
        )
        super().handleCreate(confInfo)
