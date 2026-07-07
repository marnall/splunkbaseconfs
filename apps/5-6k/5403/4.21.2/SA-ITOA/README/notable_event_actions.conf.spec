# This file contains attributes and values for taking actions on episodes
# in Episode Review.
#
# There is a notable_event_actions.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place a notable_event_actions.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local/. You must restart Splunk to enable
# configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

####
# GLOBAL SETTINGS
####
#  Use the [default] stanza to define any global settings.
#  * You can also define global settings outside of any stanza, at the top
#    of the file.
#  * Each conf file should have at most one default stanza. If there are
#    multiple default stanzas, attributes are combined. In the case of
#    multiple definitions of the same attribute, the last definition in the
#    file wins.
#  * If an attribute is defined at both the global level and in a specific
#    stanza, the value in the specific stanza takes precedence.

disabled = <boolean>
* Disable a notable event action by setting to 1.
* Optional.
* Default: 0

is_group_compatible = <boolean>
* Make an action available for episodes by setting to 1.
* Default: 1

is_bulk_compatible = <boolean>
* Make an action available for bulk episodes by setting to 1.
* Default: 0

run_bulk_action_iteratively = <boolean>
* If set to "1", bulk episode actions run iteratively rather than simultaneously.
* This value only takes effect if the ‘is_bulk_compatible’ setting is set to "1".
* For custom ServiceNow add-ons, this setting must be set to "1"  in order
  for bulk episode actions to function properly.
* Default: 0

max_retries = <integer>
* Number of retries for the actions to run if the action fails
* Default: 2

retry_interval = <integer>
* Sleep between the retries of the actions in seconds
* Default: 5

[<action_name>]
* Each stanza represents an episode action. The action name
  is the type of action you want to configure.
* Options are email, script, itsi_sample_event_action_ping,
  itsi_event_action_link_ticket, webhook, snow_incident, remedy_incident, remedy_incident_rest.
* If the action is defined in alert_actions.conf, the action name should be the same.

execute_in_sync = <boolean>
* If 1, ITSI executes the action synchronously.
* The UI notifies you when the action is truly complete, rather
  than requiring you to check back later to confirm.
* It is recommended that you set this value to 1 for an external
  ticket created by a Splunk custom search command or modular alert.
* Default: 0

execute_once_per_group = <boolean>
* If 1, ITSI executes the action exactly once in the case of a
  bulk action.
* In special cases (like if this alert action has 'type' set to "external_ticket"),
  the result of a refresh is associated with all the events in the group.
* Default: 0

type = <string>
* The type of action to take on the episode.
* Use this setting if you are creating a ServiceNow or Remedy ticket from
  an episode.
* The only supported value for this setting is "external_ticket",
  which creates a ticket in the external ticketing system you choose.
* If you set the value to "external_ticket", ITSI runs a refresh action
  right after execution.
* The attribute-value pairs below are applicable when 'type' is "external_ticket".

app_name = <string>
* The name of the app or app-on that runs the action.
* This settings is used to fetch the app version if the alt_command setting is configured.

alt_command_supported_version = <string>
* The version of the app or add-on that supports the alt_command setting, if configured.

alt_command = <string>
* A search command to execute the action instead of the specified action_name.

ticket_system_name = <string>
* The name of the external ticketing system in which to create the ticket.

relative_refresh_uri = <string>
* A relative URI for the search head where ITSI is installed.
* https://localhost:8089/ or something similar is prepended to the URI.
* ITSI constructs this link so you can navigate directly to the
  external ticket.
* ITSI issues a GET call on this URI and outputs JSON data.
* 'refresh_response_json_path' indicates the path to walk through the
  received JSON output.
* Do not change this from the default value or refresh will not work.

relative_refresh_correlation_key = <string>
* The key used to query the relative_refresh_uri. You only need to change
  this value if the relative_refresh_uri setting doesn't accept the value of
  the 'correlation_key' setting as a query parameter.
* Default: correlation_id

correlation_key = <string>
* Optional. The query parameter to be appended to 'relative_refresh_uri'.
* The parameter is also saved in the KV store collection that contains
  all created tickets.
* Do not change this from the default value or refresh will not work.
* Default: correlation_id

correlation_value = <string>
* The key in the raw notable event whose value to append
  to the refresh URI.
* If a 'correlation_key' exists, ITSI appends this value to the
  refresh URI instead.
* Do not change this from the default value or refresh will not work.
* Default: $result.event_id$

correlation_value_for_group = <string>
* The key in the episode whose value to append
  to the refresh URI.
* By default, ITSI uses the value corresponding to `itsi_group_id'.
* Do not change this from the default value or refresh will not work.
* Default: $result.itsi_group_id$

refresh_response_json_path = <string>
* Because the JSON output of 'relative_refresh_uri' can be nested and
  complex, this setting indicates the path to walk through the received output.
* Do not change this from the default value or refresh will not work.
* Default: entry.{0}.content

refresh_response_ticket_id_key = <string>
* After traversing the JSON path specified in 'refresh_response_json_path'
  and fetching a JSON blob, the key corresponding to the external ticket ID.
* Do not change this from the default value or refresh will not work.

refresh_response_ticket_url_key = <string>
* After traversing the JSON path specified in 'refresh_response_json_path'
  and fetching a JSON blob, the key corresponding to the external ticket URL.
* Do not change this from the default value or refresh will not work.

bulk_max = <string>
* The maximum number of episodes that this action can be executed on.
* Default: 25

send_first_event_only = <boolean>
* Flag to include only the first event when sending an episode to Phantom.
* If 1, ITSI sends the first event of an episode to Phantom. Otherwise, ITSI sends all events in the episode.
* Default: 1

splunk_itsi_get_notables_search_api_page_size = <integer>
* The size of each page of results pulled from ITSI.
* Default: 50

phantom_artifacts_create_api_page_size = <integer>
* The size of each page of results pushed to Phantom from ITSI.
* Default: 50

num_parallel_job_slots = <integer>
* The number of slots in the ITSI backend to run parallel jobs for actions.
* Default: 5

job_refresh_interval = <integer>
* The interval, in seconds, that the backend checks for the status of parallel action jobs.
* Default: 2

job_timeout = <integer>
* The interval in milliseconds to wait before an action times out.
* Default: 2000

max_num_intervals = <integer>
* The maximum number of intervals to check for scheduled jobs.
* Default: 100

refresh_impact_tab = <boolean>
* Automatically reloads the Impact tab of an episode after an action runs. If set to "1", any tickets or reference
  links added by the action immediately appear on the Impact tab without having to refresh the page.
* Optional

max_retries = <integer>
* Number of retries for the actions to run if the action fails


retry_interval = <integer>
* Sleep between the retries of the actions in seconds
