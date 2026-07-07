# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
# this is just a handover point for splunk. From here we will go into the respective module to do
# the rest of the actions
# this approach will bring modularity in the code
import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'phantom', 'bin']))
from ITOA.setup_logging import getLogger
from integrations.phantom.splunk_connector import SendToPhantomAction


if __name__ == "__main__":
    logger = getLogger(logger_name="itsi.event_action.send_to_phantom")
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        # the following try catch is put because splunk seems to swallow the errors that we throw
        # i want the error to be logged in our integration's log, this is a workaround for splunk's problem
        try:
            input_params = sys.stdin.read()
            logger.info('Action --> SendToPhantomAction : Initialization Started')
            action = SendToPhantomAction(input_params)
            logger.info('Action --> SendToPhantomAction : Initialization Successful')
            logger.info('Action --> SendToPhantomAction : Execution Started')
            action.execute()
            logger.info('Action --> SendToPhantomAction : Execution Successful')
        except Exception as e:
            logger.error(e)
            raise e
