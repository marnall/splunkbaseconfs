[global]
* #::HDR:: ;; * App: vmware_app_for_splunk ;; * File: savedsearches.conf.spec ;; * Updated: 2023-04-07 14:33:40
* ### Kill Process
action.vmware-kill-process                                  = [0|1]
* Enable vmware-kill-process Actions
action.vmware-kill-process.param.process_field              = <string>
action.vmware-kill-process.param.device_id_field            = <string>
action.vmware-kill-process.param._cam                       = <object>
* ### List Processes
action.vmware-list-process                                  = [0|1]
* Enable vmware-list-process Actions
action.vmware-list-process.param.device_id_field            = <string>
action.vmware-list-process.param._cam                       = <object>
* ### Quarantine Device
action.vmware-quarantine-device                             = [0|1]
* Enable vmware-quarantine-device Actions
action.vmware-quarantine-device.param.device_id_field       = <string>
action.vmware-quarantine-device.param._cam                  = <object>
* ### Un-Quarantine Device
action.vmware-unquarantine-device                           = [0|1]
* Enable vmware-unquarantine-device Actions
action.vmware-unquarantine-device.param.device_id_field     = <string>
action.vmware-unquarantine-device.param._cam                = <object>
* ### Add-IOC to Watchlist
action.vmware-add-ioc-watchlist                             = [0|1]
* Enable vmware-add-ioc-watchlist Actions
action.vmware-add-ioc-watchlist.param.watchlist             = <string>
action.vmware-add-ioc-watchlist.param.report_name           = <string>
action.vmware-add-ioc-watchlist.param.ioc_type              = <string>
action.vmware-add-ioc-watchlist.param.ioc_field             = <string>
action.vmware-add-ioc-watchlist.param.severity_field        = <string>
action.vmware-add-ioc-watchlist.param._cam                  = <object>
* ### Remove-IOC to Watchlist
action.vmware-remove-ioc-watchlist                          = [0|1]
* Enable vmware-remove-ioc-watchlist Actions
action.vmware-remove-ioc-watchlist.param.watchlist          = <string>
action.vmware-remove-ioc-watchlist.param.report_name        = <string>
action.vmware-remove-ioc-watchlist.param.ioc_field          = <string>
action.vmware-remove-ioc-watchlist.param._cam               = <object>
* ### Get File metadata
action.vmware-get-file-metadata                             = [0|1]
* Enable vmware-get-file-metadata Actions
action.vmware-get-file-metadata.param.hash_field            = <string>
action.vmware-get-file-metadata.param._cam                  = <object>
* ### Ban Hash
action.vmware-ban-hash                                      = [0|1]
* Enable vmware-ban-hash Actions
action.vmware-ban-hash.param.hash_field                     = <string>
action.vmware-ban-hash.param._cam                           = <object>
* ### Enrich Files
action.vmware-enrich-events                                 = [0|1]
* Enable vmware-enrich-events Actions
action.vmware-enrich-events.param.alert_id_field            = <string>
action.vmware-enrich-events.param._cam                      = <object>
* ### Run LiveQuery
action.vmware-run-livequery                                 = [0|1]
* Enable Live Query actions
action.vmware-run-livequery.param.livequery_name            = <string>
action.vmware-run-livequery.param.sql_query                 = <string>
action.vmware-run-livequery.param.device_ids                = <string>
action.vmware-run-livequery.param.device_os                 = <string>
action.vmware-run-livequery.param.policy_name               = <string>
action.vmware-run-livequery.param._cam                      = <object>
* ### Close Alert
action.vmware-close-alert                                   = [0|1]
* Enable Close Alert Actions
action.vmware-close-alert.param.alert_id                    = <string>
action.vmware-close-alert.param._cam                        = <object>
* ### Update Device Policy
action.vmware-update-device-policy                          = [0|1]
* Enable Update Device Policy Actions
action.vmware-update-device-policy.param.device_id          = <string>
action.vmware-update-device-policy.param.policy_id          = <string>
action.vmware-update-device-policy.param._cam               = <object>
* ### Process guid details
action.vmware-process-guid-details                          = [0|1]
* Enable Process Guid Actions
action.vmware-process-guid-details.param.process_guid_field = <string>
action.vmware-process-guid-details.param._cam               = <object>
action.vmware-enrich-alert-obs                              = [0|1]
* VMwareCBC Enrich Alert Observations
action.vmware-enrich-alert-obs.param._cam                   = <object>
* Common Alert Model configuration object.
action.vmware-enrich-alert-obs.param.alert_id_field         = <string>
* Enter the field that contains the Alert ID
action.vmware-enrich-alert-obs.param.org_key_field          = <string>
action.vmware-alert-history                                 = [0|1]
* VMware CBC Alert History
action.vmware-alert-history.param._cam                      = <object>
* Common Alert Model configuration object.
action.vmware-alert-history.param.alert_id_field            = <string>
* Enter the field that contains the Alert ID
action.vmware-alert-history.param.org_key_field             = <string>