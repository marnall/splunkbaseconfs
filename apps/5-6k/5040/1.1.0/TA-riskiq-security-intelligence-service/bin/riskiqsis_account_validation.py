"""Validation for account and proxy."""

from splunktaucclib.rest_handler.endpoint.validator import Validator
from botocore.exceptions import ClientError, ProxyConnectionError

import riskiqsis_utils
from riskiqsis_utils import DATA_TYPE_MAPPING, FRONTEND_DATATYPE_MAPPING, make_client


class AccessKeyValidator(Validator):
    """This class extends base class of Validator."""

    def validate(self, value, data):
        """We define Custom validation here for verifying credentials when storing account information."""
        try:
            ACCESS_KEY = data.get('accesskey')
            SECRET_KEY = data.get('secretkey')

            proxies = riskiqsis_utils.create_requests_proxy_dict()
            s3_client = make_client('s3', ACCESS_KEY, SECRET_KEY, proxies)
            sts_client = make_client('sts', ACCESS_KEY, SECRET_KEY, proxies)

            selected_datatypes = data.get('data_types')
            datatypes_list = selected_datatypes.split('~')
            try:
                sts_client.get_caller_identity()
            except ClientError as e:
                self.put_msg('Failed to validate account due to {}'.format(e.response.get('Error').get('Code')))
                return False
            except ProxyConnectionError:
                self.put_msg("Error occurred while adding Account. Please recheck Proxy settings.")
                return False

            all_buckets_are_accessible = True
            access_denied_buckets = []

            for datatype in datatypes_list:
                bucket_name = DATA_TYPE_MAPPING.get(datatype)
                try:
                    s3_client.head_bucket(Bucket=bucket_name)
                except ClientError:
                    all_buckets_are_accessible = False
                    access_denied_buckets.append(FRONTEND_DATATYPE_MAPPING.get(datatype))

            if all_buckets_are_accessible:
                return True
            else:
                access_denied_buckets_str = ', '.join(str(e) for e in access_denied_buckets)
                self.put_msg("You don't have access to : {}. Please remove them and try again."
                             .format(access_denied_buckets_str))
                return False
        except Exception:
            self.put_msg("Error Occurred while configuring Account. Please Try Again.")
            return False
