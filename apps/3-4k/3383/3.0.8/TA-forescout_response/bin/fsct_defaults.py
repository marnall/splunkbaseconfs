"""
fs_defaults.py

Define all ForeScout-Splunk integration defaults in this file.
"""

# ForeScout's Splunk App names
FS_TA_APP_NAME           = 'TA-forescout'
FS_TA_RESPONSE_APP_NAME  = 'TA-forescout_response'
FS_TA_RESPONSE_APP_LABEL = 'ForeScout Adaptive Response Add-on for Splunk'

# TA setup details
FS_TA_SETUP_CONF_FILE   = 'fsctsetup'
FS_TA_SETUP_CONF_STANZA = 'fsct_config'
FS_TA_INDEX_KEY         = 'fsct_index'
FS_TA_EMIP_KEY          = 'fsct_emip'
FS_TA_CALLBACKID_KEY    = 'fsct_callbackid'
FS_TA_USESSL_KEY        = 'usessl'
FS_TA_VERIFYCERT_KEY    = 'verifycert'

# json file containing CounterACT alerts actions info
FS_ACTIONS_DISPOSITION_MAPPING_FILE = 'action_disposition_mapping.json'

# Supported CounterACT actions
FS_SUPPORTED_ACTION_NAMES = (
	'recheck_host',
	'http_notification',
	'browser_redirection',
	'balloon_message',
	'sendmail',
	'sendmailtohost_ad_mail',
	'block_bridging',
	'cloud_app_kill',
	'im_kill',
	'p2p_kill',
	'sw_block',
	'adaptive_response_test',
	'sw_access_port_acl_priority',
	'sw_acl',
	'sw_quarantine',
	'dot1x_authorize',
	'wifi_block',
	'wifi_assign',
	'vpn_block',
	'virtual-fw-rule'
)