{
    "results_link": <Required> <String> Link to Splunk web UI.
    "result":{ <Required> <Nested Object> Non-deterministic set of key/value pairs. Given the fact Splunk is schema-less and searches can mutate fields can be added or removed.
        "_raw": <Optional> <String> Raw event string in un-altered state. Core field for non-transforming search commands.
        "_time": <Optional> <String> Splunk extracted normalized time. Core index level field for non-transforming and transforming search commands that are based on time.
        "source": <Optional> <String> Core index level field for non-transforming search commands.
        "sourcetype": <Optional> <String> Core index level field for non-transforming search commands.
        "host": <Optional> <String> Core index level field for non-transforming search commands.
        "_*": <Optional> <String> Internal/Hidden fields for non-transforming and transforming search commands.
    },
    "app": <Required> <String> The Splunk app namespace/context of origin search.
    "server_uri": <Required> <String> The Splunk REST Management server.
    "configuration":{ <Required> <Object>
        "severity": <Required> <Enum String> Low, Medium, High, "Very High"
    },
    "owner": <Required> <String> The scheduled alert owner. NOTE: Saved Searches can be alerts in Splunk.
    "search_name": <Required> <String> The scheduled alert name. NOTE: Saved Searches can be alerts in Splunk.
    "__AGENT__":"SPLUNK_SAP_ETD_ALERT_ACTION_V1.0.0", <Required> <Constant String> A hard coded constant string for the SAP ETD classifier.
    "results_file": <Required> <String> The search results artifact on disk.
    "search_uri": <Required> <String> The alert object REST reference.
    "server_host": <Required> <String> The Splunk origin hostname.
    "sid": <Required> <String> The Splunk asyncronous search id reference.
}
