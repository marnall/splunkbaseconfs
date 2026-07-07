import ta_threatquotient_add_on_declare
import os

VERIFY_SSL = True           # Default: True. Change this to False if certificate validation is not required.
VERIFY_SSL_KVSTORE = False  # Default: False. This will be used for internal calls to KV store.

CERT_FILE_LOC = os.path.join(
    os.environ.get('SPLUNK_HOME'),
    'etc',
    'apps',
    ta_threatquotient_add_on_declare.ta_name,
    'local',
    'cac_certs',
    'custom_cert.pem',
)
KEY_FILE_LOC = os.path.join(
    os.environ.get('SPLUNK_HOME'),
    'etc',
    'apps',
    ta_threatquotient_add_on_declare.ta_name,
    'local',
    'cac_certs',
    'custom_key.pem',
)
