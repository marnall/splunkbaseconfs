# encoding = utf-8
# Always put this line at the beginning of this file
import import_declare_test

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
from ta_amazon_s3_uploader import modalert_amazon_s3_upload_helper

class AlertActionWorkeramazon_s3_upload(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkeramazon_s3_upload, self).__init__(ta_name, alert_name)

    def validate_params(self):


        if not self.get_param("bucket_name"):
            self.log_error('bucket_name is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("object_key"):
            self.log_error('object_key is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("account"):
            self.log_error('account is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_amazon_s3_upload_helper.process_event(self, *args, **kwargs)
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(str(e)))
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status

if __name__ == "__main__":
    exitcode = AlertActionWorkeramazon_s3_upload("TA_amazon_s3_uploader", "amazon_s3_upload").run(sys.argv)
    sys.exit(exitcode)
