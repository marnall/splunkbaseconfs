from typing import Dict, List, Union

COL1 = "message"
COL2 = "_raw"

HELP_ALL_PAYLOAD: Dict[str, Union[List[Dict[str, Union[str, int, Dict[str, str]]]], str]] = {
    "help_all_payload": [
        {
            COL1: '"| queryai help=all" ================================> Help with all the available `queryai` command options and sub-options.',
            COL2: '"| queryai help=all" ================================> Help with all the available `queryai` command options and sub-options.',
        },
        {
            COL1: '"| queryai help=events" =============================> List all the available OCSF events supported by Query.',
            COL2: '"| queryai help=events" =============================> List all the available OCSF events supported by Query.',
        },
        {
            COL1: '"| queryai help=entities" =============================> List all the searchable entities, i.e. field types of interest in events.',
            COL2: '"| queryai help=entities" =============================> List all the searchable entities, i.e. field types of interest in events.',
        },
        {
            COL1: '"| queryai help=connectors" =========================> List the connectors that have been configured in your environment for your data sources.',
            COL2: '"| queryai help=connectors" =========================> List the connectors that have been configured in your environment for your data sources.',
        },
        {
            COL1: '"| queryai help=OCSF_Event_name" ===> For the given OCSF event, get its schema structure, its attributes, and their data types. This helps get an in-depth understanding of that particular event.',
            COL2: '"| queryai help=OCSF_Event_name" ===> For the given OCSF event, get its schema structure, its attributes, and their data types. This helps get an in-depth understanding of that particular event.',
        },
        {
            COL1: '"| queryai help=search" =============================> Understand federated search\'s query syntax along with example queries. Also understand how to limit searching to specific events and connectors.',
            COL2: '"| queryai help=search" =============================> Understand federated search\'s query syntax along with example queries. Also understand how to limit searching to specific events and connectors.',
        },
    ]
}


HELP_SEARCH_PAYLOAD: Dict[str, List[Dict[str, Union[str, int, Dict[str, str]]]]] = {
    "help_search_payload": [
        {
            COL1: "\"| queryai search='<search conditions>'\" ============================================================================> Syntax of a basic search. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide",
            COL2: "\"| queryai search='<search conditions>'\" ============================================================================> Syntax of a basic search. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide",
        },
        {
            COL1: '"| queryai search=*" ============================================================================> Search all events without filters. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide',
            COL2: '"| queryai search=*" ============================================================================> Search all events without filters. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide',
        },
        {
            COL1: '"| queryai events=*" ============================================================================> Search all events without filters. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide',
            COL2: '"| queryai events=*" ============================================================================> Search all events without filters. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide',
        },
        {
            COL1: "\"| queryai events='network_activity, process_activity'\" ============================================================================> Search events network_activity and process_activity without filters. Similarly, other preferred event names can be provided as a comma separated values. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide",
            COL2: "\"| queryai events='network_activity, process_activity'\" ============================================================================> Search events network_activity and process_activity without filters. Similarly, other preferred event names can be provided as a comma separated values. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide",
        },
        {
            COL1: "\"| queryai search='network_activity.action_id=DENIED'\" =========> Search all the network_activity events where action_id is DENIED.",
            COL2: "\"| queryai search='network_activity.action_id=DENIED'\" =========> Search all the network_activity events where action_id is DENIED.",
        },
        {
            COL1: "\"| queryai search='file_hash = b5045d802394f4560280a7404af69263' exclude_connectors='entraId, Crowdstrike'\" =========> `exclude_connectors` queries all connectors except the ones specified.",
            COL2: "\"| queryai search='file_hash = b5045d802394f4560280a7404af69263' exclude_connectors='entraId, Crowdstrike'\" =========> `exclude_connectors` queries all connectors except the ones specified.",
        },
        {
            COL1: "\"| queryai search='hostname = abc.xyz' events='security_finding, http_activity'\" ==========================================> `events` sub-option lets you filter out all other event classes, except the ones you list.",
            COL2: "\"| queryai search='hostname = abc.xyz' events='security_finding, http_activity'\" ==========================================> `events` sub-option lets you filter out all other event classes, except the ones you list.",
        },
        {
            COL1: "\"| queryai search='process_name = xyz.exe' exclude_events='email_activity, http_activity'\" ================================> `exclude_events` sub-option lets you filter out your provided list of event classes from search results.",
            COL2: "\"| queryai search='process_name = xyz.exe' exclude_events='email_activity, http_activity'\" ================================> `exclude_events` sub-option lets you filter out your provided list of event classes from search results.",
        },
        {
            COL1: "\"| queryai search='ip = 1.1.1.1' connectors='S3, elastic, sentinel'\" ==============================================> Search for events with the given ip entity in the mentioned connectors.",
            COL2: "\"| queryai search='ip = 1.1.1.1' connectors='S3, elastic, sentinel'\" ==============================================> Search for events with the given ip entity in the mentioned connectors.",
        },
        {
            COL1: "\"| queryai search='ip = 1.1.1.1' exclude_connectors='Crowdstrike'\" =======================================================> Search for events matching the given ip entity. The 'exclude_connectors' ensures that `Crowdstrike` connector won't be searched.",
            COL2: "\"| queryai search='ip = 1.1.1.1' exclude_connectors='Crowdstrike'\" =======================================================> Search for events matching the given ip entity. The 'exclude_connectors' ensures that `Crowdstrike` connector won't be searched.",
        },
        {
            COL1: "\"| queryai connectors='<conn1, conn2, ...>'\" ============================================================================> Search for all the events in the selected connectors. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide",
            COL2: "\"| queryai connectors='<conn1, conn2, ...>'\" ============================================================================> Search for all the events in the selected connectors. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide",
        },
        {
            COL1: "\"| queryai exclude_connectors='<conn1, conn2, ...>'\" ============================================================================> Search for all the events in all the connectors except the mentioned connectors. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide",
            COL2: "\"| queryai exclude_connectors='<conn1, conn2, ...>'\" ============================================================================> Search for all the events in all the connectors except the mentioned connectors. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide",
        },
        {
            COL1: "\"| queryai exclude_events='<event1, event2, ...>'\" ============================================================================> Search for all the events except mentioned events in all the connectors. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide",
            COL2: "\"| queryai exclude_events='<event2, event2, ...>'\" ============================================================================> Search for all the events except mentioned events in all the connectors. For more operators and condition logic, see https://docs.query.ai/docs/splunk-app-quick-reference-guide",
        },
    ]
}
