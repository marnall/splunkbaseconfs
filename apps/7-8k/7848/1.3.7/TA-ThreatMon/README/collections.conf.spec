# collections.conf.spec
# Configuration specification for ThreatMon collections

[<collection_name>]
* Defines settings for KV store collections used by ThreatMon app.

replicate = <boolean>
* Whether to replicate this collection across search head cluster members.
* Default: false

accelerated_fields.<fieldname> = <JSON object>
* Accelerated field definitions for fast searching.
* JSON object defining the field acceleration pattern.

field.<fieldname> = <string>|number|bool
* Field definitions for the collection.
* Valid types: string, number, bool 