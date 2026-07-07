import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ipinfo_bootstrap  # noqa: F401  -- pin vendored splunklib before any other import to defeat Splunk Enterprise Security sys.path collisions

import splunk.Intersplunk as si
from ipinfo_utils import get_config


# Custom command made by splunk v1 method use to get method from ip_info_setup.conf
def custom_command():
    try:
        method = get_config("method")
        results = [{"Method": method}]
        si.outputResults(results)
    except Exception as e:
        si.generateErrorResults("Error: {}".format(str(e)))


if __name__ == "__main__":
    custom_command()
