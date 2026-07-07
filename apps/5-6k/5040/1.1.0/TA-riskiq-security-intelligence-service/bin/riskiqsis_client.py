import os
import shutil
import datetime
import traceback
from splunk.clilib.bundle_paths import make_splunkhome_path
from riskiqsis_utils import APP_NAME, DATA_TYPE_MAPPING, DATA_TYPE_PREFIX
from riskiqsis_rest_client import RiskiqsisRestClient

NEW_OBSERVATION = ["newly_observed_domain", "newly_observed_host"]
MAX_DAYS = 7


class RiskiqsisClient(object):
    """Class for handling data collection for RiskIQ Security Intelligence Service."""

    def __init__(self, helper):
        """
        Initialize NetskopeWtClient object with input params.

        :param helper: object of BaseModInput class
        """
        self.helper = helper
        self.account = self.helper.get_arg("global_account")
        self.accesskey = self.account.get("accesskey")
        self.secretkey = self.account.get("secretkey")

        self.data_type = self.helper.get_arg("data_type")
        self.collect_data_from = self.helper.get_arg("collect_data_for")
        self.input_name = helper.get_arg("name")
        self.bucket = DATA_TYPE_MAPPING.get(self.data_type)

        self.storage_path = make_splunkhome_path(["var", "spool", "splunk"])
        self.temp_storage_path = make_splunkhome_path(["etc", "apps", APP_NAME, "local", "downloads"])

        self.checkpoint_key = "{}_{}".format(self.account.get("name"), self.input_name)
        self.dt_1970 = datetime.datetime(1970, 1, 1)
        self.total_collected = 0

        self.rest_client = RiskiqsisRestClient(self.input_name, self.accesskey, self.secretkey, self.helper)

        if not os.path.exists(self.temp_storage_path):
            os.makedirs(self.temp_storage_path)

    def collect_data(self):
        """
        Collect data for RiskIQ Security Intelligence Service.

        Step1: Fetches list of objects present in bucket based on data type
        Step2: Downloads and stores the bucket object in $SPLUNK_HOME/var/spool/splunk folder which are
        updated since last data collection by checking its LastModified time and its size
        Step3: Saves time in checkpoint
        """
        if self.data_type not in DATA_TYPE_PREFIX.keys():
            self.helper.log_error(
                "Invalid Data Type: {} is provided. input: {}".format(self.data_type, self.input_name)
            )
            return

        prefix = DATA_TYPE_PREFIX.get(self.data_type)
        new_chkpnt = checkpoint_time = self.get_checkpoint_time()

        if self.checkpoint_val.get("error_list"):
            self.handle_error_case()

        bucket_objects = self.rest_client.get_bucket_objects(bucket=self.bucket, prefix=prefix)

        if not bucket_objects:
            self.helper.log_info("No file objects found in bucket: {}. input: {} ".format(self.bucket, self.input_name))
            return

        for bucket_object in bucket_objects:
            key = bucket_object.get("Key")
            last_modified_time = bucket_object.get("LastModified")
            try:
                if not self.dt_1970.tzinfo:
                    self.dt_1970 = self.dt_1970.replace(tzinfo=last_modified_time.tzinfo)

                last_modified_time_epoch = int((last_modified_time - self.dt_1970).total_seconds())

                if last_modified_time_epoch > checkpoint_time:
                    new_chkpnt = max(last_modified_time_epoch, new_chkpnt)
                    self.download_and_store(bucket_object)

            except Exception as e:
                self.helper.log_error(
                    "Error occured while processing object: {}, bucket={}, Error: {}".format(key, self.bucket, str(e))
                )
                if self.checkpoint_val.get("error_list"):
                    if key not in self.checkpoint_val.get("error_list"):
                        self.checkpoint_val["error_list"].append(key)
                else:
                    self.checkpoint_val["error_list"] = [key]
                self.helper.log_error(traceback.format_exc())
            finally:
                self.checkpoint_val["checkpoint_time"] = new_chkpnt

        self.helper.save_check_point(self.checkpoint_key, self.checkpoint_val)
        self.helper.log_info("Total file objects collected: {} input: {}".format(self.total_collected, self.input_name))

    def get_checkpoint_time(self):
        """Get time to collect data from."""
        self.checkpoint_val = self.helper.get_check_point(self.checkpoint_key) or {}
        checkpoint_time = self.checkpoint_val.get("checkpoint_time")

        if checkpoint_time:
            checkpoint_time = int(checkpoint_time)
        else:
            #  This is for first time data collection. when checkpoint is not present.
            if not self.is_valid_collect_data_for():
                raise Exception(
                    "Invalid value provided to collect_data_for: {}. must be an integer >=0 and <=7. input: {}".format(
                        self.collect_data_from, self.input_name
                    )
                )
            checkpoint_time = (datetime.datetime.utcnow() - self.dt_1970).total_seconds() - (
                86400 * int(self.collect_data_from)
            )
        return checkpoint_time

    def is_valid_collect_data_for(self):
        """Check collect_data_for value."""
        try:
            val = int(self.collect_data_from)
            if val in range(MAX_DAYS + 1):
                return True
            return False
        except ValueError:
            return False

    def download_and_store(self, bucket_object):
        """Download file object and store in checkpoint."""
        try:
            key = bucket_object.get("Key")
            size = bucket_object.get("Size")

            day = key.split("/")[1]

            if self.data_type not in NEW_OBSERVATION:
                hour = day.split("=")[1]
                day = "day={}".format(hour[:-2])

            day_checkpoint_key = "{}_{}_{}".format(self.account.get("name"), self.input_name, day)
            day_checkpoint_list = self.helper.get_check_point(day_checkpoint_key) or {}

            if size != int(day_checkpoint_list.get(key, -1)):
                self.download_object(key)
                day_checkpoint_list[key] = size
                self.helper.save_check_point(day_checkpoint_key, day_checkpoint_list)
                self.total_collected += 1
            else:
                self.helper.log_debug("object:{} with size: {} already downloaded previously".format(key, size))
        except IndexError:
            self.helper.log_error(
                "File object key(path down to file level) is not in valid format: {}, bucket: {}, input: {}".format(
                    key, self.bucket, self.input_name
                )
            )
        except Exception as e:
            self.helper.log_error("Error occured in download and store: {}, input: {}".format(str(e), self.input_name))
            raise

    def download_object(self, key):
        """
        Download and store bucket object in $SPLUNK_HOME/var/spool/splunk.

        :param key: Bucket object to be downloaded
        """
        self.helper.log_debug("Downloading object: {}, bucket: {}, input: {}".format(key, self.bucket, self.input_name))
        modified_key = key.replace("/", "_")
        object_name = "{}_{}".format(self.input_name, modified_key)
        temp_storage_path = os.path.join(self.temp_storage_path, object_name)
        try:
            self.rest_client.download_bucket_object(bucket=self.bucket, key=key, path_to_store=temp_storage_path)
            self.move_to_spool(temp_storage_path, object_name)
            self.helper.log_info(
                "Downloaded object: {}, bucket: {}, input: {}".format(key, self.bucket, self.input_name)
            )
        except Exception as e:
            self.helper.log_error(
                "Error occured while downloading object: {}, bucket: {}, input: {}. Error: {}".format(
                    key, self.bucket, self.input_name, str(e)
                )
            )
            raise

    def move_to_spool(self, temp_storage_path, object_name):
        """
        Move file from TA-riskiq-security-intelligence-service/local/downloads to var/spool/splunk.

        :param temp_storage_path: Path to TA-riskiq-security-intelligence-service/local/downloads/<object_name>
        :param object_name: Object name
        """
        try:
            spool_path = os.path.join(self.storage_path, object_name)
            self.helper.log_debug("Moving object to {} from {}".format(temp_storage_path, spool_path))
            shutil.move(temp_storage_path, spool_path)
        except Exception as e:
            self.helper.log_error(
                "Error occured while moving object to spool. object: {}, bucket:{}, input: {}. Error: {}".format(
                    object_name, self.bucket, self.input_name, str(e)
                )
            )
            raise

    def handle_error_case(self):
        """Handle error case. Collect objects for which error occured in previous execution."""
        self.helper.log_info(
            "Trying to collect objects for which error has been occured in previous execution. input: {}".format(
                self.input_name
            )
        )
        not_collected_objects = []
        for object_key in self.checkpoint_val.get("error_list"):
            try:
                bucket_object = self.rest_client.get_bucket_objects(bucket=self.bucket, prefix=object_key)
                if bucket_object:
                    self.download_and_store(bucket_object[0])
                else:
                    self.helper.log_info(
                        "Object: {} not found in bucket. input: {}".format(object_key, self.input_name)
                    )
            except Exception as e:
                self.helper.log_error(
                    "Error occured again while downloading object: {}. Error: {}".format(object_key, str(e))
                )
                not_collected_objects.append(object_key)

        self.checkpoint_val["error_list"] = not_collected_objects
        self.helper.log_info(
            "Collected objects for which error has been occured in previous execution. input: {}".format(
                self.input_name
            )
        )
