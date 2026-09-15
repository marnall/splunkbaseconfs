@placement search-head

[<record_name>]
description = <string>
* Human-readable description or label for the context record.

context_data = <string>
* Context, approved SPL, quick-query content, or protected system-prompt content.

default_search = <string>
* Optional approved SPL used as a fallback search for the record.

type = <string>
* Record type. The application uses datamodel for Data Model registry entries.

datamodel = <string>
* CIM Data Model name for a Data Model registry entry.

dataset = <string>
* Fully qualified Data Model dataset name.

accelerated = <boolean>
* Whether the Data Model is accelerated.

fields = <string>
* Comma-separated logical field names registered for the Data Model entry.

field.<field_name> = <string>
* Maps a logical field name to its physical Data Model field.

value.<field_name>.<logical_value> = <string>
* Maps a logical field value to the physical Data Model value.
