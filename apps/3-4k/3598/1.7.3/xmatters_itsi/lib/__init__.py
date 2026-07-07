"""
    Some common module library includes
"""
import sys

# pylint: disable = import-error
# pylint: disable = wrong-import-position
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))

# pylint: disable = no-name-in-module
from lib.ITOA.itoa_common import add_to_sys_path
from ITOA.setup_logging import setup_logging
# pylint: enable = no-name-in-module
# pylint: enable = wrong-import-position
# pylint: enable = import-error

# Add lib path to import paths for packages
add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'xmatters_itsi', 'lib'])])
