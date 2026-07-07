import requests
import splunk
import splunk.admin as admin
from radar_settings_manager import *
from radar_client import RadarClient

RADAR_PACKAGE = 'radar'

class RadarAddOnConfigHandler(admin.MConfigHandler):
    def __init__(self, *args):
        admin.MConfigHandler.__init__(self, *args)
        self.settings_manager = RadarSettingsManager(splunk.getLocalServerInfo(),
                                                     self.getSessionKey())

    def setup(self):
        for arg in [RADAR_PARAM_API_TOKEN, RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS]:
            self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        """
        Populate add-on configuration UI elements from saved settings.
        """
        radar_settings = self.settings_manager.get_radar_settings()
        token = radar_settings.get(RADAR_PARAM_API_TOKEN, '')
        confInfo[RADAR_PACKAGE][RADAR_PARAM_API_TOKEN] = token
        skip = str(int(radar_settings[RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS]))
        confInfo[RADAR_PACKAGE][RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS] = skip

    def handleEdit(self, confInfo):
        """
        Persist changes made in add-on configuration UI.
        """
        if self.callerArgs.id != RADAR_PACKAGE:
            return

        radar_settings = self.settings_manager.get_radar_settings()

        self._applySetting(radar_settings, RADAR_PARAM_API_TOKEN, lambda x: x.strip())
        self._applySetting(radar_settings, RADAR_PARAM_SKIP_VERIFY_SSL_CERT_FOR_SPLUNK_REST_CALLS, lambda x: bool(int(x.strip())))

        self._validateRADARSettings(radar_settings)
        self.settings_manager.update_radar_settings(radar_settings)

    def _applySetting(self, radarSettings, key, parse):
        """
        Read the given config key from callerArgs, and put it into radar_settings
        """
        # N.b.: "key in self.callerArgs" doesn't work properly here, returns False incorrectly.
        d = self.callerArgs.data
        if key in d and len(d[key]):
            # callerArgs values arrive as lists, so we just grab the first-and-only element
            val = d[key][0]
            if val is None:
                radarSettings[key] = None
            else:
                radarSettings[key] = parse(val)

    def _validateRADARSettings(self, radar_settings):
        if radar_settings[RADAR_PARAM_API_TOKEN] not in (None, ERROR_SPLUNK_SSL_VERIFICATION) and \
           not RadarClient(radar_settings).validate_radar_settings():
            raise admin.ArgValidationException, "Error connecting to RADAR service"


if __name__ == "__main__":
    admin.init(RadarAddOnConfigHandler, admin.CONTEXT_APP_ONLY)
