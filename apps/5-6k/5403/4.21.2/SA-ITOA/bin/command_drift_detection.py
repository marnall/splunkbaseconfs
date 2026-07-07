import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))

from splunk import rest
from itsi.itsi_utils import ITOAInterfaceUtils
from ITOA.itoa_common import is_feature_enabled
from ITOA.setup_logging import setup_logging
from SA_ITOA_app_common.splunklib.searchcommands import Configuration, GeneratingCommand, dispatch


@Configuration()
class ITSIDriftDetection(GeneratingCommand):
    logger = setup_logging("itsi_drift_detection.log", "itsi.change.drift_detection")

    def enable_or_disable_drift_detection_search(self, session_key):
        is_drift_detection_enabled = is_feature_enabled('itsi-drift-detection', session_key)
        try:
            service = ITOAInterfaceUtils.service_connection(self.service.token, app_name="itsi")
            if is_drift_detection_enabled:
                rest.simpleRequest('/servicesNS/nobody/itsi/saved/searches/itsi_kpi_drift_detection?disabled=0',
                                   sessionKey=session_key, method='POST', raiseAllErrors=True)

                itsi_drift_detection_search = service.saved_searches["itsi_kpi_drift_detection"]
                self.logger.info('Status of itsi_kpi_drift_detection search after enabling it : disabled=%s',
                                 itsi_drift_detection_search["disabled"])
            else:
                rest.simpleRequest('/servicesNS/nobody/itsi/saved/searches/itsi_kpi_drift_detection?disabled=1',
                                   sessionKey=session_key, method='POST', raiseAllErrors=True)

                itsi_drift_detection_search = service.saved_searches["itsi_kpi_drift_detection"]
                self.logger.info('Status of itsi_kpi_drift_detection search after disabling it : disabled=%s',
                                 itsi_drift_detection_search["disabled"])
        except Exception as err:
            self.logger.error(
                'Error occurred while disabling/enabling the itsi_kpi_drift_detection search: %s', err)

    def generate(self):
        self.logger.info('Drift detection custom command is running...')
        self.enable_or_disable_drift_detection_search(self.service.token)
        yield {}


dispatch(ITSIDriftDetection, sys.argv, sys.stdin, sys.stdout, __name__)
