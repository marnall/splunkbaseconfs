# Configuration spec for checklist.conf
# This file defines health checks for the ZTAP app

[<stanza_name>]
* Each stanza represents a health check

title = <string>
* Display title for the health check
* Required

category = <string>
* Category of the health check (e.g., Data Ingest, Configuration)
* Required

tags = <string>
* Comma-separated tags for categorizing the check
* Optional

description = <string>
* Detailed description of what the check does
* Required

failure_text = <string>
* Message to display when the check fails
* Required

suggested_action = <string>
* Recommended action to resolve failures
* Required

search = <string>
* SPL search query to execute for the health check
* Should use macros when possible (e.g., | `macro_name`)
* Required
