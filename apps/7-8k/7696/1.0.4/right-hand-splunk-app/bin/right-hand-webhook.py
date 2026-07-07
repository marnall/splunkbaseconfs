import os
import sys
import json
from urllib.error import HTTPError
import splunk
import logging
import splunklib.client as client
from urllib.request import urlopen, Request
from logging.handlers import RotatingFileHandler


def setup_logging():
    logger = logging.getLogger('splunk.right-hand-hrm-app')    
    SPLUNK_HOME = os.environ['SPLUNK_HOME']

    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "right-hand-hrm-app.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a'
    ) 
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger


BASE_URL = "https://hrm.api.right-hand.ai"
ENDPOINT = "/api"
WEBHOOK_URL = BASE_URL + ENDPOINT
HEADERS = {
    'Authorization': "",
    'Content-Type': 'application/json'
}
logger = setup_logging()


def handle_exception(msg):
    def decorator(fn):
        def inner(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception:
                logger.exception(msg)
                sys.exit(1)
        return inner
    return decorator


class RightHandWebhook:
    def __init__(self, payload, **kwargs):
        self.payload = payload
        self.client = self.get_client(self.payload)

    @handle_exception("Failed to get splunk client")
    def get_client(self, payload):
        return client.connect(
                host="127.0.0.1",
                port="8089",
                token=payload.get('session_key'),
                app=payload.get('app'),
                owner='nobody',
                sharing="app"
            )

    @handle_exception("failed to fetch auth token from splunk")
    def retrieve_api_token(self):
        storage_passwords = self.client.storage_passwords
        for storage_password in storage_passwords.list():
            if storage_password.username == 'rh_token':
                return storage_password.clear_password

    @handle_exception("failed to send request to webhook")
    def send_data(self, payload, api_token):
        api_token = (api_token or "").strip()
        if not api_token:
            raise ValueError("missing API token")

        HEADERS['Authorization'] = api_token
        request = Request(
            WEBHOOK_URL,
            json.dumps(payload).encode('ascii'),
            HEADERS
        )
        try:
            with urlopen(request) as response:
                logger.info(f"received response {response.status}")
        except HTTPError as e:
            raise RuntimeError(f"request to webhook failed with status {e.code}") from e

        if not (200 <= response.status < 300):
            raise RuntimeError(f"request to webhook failed with status {response.status}")

    @handle_exception("modalert execution failed")
    def execute(self):
        api_token = self.retrieve_api_token()
        data = self.payload.get('result')
        if data is None or not isinstance(data, dict):
            raise ValueError("invalid payload: expected result dictionary")
        self.send_data(data, api_token)


@handle_exception("main process broke")
def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        modular_alert = RightHandWebhook(payload)
        modular_alert.execute()
        sys.exit(0)
    else:
        logger.error("Unsupported execution mode (expected --execute flag)")
        sys.exit(1)


if __name__ == '__main__':
    main()
