# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import ipaddress
import json
import requests
from requests.adapters import HTTPAdapter
import socket
import ssl
import sys
from urllib.parse import urlparse
from urllib3.util.ssl_ import create_urllib3_context

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

from ITOA.itoa_common import get_conf
from ITOA.setup_logging import getLogger
from ITOA.event_management.notable_event_utils import Audit
from itsi.event_management.sdk.custom_group_action_base import CustomGroupActionBase
import splunk.rest as splunk_rest
from splunk.util import safeURLQuote

WEBHOOK_AUTH_TYPES = {
    'BASIC_AUTH': 'Basic authentication',
    'BEARER_TOKEN': 'Bearer token',
    'NO_AUTH': 'No authentication'
}


class SNIAdapter(HTTPAdapter):
    """
    Custom HTTPAdapter that allows specifying a different hostname for SNI
    (Server Name Indication) during SSL/TLS handshake.

    This is needed when connecting to an IP address but needing SSL certificate
    verification against the original hostname (to prevent DNS rebinding attacks
    while still allowing proper certificate validation).
    """

    def __init__(self, server_hostname=None, **kwargs):
        """
        Initialize the adapter with an optional server_hostname for SNI.

        @type: str
        @param server_hostname: The hostname to use for SNI and certificate verification
        """
        self.server_hostname = server_hostname
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        """
        Initialize the pool manager with custom SSL context that uses SNI.
        """
        if self.server_hostname:
            ctx = create_urllib3_context()
            kwargs['ssl_context'] = ctx
            kwargs['server_hostname'] = self.server_hostname
        super().init_poolmanager(*args, **kwargs)


class Webhook(CustomGroupActionBase):
    """
    Class that performs Webhook action on notable events group.
    """

    def __init__(self, settings, app='SA-ITOA'):
        """
        Initialize the object
        @type settings: dict/basestring
        @param settings: incoming settings for this alert action that splunkd
            passes via stdin.

        @returns Nothing
        """
        self.logger = getLogger(logger_name="itsi.event_action.webhook")

        super(Webhook, self).__init__(settings, self.logger)

        self.app = app
        self.owner = 'nobody'
        self.session_key = self.get_session_key()
        self.webhook_name = None
        self.webhook_url = None
        self.conf_file_name = 'webhooks'
        self.webhook_header = ''
        self.parsed_url_hostname = ''
        self.ip_addresses = []
        self.itsi_group_id = None
        self.itsi_policy_id = None
        self.allowed_ips = []
        self.webhook_configuration = None
        self.audit = Audit(self.session_key, audit_token_name='Auto Generated ITSI Notable Index Audit Token')

    def get_clear_password(self, username):
        """
        Get the actual password and token

        @type: str
        @param username: username/webhook name

        @rtype: str
        @return: decoded password/token
        """
        try:
            realm_user = self.webhook_name + ':' + username
            uri_string = ('/servicesNS/{0}/{1}/storage/passwords/{2}').format(self.owner, self.app, realm_user)
            uri = safeURLQuote(uri_string)
            res, content = splunk_rest.simpleRequest(uri, getargs={'output_mode': 'json'},
                                                     sessionKey=self.session_key)

            if res.status == 200:
                self.logger.info(
                    'Password is fetched successfully for webhook=%s itsi_group_id=%s', self.webhook_name, self.itsi_group_id)
            else:
                self.logger.error(
                    'Error in getting password from passwords.conf. response=%s content=%s itsi_group_id=%s', res, content, self.itsi_group_id)
                return None
            if not content:
                self.logger.error('content was not returned from passwords.conf for itsi_group_id=%s', self.itsi_group_id)
                return None

            parsed_content = json.loads(content)
            password = parsed_content.get('entry', [])[0].get('content', {}).get('clear_password', {})
            return password

        except Exception as e:
            self.logger.exception('An error occurred while fetching the password. Exception: %s itsi_group_id=%s', e, self.itsi_group_id)
            return None

    def _validate_ip_address(self, raise_on_private=True):
        """
        Resolve hostname to IP addresses and validate.
        - If allowed_ips is configured: Use ONLY those IPs (private or public allowed)
        - If allowed_ips is NOT configured: Use DNS lookup and require public IPs only

        @type: bool
        @param raise_on_private: If True, raises exception for private IPs. If False, logs error and exits.
        @rtype: str
        @return: The first valid IP address
        @raises: Exception if no valid IP addresses are found
        """
        try:
            # Option 1: If allowed_ips is configured, use ONLY those IPs (skip DNS)
            if self.allowed_ips:
                self.logger.info(
                    'Using configured allowed_ips={0} for webhook={1} itsi_group_id={2}'.format(
                        self.allowed_ips, self.webhook_name, self.itsi_group_id
                    )
                )
                valid_ips = []
                for ip in self.allowed_ips:
                    try:
                        ipaddress.ip_address(ip)
                        valid_ips.append(ip)
                    except ValueError:
                        self.logger.warning(
                            'Skipping invalid IP format: {0}. Webhook={1} itsi_group_id={2}'.format(
                                ip, self.webhook_name, self.itsi_group_id
                            )
                        )
                if not valid_ips:
                    error_msg = 'No valid IP addresses found in allowed_ips: {}'.format(self.allowed_ips)
                    self.logger.error(
                        'No valid IP addresses found in allowed_ips: {0}. Webhook={1} itsi_group_id={2}'.format(
                            self.allowed_ips, self.webhook_name, self.itsi_group_id
                        )
                    )
                    self.audit.send_activity_to_audit({
                        'event_id': self.itsi_group_id,
                        'itsi_policy_id': self.itsi_policy_id
                    }, 'Webhook "{0}" failed. Error: {1}'.format(self.webhook_name, error_msg), 'Webhook action failed')
                    raise Exception(error_msg)
                self.ip_addresses = valid_ips
                return valid_ips[0]

            # Option 2: No allowed_ips configured - use DNS and require public IPs only
            addr_info = socket.getaddrinfo(self.parsed_url_hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            dns_ips = [info[4][0] for info in addr_info]

            # Filter to only global (public) IPs
            public_ips = []
            for dns_ip in dns_ips:
                try:
                    if ipaddress.ip_address(dns_ip).is_global:
                        public_ips.append(dns_ip)
                except ValueError:
                    pass

            if public_ips:
                self.ip_addresses = public_ips
                return public_ips[0]
            else:
                # DNS returned only private IPs - not allowed without allowed_ips config
                error_msg = 'Private IP addresses are not allowed for webhook URLs. Configure allowed_ips to use private IPs.'
                if raise_on_private:
                    self.logger.error(
                        'Private IP addresses are not allowed for webhook URLs. Configure allowed_ips to use private IPs. Webhook={0} itsi_group_id={1}'.format(
                            self.webhook_name, self.itsi_group_id
                        )
                    )
                    self.audit.send_activity_to_audit({
                        'event_id': self.itsi_group_id,
                        'itsi_policy_id': self.itsi_policy_id
                    }, 'Webhook "{0}" failed. Error: {1}'.format(self.webhook_name, error_msg), 'Webhook action failed')
                    raise Exception('Private IP addresses are not allowed for webhook URLs')
                else:
                    self.logger.error(
                        'Webhook URL must be public for webhook action. Configure allowed_ips to use private IPs. Webhook={0} itsi_group_id={1}'.format(
                            self.webhook_name, self.itsi_group_id
                        )
                    )
                    self.audit.send_activity_to_audit({
                        'event_id': self.itsi_group_id,
                        'itsi_policy_id': self.itsi_policy_id
                    }, 'Webhook "{0}" failed. Error: {1}'.format(self.webhook_name, error_msg), 'Webhook action failed')
                    sys.exit(1)

        except Exception as e:
            if 'Private IP addresses are not allowed' in str(e):
                raise
            if 'No valid IP addresses found in allowed_ips' in str(e):
                raise
            self.logger.exception(
                'An error occurred while validating IP address. Webhook={0} itsi_group_id={1} Exception: {2}'.format(
                    self.webhook_name, self.itsi_group_id, e
                )
            )
            raise

    def _build_safe_url(self, validated_ip):
        """
        Build a URL using the validated IP address instead of hostname to prevent DNS rebinding.

        @type: str
        @param validated_ip: The validated IP address to use

        @rtype: str
        @return: URL with IP address instead of hostname
        """
        parsed = urlparse(self.webhook_url)
        port_part = f":{parsed.port}" if parsed.port else ""
        # IPv6 addresses must be wrapped in brackets in URLs
        ip_part = f"[{validated_ip}]" if ':' in validated_ip else validated_ip
        safe_url = f"{parsed.scheme}://{ip_part}{port_part}{parsed.path}"
        if parsed.query:
            safe_url += f"?{parsed.query}"
        return safe_url

    def _execute_post_with_failover(self, data, headers, auth=None, verify=True):
        """
        Execute POST request with failover across multiple IP addresses.

        @type: str
        @param data: payload to send via url

        @type: dict
        @param headers: HTTP headers to include in the request

        @type: tuple or None
        @param auth: Optional tuple of (username, password) for Basic Auth

        @type: bool
        @param verify: Whether to verify SSL certificates (default True)

        @return: Nothing
        @raises: SystemExit on failure
        """
        last_error = None
        parsed = urlparse(self.webhook_url)
        is_https = parsed.scheme == 'https'

        for idx, ip_address in enumerate(self.ip_addresses):
            try:
                safe_url = self._build_safe_url(ip_address)
                self.logger.debug(
                    'Attempting webhook request to IP {0} ({1}/{2}) for webhook={3} itsi_group_id={4}'.format(
                        ip_address, idx + 1, len(self.ip_addresses), self.webhook_name, self.itsi_group_id
                    )
                )

                # Use a session with SNI adapter for HTTPS to handle certificate verification
                # against the original hostname when connecting to an IP address
                session = requests.Session()
                if is_https:
                    sni_adapter = SNIAdapter(server_hostname=self.parsed_url_hostname)
                    session.mount('https://', sni_adapter)

                response = session.post(
                    safe_url,
                    data=data,
                    headers=headers,
                    auth=auth,
                    verify=verify,
                    allow_redirects=False,
                )
                # Check if the request was successful (status code 2xx)
                if response.status_code >= 200 and response.status_code < 300:
                    self.logger.info(
                        'Webhook action for webhook {0} executed successfully using IP {1} for itsi_group_id={2}'.format(
                            self.webhook_name, ip_address, self.itsi_group_id
                        )
                    )
                    return  # Success - exit the method
                else:
                    last_error = 'status={0} response_text={1}'.format(response.status_code, response.text)
                    self.logger.warning(
                        'Failed to execute Webhook action for webhook={0} using IP {1}. {2} itsi_group_id={3}. Trying next IP...'.format(
                            self.webhook_name, ip_address, last_error, self.itsi_group_id
                        )
                    )
            except requests.exceptions.RequestException as req_error:
                last_error = str(req_error)
                self.logger.warning(
                    'Request failed for webhook={0} using IP {1}. Error: {2} itsi_group_id={3}. Trying next IP...'.format(
                        self.webhook_name, ip_address, last_error, self.itsi_group_id
                    )
                )

        # All IPs failed
        self.logger.error(
            'Failed to execute Webhook action for webhook={0}. All IPs exhausted. Last error: {1} itsi_group_id={2}'.format(
                self.webhook_name, last_error, self.itsi_group_id
            )
        )
        self.audit.send_activity_to_audit({
            'event_id': self.itsi_group_id,
            'itsi_policy_id': self.itsi_policy_id
        }, 'Webhook "{0}" failed. Error: {1}'.format(self.webhook_name, last_error), 'Webhook action failed')
        sys.exit(1)

    def send_post_request(self, data):
        """
        Send POST request with data to url. Tries each IP in ip_addresses list with failover.

        @type: dict
        @param data: payload to send via url

        @return: Nothing
        """
        try:
            # self.ip_addresses is already validated in execute() before this method is called
            headers = {"Content-Type": "application/json", "Host": self.parsed_url_hostname}
            if self.webhook_header is not None:
                try:
                    headers = json.loads(self.webhook_header)
                    headers.setdefault("Host", self.parsed_url_hostname)
                except Exception as e:
                    self.logger.error(
                        'Unable to complete webhook action because the header is invalid. Update the header and try again. Webhook={0} header={1} itsi_group_id={2} Exception={3}.'.format(
                            self.webhook_name, self.webhook_header, self.itsi_group_id, e
                        )
                    )
                    sys.exit(1)

            self._execute_post_with_failover(
                data, headers,
                verify=self.is_ssl_certificate_validation_enabled
            )

        except Exception as e:
            self.logger.exception(
                'An error occurred while executing the webhook action. Webhook={0} itsi_group_id={1} Exception={2}'.format(
                    self.webhook_name, self.itsi_group_id, e
                )
            )
            sys.exit(1)

    def send_post_request_with_auth(self, data, username):
        """
        Send POST request with data to url using username and password. Tries each IP with failover.

        @type: dict
        @param data: payload to send via url

        @type: str
        @param username: username for authentication

        @return: Nothing
        """
        try:
            # self.ip_addresses is already validated in execute() before this method is called
            decrypted_password = self.get_clear_password(username)
            headers = {'Content-Type': 'application/json', 'Host': self.parsed_url_hostname}
            if self.webhook_header is not None:
                try:
                    headers = json.loads(self.webhook_header)
                    headers.setdefault('Host', self.parsed_url_hostname)
                except Exception as e:
                    self.logger.error(
                        'Unable to complete webhook action because the header is invalid. Update the header and try again. Webhook={0} header={1} itsi_group_id={2} Exception: {3}.'.format(
                            self.webhook_name, self.webhook_header, self.itsi_group_id, e
                        )
                    )
                    sys.exit(1)
            if decrypted_password is None:
                self.logger.error(
                    'Password not found for provided Webhook=%s itsi_group_id=%s', self.webhook_name, self.itsi_group_id
                )
                sys.exit(1)

            self._execute_post_with_failover(
                data, headers,
                auth=(username, decrypted_password),
                verify=self.is_ssl_certificate_validation_enabled
            )

        except Exception as e:
            self.logger.exception(
                'An error occurred while executing the webhook action. Webhook={0} itsi_group_id={1} Exception={2}'.format(
                    self.webhook_name, self.itsi_group_id, e
                )
            )
            sys.exit(1)

    def send_post_request_with_token(self, data):
        """
        Send POST request with data to url using Token. Tries each IP with failover.

        @type: dict
        @param data: payload to send via url

        @return: Nothing
        """
        try:
            # self.ip_addresses is already validated in execute() before this method is called
            decrypted_token = self.get_clear_password(self.webhook_name)
            if decrypted_token is None:
                self.logger.error(
                    'Token not found for provided Webhook=%s itsi_group_id=%s', self.webhook_name, self.itsi_group_id
                )
                sys.exit(1)
            headers = {
                "Authorization": f"Bearer {decrypted_token}",
                "Content-Type": "application/json",
                "Host": self.parsed_url_hostname,
            }
            if self.webhook_header is not None:
                try:
                    self.webhook_header = json.loads(self.webhook_header)
                    if "Authorization" not in self.webhook_header:
                        self.webhook_header.update(
                            {"Authorization": f"Bearer {decrypted_token}"}
                        )
                    self.webhook_header.setdefault("Host", self.parsed_url_hostname)
                    headers = self.webhook_header
                except Exception as e:
                    self.logger.error(
                        'Unable to complete webhook action because the header is invalid. Update the header and try again. Webhook={0} header={1} itsi_group_id={2} Exception: {3}.'.format(
                            self.webhook_name, self.webhook_header, self.itsi_group_id, e
                        )
                    )
                    sys.exit(1)

            self._execute_post_with_failover(
                data, headers,
                verify=self.is_ssl_certificate_validation_enabled
            )

        except Exception as e:
            self.logger.exception(
                'An error occurred while executing the webhook action. Webhook={0} itsi_group_id={1} Exception={2}'.format(
                    self.webhook_name, self.itsi_group_id, e
                )
            )
            sys.exit(1)

    def get_configuration(self, conf_file_name=None, app=None):
        """
        Get configurations for webhooks

        @type: str
        @param conf_file_name: configuration file name

        @type: str
        @param app: app name

        @rtype: dict
        @return: config fields with value for provided configuration file
        """
        conf_file_name = conf_file_name if conf_file_name else self.conf_file_name
        app = app if app else self.app
        rval = get_conf(self.session_key, conf_file_name, search='disabled=0', count=-1, app=app)

        response = rval.get('response')

        if response.status != 200:
            self.logger.error(
                'Failed to fetch configuration file=`%s`, rval=`%s`', self.conf_file_name, rval
            )
            raise Exception('Failed to fetch data for config="%s".', self.conf_file_name)

        content = rval.get('content')
        content = json.loads(content)

        configuration = {}
        for entry in content.get('entry', []):
            configuration[entry.get('name')] = entry.get('content', {})

        return configuration

    def execute_action(self, payload):
        """
        Performs the POST request for the provided webhook

        @type: dict
        @param payload: payload of event
        """

        # Use configuration already loaded in execute() to avoid duplicate REST call
        configuration = getattr(self, 'webhook_configuration', None) or self.get_configuration(self.conf_file_name)

        # Getting required fields from conf file
        webhook_obj = configuration.get(self.webhook_name, None) if configuration else None
        if not webhook_obj:
            raise Exception(
                'Correct Auth Type is not provided for webhook={0} itsi_group_id={1}'.format(
                    self.webhook_name, self.itsi_group_id
                )
            )
        webhook_auth_type = webhook_obj.get('auth_type', None)
        self.webhook_header = webhook_obj.get('header', None)
        self.is_ssl_certificate_validation_enabled = webhook_obj.get('should_ssl_verified', False)
        if self.is_ssl_certificate_validation_enabled:
            self.is_ssl_certificate_validation_enabled = bool(int(self.is_ssl_certificate_validation_enabled))

        # Execute POST call based on the Auth Type
        if webhook_auth_type == WEBHOOK_AUTH_TYPES['BASIC_AUTH']:  # using username password
            webhook_username = webhook_obj.get('username', None)
            if webhook_username is None:
                self.logger.error('Username must be defined for Webhook with Auth Type Basic for itsi_group_id=%s', self.itsi_group_id)
                sys.exit(1)
            self.send_post_request_with_auth(payload, webhook_username)

        elif webhook_auth_type == WEBHOOK_AUTH_TYPES['BEARER_TOKEN']:  # using token
            self.send_post_request_with_token(payload)

        elif webhook_auth_type == WEBHOOK_AUTH_TYPES['NO_AUTH']:  # direct POST call
            self.send_post_request(payload)

        else:
            raise Exception('Correct Auth Type is not provided for webhook={0} itsi_group_id={1}'.format(self.webhook_name, self.itsi_group_id))

    def execute(self):
        """
        Performs webhook action.
        executes the execute_action for the webhook with payload
        """
        self.logger.debug('Received settings from splunkd=`%s`', json.dumps(self.settings))
        payload = self.settings.get('result', None)
        self.itsi_group_id = payload.get('itsi_group_id') if payload else None
        self.itsi_policy_id = payload.get('itsi_policy_id') if payload else None
        self.logger.info('Processing webhook action for itsi_group_id=%s', self.itsi_group_id)
        config = self.settings.get('configuration', None)
        self.webhook_name = config.get('webhook_name', None)
        self.webhook_url = config.get('webhook_uri', None)
        try:
            if self.webhook_name is None:
                self.logger.error('Webhook Name must be defined for webhook action for itsi_group_id=%s', self.itsi_group_id)
                sys.exit(1)
            if self.webhook_url is None:
                self.logger.error('Webhook URL must be defined for webhook action for itsi_group_id=%s', self.itsi_group_id)
                sys.exit(1)

            self.parsed_url_hostname = urlparse(self.webhook_url).hostname

            # Read webhook configuration BEFORE IP validation so allowed_ips (if set) is available
            self.webhook_configuration = self.get_configuration(self.conf_file_name)
            webhook_obj = self.webhook_configuration.get(self.webhook_name, None) if self.webhook_configuration else None
            if webhook_obj:
                # Read allowed_ips from configuration - allows bypassing public IP validation for internal webhooks
                allowed_ips_config = webhook_obj.get('allowed_ips', None)
                if allowed_ips_config:
                    self.allowed_ips = [ip.strip() for ip in allowed_ips_config.split(',') if ip.strip()]

            self._validate_ip_address(raise_on_private=False)
            self.execute_action(json.dumps(payload))
        except Exception as e:
            self.logger.error('Failed to execute webhook action for itsi_group_id=%s', self.itsi_group_id)
            self.logger.exception(e)
            self.audit.send_activity_to_audit({
                'event_id': self.itsi_group_id,
                'itsi_policy_id': self.itsi_policy_id
            }, 'Webhook "{0}" failed. Error: {1}'.format(self.webhook_name, str(e)), 'Webhook action failed')
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        input_params = sys.stdin.read()
        webhook = Webhook(input_params)
        webhook.execute()
