"""Validation for the Inputs Page."""

from splunk import admin
from splunktaucclib.rest_handler.endpoint import validator
import riskiqsis_utils
from riskiqsis_utils import read_conf_file, RISKIQSIS_ACCOUNT_CONF, make_client, DATA_TYPE_MAPPING, get_entities,\
    get_password
from botocore.exceptions import ClientError


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


class InputValidator(validator.Validator):
    """This class extends base class of Validator. Class to validate the interval field."""

    def validate(self, value, data):
        """We define Custom validation here for verifying credentials when storing account information."""
        try:
            data_type = data.get('data_type')
            acc_name = data.get('global_account')
            access_key = read_conf_file(GetSessionKey().session_key, RISKIQSIS_ACCOUNT_CONF, acc_name).get('accesskey')
            entities = get_entities()
            secret_key = get_password(entities, name=acc_name, type="account")
            proxies = riskiqsis_utils.create_requests_proxy_dict()
            s3_client = make_client('s3', access_key, secret_key, proxies)
            bucket_name = DATA_TYPE_MAPPING.get(data_type)
            try:
                s3_client.head_bucket(Bucket=bucket_name)
            except ClientError:
                self.put_msg("You don't have access to this Data Type. Select the Appropriate Account\
                             & Data Type and try again")
                return False
            return True
        except Exception:
            self.put_msg("Error Occurred while configuring Input. Please Try Again.")
            return False
