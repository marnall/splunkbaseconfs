
import import_declare_test
from TA_GoogleSCC_account_validation import AccountValidator
import splunk.rest as rest
import json
import splunk.admin as admin
import traceback

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from solnlib import conf_manager
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from solnlib.modular_input import checkpointer
from TA_GoogleSCC_utils import is_gcp_vm, is_aws_vm, is_azure_vm, get_scheme
from TA_GoogleSCC_logger_manager import setup_logging
from TA_GoogleSCC_consts import constants
import logging

util.remove_http_proxy_env_vars()

logger = setup_logging("ta_googlescc_rh_account")

fields = [
    field.RestField(
        'service_account_json',
        required=True,
        encrypted=True,
        default='',
        validator=AccountValidator()
    ), 
    field.RestField(
        'organization_id',
        required=True,
        encrypted=False,
        default='',
        validator=None
    ),
    field.RestField(
        'credential_configuration_file',
        required=True,
        encrypted=True,
        default='',
        validator=None
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_googlescc_account',
    model,
    config_name='account'
)


class GCCSettingsHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)
        session_key = self.getSessionKey()
        # Checkpoint to store Instance details
        checkpoint_name = constants.INSTANCE_CHECKPOINT
        try:
            checkpoint_collection = checkpointer.KVStoreCheckpointer(
                checkpoint_name, session_key, import_declare_test.ta_name)
            checkpoint_dict = checkpoint_collection.get(checkpoint_name) or {}
            scheme = get_scheme(logger, session_key)
            checkpoint_scheme = checkpoint_dict.get('scheme')
            
            if not checkpoint_dict:
                is_gcp = is_gcp_vm(logger)
                is_aws = is_aws_vm(logger, session_key)
                is_azure = is_azure_vm(logger, session_key)
                checkpoint_collection.update(checkpoint_name, {
                    "is_gcp": is_gcp,
                    "is_aws": is_aws,
                    "is_azure": is_azure,
                    "scheme": scheme
                })
            else:
                if scheme!=checkpoint_scheme:
                    is_gcp = is_gcp_vm(logger)
                    is_aws = is_aws_vm(logger, session_key)
                    is_azure = is_azure_vm(logger, session_key)
                    checkpoint_collection.update(checkpoint_name, {
                        "is_gcp": is_gcp,
                        "is_aws": is_aws,
                        "is_azure": is_azure,
                        "scheme": scheme
                    })
        except Exception:
            logger.error("message=instance_checkpoint_error |"
                         " Error while fetching Instance details KV Store checkpoint. Error:{}".format(traceback.format_exc()))

    
    def handleRemove(self, confInfo):
        conf_file = "inputs"
        APP_NAME = "TA_GoogleSCC"
        try:
            conf_file = conf_manager.ConfManager(
                self.getSessionKey(),
                APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, conf_file),
            ).get_conf(conf_file)
            inputs_file = conf_file.get_all(only_current_app=True)
            created_inputs = list(inputs_file.keys())

        except Exception as e:
            logger.error("message=account_deletion_error | "
                         "Google SCC account deletion: Error occured while getting input details."
                         " Error_message=\"{}\"".format(traceback.format_exc()))
            raise admin.ArgValidationException("Error occured while getting input details. Error=\"{}\"".format(str(e)))
        else:
            input_list = []
            input_type_list = ["sources_input", "assets_input", "findings_input", "auditlog_input"]

            for _input in created_inputs:
                googlescc_input = _input.split('://')
                if googlescc_input[0] in input_type_list:
                    configured_account = inputs_file.get(_input).get('google_scc_account')
                    if configured_account == self.callerArgs.id:
                        input_list.append(googlescc_input[1])
            if len(input_list) > 0:
                logger.error("message=account_deletion_error |"
                             " Google SCC account deletion: Account \"{}\" can not be deleted because "
                             "it is linked with the following inputs: [\"{}\"]".format(self.callerArgs.id,"\", \"".join(input_list)))
                raise admin.ArgValidationException(
                    "Account \"{}\" can not be deleted because it is linked with the following inputs=[\"{}\"]"
                    .format(self.callerArgs.id,"\", \"".join(input_list)))
            else:
                super(GCCSettingsHandler, self).handleRemove(confInfo)

if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=GCCSettingsHandler,
    )