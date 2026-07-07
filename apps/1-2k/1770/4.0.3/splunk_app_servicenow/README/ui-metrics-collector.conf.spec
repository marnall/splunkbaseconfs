# This file contains possible attributes and values you can use to configure
# `ui-metrics-collector`.
#
# To set custom configurations, place a ui-metrics-collector.conf in
# $SPLUNK_HOME/etc/apps/<your_app>/local/. For examples, see ui-metrics-collector.conf.example.
# You must restart Splunk to enable configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/Splunk/latest/Admin/Aboutconfigurationfiles

[partyjs]
* Set Party.js configuration options under this stanza name.
* Follow this stanza name with any number of the following attribute/value
  pairs.
* If you do not specify an entry for each attribute, default value will be used.

apiKey = <mint_key_string>
* The MINT App key

[collector]
mode = [On | Off | None]
* The mode of analytics data collection with Party.js.
*   On       - users optted in, data will be collected.
*   Off      - users optted out, data will not be collected.
*   None     - awaiting users opt in or out, data will not be collected.
* Defaults to None.
* Values are case insensitive

app_id = <uuid_string>
* A UUID used to identify the Splunk App instance.
* This will be generated automatically when the Splunk user opts in the first time.

networkCallFilters = <filters_string>
* URL patterns used to filter network call collection.
* If the URL of a network call matches one of the patterns listed in this config item,
* that network call will not be collected.

dedupInterval.<tag_name_string> = <integer>
* defines an interval of an event by its tag. Each Collector methods supports a `tag` option. If the `tag` option is used, and an interval value is set for that tag, then, events with the same tag won't be able to be sent more than once in a period defined by the interval value.

[views]
learn_more_link = <string>
* the learn more link id

[restapi]
index_volumes_endpoint = <string>
* the endpoint of the index volumes REST API, the default value is "ui-metrics-collector/ui_metrics_collector_index_volumes".
