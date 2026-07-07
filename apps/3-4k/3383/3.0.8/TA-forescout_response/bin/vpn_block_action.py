from __future__ import absolute_import
from __future__ import print_function
import logging
import sys

from fsbase_actions import CounterACTBaseAction

try:
	from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
	from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

## Setup the logger
logger = CounterACTBaseAction.setup_logger('vpn_block_action_modalert')

## ModularAction wrapper
class CounterACTAdaptiveResponseTestAction(CounterACTBaseAction):

	def __init__(self, settings, logger, action_name=None):
		super(CounterACTAdaptiveResponseTestAction, self).__init__(settings, logger, action_name)

# If the script is being called directly from the command-line, then this is likely being executed by Splunk.
if __name__ == "__main__":

	if len(sys.argv) > 1 and sys.argv[1] != "--execute":
		print('FATAL Unsupported execution mode (expected --execute flag)', file=sys.stderr)
		sys.exit(1)

	modaction = CounterACTAdaptiveResponseTestAction(sys.stdin.read(), logger, 'vpn_block_action')
	try:
		modaction.perform_mod_action()
	except Exception as e:
		try:
			modaction.message(e, 'failure', level = logging.CRITICAL)
		except:
			logger.critical(e)
		print('ERROR Unexpected error: %s' % e, file=sys.stderr)
		sys.exit(3)