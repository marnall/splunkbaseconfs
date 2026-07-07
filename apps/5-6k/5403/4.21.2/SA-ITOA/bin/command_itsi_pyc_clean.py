# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
ITSIPyc cleaner that runs when Modular input runs. It does the following:
1. check if user have required permissions.
2. clean pyc if requirement is satisfied.
"""

import sys
import time
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "lib"]))
sys.path.append(
    make_splunkhome_path(["etc", "apps", "SA-ITOA", "lib", "SA_ITOA_app_common"])
)
from itsi.upgrade.file_manager import FileManager
from ITOA.itoa_common import SplunkUser

from SA_ITOA_app_common.splunklib.searchcommands import Configuration, GeneratingCommand, dispatch
from ITOA.setup_logging import setup_logging
from ITOA.controller_utils import ITOAError


@Configuration()
class PycCleaner(GeneratingCommand):
    logger = setup_logging(
        "itsi_pyc_clean.log", "itsi.pyc.cleanup"
    )
    username = 'nobody'
    required_user_capability = ["itoa_admin", "power", "admin"]

    def pycCleanup(self):
        roles_for_current_user, all_roles_for_current_user = SplunkUser.get_roles_for_user(self.username, self.service.token, self.logger)
        self.logger.info(f'roles_for_current_user={roles_for_current_user}, all_roles_for_current_user={all_roles_for_current_user}')

        if not any(capability in self.required_user_capability for capability in roles_for_current_user):
            raise ITOAError(status=401, message="User doesn't have required permissions to perform this action")

        delete_directory = make_splunkhome_path(['etc', 'apps', 'SA-ITOA'])
        FileManager.search_and_delete_file(delete_directory, self.service.token)

    def generate(self):
        self.logger.info('Pyccleaner command is running...')
        self.pycCleanup()
        data_to_return = {
            '_raw': 'Successfully completed itsipyccleaner command',
            '_time': time.time()
        }
        self.logger.info(data_to_return)
        yield data_to_return


dispatch(PycCleaner, sys.argv, sys.stdin, sys.stdout, __name__)
