from splunktaucclib.rest_handler.endpoint.validator import Validator
from mati_client import MatiApiClient
from mati_util import (
    build_proxy_config,
    create_service,
    read_conf_file,
    SplunkSessionKey,
)
from requests import RequestException


class ValidateMatiAccount(Validator):
    """Validator class to test connectivity and AuthN to MATI API."""

    def validate(self, value, data):
        """Validator method."""
        key_id = data.get("key_id")
        key_secret = data.get("key_secret")

        # Get proxy settings
        session_key = SplunkSessionKey().session_key
        proxy_config = None
        proxy_settings = read_conf_file(
            session_key, "ta_mandiant_threat_intelligence_settings", stanza="proxy"
        )

        if proxy_settings and proxy_settings.get("proxy_enabled") == "1":
            proxy_config = build_proxy_config(proxy_settings)

        mati = MatiApiClient(key_id, key_secret, proxy_config)

        try:
            resp = mati.get_entitlements()
        except RequestException as ex:
            self.put_msg(f"Connection error: {str(ex)}")
            return False

        if resp.status_code != 200:
            self.put_msg(
                f"Error authenticating with the Mandiant API. Error Code: {resp.status_code}"
            )
            return False

        return True


class IndicatorSettings(Validator):
    """Validator class to test connectivity and AuthN to MATI API."""

    def validate(self, value, data):
        """Validator method."""
        # Connect to Splunk
        session_key = SplunkSessionKey().session_key
        service = create_service(session_key)

        # Enable / Disable Saved Search
        try:
            saved_search = service.saved_searches["Mandiant Indicator Lookup"]
            if data.get("enable_indicator_lookup") != "0":
                saved_search.enable()
            else:
                saved_search.disable()
        except Exception as ex:
            self.put_msg(
                f"Unexpected error enabling / disabling saved search: {str(ex)}"
            )
            return False

        # Set Macro Values
        try:
            service.post(
                "properties/macros/mandiant_indicator_index",
                definition=data.get("mandiant_indicator_index"),
            )
            service.post(
                "properties/macros/mandiant_indicator_time_window",
                definition=data.get("mandiant_indicator_time_window"),
            )
            service.post(
                "properties/macros/mandiant_min_threat_score",
                definition=data.get("mandiant_min_threat_score"),
            )
        except Exception as ex:
            self.put_msg(f"Unexpected error setting macro values: {str(ex)}")
            return False

        return True
