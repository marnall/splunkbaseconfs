"""This file checks Version Compatibility."""
import csv
import os
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib.decorators import expose_page


class test_version_compatibility(controllers.BaseController):
    """Test Vesrion Compatibility Class."""

    @expose_page(must_login=True, methods=['GET', 'POST'])
    def check_compatiblity(self, **kwargs):
        """Check Compatibility."""
        SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
        path_to_lookups_dir = SPLUNK_HOME + '/etc/apps/netapp_app_eseries_perf/lookups'
        os.chdir(path_to_lookups_dir)
        compatible_versions = open('nesa_compatibility_matrix.csv')
        compatible_app_versions = csv.reader(compatible_versions)
        compatible_app_versions.next()
        current_TA = kwargs.get("TAVersion", None)
        current_proxy = kwargs.get("ProxyVersion", None)
        for compatible_app_version in compatible_app_versions:
            if compatible_app_version[0].strip() == current_TA:
                compatible_proxy = compatible_app_version[2]
                compatible_proxy = compatible_proxy.split("|")
                compatible_proxy = [x.strip() for x in compatible_proxy]
                if current_proxy not in compatible_proxy:
                    message = "Current version of TA is not compatible with web proxy. " \
                              "Please check Compatibility Matrix on this page"
                else:
                    message = "Current version of TA is compatible with web proxy."
        return message
