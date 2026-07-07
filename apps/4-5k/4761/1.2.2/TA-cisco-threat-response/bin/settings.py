import json

CONFIGURATION_FILE = "ta_cisco_threat_response_settings"
STANZA = 'additional_parameters'
REALM = "__REST_CREDENTIAL__#TA-cisco-threat-response" \
        "#configs/conf-ta_cisco_threat_response_settings"

ENCRYPTED_PASSWORD_PLACEHOLDER = u'********'


class SettingsConfigurationError(Exception):
    """ Raised when settings can't be gotten. """
    def __init__(self, key):
        super(SettingsConfigurationError, self).__init__(
            'Failed to get any configuration value for "{}" from the settings.'
            ' Please make sure to specify it.'.format(
                Settings.key_external(key)
            )
        )


class SettingsAttributeError(SettingsConfigurationError):
    """ Raised when wrong setting name specified. """
    pass


class CredentialsConfigurationError(Exception):
    """ Raised when credentials can't be gotten """
    pass


class BaseSettings(object):
    """ Wraps configurations. """

    def __init__(self, configurations):
        self._settings = configurations

    def __getitem__(self, key):
        key = str(key)
        try:
            return self._settings[key]
        except (AttributeError, KeyError):
            raise SettingsAttributeError(key)
        except Exception:
            raise SettingsConfigurationError(key)

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except SettingsAttributeError:
            return default


class CredentialsSettings(BaseSettings):
    """ Gets clear passwords for settings from the storage. """

    def __init__(self, configurations, storage_passwords, password_keys):
        super(CredentialsSettings, self).__init__(configurations)
        self._password_keys = password_keys
        self._storage_passwords = storage_passwords
        self._passwords_map = None

    def __getitem__(self, key):
        key = str(key)
        value = super(CredentialsSettings, self).__getitem__(key)

        if (key in self._password_keys
                and value == ENCRYPTED_PASSWORD_PLACEHOLDER):
            value = self.passwords_map.get(key)

        return value

    @property
    def passwords_map(self):
        if self._passwords_map is None:

            credentials = next(
                (cred for cred in self._storage_passwords
                 if cred.realm == REALM
                 and cred.username.startswith(STANZA)),
                None
            )

            if not credentials:
                msg = 'Failed to get credentials for realm {} user {}'
                raise CredentialsConfigurationError(msg.format(REALM, STANZA))

            self._passwords_map = json.loads(credentials.clear_password)

        return self._passwords_map


class Settings(CredentialsSettings):
    """ Provides the settings from the add-on configuration page. """

    def __init__(self, configurations, storage_passwords):
        super(Settings, self).__init__(configurations, storage_passwords,
                                       ['client_password',
                                        'proxy_password'])

        self._proxy_url = None

    @property
    def proxy_enabled(self):
        return bool(int(self['proxy_enabled']))

    @property
    def proxy_url(self):
        """ URL format: http[s]://[username[:password]@]host[:port] . """

        if not self.proxy_enabled:
            return None

        if not self._proxy_url:

            credentials = None
            username = self.get('proxy_username')

            if username:
                credentials = username

                password = self.get('proxy_password')
                if password:
                    credentials = credentials + ':' + password

            port = self.get('proxy_port')
            self._proxy_url = '{type}://{credentials}{host}{port}'.format(
                type=self['proxy_type'],
                credentials=credentials + '@' if credentials else '',
                host=self['proxy_url'],
                port=':' + port if port else ''
            )

        return self._proxy_url

    @staticmethod
    def key_external(key_internal):
        if key_internal == 'client_id':
            return 'Client ID'
        return key_internal.replace('_', ' ').title()
