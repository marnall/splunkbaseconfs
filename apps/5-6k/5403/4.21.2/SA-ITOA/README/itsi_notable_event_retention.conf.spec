# This file contains attributes and values for defining how long notable event metadata remains
# in the KV store before it moves to the 'itsi_notable_archive' index.
#
# There is an itsi_notable_event_retention.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place an itsi_notable_event_retention.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local/. You must restart Splunk to enable
# configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

####
# GLOBAL SETTINGS
####
# Use the [default] stanza to define any global settings.
#  * You can also define global settings outside of any stanza, at the top
#    of the file.
#  * Each .conf file should have at most one default stanza. If there are
#    multiple default stanzas, attributes are combined. In the case of
#    multiple definitions of the same attribute, the last definition in the
#    file wins.
#  * If an attribute is defined at both the global level and in a specific
#    stanza, the value in the specific stanza takes precedence.

[<collection_name>]

retentionTimeInSec = <seconds>
* The amount of time, in seconds, to retain the notable event object type.
* Default: 15768000 (6 months)

retentionObjectCount = <number of objects>
* The maximum number of a single object type (for example, notable_event_comment) to retain in the KV store.
* The retention policy runs every hour. If the retention count is 500,000 and a KV store collection exceeds 500,000 objects,
* the oldest objects are moved to the archive index so the collection only has 500,000 objects.
* Default: 500000

disabled = 0|1
* Whether this stanza is enabled or disabled. 
* This setting only applies when the 'smart_recycling' setting is disabled.
  If smart recycling is enabled, this parameter is ignored.
* If "1", the stanza is disabled.
* If "0", the stanza is enabled.

object_type = <string>
* The notable event object type to retain.
* For example, comments, tags, external tickets, and so on.
* Required.
* If 'object_type' is not specified, the entire stanza is ignored.

batch_size = <integer>
* The size of each batch of KV store objects recycled to the archive index at a time.
* Default: 1000

event_push_iterations = <integer>
* The maximum number of attempts to push events from a single KV store collection into the archive index.
* If this limit is reached, the retention policy moves on to the next collection.
* Only set this property in the global [default] stanza. It cannot be set on a per-collection basis.
* Default: 20

warning_percentage = <integer>
* The percentage of retentionObjectCount needed to trigger a capacity warning message.
* Default: 90

smart_recycling = <boolean>
* Enable or disable the smart retention policy, which chooses to recycle inactive episodes and
  related objects first before recycling other objects. Smart retention begins when the limits for the
  'retentionTimeInSec' setting or the 'retentionObjectCount' settings are exceeded.
* If "1", smart recycling is enabled.
* If "0", smart recycling is disabled.
* Only set this property in the global [default] stanza. It cannot be set on a per-collection basis.
* Default: 1 (enabled)

recycle_remaining = <boolean>
* When smart_recycling is enabled, this setting determines whether to continue recycling objects
  after all inactive and closed episodes (and their related objects) have been recycled. 
* If "1", the archiver continues to recycle remaining objects until the retentionObjectCount limit is reached.
* If "0", the archiver stops the archival process after all inactive and closed episodes have been archived.
* Enabling this setting might archive some old active episodes and their related objects, but it can prevent 
  over-exhausting system resources by making sure the KV store collection sizes don't exceed their limits.
* Default: 1 for itsi_notable_group_system and itsi_notable_group_user, 0 for other KV store collections.
