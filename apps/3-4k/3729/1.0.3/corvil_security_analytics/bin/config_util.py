from os.path import basename
from os.path import dirname

import splunk.bundle
import splunk.auth
import splunk.entity as entity
class SplunkConfig:
    namespaces = ['search', 'launcher', 'Corvil']

    def __init__(self):
        pass

class InputsConfig(SplunkConfig):
    MANDATORY_FIELDS = ["Hostname", "Port-Number", "Analytic-Stream-Name"]
    CONNECTOR_1_1_0_FIELDS = ["Use-Auth-Script", "Encrypted"]
    USERNAME = "Username"
    PASSWORD = "Password"
    AUTH_SCRIPT = "Auth-Script"
    USE_AUTH_SCRIPT = "Use-Auth-Script"
    ENCRYPTED = "Encrypted"

    def __init__(self, host, port, username, password, stream_name, auth_script, use_auth_script, encrypted):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.stream_name = stream_name
        self.auth_script = auth_script
        self.use_auth_script = use_auth_script
        self.encrypted = encrypted

    def __getitem__(self, item):
        return getattr(self, item)

    @staticmethod
    def get_all_configs(additional_namespaces=[], session_key=None):
        """
        Returns all the configs specified in Corvil Connector data input
        """
        app_config = AppConfig()
        app_name = app_config.name
        namespaces = SplunkConfig.namespaces + [app_name] + additional_namespaces
        configs = []
        for app in namespaces:
            try:
                config = InputsConfig.get_inputs_config(app, session_key)
                for source in config:
                    if all(field in config[source] for field in InputsConfig.MANDATORY_FIELDS): #Check if all the required fields are present in source
                        if InputsConfig.USERNAME and InputsConfig.PASSWORD in config[source]:
                            InputsConfig.get_configs_with_username_password(config[source], configs)
                        elif InputsConfig.AUTH_SCRIPT and InputsConfig.USE_AUTH_SCRIPT in config[source]:
                            InputsConfig.get_configs_with_auth_script(config[source], configs)
            except: # Couldn't find an inputs.conf in the namespace, continue to the next
                continue
        return configs

    @staticmethod
    def from_key_value(key, value, additional_namespaces=[], session_key=None):
        app_config = AppConfig()
        app_name = app_config.name
        namespaces = SplunkConfig.namespaces + [app_name] + additional_namespaces
        configs = []

        for app in namespaces:
            try:
                config = InputsConfig.get_inputs_config(app, session_key)
                for source in config:
                    if key in config[source] and config[source][key].lower() == value.lower():
                        if InputsConfig.USERNAME and InputsConfig.PASSWORD in config[source]:
                            InputsConfig.get_configs_with_username_password(config[source], configs)
                            break
                        elif InputsConfig.AUTH_SCRIPT and InputsConfig.USE_AUTH_SCRIPT in config[source]:
                            InputsConfig.get_configs_with_auth_script(config[source], configs)
                            break
            except: # Couldn't find an inputs.conf in the namespace, continue to the next
                continue
        return configs

    @staticmethod
    def from_source(source, additional_namespaces=[], session_key=None):
        return InputsConfig.from_key_value("source", source, additional_namespaces, session_key)

    @staticmethod
    def from_source_type(source_type, addition_namespaces=[], session_key=None):
        return InputsConfig.from_key_value("sourcetype", source_type, addition_namespaces, session_key)

    @staticmethod
    def from_host(host, additional_namespaces=[], session_key=None):
        return InputsConfig.from_key_value("Hostname", host, additional_namespaces, session_key)

    @staticmethod
    def get_configs_with_username_password(config_source, configs):
        """
        It appends InputsConfig containing host, port, username, password and stream_name to configs.
        """
        host        = config_source[InputsConfig.MANDATORY_FIELDS[0]]
        port        = config_source[InputsConfig.MANDATORY_FIELDS[1]]
        stream_name  = config_source[InputsConfig.MANDATORY_FIELDS[2]]
        username    = config_source[InputsConfig.USERNAME]
        password    = config_source[InputsConfig.PASSWORD]
        encrypted = config_source[InputsConfig.ENCRYPTED]
        if username and password and host and port and stream_name:
            configs.append(InputsConfig(host, port, username, password, stream_name, None, None, encrypted))

    @staticmethod
    def get_configs_with_auth_script(config_source, configs):
        """
        It appends InputsConfig containing host, port, stream_name, auth_script and use_auth_script to configs.
        """
        host        = config_source[InputsConfig.MANDATORY_FIELDS[0]]
        port        = config_source[InputsConfig.MANDATORY_FIELDS[1]]
        stream_name  = config_source[InputsConfig.MANDATORY_FIELDS[2]]
        auth_script = config_source[InputsConfig.AUTH_SCRIPT]
        use_auth_script = config_source[InputsConfig.USE_AUTH_SCRIPT]
        encrypted = config_source[InputsConfig.ENCRYPTED]
        if auth_script and use_auth_script and host and port and stream_name:
            configs.append(InputsConfig(host, port, None, None, stream_name, auth_script, use_auth_script, encrypted))

    @staticmethod
    def get_inputs_config(app, session_key=None):
        """
        Returns the config present in inputs.conf of provided app/namespace
        """
        if session_key:
            config = splunk.bundle.getConf('inputs', namespace=app, sessionKey=session_key, owner="-")
        else:
            config = splunk.bundle.getConf('inputs', namespace=app)
        return config

class PasswordsConfig(SplunkConfig):

    @staticmethod
    def get_password(username, additional_namespaces=[], session_key=None):
        """
        Returns clear text password for specific username
        """
        app_config = AppConfig()
        app_name = app_config.name
        namespaces = SplunkConfig.namespaces + [app_name] + additional_namespaces
        for app in namespaces:
            try:
                # list all credentials
                entities = entity.getEntities(['admin', 'passwords'], namespace=app, owner='nobody', sessionKey=session_key)
                for i,c in entities.items():
                    if c['username'] == username:
                        return c['clear_password']
            except: # Couldn't find credentials in the namespace, continue to the next
                continue
        raise Exception("No credentials found for username: %s" % username)

class AppConfig(SplunkConfig):
    def __init__(self):
        # Assumes structure of "$app/bin/ConfigUtil.py"
        self.name = basename(dirname(dirname(__file__)))
