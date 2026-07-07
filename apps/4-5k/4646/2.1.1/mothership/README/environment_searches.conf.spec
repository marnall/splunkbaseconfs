[mothership]
label = <label string>
* The label for the environment search that is not subject to a unique name constraint like name
search = <SPL search string OR template link alternate>
* The SPL of the search that will be run on the remote Splunk instance
environment_link_alternate = <link alternate>
* Splunk link alternate of environment conf stanza
type = <inline OR template>
* string signifying if search attribute is an inline search string or a template link alternate
hec_token_link_alternate = <link alternate>
* Splunk link alternate of token for sending data to the HTTP Event Collector
lookup_link_alternate = <link alternate>
* Splunk link alternate of the lookup used to store results from transforming searches
index_link_alternate = <link alternate>
* Splunk link alternate of the index used to store events from non-transforming searches
savedsearch_link_alternate = <link alternate>
* Splunk link alternate of the savedsearch used to query remote environments
