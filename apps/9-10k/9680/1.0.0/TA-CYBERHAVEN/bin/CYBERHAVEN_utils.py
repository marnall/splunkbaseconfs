"""Utility classes and functions for the Cyberhaven TA configuration."""
import import_declare_test  # noqa: F401

from urllib.parse import quote

from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunktaucclib.rest_handler.credentials import RestCredentials
import splunklib.client as client
import splunk.admin as admin
import splunk.clilib.cli_common
import requests
import socket
from solnlib import conf_manager
from splunk.clilib import cli_common as cli
from splunk.clilib.bundle_paths import make_splunkhome_path
from logger_manager import get_logger


DATA_SOURCES = {
    'incidents':  'cyberhaven:incidents',
    'events':     'cyberhaven:events',
    'audit_logs': 'cyberhaven:audit',
}

DATA_SOURCE_LABELS = {
    'incidents':  'Incidents',
    'events':     'Events',
    'audit_logs': 'Audit Logs',
}

# App and saved search names touched by the "Enable Notable Event Automation" checkbox.
# The saved search names must match the stanzas shipped in CYBERHAVEN/default/savedsearches.conf.
CYBERHAVEN_APP_NAME = 'CYBERHAVEN'
ENTERPRISE_SECURITY_APP_NAME = 'SplunkEnterpriseSecuritySuite'
NOTABLE_CORRELATION_SEARCH = 'Cyberhaven - Incident Notable'
NOTABLE_SYNC_SEARCH = 'Cyberhaven - Sync Closed Notable Status to Platform'
NOTABLE_OWNER_SYNC_SEARCH = 'Cyberhaven - Sync Notable Owner to Platform'
NOTABLE_REOPEN_SYNC_SEARCH = 'Cyberhaven - Sync Reopened Notable Status to Platform'

_DEFAULT_APP_VERSION = '1.0.0'


def _get_app_version():
    """Read this add-on's own version from app.conf's [launcher] stanza.

    Reads directly from the file (local overriding default) rather than via a
    btool subprocess -- this runs on every Configuration UI save. Falls back
    to _DEFAULT_APP_VERSION if app.conf can't be read for any reason.
    """
    try:
        app_path = make_splunkhome_path(['etc', 'apps', import_declare_test.ta_name])
        conf = cli.getAppConf('app', import_declare_test.ta_name, use_btool=False, app_path=app_path)
        return conf['launcher']['version']
    except Exception:
        return _DEFAULT_APP_VERSION


USER_AGENT = f'Splunk-{import_declare_test.ta_name}/{_get_app_version()}'


def resolve_host():
    """Resolve hostname to an IPv4 or IPv6 address."""
    try:
        mgmt_uri = splunk.clilib.cli_common.getMgmtUri()
        hostname = mgmt_uri.split("//")[-1].split(":")[0]
        mgmt_port = mgmt_uri.split(":")[-1]
        infos = socket.getaddrinfo(hostname, None)
        ipv4_addresses = [info for info in infos if info[0] == socket.AF_INET]
        ipv6_addresses = [info for info in infos if info[0] == socket.AF_INET6]
        if ipv4_addresses:
            return ipv4_addresses[0][4][0], mgmt_port
        elif ipv6_addresses:
            return ipv6_addresses[0][4][0], mgmt_port
        return None, None
    except socket.gaierror:
        return None, None


class GetSessionKey(admin.MConfigHandler):
    """This class is used to get Splunk session key."""

    def __init__(self):
        """Init method for class."""
        self.session_key = self.getSessionKey()


def get_notable_automation_settings(session_key):
    """Read the tenant URL and (decrypted) API key used by the notable automation adaptive response.

    Returns a dict with 'tenant_url' and 'api_key', defaulting each to ''.
    """
    realm = "__REST_CREDENTIAL__#{}#configs/conf-{}".format(
        import_declare_test.ta_name, 'ta-cyberhaven_settings'
    )
    cfm = conf_manager.ConfManager(session_key, import_declare_test.ta_name, realm=realm)
    conf = cfm.get_conf('ta-cyberhaven_settings')
    hec_settings = conf.get('hec_settings')
    notable_automation = conf.get('notable_automation')
    return {
        'tenant_url': (hec_settings.get('tenant_url') or '').strip().strip('/'),
        'api_key': (notable_automation.get('api_key') or '').strip(),
    }


def get_proxy_settings(session_key):
    """Read the [proxy] stanza and return a requests-style proxies dict, or None.

    Returns None if proxying is disabled or Host/Port aren't configured, so callers can
    pass the result straight through to requests as `proxies=` with no None-check dance.
    Mirrors CYBERHAVEN/bin/cyberhaven_settings.py:get_proxy_settings, which reads the
    same stanza for the adaptive response actions' own outbound calls.
    """
    realm = "__REST_CREDENTIAL__#{}#configs/conf-{}".format(
        import_declare_test.ta_name, 'ta-cyberhaven_settings'
    )
    cfm = conf_manager.ConfManager(session_key, import_declare_test.ta_name, realm=realm)
    conf = cfm.get_conf('ta-cyberhaven_settings')
    try:
        proxy = conf.get('proxy')
    except Exception:
        return None

    if str(proxy.get('proxy_enabled', '0')).strip().lower() not in ('1', 'true'):
        return None

    host = (proxy.get('proxy_url') or '').strip()
    port = (proxy.get('proxy_port') or '').strip()
    if not host or not port:
        return None

    username = (proxy.get('proxy_username') or '').strip()
    password = (proxy.get('proxy_password') or '').strip()
    userinfo = ''
    if username:
        userinfo = quote(username, safe='')
        if password:
            userinfo += f":{quote(password, safe='')}"
        userinfo += '@'

    # "http://" here is the scheme used to talk to the proxy itself (only "http" proxy_type
    # is supported), not the scheme of the request being proxied -- every call this add-on's
    # own validators make goes to https://<tenant_url>/..., so the actual traffic to Cyberhaven
    # stays fully TLS-encrypted end-to-end through the CONNECT tunnel regardless of this value.
    proxy_url = f"http://{userinfo}{host}:{port}"  # NOSONAR
    return {"http": proxy_url, "https": proxy_url}


class NotableAutomationValidator(Validator):
    """Validates and applies the "Enable Notable Event Automation" checkbox.

    When enabling, checks that the CYBERHAVEN app and Splunk Enterprise Security
    are installed and enabled before turning on the two saved searches shipped
    in the CYBERHAVEN app. When disabling, best-effort disables them again.
    """

    SAVED_SEARCHES = (
        NOTABLE_CORRELATION_SEARCH,
        NOTABLE_SYNC_SEARCH,
        NOTABLE_OWNER_SYNC_SEARCH,
        NOTABLE_REOPEN_SYNC_SEARCH,
    )

    def __init__(self):
        """Initialize NotableAutomationValidator with logger."""
        super().__init__()
        self.logger = get_logger("notable_automation")

    def _connect(self, session_key, app):
        try:
            ip_address, mgmt_port = resolve_host()
            if not ip_address:
                raise Exception("Failed to resolve Splunk management URI to an IP address.")
            return client.connect(host=ip_address, port=mgmt_port, token=session_key, owner='nobody', app=app)
        except Exception as e:
            self.logger.error(f"Failed to connect to Splunk (app={app}): {e}")
            return None

    def _app_enabled(self, service, app_name):
        try:
            app_entity = service.apps[app_name]
        except KeyError:
            return False
        disabled = str(app_entity.content.get('disabled', '0')).strip().lower() in ('1', 'true')
        return not disabled

    def _set_saved_searches_disabled(self, service, disabled):
        """Enable/disable the CYBERHAVEN saved searches; return False if enabling failed anywhere."""
        ok = True
        for name in self.SAVED_SEARCHES:
            try:
                service.saved_searches[name].update(disabled=disabled)
                self.logger.info(f"Set disabled={disabled} for saved search '{name}'.")
            except KeyError:
                self.logger.warning(f"Saved search '{name}' not found in the CYBERHAVEN app.")
                if not disabled:
                    self.put_msg(
                        f"Could not find saved search '{name}' in the CYBERHAVEN app. "
                        "Please make sure the CYBERHAVEN app is installed and up to date."
                    )
                    ok = False
            except Exception as e:
                self.logger.error(f"Failed to update saved search '{name}': {e}")
                self.put_msg(
                    f"Failed to update saved search '{name}'. "
                    "Check TA-CYBERHAVEN_notable_automation.log for details."
                )
                ok = False
        return ok

    def validate(self, value, data):
        """Validate and apply the enable/disable toggle for notable event automation."""
        enable = str(value).strip().lower() in ('1', 'true', 'yes')
        session_key = GetSessionKey().session_key

        if not enable:
            ch_service = self._connect(session_key, CYBERHAVEN_APP_NAME)
            if ch_service is not None:
                self._set_saved_searches_disabled(ch_service, True)
            return True

        api_key = (data.get('api_key') or '').strip()
        if not api_key:
            self.put_msg("A Cyberhaven API Key is required to enable notable event automation.")
            return False

        admin_service = self._connect(session_key, import_declare_test.ta_name)
        if admin_service is None:
            self.put_msg(
                "Failed to connect to Splunk. Check TA-CYBERHAVEN_notable_automation.log for details."
            )
            return False

        if not self._app_enabled(admin_service, CYBERHAVEN_APP_NAME):
            self.logger.error("CYBERHAVEN app is not installed or is disabled.")
            self.put_msg(
                "The CYBERHAVEN app is not installed or is disabled. "
                "Install and enable the CYBERHAVEN app before enabling notable event automation."
            )
            return False

        if not self._app_enabled(admin_service, ENTERPRISE_SECURITY_APP_NAME):
            self.logger.error("Splunk Enterprise Security is not installed or is disabled.")
            self.put_msg(
                "Splunk Enterprise Security is not installed or is disabled. "
                "Install and enable Splunk Enterprise Security before enabling notable event automation."
            )
            return False

        ch_service = self._connect(session_key, CYBERHAVEN_APP_NAME)
        if ch_service is None:
            self.put_msg(
                "Failed to connect to the CYBERHAVEN app. "
                "Check TA-CYBERHAVEN_notable_automation.log for details."
            )
            return False

        return self._set_saved_searches_disabled(ch_service, False)


class CyberhavenApiKeyValidator(Validator):
    """Validates the Cyberhaven API Key by exchanging it for an access token.

    Calls POST {tenant_url}/public/v2/auth/token/access (see the "Cyberhaven API"
    Postman collection), the same call the cyberhaven_update_status adaptive
    response action makes, to confirm the key actually authenticates against the
    Cyberhaven platform before it is saved.
    """

    def __init__(self):
        """Initialize CyberhavenApiKeyValidator with logger."""
        super().__init__()
        self.logger = get_logger("notable_automation")

    def _get_tenant_url(self, session_key):
        try:
            ip_address, mgmt_port = resolve_host()
            if not ip_address:
                raise Exception("Failed to resolve Splunk management URI to an IP address.")
            service = client.connect(
                host=ip_address, port=mgmt_port, token=session_key, owner='nobody', app=import_declare_test.ta_name
            )
            stanza = service.confs['ta-cyberhaven_settings']['hec_settings']
            return (stanza.content.get('tenant_url') or '').strip().strip('/')
        except Exception as e:
            self.logger.error(f"Failed to read Cyberhaven Tenant URL: {e}")
            return ''

    def validate(self, value, data):
        """Validate the API key by exchanging it for a Cyberhaven access token."""
        api_key = (value or '').strip()
        if not api_key:
            self.put_msg("A Cyberhaven API Key is required.")
            return False

        if RestCredentials.is_placeholder(api_key):
            # Unchanged, already-validated encrypted value; nothing new to verify.
            return True

        session_key = GetSessionKey().session_key
        tenant_url = self._get_tenant_url(session_key)
        if not tenant_url:
            self.put_msg(
                "Cannot validate the Cyberhaven API Key because the Cyberhaven Tenant URL "
                "is not configured. Set the Tenant URL on the HEC Configuration tab first."
            )
            return False

        base_url = f"{tenant_url}/public"
        proxies = get_proxy_settings(session_key)
        try:
            resp = requests.post(
                f"{base_url}/v2/auth/token/access",
                headers={
                    "Authorization": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                },
                json={"refresh_token": api_key},
                timeout=15,
                proxies=proxies,
            )
        except requests.exceptions.ProxyError as e:
            self.logger.error(f"Cyberhaven API Key validation: proxy error: {e}")
            self.put_msg(
                "Failed to reach the Cyberhaven platform through the configured proxy. "
                "Check the Proxy settings (Configuration -> Proxy) and try again."
            )
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Cyberhaven API Key validation request failed: {e}")
            self.put_msg(
                "Failed to reach the Cyberhaven platform to validate the API Key. "
                "Check the Tenant URL and network connectivity."
            )
            return False

        if resp.status_code != 200:
            self.logger.error(
                f"Cyberhaven API Key validation failed with status {resp.status_code}: {resp.text}"
            )
            self.put_msg("The provided Cyberhaven API Key could not be validated. Check the key and try again.")
            return False

        try:
            body = resp.json()
        except ValueError:
            self.logger.error("Cyberhaven API Key validation: non-JSON response from Cyberhaven.")
            self.put_msg("Unexpected response from Cyberhaven while validating the API Key.")
            return False

        errors = body.get("errors") or []
        access_token = body.get("access_token")
        if errors or not access_token:
            self.logger.error(f"Cyberhaven API Key validation errors: {errors}")
            self.put_msg("The provided Cyberhaven API Key is invalid or could not be exchanged for an access token.")
            return False

        self.logger.info("Cyberhaven API Key validated successfully.")
        return True


class CyberhavenHECValidator(Validator):
    """Cyberhaven HEC Configuration Validator."""

    def __init__(self):
        """Initialize CyberhavenHECValidator with logger."""
        super().__init__()
        self.logger = get_logger("hec_configuration")

    def validate_tenant_url(self, tenant_url, session_key):
        """Validate that the tenant URL is reachable and resembles a Cyberhaven URL."""
        try:
            if "cyberhaven" not in tenant_url:
                self.put_msg(
                    "Provided Tenant URL does not look like a Cyberhaven URL."
                    " e.g., https://acme.cyberhaven.io"
                )
                self.logger.info("Provided Tenant URL does not have cyberhaven in it.")
                return False
            requests.head(
                tenant_url,
                allow_redirects=True,
                timeout=5,
                headers={"User-Agent": USER_AGENT},
                proxies=get_proxy_settings(session_key),
            )
            self.logger.info("Tenant URL Validation Success! The Cyberhaven tenant is active and reachable.")
            return True
        except requests.exceptions.ProxyError as e:
            self.logger.error(f"Received ProxyError validating tenant_url={tenant_url}: {e}")
            self.put_msg(
                "Failed to reach the Cyberhaven platform through the configured proxy. "
                "Check the Proxy settings (Configuration -> Proxy) and try again."
            )
            return False
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Received ConnectionError for tenant_url: {tenant_url}")
            self.put_msg("Provided Tenant URL is not valid.")
            return False
        except requests.exceptions.RequestException:
            self.put_msg(f"Provided Tenant URL {tenant_url} is not valid.")
            return False

    def _upsert_macro(self, service, macro_name, definition):
        try:
            try:
                service.confs['macros'][macro_name].update(definition=definition)
                self.logger.info(f"Updated {macro_name} macro: {definition}")
            except KeyError:
                service.confs['macros'].create(macro_name, **{'definition': definition})
                self.logger.info(f"Created {macro_name} macro: {definition}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update {macro_name} macro: {e}")
            self.put_msg(
                f"Failed to update {macro_name} macro. "
                "Check TA-CYBERHAVEN_hec_configuration.log for details."
            )
            return False

    def _update_index_macro(self, service, indices):
        definition = 'index IN ({})'.format(', '.join(f'"{i}"' for i in indices))
        return self._upsert_macro(service, 'cyberhaven_index', definition)

    def _get_saved_settings(self, service):
        try:
            stanza = service.confs['ta-cyberhaven_settings']['hec_settings']
            return dict(stanza.content)
        except Exception as e:
            self.logger.debug(f"Could not read saved settings: {e}")
            return {}

    def generate_hec_token(self, service, hec_name, index, sourcetype):
        """Create a new HEC token in Splunk and return its value."""
        try:
            hec_input = service.inputs.create(
                hec_name,
                'http',
                disabled=False,
                sourcetype=sourcetype,
                index=index,
                output_mode='json'
            )
            self.logger.info(f"Created HEC input '{hec_name}' with sourcetype '{sourcetype}'.")
            return hec_input.content.get('token')
        except Exception as e:
            error_str = str(e)
            if '409' in error_str or 'already exists' in error_str.lower():
                self.logger.warning(f"HEC input '{hec_name}' already exists in Splunk.")
                self.put_msg(
                    f"HEC Token Name '{hec_name}' already exists in Splunk. "
                    f"Please provide a different name or delete the existing one from "
                    f"Settings > Data Inputs > HTTP Event Collector."
                )
            else:
                self.logger.error(f"Failed to create HEC token for '{hec_name}': {e}")
                self.put_msg(
                    f"Failed to create HEC token '{hec_name}'. "
                    f"Check TA-CYBERHAVEN_hec_configuration.log for details."
                )
            return False

    def _connect_to_splunk(self, session_key):
        """Connect to the local Splunk service and return the client, or None on failure."""
        try:
            ip_address, mgmt_port = resolve_host()
            if not ip_address:
                raise Exception("Failed to resolve Splunk management URI to an IP address.")
            service = client.connect(
                host=ip_address,
                port=mgmt_port,
                token=session_key,
                owner='nobody',
                app=import_declare_test.ta_name
            )
            self.logger.info("Connected to Splunk service successfully.")
            return service
        except Exception as e:
            self.logger.error(f"Failed to connect to Splunk: {e}")
            self.put_msg("Failed to connect to Splunk. Check TA-CYBERHAVEN_hec_configuration.log for details.")
            return None

    def _update_macro_if_changed(self, service, data, saved):
        """Update the cyberhaven_index macro when the index list has changed."""
        curr = data.get("macro_indices", "").strip()
        prev = saved.get("macro_indices", "").strip()
        if curr != prev:
            indices = [i.strip() for i in curr.split(",") if i.strip()]
            return self._update_index_macro(service, indices)
        return True

    def _validate_unique_hec_names(self, data, selected_types):
        """Return False if any two selected data sources share an HEC token name."""
        seen = {}
        for source_type in selected_types:
            hec_name = data.get(f"hec_name_{source_type}", "").strip()
            if not hec_name:
                continue
            if hec_name in seen:
                self.put_msg(
                    f"HEC Token Name '{hec_name}' is already used for "
                    f"'{DATA_SOURCE_LABELS[seen[hec_name]]}'. "
                    f"Each data source must have a unique HEC Token Name."
                )
                return False
            seen[hec_name] = source_type
        return True

    def _provision_single_hec_token(self, service, data, saved, source_type, sourcetype):
        """Create or reuse the HEC token for one data source; return False on error."""
        hec_name = data.get(f"hec_name_{source_type}", "").strip()
        index = data.get(f"index_{source_type}", "").strip()

        if not hec_name and not index:
            return True

        if not hec_name or not index:
            self.put_msg(
                f"Both HEC Token Name and Index are required for '{DATA_SOURCE_LABELS[source_type]}'."
            )
            return False

        prev_hec_name = (saved.get(f"hec_name_{source_type}") or "").strip()
        prev_index = (saved.get(f"index_{source_type}") or "").strip()
        prev_hec_token = (saved.get(f"hec_token_{source_type}") or "").strip()

        if prev_hec_token and prev_hec_name == hec_name and prev_index == index:
            self.logger.info(
                f"HEC name and index unchanged for '{DATA_SOURCE_LABELS[source_type]}',"
                " keeping existing token."
            )
            data[f"hec_token_{source_type}"] = prev_hec_token
            return True

        self.logger.debug(f"Generating new HEC token for '{source_type}' (name: '{hec_name}').")
        token_value = self.generate_hec_token(service, hec_name, index, sourcetype)
        if not token_value:
            return False
        data[f"hec_token_{source_type}"] = token_value
        return True

    def _provision_hec_tokens(self, service, data, saved, selected_types):
        """Iterate over all data sources and provision their HEC tokens."""
        for source_type, sourcetype in DATA_SOURCES.items():
            if source_type not in selected_types:
                continue
            if not self._provision_single_hec_token(service, data, saved, source_type, sourcetype):
                return False
        return True

    def validate(self, _value, data):
        """Validate HEC configuration and create or reuse HEC tokens for each data source."""
        tenant_url = data.get("tenant_url", "").strip().strip("/")
        session_key = GetSessionKey().session_key

        self.logger.debug(f"Validating tenant url: {tenant_url}")
        if not self.validate_tenant_url(tenant_url, session_key):
            return False

        service = self._connect_to_splunk(session_key)
        if service is None:
            return False

        saved = self._get_saved_settings(service)

        if not self._update_macro_if_changed(service, data, saved):
            return False

        selected_types = [t.strip() for t in data.get("type", "").split(",") if t.strip()]

        if not self._validate_unique_hec_names(data, selected_types):
            return False

        return self._provision_hec_tokens(service, data, saved, selected_types)
