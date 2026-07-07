TA_NAME = 'TA_ms_advanced_hunting'
APP_NAME = 'TA_ms_advanced_hunting'
SETTINGS_CONF_NAME = "ta_ms_advanced_hunting_settings"
ACCOUNT_CONF_NAME = "ta_ms_advanced_hunting_account"
TOKEN_REALM = "ms_advhunt_token"

# '__REST_CREDENTIAL__#TA_ms_advanced_hunting#configs/conf-ta_ms_advanced_hunting_account
REST_REALM = f'__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{ACCOUNT_CONF_NAME}'

SEP = '``splunk_cred_sep``'

READ_TIMEOUT=60
CONNECTION_TIMEOUT=10
RETRY_NUM=0
