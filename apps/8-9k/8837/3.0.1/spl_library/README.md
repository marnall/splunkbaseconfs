# SPL Library v3.0 — Cloud Ready

A modern library for storing, searching, and managing your Splunk queries.

## Cloud compatibility

Built to pass Splunk AppInspect cloud checks:
- No custom REST handlers, no restmap.conf, no web.conf changes
- No binaries or Python in bin/
- No inline JavaScript in views — all code lives in appserver/static/
- No external CDN resources; only Splunk-provided libraries (jQuery, splunkjs)
- Storage is the standard App Key Value Store (KV Store)

## Features

- Modern dark card-based interface
- Full-text search across titles, descriptions, tags, and SPL
- Category filters with live counts (Security, Network, Application,
  Database, Performance, Other)
- Expand any card to view the full SPL
- Copy SPL to clipboard with one click
- "Open in Search" — runs the saved query directly in the Search app
- Add / edit / delete queries via a modal form with tag management
- Auto-seeds four example queries on first load
- Records author and created/updated dates per query

## Storage

Queries live in the spl_library_queries KV Store collection, also exposed
as the spl_library_lookup lookup so you can use the library in SPL:

    | inputlookup spl_library_lookup
    | inputlookup spl_library_lookup | search category=Security

## Installation

Splunk Cloud: install via Apps > Manage Apps > Install app from file,
or through self-service app install / Admin Config Service (ACS),
depending on your stack's policy. Private apps must pass AppInspect;
this app is structured for the cloud check set.

Splunk Enterprise: extract to $SPLUNK_HOME/etc/apps/ or install the
.tar.gz from Manage Apps, then restart.

## Permissions

All users can read and add queries. To restrict who can write, edit the
[collections] stanza in metadata/default.meta.
