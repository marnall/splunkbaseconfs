"""
(C) 2022 Splunk Inc. All rights reserved.

"""

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

from splunkar import constants
from splunkar import logging
from splunkar.util.modular_input_utils import SplunkARModularInput
from splunkar.telemetry.client import TelemetryClient
from splunkar.telemetry.metrics import EdgeHubMetricsCollector, OtiDatastreamerMetricsCollector

sys.path.remove(make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

LOGGER = logging.get_logger(__name__)


class SplunkEdgeARMetricsModularInput(SplunkARModularInput):
    """Modular input to complete registrations for Edge Hub devices."""

    title = 'Splunk Edge AR Hub Metrics Collector'
    description = 'Splunk Edge and AR Metrics Collector'
    app = constants.APP_NAME
    name = 'splunkedge_ar_metrics_modular_input'
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def __init__(self, logger):
        super().__init__(logger)

    def run(self) -> None:
        self.logger.debug('Running Hub Metrics Collection Modular Input')
        metrics = [
            EdgeHubMetricsCollector(self.logger, self.session_key, constants.APP_NAME),
            OtiDatastreamerMetricsCollector(self.logger, self.session_key, constants.APP_NAME),
        ]
        telemetry_client = TelemetryClient(self.logger, self.session_key)

        for metric in metrics:
            self.logger.debug(f"Collecting metrics for {metric.__class__.__name__}")
            metric = metric.collect()
            telemetry_client.post_metric(metric)


if __name__ == '__main__':
    m = SplunkEdgeARMetricsModularInput(LOGGER)
    m.execute()
