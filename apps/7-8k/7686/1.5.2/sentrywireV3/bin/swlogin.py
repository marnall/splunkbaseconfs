from sentrywire.client import Sentrywire
from swstorage import SentryWireStore
import time, json, sys, os
from swutils import *
from swconst import *

try:
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
    from splunklib import client
except ImportError as e:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "lib"))
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
    from splunklib import client

@Configuration()
class SentrywireLoginCommand(StreamingCommand):
    host = Option(require=True, validate=validators.Match("host", ".*"))
    username = Option(require=True, validate=validators.Match("username", ".*"))
    password = Option(require=True, validate=validators.Match("password", ".*"))

    def stream(self, events):
        logger = setup_logging()

        splunk_user = self._metadata.searchinfo.username
        session_key = self._metadata.searchinfo.session_key

        debug_extras = {
            'splunk_user': splunk_user, 
            'sentrywire_user': self.username, 
            'sentrywire_host': self.host, 
            'debug_mode': SENTRYWIRE_DEBUG_MODE
            }

        if SENTRYWIRE_DEBUG_MODE:
            logger.warning("Debug mode is enabled! This disables SSL checks!", extra=debug_extras)
        
        # Sentrywire authentication handling
        try:
            sw = Sentrywire(host=self.host, ssl_verify=(not SENTRYWIRE_DEBUG_MODE))
            logger.info("Initialized SentryWire wrapper", extra=debug_extras)
        except Exception as e:
            debug_extras["error"] = e
            logger.error("Failed to initialize SentryWire wrapper", extra=debug_extras)
            raise e

        # Authenticate with SentryWire
        if not ((response := sw.login(username=self.username, password=self.password)).status_code == 200):
            msg = f"Failed to authenticate with SentryWire host"
            debug_extras["server_response"] = response.json()
            logger.error(msg, extra=debug_extras)
            raise msg

        # Parse Authentication Token
        try:
            sw_token = (json.loads(response.content.decode('utf-8'))).get("rest_token")
            host_with_sw_token = f"{self.host}:{sw_token}"
            logger.info(f"Authenticated with SentryWire as '{self.username}@{self.host}'", extra=debug_extras)
        except Exception as e:
            debug_extras["error"] = e
            logger.error("Failed to parse SentryWire response", extra=debug_extras)
            raise e

        # Splunk password storage handling
        service = client.connect(token=session_key, app='sentrywireV3', owner=splunk_user)
        logger.info(f"Authenticated with Splunk using session key", extra=debug_extras)

        try:
            storage_passwords = service.storage_passwords
        except Exception as e:
            logger.error(f"Failed to load stored passwords", extra=debug_extras)
            raise e

        # De-authorize existing token
        try:
            if (stale_token := get_encrypted_token(storage_passwords, splunk_user)):
                sw.logout(rest_token=stale_token.split(':')[-1])
                logger.info(f"De-authorized existing SentryWire", extra=debug_extras)
        except KeyError:
            pass

        # Delete token from password store if it exists
        try:
            storage_passwords.delete(username=splunk_user, realm=SECRET_REALM)
            logger.info(f"Removed existing SentryWire token for '{self.username}@{self.host}' from password store")
        except KeyError:
            pass
        except Exception as e:
            logger.error(f"Failed to remove stale token for '{splunk_user}' from password store: {e}")
            raise e

        # Store new SentryWire token
        try:
            storage_passwords.create(password=host_with_sw_token, username=splunk_user, realm=SECRET_REALM)

            # Verify credentials were stored properly
            if not (get_encrypted_token(storage_passwords, splunk_user)):
                raise Exception("Failed save step verification")

            logger.info(f"Added SentryWire token for '{self.username}@{self.host}' to password store")
        except Exception as e:
            logger.error(f"Splunk user '{splunk_user}' failed to store SentryWire Token: {e}")
            raise e
        
        yield {'_time': time.time(), 'event_no': 0, '_raw': f"Username {self.username} accepted."}

        
try:
    dispatch(SentrywireLoginCommand, sys.argv, sys.stdin, sys.stdout, __name__)
except Exception as e:
    print(str(e))