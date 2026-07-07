import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import dependency_handler  # noqa: F401  # Do not delete

from libs.base_objects.splunk_command_base import SplunkCommandBaseMixin
from libs.base_objects.table_structures import PackageStatus
from splunklib.searchcommands import dispatch, Configuration, EventingCommand


@Configuration()
class SaveResults(SplunkCommandBaseMixin, EventingCommand):
    def get_service(self):
        return self.service

    def get_logger_defaults(self):
        return {
            "app_name": "attackiq_flex_detections",
            "class_name": type(self).__name__,
            "type": "Script",
        }

    def transform(self, records):
        # For each record (package_status), write results to sourcetype and expire package_status
        for record in records:
            try:
                package_status = PackageStatus.from_dict(**record)
                self.finalize_package(package_status, increase_count=False)
            except Exception as e:
                self.aiq_logger.error(f"Error while running saveresults: {str(e)}")
            yield record


dispatch(SaveResults, sys.argv, sys.stdin, sys.stdout, __name__)
