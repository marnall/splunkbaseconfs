# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from ITOA.setup_logging import getLogger
logger = getLogger(logger_name='itsi.custom_alert.itsi_generator')

from ITOA.event_management.base_event_generation import SendAlert
from itsi.event_management.utils import NotableEventValidator

EXECUTE_MODE_ARGS = '--execute'


class ItsiSendAlert(SendAlert):
    """
    Class which inherit SendAlert and implement abstract methods
    """

    def __init__(self, settings, is_validate=True):
        """
        Initialize

        @type settings: basestring
        @param settings: sys.stdin.read() contains

        @type is_validate: bool
        @param is_validate: flag to validate required params or not
        @return:
        """
        super(ItsiSendAlert, self).__init__(settings, is_validate)
        self.validator = NotableEventValidator(self.session_key, logger)

    def pre_processing(self, data):
        """
        Validate schema before we push events to index

        @type data: dict
        @param data: data which has been pushed or going to be pushed to index

        @return: return True or throw exception
        """
        return self.validator.validate_schema(data)

    def undo_pre_processing(self):
        """
        Undo pre-processing work, in this case no operation is required
        """
        pass


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == EXECUTE_MODE_ARGS:
        try:
            modular_alert = ItsiSendAlert(sys.stdin.read())
            modular_alert.run()
        except Exception as e:
            logger.exception(e)
            sys.exit(-1)
    else:
        sys.stderr.write(
            'Invalid system argument={0}, Script only support {1} mode'.format(sys.argv, EXECUTE_MODE_ARGS))
        sys.exit(3)
