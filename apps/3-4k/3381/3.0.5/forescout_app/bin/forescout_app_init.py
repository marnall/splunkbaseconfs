from __future__ import absolute_import
from __future__ import print_function
from builtins import str
import sys
#import logging
import logging.handlers

from fsct_ta_config_reader import TAForescoutConfigFetcher
from fsct_rest_api_wrapper import FSSplunkRestApiWrapper
from fsct_exception import Error
import fsct_defaults

try:
	from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
	from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# define a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
setup_log_filename = make_splunkhome_path(['var', 'log', 'splunk', fsct_defaults.FS_APP_NAME + '_init.log'])
handler = logging.handlers.RotatingFileHandler(setup_log_filename, maxBytes=25000000, backupCount=5)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

if __name__ == "__main__":

	if len(sys.argv) > 1 and sys.argv[1] != "--execute":
		print('FATAL Unsupported execution mode (expected --execute flag)', file=sys.stderr)
		logger.critical('FATAL Unsupported execution mode (expected --execute flag). Exiting')
		sys.exit(1)

	logger.debug('Initializing app: [' + fsct_defaults.FS_APP_NAME + ']...')
	rest_api_handle = FSSplunkRestApiWrapper(logger)
	try:
		# read index value from TA-forescout app
		fsct_index = TAForescoutConfigFetcher().get_fsct_index()
		logger.info('Read index value: [' + fsct_index + '] from ' + fsct_defaults.FS_TA_APP_NAME)

		# Update the 'get_index' macro with the new index value
		rest_api_handle.updateIndexMacrosConf(fsct_index)
	except Error as err:
		logger.critical('Error while reading setup config from [' + fsct_defaults.FS_TA_APP_NAME + ']: ' + err.message)
		rest_api_handle.updateMessages('POST', fsct_defaults.FS_APP_NAME + '_init', 'App: [' + fsct_defaults.FS_APP_LABEL + '] could not read index from : [' + fsct_defaults.FS_TA_APP_LABEL + ']', 'error')
		sys.exit(1)
	except Exception as err:
		logger.critical('Unexpected error: ' + str(err.message))
		rest_api_handle.updateMessages('POST', fsct_defaults.FS_APP_NAME + '_init', 'App: [' + fsct_defaults.FS_APP_LABEL + '] could not read index from : [' + fsct_defaults.FS_TA_APP_LABEL + ']', 'error')
		sys.exit(1)
	else:
		try:
			rest_api_handle.updateMessages('POST', fsct_defaults.FS_APP_NAME + '_init', 'App: [' + fsct_defaults.FS_APP_LABEL + '] is working with index: [' + fsct_index + ']', 'info')
		except Error as err:
			logger.error('Error while posting message to bulletin: ' + str(err.message))
		except Exception as err:
			logger.error('Unexpected error while posting message to bulletin: ' + str(err.message))