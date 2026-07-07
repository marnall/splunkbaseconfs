# This file contains possible settings you can use to upload sample
# KPI threshold templates to the KV store.
#
# There is an itsi_kpi_threshold_template.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default. To set custom
# configurations, place an itsi_kpi_threshold_template.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/local.
# You must restart ITSI to enable new configurations.
#
# To learn more about configuration files (including precedence), see the
# documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles.

[<kpi_threshold_template>]
* Each stanza represents a KPI threshold template.
* Use threshold templates to build your time policies.
* You can create different policies with different time block
  combinations, such as work hours, off hours, or weekends.

title = <string>
* The title of the KPI threshold template.

description = <string>
* A description of the KPI threshold template.

time_variate_thresholds_specification = <JSON>
* A JSON blob containing the detailed time variant threshold object.

acl = <JSON>
* A JSON blob containing the ACL information for the KPI threshold template.
* Use the following format:
     {
        "perms":{
           "read":[
               <LIST_OF_ROLES>
           ],
           "write":[
               <LIST_OF_ROLES>
           ]
        },
        "can_share_user":[true|false],
        "can_share_app":[true|false],
        "modifiable":[true|false],
        "sharing":["app"|"global"],
        "can_change_perms":[true|false],
        "can_share_global":[true|false],
        "owner": <OWNER_NAME_STRING>,
        "can_write":[true|false]
     }

time_variate_thresholds = [True|False]
* Whether to enable time-variate thresholds.
* Time-variate thresholds accommodate normal variations in usage across
  your services and improve the accuracy of KPI and service health scores.
* For example, a time-variate threshold might take into account higher levels
  of usage during work hours, and lower levels of usage during off-hours
  and weekends.
* Default: True

adaptive_thresholding_training_window = <-7|-14|-30|-60>[d]
* The time window over which historical KPI data is analyzed for
  adaptive threshold updates.
* You must have 7 days of summary data in the summary index for
  adaptive thresholding to work properly.
* Default: -7 days

adaptive_thresholds_is_enabled = [True|False]
* Whether to enable adaptive thresholding for policies in time-variate thresholds.
* Adaptive thresholding lets you create time polices that generate thresholds
  dynamically and update daily based on changes in your data.
* If you set this value to "true", the 'time_variate_thresholds' setting must
  also be set to "true".
* Default: False
