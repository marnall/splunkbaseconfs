import os
import traceback

import import_declare_test
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import splunk.admin as admin
import TA_cisco_cybervision_utils as utils
from solnlib import log, conf_manager
from solnlib.utils import is_true


class AccountCleanUpHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, confInfo):
        log_filename = "TA_cisco_cybervision_rh_account_cleanup"
        logger = log.Logs().get_logger(log_filename)

        input_conf_file_name = "inputs"
        account_conf_file_name = "ta_cisco_cybervision_account"
        APP_NAME = "TA-cisco_cybervision"
        account_stanza_name = self.callerArgs.id
        try:
            account_conf_file = conf_manager.ConfManager(
                self.getSessionKey(),
                APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, account_conf_file_name),
            ).get_conf(account_conf_file_name)
            account_conf_file_stanza = account_conf_file.get(account_stanza_name)
            inputs_conf_file = conf_manager.ConfManager(
                self.getSessionKey(),
                APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, input_conf_file_name),
            ).get_conf(input_conf_file_name)
            inputs_file = inputs_conf_file.get_all(only_current_app=True)
            created_inputs = list(inputs_file.keys())
            input_list = []
            input_type_list = ["cybervision_activities", "cybervision_components","cybervision_devices", "cybervision_events", "cybervision_flows", "cybervision_vulnerabilities"]

            for _input in created_inputs:
                cisco_cv_input = _input.split('://')
                if cisco_cv_input[0] in input_type_list:
                    configured_account = inputs_file.get(_input).get('global_account')
                    if configured_account == account_stanza_name:
                        input_list.append(cisco_cv_input[1])
            if len(input_list) > 0:
                raise admin.ArgValidationException("Account '{}' can not be deleted because it is linked with the following inputs= {}".format(account_stanza_name, input_list))

            if is_true(account_conf_file_stanza.get("use_ca_cert", False)):
                cert_file_name = account_conf_file_stanza.get("copy_account_name")
                cert_file_loc = utils.CERT_FILE_LOC.format(cert_name=cert_file_name)
                if os.path.exists(cert_file_loc):
                    os.remove(cert_file_loc)
                    logger.info(
                        "account_name={} | message=CA_cert_deleted_successfully | CA cert deleted successfully "
                        "for the Account: {}".format(account_stanza_name, account_stanza_name)
                    )
            super(AccountCleanUpHandler, self).handleRemove(confInfo)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise admin.ArgValidationException(e)