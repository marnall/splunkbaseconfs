# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
from ITOA.itoa_common import modular_input_should_run
from ITOA.setup_logging import getLogger4ModInput
from custom_threshold_windows.overlapping_custom_threshold_detector import OverlappingCustomThresholdDetector
from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from itsi.itsi_utils import ITOAInterfaceUtils
from itsi.upgrade.constants import NEW_VERSION


class CustomThresholdWindowOverlapDetectorModularInput(ModularInput):
    """
    Mod input dedicated to populate Overlapping KPIs for Custom threshold Window and update associated fields
    """

    title = "IT Service Intelligence Custom Threshold Windows Overlap Detector Modular Input"
    description = "Minder to populate overlapping KPIs for Custom Threshold Window"
    handlers = None
    app = 'SA-ITOA'
    name = 'custom_threshold_window_overlaps_detector'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    owner = 'nobody'

    def extra_arguments(self):
        return [{
                'name': "log_level",
                'title': "Logging Level",
                'description': "Level at which log data."}]

    def do_run(self, input_config):
        """
        - This is the method called by splunkd when mod input is enabled.

        @type: object
        @param input_config: config passed down by splunkd
        """
        logger = getLogger4ModInput(input_config)
        logger.debug('CustomThresholdWindowOverlapDetectorModularInput Invoked')

        if modular_input_should_run(self.session_key, logger):
            OverlappingCustomThresholdDetector(self.session_key).populate_overlapping_ctw_data()


if __name__ == "__main__":
    worker = CustomThresholdWindowOverlapDetectorModularInput()
    worker.execute()
