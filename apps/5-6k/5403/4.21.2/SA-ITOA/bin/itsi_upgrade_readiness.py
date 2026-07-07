# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Modular Input that performs scheduled sync from service templates to services
"""

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
from ITOA.itoa_common import modular_input_should_run
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from migration_utility.itsi_upgrade_readiness_log import ItsiUpgradeReadinessLog
from migration_utility.constants import MODES

from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from SA_ITOA_app_common.solnlib.conf_manager import ConfManager


class ItsiUpgradeReadiness(ModularInput):
    """
    Modular Input that performs scheduled execution of prechecks to validate ITSI Kvstore data
    """

    title = 'IT Service Intelligence Upgrade Readiness Prechecker'
    description = 'Performs scheduled precheck job to determine upgrade readiness.'
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_upgrade_readiness_precheck'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [{
                'name': "log_level",
                'title': "Logging Level",
                'description': "This is the level at which the modular input will log data."}]

    @skip_run_during_migration
    def do_run(self, input_config):
        """
        - This is the method called by splunkd when mod input is enabled.
        @param input_config: config passed down by splunkd
        """
        logger = getLogger4ModInput(input_config)
        cfm = ConfManager(self.session_key, 'SA-ITOA')
        conf = cfm.get_conf('itsi_settings')
        auto_remediate_settings = conf.get('auto_remediate_upgrade_readiness')
        is_auto_remediation_enabled = auto_remediate_settings.get('auto_remediate_upgrade_readiness_issues')
        logger.info(f"Auto-remediation enabled : {is_auto_remediation_enabled}")
        operation_mode = MODES["PRECHECK"]
        if str(is_auto_remediation_enabled) == "1":
            operation_mode = MODES["AUTO_REMEDIATION"]

        logger.info('Checking for pending upgrade readiness precheck job.')

        if modular_input_should_run(self.session_key, logger):
            itsi_upgrade_readiness_obj = ItsiUpgradeReadinessLog(self.session_key)
            itsi_upgrade_readiness_obj.upgrade_readiness_activity(operation_mode)
        else:
            logger.info("ItsiUpgradeReadiness modular input will not run on this node.")


if __name__ == "__main__":
    worker = ItsiUpgradeReadiness()
    worker.execute()
    sys.exit(0)
