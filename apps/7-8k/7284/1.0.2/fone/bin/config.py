import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

SPLUNK_APP_NAME = 'fone'


class Config(object):
    def __init__(self):
        self.access_key_id = None
        self.secret_access_key = None
        self.log_action_types = []
        self.tenant_id = None
        self.access_point = None
        self.sessionKey = None
        self.proxies = None

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
        secret_access_key = ''
        proxies = ''
        try:
            for storage_password in storage_passwords.list():
                username = storage_password.username
                if username == 'proxies':
                    proxies = storage_password.clear_password
                else:
                    access_key_id = username
                    self.access_key_id = access_key_id
                    secret_access_key = storage_password.clear_password
        except BaseException as e:
            logging.warning('Splunk app "%s": Error while getting credentials: %s' % (appName, e))
            return False

        if secret_access_key not in ['', '__notset__']:
            self.secret_access_key = secret_access_key
        if proxies not in ['', '__notset__']:
            self.proxies = proxies
        return True

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

            self.log_action_types = []

            if int(cfg.get('all')):
                self.log_action_types.append(u'all')
            if int(cfg.get('notallowed')):
                self.log_action_types.append(u'notallowed')

            self.tenant_id = cfg.get('tenant_id')
            self.access_point = cfg.get('access_point')

        except Exception as e:
            logging.error('Splunk app "%s" error while getting configuration params: %s' % (appName, e))
            return False

        # Alarm right here if niether creds nor token available
        if (self.access_key_id is None or self.access_key_id == '' or self.secret_access_key is None or self.secret_access_key == ''):
            logging.error('Splunk app "%s": No valid authentication options available, please run the setup page' % appName)
            return False

        logging.info('LoadConfiguration SUCCESS')
        return True
