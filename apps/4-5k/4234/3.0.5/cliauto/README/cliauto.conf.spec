# This file describes the cliauto.conf file that is included
# with the CLI Auto for Splunk app.
# 

# ---- Main Stanza ----
# Contains global, local, and UI variables for the app.
#
# ---- addon:<ip address> Stanzas ----
# Contains remote addon variables for the app.

[main]

index=main
* Splunk index to store results

sourcetype=cliauto_ssh
* Sourcetpye to store results to the Splunk index

source=cliauto
* Sourcetpye to store results to the Splunk index

local_addon_enable = <yes | no>
* localhost addon enable
* Set value to yes if the localhost is an addon server
* It is recommended to set value to no if the cliauto app is installed in a distributed or cluster Splunk environment

local_rest_port = 8089
* Splunk REST API Management port of local addon server

absolute_input_data_length_max = <number of characters>
* Absolute max length of data input strings of Custom REST API. Min = 1, Max = 2000.

max_host_count=2000
* The maximum number of hosts that are processed in a Node List file. Min = 1, Max = 5000. 

allow_duplicate_ip_address=no
* Allow duplicate ip address in node list

ui_search_job_status_interval=5
* UI time interval (seconds) to check job status.

ui_search_job_events_interval=5
* UI time interval (seconds) to search for job events.

ui_search_job_events_int_count=5
* UI number of intervals to search for job events.

ui_job_rows = <number of jobs>
* UI <number of jobs> (rows) in history to display from KVStore table.

default_input_data_length_max = <number of characters>
* Default max length of data input strings of Custom REST API. Min = 1, Max = 1000.

absolute_input_data_length_max = <number of characters>
* Absolute max length of data input strings of Custom REST API. Min = 1, Max = 2000.

allow_duplicate_ip_address = <no | yes>
* Allow duplicate ip address in node list

kex_verbose_level = <0 | 1 | 2 | 3>
* ssh key exchange verbose level for the "Check ssh Key Exchange" command type

kex_filter_regex = <regular expression>
* ssh key exchange regex filter for the "Check ssh Key Exchange" command type

ui_job_rows = <number of jobs>
* UI <number of jobs> (rows) in history to display from KVStore table.

ui_aoserver_title = <short description>
* UI Addon Server title (tooltip)

ui_jobid_title = <short description>
* UI Job ID title (tooltip)

ui_nodelist_title = <short description>
* UI NodeList title (tooltip)

ui_status_title = <short description>
* UI Status title (tooltip)

ui_pid_title = <short description>
* UI PID title (tooltip)

ui_timestamp_title = <short description>
* UI Timestamp title (tooltip)

ui_command_title = <short description>
* UI Command title (tooltip)

ui_starttime_title = <short description>
* UI Starttime title (tooltip)

ui_endtime_title = <short description>
* UI Endtime title (tooltip)

ui_scriptuser_title = <short description>
* UI Script User title (tooltip)

ui_sessionuser_title = <short description>
* UI Session User title (tooltip)

ui_hostcount_title = <short description>
* UI Host Count title (tooltip)

[addon:<ip address>]
* Addon stanzas define any remote servers with CLI Auto Add-on app installed
* Stanza name starts with "addon:" test and ends with url prefix to the addon server

addon_enable = <yes | no>
* Set value to yes to enable addon server

username = <username>
* Username to access remote addon server

description = <string>
* Description of Addon server in dropdown

rest_port = <port>
* Splunk REST API Management port of addon server

enable_authtoken = <yes | no>
* Enable authenication with token
* If enabled, disables authenication with username and password

authtoken = <yes | no>
* Splunk authenication token

