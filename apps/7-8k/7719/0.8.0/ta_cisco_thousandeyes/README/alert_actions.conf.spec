############################################################################
# OVERVIEW
############################################################################
# This file contains descriptions of the settings to configure alert action for ThousandEyes.

[thousandeyes_forward_splunk_events]
param.public_host_url = <string>
* (Required) The public host url of Splunk instance
param.sampling_min_interval = <string>
* (Required) The minimum time interval between sampled ITSI events
param.sampling_track_changes = <string>
* (Required) Comma-separated list of ITSI event fields to monitor for changes and notify ThousandEyes
