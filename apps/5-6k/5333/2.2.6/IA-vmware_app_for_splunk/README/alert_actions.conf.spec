* #::HDR:: ;; * App: vmware_app_for_splunk ;; * File: alert_actions.conf.spec ;; * Updated: 2023-04-07 14:33:40

[vmware-kill-process]
param._cam            = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant          = <value>
* The VmWare tenant configuration to use
param.proxy_guid      = <value>
* The Proxy Guid to use
param.verify_ssl      = <value>
* Verify SSL
param.debug_cbapi     = <value>
* Set to "enable" if debug is required.
param.process_field   = <string>
param.device_id_field = <string>
maxtime               = <string>

[vmware-list-process]
param._cam            = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant          = <value>
* The VmWare tenant configuration to use
param.proxy_guid      = <value>
* The Proxy Guid to use
param.verify_ssl      = <value>
* Verify SSL
param.debug_cbapi     = <value>
* Set to "enable" if debug is required.
param.device_id_field = <string>
maxtime               = <string>

[vmware-quarantine-device]
param._cam            = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant          = <value>
* The VmWare tenant configuration to use
param.proxy_guid      = <value>
* The Proxy Guid to use
param.verify_ssl      = <value>
* Verify SSL
param.debug_cbapi     = <value>
* Set to "enable" if debug is required.
param.device_id_field = <string>

[vmware-unquarantine-device]
param._cam            = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant          = <value>
* The VmWare tenant configuration to use
param.proxy_guid      = <value>
* The Proxy Guid to use
param.verify_ssl      = <value>
* Verify SSL
param.debug_cbapi     = <value>
* Set to "enable" if debug is required.
param.device_id_field = <string>

[vmware-add-ioc-watchlist]
param._cam           = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant         = <value>
* The VmWare tenant configuration to use
param.watchlist      = <value>
* The VMware watchlist to put the IOC
param.report_name    = <value>
* The VMware field to use for the report name in the watchlist
param.ioc_field      = <value>
* The VMware field to use for the IOC
param.ioc_type       = <value>
* The VMware field to use for the IOC type
param.org_key_field  = <value>
* The VMware field to use for the org key in the feed
param.severity_field = <value>
* The VMware field to use for the severity for the IOC
param.proxy_guid     = <value>
* The Proxy Guid to use
param.verify_ssl     = <value>
* Verify SSL
param.debug_cbapi    = <value>
* Set to "enable" if debug is required.

[vmware-remove-ioc-watchlist]
param._cam        = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant      = <value>
* The VmWare tenant configuration to use
param.watchlist   = <value>
* The VMware watchlist to put the IOC
param.report_name = <value>
* The VMware field to use for the report name in the watchlist
param.ioc_field   = <value>
* The VMware field to use for the IOC
param.proxy_guid  = <value>
* The Proxy Guid to use
param.verify_ssl  = <value>
* Verify SSL
param.debug_cbapi = <value>
* Set to "enable" if debug is required.

[vmware-get-file-metadata]
param._cam        = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant      = <value>
* The VmWare tenant configuration to use
param.proxy_guid  = <value>
* The Proxy Guid to use
param.verify_ssl  = <value>
* Verify SSL
param.debug_cbapi = <value>
* Set to "enable" if debug is required.
param.hash_field  = <string>

[vmware-ban-hash]
param._cam        = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant      = <value>
* The VmWare tenant configuration to use
param.proxy_guid  = <value>
* The Proxy Guid to use
param.verify_ssl  = <value>
* Verify SSL
param.debug_cbapi = <value>
* Set to "enable" if debug is required.
param.hash_field  = <string>
* Set the hash field name

[vmware-run-livequery]
param._cam           = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant         = <value>
* The VmWare tenant configuration to use
param.proxy_guid     = <value>
* The Proxy Guid to use
param.verify_ssl     = <value>
* Verify SSL
param.livequery_name = <value>
* The VMware LiveQuery name that should be used
param.sql_query      = <value>
* The VMware SQL query that should be run as a livequery
param.device_ids     = <value>
* The VMware device ids that the livequery should run against
param.policy_name    = <value>
* The VMware policy that the livequery should run against
param.device_os      = <value>
* The VMware device os that the livequery should run against
param.debug_cbapi    = <value>
* Set to "enable" if debug is required.

[vmware-close-alert]
param._cam        = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant      = <value>
* The VmWare tenant configuration to use
param.proxy_guid  = <value>
* The Proxy Guid to use
param.verify_ssl  = <value>
* Verify SSL
param.alert_id    = <value>
* The VMware alert ID that should be closed
param.debug_cbapi = <value>
* Set to "enable" if debug is required.

[vmware-update-device-policy]
param._cam        = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant      = <value>
* The VmWare tenant configuration to use
param.proxy_guid  = <value>
* The Proxy Guid to use
param.verify_ssl  = <value>
* Verify SSL
param.device_id   = <value>
* The VMware device ID that should be updated
param.policy_id   = <value>
* The VMware policy ID that should be assigned to the device ids
param.debug_cbapi = <value>
* Set to "enable" if debug is required.

[vmware-enrich-events]
param._cam            = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant          = <value>
* The VmWare tenant configuration to use
param.proxy_guid      = <value>
* The Proxy Guid to use
param.verify_ssl      = <value>
* Verify SSL
param.alert_id_field  = <value>
* The Alert ID Field to consume
param.debug_cbapi     = <value>
* Set to "enable" if debug is required.
param.process_field   = <string>
param.device_id_field = <string>
maxtime               = <string>

[vmware-process-guid-details]
param._cam               = <value>
* CIM Actions / Adaptive Response Requirement
param.tenant             = <value>
* The VmWare tenant configuration to use
param.proxy_guid         = <value>
* The Proxy Guid to use
param.verify_ssl         = <value>
* Verify SSL
param.process_guid_field = <value>
* The process GUID Field to consume
param.debug_cbapi        = <value>

[vmware-enrich-alert-obs]
param._cam           = <object>
* Common Alert Model configuration object.
param.alert_id_field = <string>
* Enter the field that contains the Alert ID
param.org_key_field  = <string>
param.tenant         = <value>
* The VmWare tenant configuration to use

[vmware-alert-history]
param._cam           = <object>
* Common Alert Model configuration object.
param.alert_id_field = <string>
* Enter the field that contains the Alert ID
param.org_key_field  = <string>
param.tenant         = <value>