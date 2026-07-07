from __future__ import absolute_import
from builtins import object
import os

from splunk.clilib import cli_common as cli

from fsct_exception import Error
import fsct_defaults

class TAForescoutConfigFetcher(object):

	def get_fsct_config(self):
		app_bin_dir     = os.path.dirname(os.path.realpath(__file__))
		app_root_dir    = os.path.dirname(app_bin_dir)
		splunk_apps_dir = os.path.dirname(app_root_dir)
		ta_root_dir     = os.path.join(splunk_apps_dir, fsct_defaults.FS_TA_APP_NAME)
		if os.path.exists(ta_root_dir):
			os.chdir(ta_root_dir)
			# read configuration stanza from setup conf file, if TA-forescout installation directory is found.
			configuration_dict = cli.getConfStanza(fsct_defaults.FS_TA_SETUP_CONF_FILE, fsct_defaults.FS_TA_SETUP_CONF_STANZA)
			return configuration_dict
		else:
			raise Error('Could not find the installation directory for app: [' + fsct_defaults.FS_TA_APP_NAME + ']')

	def get_fsct_index(self):
		config_dict = self.get_fsct_config()
		fsct_index  = config_dict.get(fsct_defaults.FS_TA_INDEX_KEY, '')
		if fsct_index in [None, '']:
			# index is a required field on TA-forescout setup page. If its value is null or empty, raise an exception.
			raise Error('Invalid index value:[' + fsct_index + ']')
		else:
			return fsct_index