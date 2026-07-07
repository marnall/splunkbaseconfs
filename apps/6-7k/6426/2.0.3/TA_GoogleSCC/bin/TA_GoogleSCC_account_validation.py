"""This file is used for validating Google SCC account."""
from splunktaucclib.rest_handler.endpoint.validator import Validator
from TA_GoogleSCC_logger_manager import setup_logging
from google.oauth2 import service_account
from google_auth_httplib2 import AuthorizedHttp
import google.auth
from google.auth import aws
from google.auth import identity_pool
from googleapiclient import discovery
import ssl
import json
from TA_GoogleSCC_consts import constants
import TA_GoogleSCC_apiclient as gsu
from TA_GoogleSCC_utils import get_proxy_settings, get_vm_details  # noqa F401
import traceback
import httplib2
import splunk.admin as admin


class GetSessionKey(admin.MConfigHandler):
    """Session key."""

    def __init__(self):
        """Initialize Session Key."""
        self.session_key = self.getSessionKey()


class AccountValidator(Validator):
    """This class validates google scc account."""

    def validate(self, value, data, acc_name=None, session_key=None, ui=True):
        """Validate google scc account service account."""
        logger = setup_logging('ta_google_scc_account_validation', account_name=acc_name)
        service_account_json = data['service_account_json']
        credential_configuration_file = data['credential_configuration_file']
        if not session_key:
            session_key = GetSessionKey().session_key
        proxy = get_proxy_settings(logger, session_key)
        try:
            is_gcp, is_aws, is_azure = get_vm_details(logger, session_key)
            if is_gcp:
                credentials, project_id = google.auth.default()
            elif is_aws:
                credential_configuration_file = json.loads(credential_configuration_file)
                credentials = aws.Credentials.from_info(
                    info=credential_configuration_file, scopes=constants.SCOPES)
            elif is_azure:
                credential_configuration_file = json.loads(credential_configuration_file)
                credentials = identity_pool.Credentials.from_info(
                    info=credential_configuration_file, scopes=constants.SCOPES)
            else:
                if ui:
                    service_account_json = json.loads(service_account_json)
                credentials = service_account.Credentials.from_service_account_info(
                    info=service_account_json, scopes=constants.SCOPES
                )
            http_client = AuthorizedHttp(credentials=credentials, http=proxy)
            service = discovery.build(
                constants.SERVICE_NAME,
                constants.SERVICE_VERSION,
                http=http_client,
                cache_discovery=False
                )
            request = (service.organizations().sources().findings().list(
                parent="organizations/{0}/sources/-".format(data['organization_id']),
                pageSize=1,
                filter='state="ACTIVE"'
                )
            )
            resp = gsu.GoogleClient.execute_request(request, logger)
            if not resp:
                if ui:
                    self.put_msg("Verify Service Account JSON/Configuration, Organization Id or Proxy settings.")
                logger.error("message=invalid_credentials |"
                             " Verify Service Account JSON/Configuration, Organization Id or Proxy settings.")
                return False
            return True
        except ssl.SSLError:
            if ui:
                self.put_msg("Verify SSL certificate.")
            logger.error("message=ssl_error |"
                         " Error occurred while validating service account.\n{0}".format(traceback.format_exc()))
            return False
        except httplib2.socks.HTTPError:
            if ui:
                self.put_msg("Invalid Proxy credentials. Please recheck Proxy settings.")
            logger.error("message=http_error |"
                         " Error occurred while validating service account.\n{0}".format(traceback.format_exc()))
            return False
        except Exception:
            if ui:
                self.put_msg("Verify Service Account JSON/Configuration, Organization Id or Proxy settings.")
            logger.error("message=credentials_validation_error |"
                         " Error occured while validating service account.\n{0}".format(traceback.format_exc()))
            return False
