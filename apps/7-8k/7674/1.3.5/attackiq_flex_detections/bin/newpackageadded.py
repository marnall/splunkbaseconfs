import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import dependency_handler  # noqa: F401  # Do not delete

from libs.base_objects.splunk_command_base import SplunkCommandBaseMixin
from libs.base_objects.table_structures import PackageRun
from splunklib.searchcommands import dispatch, Configuration, EventingCommand


@Configuration()
class NewPackageAdded(SplunkCommandBaseMixin, EventingCommand):
    def get_service(self):
        return self.service

    def get_logger_defaults(self):
        return {
            "app_name": "attackiq_flex_detections",
            "class_name": type(self).__name__,
            "type": "Script",
        }

    def transform(self, records):
        # For each record (package_runs), run the correlation
        for record in records:
            try:
                package_run = PackageRun.from_dict(**record)
                self.add_new_package(package_run, record["_time"])
            except Exception as e:
                self.aiq_logger.error(f"Error while running newpackageadded: {str(e)}")
            yield record


dispatch(NewPackageAdded, sys.argv, sys.stdin, sys.stdout, __name__)
