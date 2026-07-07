# Mothership REST audit
### mothership/environments
This endpoint returns all environments described in environments.conf and can be used to create a new environment.	
* **Supported GET request params:**
    * `skip_metrics_search`: A performance flag that determines if the request will run an internal Splunk metrics search. If the flag is enabled (skip_metrics_search=0), the following fields [network_error_count_sparkline, most_recent_environment_status] will be populated in the response, otherwise (skip_metrics_search=1), they will all be populated by empty strings. (valid values -> [0, 1]).
    * `poller_metrics_earliest_time`: The amount of time in seconds that internal metric searches will lookback. Default is the configurable poller_metrics_earliest_time stored in mothership.conf. The default value in mothership.conf is 90000 seconds (25 hours).

* **Supported POST request params (create):**
    * `name`: **Required.** The human readable name for the environment. This name should be unique across existing environments.
    * `mgmt_scheme_host_port`: **Required.** The URI of the environment that includes the management scheme, hostname, and the Splunk management port. (Ex. https://example.demo.com:8089).
    * `splunk_web_uri`: **Required.** The URI that provides a hyperlink to Splunk web for the environment.
    * `username`: **Required.** The username of the remote Splunk environment.
    * `password`: **Required.** The password for the provided username of the remote Splunk environment.
    * `tags`: A comma separated list of tags for an instance.
    * `search_templates`: A comma separated list of valid search template lik alternates. Each template in this list will be applied as an enabled environment search with default settings to the created environment.

* **Response fields:**
    ***For each environment in environments.conf:***
    * `environment_id`: The link alternate of the environments.conf entry for the environment. 
    * `mgmt_scheme_host_port`: The URI of the environment that includes the management scheme, hostname, and the Splunk management port. (Ex. https://example.demo.com:8089).
    * `most_recent_environment_status`: A flag signifying the status of the environment based off of the most recent environment search run against the environment. Mapping of returned value to actual meaning is as follows {"0": "Down", "1": "Up", "": "No environment search run in searched time range"}.
    * `network_error_count_sparkline`: A Splunk sparkline showing count of network errors over the last x period of time. X is the poller_metrics_earliest_time described in mothership.conf.
    * `splunk_web_uri`: The URI that provides a hyperlink to Splunk web for the environment.
    * `tags`: A comma seperated list of tags for an instance. 
    * `title`: The environments.conf stanza name for this environment.
    * `username`: The username of the remote Splunk environment.

### mothership/environments/{name}
This endpoint returns the configuration of the environment with the provided {name} as it is described in environments.conf and can be used to update the environment with the provided {name}.
* **Supported GET request params:**
    * `skip_metrics_search`: A performance flag that determines if the request will run an internal Splunk metrics search. If the flag is enabled (skip_metrics_search=0), the following fields [network_error_count_sparkline, most_recent_environment_status] will be populated in the response, otherwise (skip_metrics_search=1), they will all be populated by empty strings. (valid values -> [0, 1]).
    * `poller_metrics_earliest_time`: The amount of time in seconds that internal metric searches will lookback. Default is the configurable poller_metrics_earliest_time stored in mothership.conf. The default value in mothership.conf is 90000 seconds (25 hours).

* **Supported POST request params (update):**
    * `splunk_web_uri`: The URI that provides a hyperlink to Splunk web for the environment.
    * `username`: The username of the remote Splunk environment.
    * `password`: The password for the provided username of the remote Splunk environment.
    * `tags`: A comma seperated list of tags for an instance. The provided list will overwrite any existing list of tags for the environment with the provided {name}.

* **Response fields:**
	* `environment_id`: The link alternate of the environments.conf entry for the environment.
	* `mgmt_scheme_host_port`: The URI of the environment that includes the management scheme, hostname, and the Splunk management port. (Ex. https://example.demo.com:8089).
	* `most_recent_environment_status`: A flag signifying the status of the environment based off of the most recent environment search run against the environment. Mapping of returned value to actual meaning is as follows {"0": "Down", "1": "Up", "": "No environment search run in searched time range"}.
	* `network_error_count_sparkline`: A Splunk sparkline showing count of network errors over the last x period of time. X is the poller_metrics_earliest_time described in mothership.conf.
	* `splunk_web_uri`: The URI that provides a hyperlink to Splunk web for the environment.
	* `tags`: A comma seperated list of tags for an instance. 
	* `title`: The environments.conf stanza name for this environment.
    * `username`: The username of the remote Splunk environment.

### mothership/environment_searches
This endpoint returns all environment searches described in environment_searches.conf and can be used to create a new environment search.
* **Supported GET request params:**
	* `skip_metrics_search`: A performance flag that determines if the request will run an internal Splunk metrics search. If the flag is enabled (skip_metrics_search=0), the following fields [job_run_duration, script_run_duration, script_run_time, results_count, results_count_sparkline, report_search] will be populated in the response, otherwise (skip_metrics_search=1), they will all be populated by empty strings. (valid values -> [0, 1]).
    * `poller_metrics_earliest_time`: The amount of time in seconds that internal metric searches will lookback. Default is the configurable poller_metrics_earliest_time stored in mothership.conf. The default value in mothership.conf is 90000 seconds (25 hours).

* **Supported POST request params:**
    * `name`: **Required.** A GUID that uniquely identifies an environment search.
    * `environment_id`: **Required.** The link alternate of the environment this environment search will run on.
    * `search`: **Required.** - This field contains either the link alternate of an existing search template (described in search_templates.conf), or an SPL search string. The type field must match the type provided to this field.
    * `type`: **Required.** - The type of search string provided. Etiher an existing search template, or an inline SPL search string. (valid values -> [inline, template]).
    * `label`: A human readable name for the environment search. This value will be displayed in the environment search table in the environment management table. (default -> GUID provided to name).
    * `disabled`: A boolean value the describes whether or not the environment search will be run. (default -> False) (valid values -> [True, False]).
    * `interval`: An integer describing the time in seconds between each remote search being executed. (default -> 300 seconds).
    * `index`: The index where non-transforming events returned by a remote search will be written. (default -> Automatically generate an index).

* **Response fields:**
	***For each environment search in environment_searches.conf:***
	* `environment_id`: The link alternate of the environment this environment search will run on.
	* `environment_name`: The name of the environment this environment search will run on.
	* `index_event_max_time`: The oldest event in index described in this environment search's environment_searches.conf entry.
    * `index_current_db_size_mb`: The size of the index described in this environment search's environment_searches.conf entry.
	* `index_event_min_time`: The freshest event in the index described in this environment search's environment_searches.conf entry.
    * `index_total_event_count`: The total number of events in the index described in this environment search's environment_searches.conf entry.
	* `hec_global_disabled`: The global status of HEC on the Splunk environment Mothership is installed on.
	* `hec_token_enabled`: The status of the HEC token described in this environment search's environment_searches.conf entry.
	* `hec_token_link_alternate`: The link alternate of the HEC token described in this environment search's environment_searches.conf entry.
	* `hec_token_name`: The name of the HEC token described in this environment search's environment_searches.conf entry.
	* `hec_token_value`: The value of the HEC token described in this environment search's environment_searches.conf entry.
	* `index`: The name of the index this environment search will write raw events to.
	* `input_link_alternate`: The link alternate of the input described in this environment search's environment_searches.conf entry.
	* `interval`: The interval in seconds that this environment search will run on.
	* `job_run_duration`: The duration of the Splunk search on the remote environment in the most recent run of this environment search's scripted input.
	* `label`: The human readable name for the environment search.
	* `lookup_link_alternate`: The link alternate of the lookup described in this environment search's environment_searches.conf entry.
	* `lookup_name`: The name of the lookup described in this environment search's environment_searches.conf entry.
	* `mgmt_scheme_host_port`: The URI containing the Splunk management port of the remote Splunk environment.
	* `report_search`: Describes if this search is a reporting/transforming search which is written to a lookup, or a non-transforming search which return raw results written to an index. {"0": non-transforming/non-reporting search, "1": transforming/reporting search, "": No environment search run in searched time range}.
	* `results_count`: The count of results returned by the most recent run of this environment search's scripted input.
	* `results_count_sparkline`: A Splunk sparkline of results returned by the environment search over the last x period of time. X is the poller_metrics_earliest_time described in mothership.conf.
	* `script_run_duration`: The duration of the most recent run of this environment search's scripted input (includes the remote Splunk search time).
	* `script_run_time`: The most recent time this environment search was run. 
	* `search`: This field contains either the link alternate of an existing search template (described in search_templates.conf), or an SPL search string.
	* `search_string`: The SPL search string, derived either from the search field if this environment search is of type inline, otherwise derived from the search template.
	* `splunk_web_uri`: The URI that provides a hyperlink to Splunk web for the environment described in this environment search's environment_searches.conf entry.
	* `type`: The type of this environment search, either a search template or an inline SPL search string.
	* `username`: The username of the remote Splunk environment described in this environment search's environment_searches.conf entry.

### mothership/environment_searches/{name}
This endpoint returns the configuration of the environment search with the provided {name} as it is described in environment_searches.conf and can be used to update the environment search with the provided {name}.
* **Supported GET request params:**
	* `skip_metrics_search`: A performance flag that determines if the request will run an internal Splunk metrics search. If the flag is enabled (skip_metrics_search=0), the following fields [job_run_duration, script_run_duration, script_run_time, results_count, results_count_sparkline, report_search] will be populated in the response, otherwise (skip_metrics_search=1), they will all be populated by empty strings. (valid values -> [0, 1]).
    * `poller_metrics_earliest_time`: The amount of time in seconds that internal metric searches will lookback. Default is the configurable poller_metrics_earliest_time stored in mothership.conf. The default value in mothership.conf is 90000 seconds (25 hours).

* **Supported POST request params:**
    * `environment_id`: **Required.** The link alternate of the environment this environment search will run on.
    * `search`: **Required.** - This field contains either the link alternate of an existing search template (described in search_templates.conf), or an SPL search string. The type field must match the type provided to this field.
    * `type`: **Required.** - The type of search string provided. Etiher an existing search template, or an inline SPL search string. (valid values -> [inline, template])
    * `label`: A human readable name for the environment search. This value will be displayed in the management table. (default -> current label).
    * `disabled`: A boolean value the describes whether or not the environment search will be run. (default -> current disabled status) (valid values -> [True, False]).
    * `interval`: An integer describing the time in seconds between each remote search being executed. (default -> current interval).
    * `index`: The index where non-transforming events returned by a remote search will be written. (default -> current index).

* **Response fields:**
	* `environment_id`: The link alternate of the environment this environment search will run on.
	* `environment_name`: The name of the environment this environment search will run on.
	* `index_event_max_time`: The oldest event in index described in this environment search's environment_searches.conf entry.
    * `index_current_db_size_mb`: The size of the index described in this environment search's environment_searches.conf entry.
	* `index_event_min_time`: The freshest event in the index described in this environment search's environment_searches.conf entry.
    * `index_total_event_count`: The total number of events in the index described in this environment search's environment_searches.conf entry.
	* `hec_global_disabled`: The global status of HEC on the Splunk environment Mothership is installed on.
	* `hec_token_enabled`: The status of the HEC token described in this environment search's environment_searches.conf entry.
	* `hec_token_link_alternate`: The link alternate of the HEC token described in this environment search's environment_searches.conf entry.
	* `hec_token_name`: The name of the HEC token described in this environment search's environment_searches.conf entry.
	* `hec_token_value`: The value of the HEC token described in this environment search's environment_searches.conf entry.
	* `index`: The name of the index this environment search will write raw events to.
	* `input_link_alternate`: The link alternate of the input described in this environment search's environment_searches.conf entry.
	* `interval`: The interval in seconds that this environment search will run on.
	* `job_run_duration`: The duration of the Splunk search on the remote environment in the most recent run of this environment search's scripted input.
	* `label`: The human readable name for the environment search.
	* `lookup_link_alternate`: The link alternate of the lookup described in this environment search's environment_searches.conf entry.
	* `lookup_name`: The name of the lookup described in this environment search's environment_searches.conf entry.
	* `mgmt_scheme_host_port`: The URI containing the Splunk management port of the remote Splunk environment.
	* `report_search`: Describes if this search is a reporting/transforming search which is written to a lookup, or a non-transforming search which return raw results written to an index. {"0": non-transforming/non-reporting search, "1": transforming/reporting search, "": No environment search run in searched time range}.
	* `results_count`: The count of results returned by the most recent run of this environment search's scripted input.
	* `results_count_sparkline`: A Splunk sparkline of results returned by the environment search over the last x period of time. X is the poller_metrics_earliest_time described in mothership.conf.
	* `script_run_duration`: The duration of the most recent run of this environment search's scripted input (includes the remote Splunk search time).
	* `script_run_time`: The most recent time this environment search was run. 
	* `search`: This field contains either the link alternate of an existing search template (described in search_templates.conf), or an SPL search string.
	* `search_string`: The SPL search string, derived either from the search field if this environment search is of type inline, otherwise derived from the search template.
	* `splunk_web_uri`: The URI that provides a hyperlink to Splunk web for the environment described in this environment search's environment_searches.conf entry.
	* `type`: The type of this environment search, either a search template or an inline SPL search string.
	* `username`: The username of the remote Splunk environment described in this environment search's environment_searches.conf entry.

### mothership/configs/conf-environment_search_templates
This endpoint returns all environment search templates described in environment_search_templates.conf and can be used to create a new environment search template.
* **Supported GET request params:**
	* `No non-standard GET params supported.`

* **Supported POST request params:**
	* `name`: **Required.** The human readable name of the search template. Also the conf entry stanza.
	* `search_string`: **Required.** An SPL search string.

* **Response fields:**
	***For each environment search template in environment_search_templates.conf.***
	* `search_string`: An SPL search string.
    * `title`: The human readable name of the search template. Also the conf entry stanza.

### mothership/configs/conf-environment_search_templates/{name}
This endpoint returns the configuration of the environment search template with the provided {name} as it is described in environment_search_templates.conf and can be used to update the environment search template with the provided {name}.
* **Supported GET request params:**
	* `No non-standard GET params supported.`

* **Supported POST request params:**
	* `search_string`: An SPL search string.

* **Response fields:**
	* `search_string`: An SPL search string.
    * `title`: The human readable name of the search template. Also the conf entry stanza.
