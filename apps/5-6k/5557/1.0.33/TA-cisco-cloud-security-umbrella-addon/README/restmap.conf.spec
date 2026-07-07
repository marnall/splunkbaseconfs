[admin:TA_cisco_cloud_security_umbrella_addon]
match = /
members = TA_cisco_cloud_security_umbrella_addon_settings, TA_cisco_cloud_security_umbrella_addon_cisco_cloud_security_umbrella_addon
python.version=python3
[admin_external:TA_cisco_cloud_security_umbrella_addon_settings]
handlertype = python
handlerfile = TA_cisco_cloud_security_umbrella_addon_rh_settings.py
handleractions = edit, list
python.version=python3

[admin_external:TA_cisco_cloud_security_umbrella_addon_cisco_cloud_security_umbrella_addon]
handlertype = python
handlerfile = TA_cisco_cloud_security_umbrella_addon_rh_cisco_cloud_security_umbrella_addon.py
handleractions = edit, list, remove, create
python.version=python3

[script:toc_functionality_ta]
match                 = /toc_functionality_ta
script                = toc_functionality_ta.py
scripttype            = persist
handler               = toc_functionality_ta.TocFunctionality
requireAuthentication = true
capability            = cs_admin
output_modes          = json
passPayload           = true
passHttpHeaders       = true
passHttpCookies       = true
python.version=python3