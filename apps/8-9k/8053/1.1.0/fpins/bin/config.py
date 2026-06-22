import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

SPLUNK_APP_NAME = 'fpins'


def build_proxies_dict(proxy):
    """Build proxies dict for requests library. Sets both http and https
    to the same proxy URL so all outbound traffic is routed through it.
    Returns None if no proxy is configured.
    """
    if not proxy:
        return None
    return {'http': proxy, 'https': proxy}


class Config(object):
    def __init__(self):
        self.api_key = None
        self.api_token = None  # Add token field
        self.insights_base_url = None
        self.instance_id = None
        self.platform_base_url = None
        self.sessionKey = None
        self.proxies = None
        self.sync_interval = None
        self.pp_config = {}

    def LoadCredentials(self, appName=SPLUNK_APP_NAME):
        """
        Access the credentials in /servicesNS/nobody/<YourApp>/storage/passwords
        """
        try:
            import splunklib.client as client
            undersplunksdk = True
        except ImportError:
            undersplunksdk = False
        # Try getting the session key
        if undersplunksdk and self.sessionKey is None:
            # Get the session key
            sessionKey = sys.stdin.readline().strip()
            if sessionKey == 'None' or sessionKey == '':
                logging.error('Splunk app "%s": No session key found' % appName)
                return False
            self.sessionKey = sessionKey
        try:
            # List all credentials
            args = {'token': self.sessionKey, 'app': appName, 'owner': 'nobody'}
            service = client.connect(**args)
            storage_passwords = service.storage_passwords
        except NameError as e:
            # Not under Splunk SDK?
            logging.warning('Splunk app "%s": No client: %s' % (appName, e))
            logging.error(
                'The Splunk SDK Python modules (like client.py in the above message) must be present in the environment along with this app. '
            )
            return False
        except Exception as e:
            raise Exception('Splunk app "%s": Error while getting credentials: %s' % (appName, e))

        if len(storage_passwords.list()) == 0:
            logging.warning('Splunk app "%s": No credentials found' % appName)
            return False

        # Return LAST set of credentials

        api_key = ''
        proxies = ''
        api_token = ''
        try:
            for storage_password in storage_passwords.list():
                username = storage_password.username
                if username == 'proxies':
                    proxies = storage_password.clear_password
                elif username == 'api_key':
                    api_key = storage_password.clear_password
                elif username == 'api_token':
                    api_token = storage_password.clear_password
        except BaseException as e:
            logging.warning('Splunk app "%s": Error while getting credentials: %s' % (appName, e))
            return False

        if api_key not in ['', '__notset__']:
            self.api_key = api_key
        if proxies not in ['', '__notset__']:
            self.proxies = proxies
        if api_token not in ['', '__notset__']:
            self.api_token = api_token
        return True

    def StoreToken(self, token, appName=SPLUNK_APP_NAME):
        """
        Store the API token in storage/passwords under username 'api_token'.
        """
        try:
            import splunklib.client as client
        except ImportError:
            logging.error('Splunk SDK not available for storing token.')
            return False
        if self.sessionKey is None:
            sessionKey = sys.stdin.readline().strip()
            if sessionKey == 'None' or sessionKey == '':
                logging.error('No session key found for storing token.')
                return False
            self.sessionKey = sessionKey
        try:
            args = {'token': self.sessionKey, 'app': appName, 'owner': 'nobody'}
            service = client.connect(**args)
            storage_passwords = service.storage_passwords
            # Delete old token if exists
            for sp in storage_passwords:
                if sp.username == 'api_token':
                    sp.delete()
            # Create new token
            storage_passwords.create(token,'api_token', realm='')
            logging.info('API token stored in Splunk storage/passwords.')
            return True
        except Exception as e:
            logging.error(f'Error storing API token: {e}')
            return False

    def LoadConfiguration(self, appName=SPLUNK_APP_NAME):
        """
        Use Splunk api to override forward config params
        """
        # Try getting creds first
        try:
            if not self.LoadCredentials(appName):
                return False
        except Exception as e:
            logging.error('Unexpected error getting credentials: %s' % e)
            return False

        try:
            from splunk.clilib import cli_common as cli
        except ImportError:
            logging.error('Splunk app "%s": No cli_common module found' % appName)
            return False


        try:
            cfg = cli.getConfStanza('appsetup', 'app_config')
            self.insights_base_url = f"https://{cfg.get('insights_base_url')}"
            self.platform_base_url = f"https://{cfg.get('platform_base_url')}"
            self.sync_interval = cfg.get('sync_interval') or cfg.get('interval')
            self.instance_id = cfg.get('instance_id')
            pp_config_raw = cfg.get('pp_config', '')
            if pp_config_raw:
                try:
                    self.pp_config = json.loads(pp_config_raw)
                except Exception:
                    logging.error('Failed to parse pp_config JSON')
                    self.pp_config = {}

            # Backward compat: if pp_config is empty but old collection_names exists,
            # build pp_config with SSE (old app only supported SSE)
            if not self.pp_config:
                old_collections = cfg.get('collection_names', '')
                old_exported = cfg.get('exported_fields', 'all')
                if old_collections:
                    cols = [x.strip() for x in old_collections.split(',') if x.strip()]
                    if cols:
                        self.pp_config = {
                            "SSE": {
                                "exportedFields": old_exported,
                                "collections": cols
                            }
                        }
                        logging.info('Built pp_config from old collection_names for backward compatibility')

        except Exception as e:
            logging.error('Splunk app "%s" error while getting configuration params: %s' % (appName, e))
            return False

        if (self.api_key is None or self.api_key == ''):
            logging.error('Splunk app "%s": No valid authentication options available, please run the setup page' % appName)
            return False
        logging.info('LoadConfiguration SUCCESS')
        return True
