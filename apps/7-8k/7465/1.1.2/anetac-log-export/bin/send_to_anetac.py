import import_declare_test


import json
import os
from datetime import datetime, timezone
import boto3
import gzip
import shutil

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase

class AlertActionWorkersend_to_anetac(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkersend_to_anetac, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("bucket_name"):
            self.log_error('bucket_name is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("aws_key_id"):
            self.log_error('aws_key_id is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("aws_secret_key"):
            self.log_error('aws_secret_key is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("aws_region"):
            self.log_error('aws_region is a mandatory setup parameter, but its value is None.')
            return False
        return True

    def process_event(helper, *args, **kwargs):
        """
        # IMPORTANT
        # Do not remove the anchor macro:start and macro:end lines.
        # These lines are used to generate sample code. If they are
        # removed, the sample code will not be updated when configurations
        # are updated.
    
        [sample_code_macro:start]
    
        # The following example gets the setup parameters and prints them to the log
        bucket_name = helper.get_global_setting("bucket_name")
        helper.log_info("bucket_name={}".format(bucket_name))
        aws_key_id = helper.get_global_setting("aws_key_id")
        helper.log_info("aws_key_id={}".format(aws_key_id))
        aws_secret_key = helper.get_global_setting("aws_secret_key")
        helper.log_info("aws_secret_key={}".format(aws_secret_key))
        aws_region = helper.get_global_setting("aws_region")
        helper.log_info("aws_region={}".format(aws_region))
    
        # The following example adds two sample events ("hello", "world")
        # and writes them to Splunk
        # NOTE: Call helper.writeevents() only once after all events
        # have been added
        helper.addevent("hello", sourcetype="sample_sourcetype")
        helper.addevent("world", sourcetype="sample_sourcetype")
        helper.writeevents(index="summary", host="localhost", source="localhost")
    
        # The following example gets the events that trigger the alert
        events = helper.get_events()
        for event in events:
            helper.log_info("event={}".format(event))
    
        # helper.settings is a dict that includes environment configuration
        # Example usage: helper.settings["server_uri"]
        helper.log_info("server_uri={}".format(helper.settings["server_uri"]))
        [sample_code_macro:end]
        """
    
        helper.log_info("Alert action send_to_anetac started.")
    
        bucket_name = helper.get_global_setting("bucket_name")
        aws_key_id = helper.get_global_setting("aws_key_id")
        aws_secret_key = helper.get_global_setting("aws_secret_key")
        aws_region = helper.get_global_setting("aws_region")
    
        timenow = datetime.now()
        folder_sfx = timenow.strftime("%Y-%m-%d")
        file_name = timenow.strftime("%H-%M-%S")
        object_key = f"datadrop/{folder_sfx}/splunk_alert_{file_name}.csv.gz"
    
        helper.log_info(f"Results file is {helper.results_file}")
    
        s3 = boto3.client('s3',
                              aws_access_key_id=aws_key_id,
                              aws_secret_access_key=aws_secret_key,
                              region_name=aws_region)
    
        helper.log_info(f"Created S3 client with region {aws_region}")
        s3.upload_file(helper.results_file, bucket_name, object_key)
        helper.log_info(f"Alert action anetac_export completed. File uploaded to {bucket_name}/{object_key}")
        return 0
if __name__ == "__main__":
    exitcode = AlertActionWorkersend_to_anetac("anetac-log-export", "send_to_anetac").run(sys.argv)
    sys.exit(exitcode)
