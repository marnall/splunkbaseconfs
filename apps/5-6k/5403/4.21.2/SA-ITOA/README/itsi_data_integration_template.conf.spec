# This file contains possible attributes and values for uploading sample
# itsi_data_integration_template to the KV store.
#
# To upload default data integration template to the KV store, place an
# valid JSON data integration template into SA-ITOA/local/itsi_data_integration_template.conf
#
# You must restart Splunk software to enable configurations, unless you are
# editing them through the Splunk manager.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles
#
# WARNING: Manual editing of this file is not recommended. Contact Support before proceeding.

####
# GLOBAL SETTINGS
####
# Use the [default] stanza to define any global settings.
#   * You can also define global settings outside of any stanza, at the top
#     of the file.
#   * Each conf file should have at most one default stanza. If there are
#     multiple default stanzas, attributes are combined. In the case of
#     multiple definitions of the same attribute, the last definition in the
#     file wins.
#   * If an attribute is defined at both the global level and in a specific
#     stanza, the value in the specific stanza takes precedence.
[<name>]
* A name or primary identifier for the default data integration template

_key = <string>
* The identifier of the default template

title = <string>
* The title of data integration template that is displayed in the UI

data_source = <string>
* The name of the data integration

mapping_fields = <json>
* JSON list of the data integration mapping fields

mapping_field_options = <list>
* List of mapping field options

throttling_group_by_fields = <list>
* List of throttling group by fields

severity_id_mapping = <string>
* Case eval of vendor_severity to severity_id mapping

status_id_mapping = <string>
* Case eval mapping to status