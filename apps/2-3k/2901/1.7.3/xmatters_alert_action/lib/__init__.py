"""
    Some common module library includes
"""
# pylint: disable = import-error
from splunk.clilib.bundle_paths import make_splunkhome_path

# pylint: disable = no-name-in-module
from lib.ITOA.itoa_common import add_to_sys_path
# pylint: enable = no-name-in-module
# pylint: enable = import-error

# Add lib path to import paths for packages
add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'xmatters_alert_action', 'lib'])])
