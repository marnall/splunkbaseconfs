"""This file is used for input page validation."""
import import_declare_test  # noqa F401
from splunktaucclib.rest_handler.endpoint.validator import Validator
from TA_GoogleSCC_logger_manager import setup_logging
import json
import traceback
from solnlib import conf_manager
from googleapiclient.errors import HttpError
import TA_GoogleSCC_apiclient as gsa
import splunk.admin as admin
from TA_GoogleSCC_utils import get_project_id

logger = setup_logging('ta_googlescc_input_validation')


class GetSessionKey(admin.MConfigHandler):
    """Session key."""

    def __init__(self):
        """Initialize Session Key."""
        self.session_key = self.getSessionKey()


class CredsValidator(Validator):
    """This class validates if the Project ID and SubscriptionID passed for validation in input is valid or not."""  # noqa: E501

    def validate(self, value, data):
        """We define Custom validation here for verifying Project ID and SubscriptionID field."""
        session_key = GetSessionKey().session_key
        subscription_name = data.get('audit_logs_subscription_id', data.get('assets_subscription_id', data.get('findings_subscription_id')))  # noqa: E501
        try:
            subscription_name_split = subscription_name.split("/")
            project_id = subscription_name_split[1]
            subscription_id = subscription_name_split[3]
        except Exception:
            logger.error("message=invalid_subscription |"
                         " Error occured while validating Subscription Name. Invalid subscription format.")
            self.put_msg("Invalid Subscription format. Please enter Subscription Name in \
             'projects/{project_id}/subscriptions/{subscription_id}' format.", True)
            return False

        try:
            account = data.get('google_scc_account')
            cfm = conf_manager.ConfManager(
                session_key, import_declare_test.ta_name, realm='__REST_CREDENTIAL__#{}#configs/conf-{}'.format(import_declare_test.ta_name, import_declare_test.ta_accounts_conf))  # noqa: E501
            account_conf_file = cfm.get_conf(import_declare_test.ta_accounts_conf)
            account_info = account_conf_file.get(account)
            service_account_json = account_info.get('service_account_json')
            service_account_json = json.loads(service_account_json)
            credential_configuration_file = account_info.get('credential_configuration_file')
            organization_id = account_info.get('organization_id')
            project_ID = get_project_id(logger, project_id, service_account_json)

        except Exception:
            logger.error("message=account_error |"
                         " Failed to fetch account details from configuration.\n{}".format(traceback.format_exc()))
            return False

        CONFIG_TIMEOUT = 60
        scc_sub_client = gsa.init_google_pubsub_client(
                project_id=project_ID,
                subscription_id=subscription_id,
                service_account_json=service_account_json,
                credential_configuration_file=credential_configuration_file,
                logger=logger,
                organization_id=organization_id,
                timeout=CONFIG_TIMEOUT,
                session_key=session_key,
        )

        try:
            body = {"max_messages": 1, "return_immediately": True}
            validate = scc_sub_client.service.projects().subscriptions().pull(
                    subscription=subscription_name,
                    body=body
            )
            data = validate.execute()
            return True
        except HttpError as e:
            status = e.resp.status
            reason = e._get_reason()
            logger.error("message=http_error |"
                         " HttpError occurred with status={0}. {1}".format(status, reason))
            self.put_msg("Verify Project ID or Subscription ID.", True)
            return False
        except Exception as e:
            logger.error("message=validation_error |"
                         " Error occured while validating Project ID and Subscription ID.\n"
                         "{}".format(traceback.format_exc()))
            self.put_msg(e, True)
            return False
