# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

"""
This part add the app's bin directory to sys.path to make sure all modules inside of it are
accessible. It's pretty weird and we have to do this in (almost) every entry point file, like
modular inputs, rest handler, etc.
"""
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'it_essentials_learn', 'bin']))  # noqa
"""
This line will make all internal and external libraries available for imports.
"""
import ite_path_inject  # noqa

from modinput_wrapper.base_modularinput import BaseModularInput
from rest_handler.session import session
from logging_utils.log import getLogger

from ite_data_loader import (
    IteProcedureInitializer,
    IteUseCaseInitializer,
    IteUseCaseFamilyInitializer,
    IteMaturityStageInitializer
)
import ite_constants
from ite_utils import KVStoreNotReadyException, wait_until_kvstore_is_ready


logger = getLogger()


class ContentInitializer(BaseModularInput):
    """
    ContentInitializer is the modular input that runs when system starts and
    load ITE objects from their content source file into their corresponding storage locations
    """

    app = ite_constants.APP_NAME
    name = 'content_initializer'
    title = 'IT Essentials Learn - Content Initializer'
    description = 'Initializes contents in IT Essentials Learn'
    use_external_validation = False
    use_single_instance = True
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def do_additional_setup(self):
        self.wait_until_kvstore_is_ready()
        log_level = self.inputs.get('job').get('log_level', 'INFO')
        logger.setLevel(log_level)

    def do_execute(self):
        if not self.should_run():
            return

        initializer_cls_list = [
            IteProcedureInitializer,
            IteUseCaseInitializer,
            IteUseCaseFamilyInitializer,
            IteMaturityStageInitializer
        ]
        for ini_cls in initializer_cls_list:
            ini = ini_cls()
            ini.run()

    def wait_until_kvstore_is_ready(self):
        try:
            wait_until_kvstore_is_ready(session_key=session['authtoken'])
        except KVStoreNotReadyException as e:
            logger.error('Content initializer failed to run - %s' % e)
            sys.exit(1)


if __name__ == '__main__':
    inp = ContentInitializer()
    inp.execute()
