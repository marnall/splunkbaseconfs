"""Discover app environment."""
import re
import json
import requests
from requests.exceptions import HTTPError, Timeout, SSLError, ConnectionError
import platform


class lazy_property(object):
    """Meant to be used for lazy evaluation of an object attribute.

    Property should represent non-mutable data, as it replaces itself.
    """

    def __init__(self, fget):
        """Initialize."""
        self.fget = fget
        self.func_name = fget.__name__

    def __get__(self, obj, cls):
        """Return the property."""
        if obj is None:
            return None
        value = self.fget(obj)
        setattr(obj, self.func_name, value)
        return value


class RfeAppEnv(object):  # pylint: disable=too-many-instance-attributes
    """Store various environment info."""

    def __init__(self, in_dict, logger):
        """Discover the environment.

        The returned object has the following attributes:
          alerts      - a dict (key = alert config) of dicts (key = entry)
          api_key     - the API key
          api_url     - the URL to the Recorded Future api
          app_config  - the app.conf config as a dict of dicts
          app_name    - the name of the app (TA_recordedfuture-cyber)
          checkpoint_name - the name of the checkpoint object
          identifier  - how the app will identify itself during API calls
          integration_version - the version number of this integration
          log_level   - the log level to use
          my_config   - a config dict (key = section) of dicts (key = entry)
          platform    - the platform.platform string (ex
                       Linux-4.10.0-37-generic-x86_64-with-Ubuntu-17.04-zesty
          proxy       - proxy settings if any
          risklists   - a dict (key = risklist) of dicts (key = entry)
          splunk_es_version - the version of the ES app
          splunk_version - the version of the Splunk server
          system      - the platform.system string (Windows/Linux...)
          verify      - do SSL verification
        """
        object.__init__(self)
        self.logger = logger
        # Session_key and Management host and port
        self.session_key = in_dict['system_authtoken']
        self.server_uri = in_dict['server']['rest_uri']

        self.in_dict = in_dict

        self.app_name = 'TA_recordedfuture-cyber'
        self.checkpoint_name = 'TA_recordedfuture_cyber_checkpointer'
        # Read my own config
        conf_file = 'recordedfuture_settings.conf'
        self.my_config = self.read_config(conf_file)

        # RF api URL
        self.api_url = self.my_config['settings']['recorded_future_api_url']

        # RF API Token
        self.api_key = self._get_api_key()

        # Log level
        self.log_level = self.my_config['logging']['loglevel']

        self.verify = True if \
            self.my_config['settings']['verify_ssl'] == '1' \
            else False

        # Configured inputs
        self.risklists = self._get_risklist_inputs()
        self.alerts = self._get_alert_inputs()

        # integration_version, the identifier when doing API queries
        self.app_config = self.read_config('app.conf')
        self.integration_version = self.app_config \
            .get('launcher').get('version')
        self.package_id = self.app_config.get('package').get('id')
        self.identifier = '%s %s' % (self.package_id,
                                     self.integration_version)
        self.platform = platform.platform()
        self.system = platform.system()

        # Proxy settings (if any)
        if self.my_config['proxy']['proxy_enabled'] == '1':
            self.logger.debug('Proxy is enabled.')
            self.proxy = {
                'proxy_username': self.my_config['proxy'].get('proxy_username',
                                                              ''),
                'proxy_password': self.get_proxy_password(),
                'proxy_port':
                    self.my_config['proxy'].get('proxy_port', ''),
                'proxy_url':
                    self.my_config['proxy'].get('proxy_url', ''),
                'proxy_type': 'http'}
        else:
            self.proxy = {}

    def rest_call(self, path_info, search_query=None):
        """Call local REST endpoint."""
        try:
            baseurl = '%s%s%s' % (
                self.server_uri,
                '/servicesNS/nobody/%s' % self.app_name,
                path_info)
            self.logger.debug('baseurl = %s', baseurl)
            headers = {'Authorization': 'Splunk %s' % self.session_key}
            params = {'output_mode': 'json'}
            if search_query is None:
                job = requests.get(baseurl,
                                   headers=headers,
                                   params=params,
                                   verify=False)
            else:
                job = requests.post(baseurl,
                                    headers=headers,
                                    data={'search': search_query,
                                          'output_mode': 'json',
                                          'exec_mode': 'oneshot'},
                                    verify=False)
            return job.json()
        except HTTPError as err:
            self.logger.error('HTTP Error: %s', str(err))
        except Timeout as err:
            self.logger.error('Request timed out: %s', str(err))
        except SSLError as err:
            self.logger.error('SSL Error: %s', str(err))
        except ConnectionError as err:
            self.logger.error('Connection error: %s', str(err))

    @lazy_property
    def proxies(self):
        """Return a properly formatted dict for use in requests."""
        if self.proxy == {}:
            return {}

        if self.proxy.get('proxy_username', '') != '':
            proxy_auth = '%s:%s@' % (self.proxy['proxy_username'],
                                     self.proxy['proxy_password'])
        else:
            proxy_auth = ''

        if ':' in self.proxy['proxy_url']:
            proxy_host = self.proxy['proxy_url']
            if not proxy_host.startswith('['):
                proxy_host = '[' + proxy_host
            if not proxy_host.endswith(']'):
                proxy_host = proxy_host + ']'
            proxy_url = '%s://%s%s:%s' % (self.proxy['proxy_type'],
                                          proxy_auth,
                                          proxy_host,
                                          self.proxy['proxy_port'])
        else:
            proxy_url = '%s://%s%s:%s' % (self.proxy['proxy_type'],
                                          proxy_auth,
                                          self.proxy['proxy_url'],
                                          self.proxy['proxy_port'])
        return {
            'http': proxy_url,
            'https': proxy_url
        }

    def read_config(self, filename):
        """Read a configuration file using Splunk REST API."""
        blob = self.rest_call('/configs/conf-%s' % filename[:-5])
        returndata = {}
        for entry in blob['entry']:
            section = entry['name']
            returndata[section] = {}
            for k, v in entry['content'].items():
                if 'eai:' not in k:
                    returndata[section][k] = v
        return returndata

    def _get_risklist_inputs(self):
        """Return all configured risk lists.

        Returns a dict keyed on risklist stanza where each value is a
        dict with each key/value.
        """
        returndata = {}
        for k, v in self.my_config.items():
            if k.startswith('risk_list://'):
                section = k.split('://')[1]
                returndata[section] = v
        return returndata

    def _get_alert_inputs(self):
        """Return all configured alert retrieval profiles.

        Returns a dict keyd on alert retrieval profile where each value is a
        dict with each key/value.
        """
        returndata = {}
        for k, v in self.my_config.items():
            if k.startswith('alert://'):
                section = k.split('://')[1]
                returndata[section] = v
        return returndata

    @lazy_property
    def splunk_version(self):
        """Return the version of Splunk."""
        base_url = '%s%s' % (
            self.server_uri,
            '/services/server/info')
        headers = {'Authorization': 'Splunk %s' % self.session_key}
        params = {'output_mode': 'json'}
        req = requests.get(base_url,
                           headers=headers,
                           params=params,
                           verify=False)
        try:
            return req.json()['entry'][0]['content']['version']
        except Exception:
            return 'version_undisclosed'

    @lazy_property
    def splunk_minor_version(self):
        """Return the minor version of Splunk."""
        try:
            vsplunk = re.match(
                r'(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)',
                self.splunk_version).groupdict()
            if vsplunk is not None:
                return '{}.{}'.format(vsplunk['major'], vsplunk['minor'])
            else:
                return 'version_undisclosed'
        except Exception:
            return 'version_undisclosed'

    @lazy_property
    def splunk_es_version(self):
        """Return the version of Splunk ES."""
        base_url = '%s%s' % (
            self.server_uri,
            '/services/apps/local')
        headers = {'Authorization': 'Splunk %s' % self.session_key}
        params = {'output_mode': 'json'}
        req = requests.get(base_url,
                           headers=headers,
                           params=params,
                           verify=False)
        if req.ok:
            try:
                for app in req.json()['entry']:
                    if app['name'] == 'SplunkEnterpriseSecuritySuite':
                        return app['content']['version']
            except Exception:
                return 'version_undisclosed'
        return 'version_undisclosed'

    def _get_encrypted_passwords(self):
        """Make a REST call to the local Splunk server to get a password."""
        base_url = '%s%s%s%s' % (
            self.server_uri,
            '/servicesNS/nobody/%s/storage/passwords/' % self.app_name,
            self.app_name, ':encrypted_passwords:')
        headers = {'Authorization': 'Splunk %s' % self.session_key}
        params = {'output_mode': 'json'}
        req = requests.get(base_url, headers=headers, params=params,
                           verify=False)
        if req.status_code not in [200, 2001]:
            self.logger.error('Password access failed: %s', req.text)
            return None
        self.logger.info('Successfully accessed the passwords store.')
        return json.loads(req.json()['entry'][0]
                          ['content']['clear_password'])

    def _set_encrypted_password(self, name, cleartext):
        """Store a password in the password storage facility.

        The cleartext password is actually a dict with keys api_key
        and proxy_password. The name parameter indicates which of the keys
        to update.
        """
        current = self._get_encrypted_passwords()
        data = {'realm': self.app_name,
                'name': 'encrypted_passwords'
                }
        if current:
            self.logger.debug('Already exists encrypted passwords, updating.')
            current[name] = cleartext
            data = {'password': json.dumps(current)}
            base_url = '%s%s%s%s' % (
                self.server_uri,
                '/servicesNS/nobody/%s/storage/passwords/' % self.app_name,
                self.app_name, ':encrypted_passwords:')
        else:
            self.logger.debug('No passwords stored previously, creating.')
            data['password'] = json.dumps({name: cleartext})
            base_url = '%s%s' % (
                self.server_uri,
                '/servicesNS/nobody/%s/storage/passwords/' % self.app_name)
        headers = {'Authorization': 'Splunk %s' % self.session_key}
        params = {'output_mode': 'json'}
        req = requests.post(base_url, data, headers=headers,
                            params=params, verify=False)
        if req.status_code not in [200, 201]:
            self.logger.error('Failed to store passwords: %s', req.text)
            req.raise_for_status()
        self.logger.info('Successfully stored password')
        return True

    def set_api_key(self, api_key):
        """Set the API key."""
        return self._set_encrypted_password('api_key', api_key)

    def set_proxy_password(self, password):
        """Set the proxy password."""
        return self._set_encrypted_password('proxy_password', password)

    def _get_api_key(self):
        """Fetch the API key."""
        try:
            api_key = self._get_encrypted_passwords()
            return api_key.get('api_key', None)
        except HTTPError as err:
            return None
        except AttributeError as err:
            return None

    def get_proxy_password(self):
        """Fetch the proxy password."""
        password = self._get_encrypted_passwords()
        if password:
            return password.get('proxy_password', '')
        return ''
