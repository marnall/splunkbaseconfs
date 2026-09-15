# mispfuse_templates.conf.spec
# MISPFuse mapping templates. Each stanza defines one template.

[<template_name>]
grouping = <string>
* One of: single_event, per_row, by_field. Default: single_event.

event_info = <string>
* MISP event title. Supports $fieldname$ token substitution from the first
* row of a group. Default: IOCs from Splunk (MISPFuse).

distribution = <integer>
* MISP distribution level 0-4. Default: 0.

threat_level_id = <integer>
* MISP threat level 1-4 (1 High .. 4 Undefined). Default: 4.

analysis = <integer>
* MISP analysis state 0-2 (0 Initial, 1 Ongoing, 2 Completed). Default: 0.

publish = <boolean>
* Publish the event immediately after creation. Default: 0.

to_ids = <boolean>
* Default to_ids flag for attributes when a mapping does not set one. Default: 0.

tags = <string>
* Comma-separated tags applied to each event.

strict = <boolean>
* When 1, skip attributes whose type/category is not valid on the connected
* MISP instance. When 0, push anyway (the server remains the authority).
* Default: 0.

map.<n> = <string>
* A field-to-attribute mapping, in the form:
*   <source_field>:<type>:<category>:<to_ids>:<disable_correlation>[:<comment_field>]
* <type> is required. <category> may be empty to use the type default.
* Repeat as map.1, map.2, ...
