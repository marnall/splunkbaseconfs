import os
from configparser import ConfigParser
import splunk.entity as entity

class SplunkConfig:
    def __init__(self, script_location=None):
        self.script_location = script_location or os.path.dirname(os.path.abspath(__file__))
        self.splunk_paths = self.give_splunk_paths()

    def give_splunk_paths(self):
        """
        Determines various paths related to Splunk based on the script's location.
        """
        try:
            splunk_home_dir = os.environ.get('SPLUNK_HOME')
            if not splunk_home_dir:
                raise EnvironmentError("SPLUNK_HOME environment variable is not set.")

            splunk_apps_dir = os.path.normpath(os.path.join(splunk_home_dir, "etc", "apps"))
            app_name = self.script_location.replace(splunk_apps_dir + os.sep, "").split(os.sep, 1)[0]
            app_root_dir = os.path.normpath(os.path.join(splunk_apps_dir, app_name))

            return {
                'splunk_home_dir': splunk_home_dir,
                'splunk_apps_dir': splunk_apps_dir,
                'app_name': app_name,
                'app_root_dir': app_root_dir,
                'current_dir': self.script_location
            }
        except Exception as e:
            raise RuntimeError(f"Failed to determine Splunk paths: {str(e)}")

    def get_config(self, conf_file, stanza=None, option=None):
        """
        Reads and retrieves a specific configuration option from a Splunk config file.
        """
        try:
            app_dir = self.splunk_paths['app_root_dir']

            if not conf_file.endswith(".conf"):
                conf_file += ".conf"

            default_file = os.path.normpath(os.path.join(app_dir, "default", conf_file))
            local_file = os.path.normpath(os.path.join(app_dir, "local", conf_file))

            config = ConfigParser()
            files_read = config.read([default_file, local_file])

            if not files_read:
                raise FileNotFoundError(f"Configuration files not found: {default_file}, {local_file}")

            if stanza and not config.has_section(stanza):
                raise KeyError(f"Stanza '{stanza}' not found in configuration files.")

            if option and not config.has_option(stanza, option):
                raise KeyError(f"Option '{option}' not found in stanza '{stanza}'.")

            return config.get(stanza, option)
        except Exception as e:
            print(f"Error in get_config: {str(e)}")
            return None

    def get_credentials(self, username=None, app="-", session_key=None):
        """
        Retrieves credentials for the provided username from Splunk.
        """
        if app in [None, '', '-']:
            app = self.splunk_paths['app_name']

        try:
            entities = entity.getEntities(
                ['admin', 'passwords'],
                namespace=app,
                owner='nobody',
                sessionKey=session_key,
                count='-1'
            )
        except Exception:
            raise Exception(f"Could not get credentials for {app} from Splunk.")
        
        for c in entities.values():
            if c['username'] == username:
                return c['clear_password']

        return "NO_PASSWORD_FOUND_FOR_THIS_USER"
