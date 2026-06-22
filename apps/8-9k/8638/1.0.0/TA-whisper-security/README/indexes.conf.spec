#
# indexes.conf.spec — Index definitions for Whisper Security TA
#
# This file documents the settings in indexes.conf that define the
# whisper index used by all TA event data.
#
# On Splunk Cloud, the admin must create this index via the Cloud console
# before enabling inputs.
#

[whisper]
coldPath = <path>
* Path to the cold (aged) bucket storage.
* Default: $SPLUNK_DB/whisper/colddb

homePath = <path>
* Path to the hot/warm bucket storage.
* Default: $SPLUNK_DB/whisper/db

thawedPath = <path>
* Path to the thawed (restored from archive) bucket storage.
* Default: $SPLUNK_DB/whisper/thaweddb

frozenTimePeriodInSecs = <integer>
* Number of seconds after which data is frozen (deleted or archived).
* Default: 15552000 (180 days)

repFactor = <string>
* Replication factor for index data in clustered environments.
* Default: auto
