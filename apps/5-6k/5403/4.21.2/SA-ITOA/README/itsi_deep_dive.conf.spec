# This file contains possible attributes and values for uploading sample
# deep dives to the KV store.
#
# To upload deep dives to the KV store, place an
# itsi_deep_dive.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/local.
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
* A name or primary identifier for the deep dive.

focus_id = <string>
* The ID of the entity or service that is in focus in the deep dive.
* When an entity or service has focus, you see a list of metrics
 (performance metrics, event counts) for that entity/service.
* Any particular deep dive can have a particular IT context
  in focus at any given time.
* You can change the IT context in focus at any time. However,
  changing the focus has implications for historical tracking
  if not in a named deep dive.

title = <string>
* The title of the deep dive that is displayed in the UI.

lane_settings_collection = <array>
* An array of lane settings specifying each lane's configuration.

acl = <value>
* The team Access Control List (ACL) settings.

mod_time = <value>
* The last time the 'acl' setting was modified.

description = <value>
* Optional. The description of the deep dive.

is_named = <true|false>
* Whether or not this deep dive is named.
* A deep dive is considered "named" if you save it in the UI
  and give it a name. You might name a deep dive if you find it
  particularly useful and want to save it for future use.
* A deep dive is considered "unnamed" if you dynamically generated
  it (for example, from a drilldown) and did not save it.

_owner = <string>
* The user's KV store account in which to store the deep dive.
* In nearly all cases this value is "nobody".

source_itsi_da = <string>
* Optional. The ITSI module that acts as the source to define
  the deep dive.
* This attribute is used by the domain add-ons.
