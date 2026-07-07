[admin:TA_puppet_alert_actions]
match = <string>
members = <comma-separated list>

[admin_external:TA_puppet_alert_actions_account]
handlertype = python
python.version = python3
handlerfile = <string>
handleractions = <comma-separated list>

[admin_external:TA_puppet_alert_actions_settings]
handlertype = python
python.version = python3
handlerfile = <string>
handleractions = <comma-separated list>
