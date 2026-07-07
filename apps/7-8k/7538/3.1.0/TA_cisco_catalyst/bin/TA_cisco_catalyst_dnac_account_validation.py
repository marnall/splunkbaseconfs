"""Cisco Catalyst Center Account Validation Class."""
import import_declare_test  # noqa: F401
import os

from splunktaucclib.rest_handler.endpoint.validator import Validator
import utils
import consts
import logger_manager
import cisco_dnac_api as api
import splunk.admin as admin
from requests.exceptions import SSLError

logger = logger_manager.get_logger("catalyst_center_account_validation")


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


class ValidateCatalystCenterHost(Validator):
    """Class to Validate Host."""

    def __init__(self, *args, **kwargs):
        """:param validator: user-defined validating function."""
        super(ValidateCatalystCenterHost, self).__init__()
        self.my_app = __file__.split(os.sep)[-3]

    def delete_ca_cert(self, data):
        """Delete CA Cert."""
        account_name = data.get("copy_account_name").strip()
        if utils.is_true(data.get("use_ca_cert", False)):
            cert_file_loc = consts.CATALYSTC_CERT_FILE_LOC.format(cert_name=account_name)
            if os.path.exists(cert_file_loc):
                os.remove(cert_file_loc)
                logger.info(
                    "account_name={} | message=CA_cert_deleted_successfully | CA cert deleted successfully "
                    "for the Account: {}".format(account_name, account_name)
                )

    def validate(self, value, data):
        """Validate the Host.

        :param value: value to validate.
        :param data: whole payload in request.
        :return True or False
        """
        host_url = data.get("cisco_dna_center_host").strip(" ").strip("/")
        data["cisco_dna_center_host"] = host_url
        username = data.get("username")
        password = data.get("password")
        use_ca_cert = data.get("use_ca_cert")
        account_name = data.get("copy_account_name").strip()
        custom_certificate = data.get("custom_certificate").strip()

        if utils.is_true(use_ca_cert) and custom_certificate:
            cert_file_loc = consts.CATALYSTC_CERT_FILE_LOC.format(cert_name=account_name)
            data.pop("custom_certificate")
            try:
                _ = utils.save_cert_file(custom_certificate, cert_file_loc, logger)
            except OSError as e:
                err_msg = "Error while writing custom certificate to file: {}"
                self.put_msg(err_msg.format(e))
                logger.error(err_msg.format(e))
                return False
            except Exception as e:
                err_msg = "Error while saving custom certificate: {}"
                self.put_msg(err_msg.format(e))
                logger.error(err_msg.format(e))
                return False

        current_verify = True
        session_key = GetSessionKey().session_key
        if use_ca_cert is None:
            current_verify = utils.get_sslconfig(session_key, logger)
        elif utils.is_true(use_ca_cert):
            current_verify = consts.CATALYSTC_CERT_FILE_LOC.format(
                cert_name=account_name
            )
            logger.debug(
                "SSL Verification is set to True and will use the cert from this path. {}.".format(current_verify)
            )
        else:
            current_verify = utils.get_verify_ssl(session_key, logger)
        current_version = "2.2.3.3"

        try:
            catalystc = api.CatalystCenterAPI(  # noqa: F841
                username=username,
                password=password,
                base_url=host_url,
                version=current_version,
                verify=current_verify,
                debug=False,
                helper=logger,
            )
        except SSLError:
            self.delete_ca_cert(data)
            err_msg = "SSL error: Please check the provided custom certificate or the SSL configuration."
            self.put_msg(err_msg)
            logger.exception("Error occurred while validating the account.")
            return False
        except Exception:
            self.delete_ca_cert(data)
            err_msg = "Error occurred while validating the account. "\
                "Please verify the credentials or check for the log file for more details."
            self.put_msg(err_msg)
            logger.exception("Error occurred while validating the account.")
            return False
        logger.info("Catalyst Center Account created successfully.")
        return True
