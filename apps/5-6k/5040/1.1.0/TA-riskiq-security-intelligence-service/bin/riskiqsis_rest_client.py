import boto3
from botocore.config import Config
from riskiqsis_utils import create_requests_proxies_helper


class RiskiqsisRestClient(object):
    """Class for handling rest calls to RiskIQ SIS API."""

    def __init__(self, input_name, accesskey, secretkey, helper):
        """
        Initialize Instance with required parameters.

        :param input_name: Input Name
        :param accesskey: RiskIQ-AWS AccessKeyID
        :param secretkey: RiskIQ-AWS Secret Key
        """
        self.input_name = input_name
        self.accesskey = accesskey
        self.secretkey = secretkey
        self.helper = helper

        self.proxy_settings = self.helper.get_proxy()
        self.proxy_enabled = True if self.proxy_settings else False
        self.proxies = create_requests_proxies_helper(self.proxy_enabled, self.proxy_settings)

        self.client = boto3.client(
            "s3",
            aws_access_key_id=self.accesskey,
            aws_secret_access_key=self.secretkey,
            config=Config(proxies=self.proxies),
        )

    def get_bucket_objects(self, bucket, prefix):
        """
        Fetch list of all the bucket object present in given bucket.

        :param bucket: Name of bucket
        :param prefix: Prefix of object(s) to be retrived as list
        """
        try:
            response = self.client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            bucket_objects = response.get("Contents", [])
            return bucket_objects
        except Exception as e:
            self.helper.log_error(
                "Error occured while fetching object list. bucket: {}, input: {}. Error: {}".format(
                    bucket, self.input_name, str(e)
                )
            )
            raise

    def download_bucket_object(self, bucket, key, path_to_store):
        """
        Download bucket object.

        :param bucket: Name of bucket
        :param key: Bucket object to be downloaded
        :param path_to_store: Storage path
        """
        with open(path_to_store, "wb") as data:
            self.client.download_fileobj(bucket, key, data)
