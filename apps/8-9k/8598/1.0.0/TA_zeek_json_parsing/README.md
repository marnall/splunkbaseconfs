# TA_zeek_json_parsing

`TA_zeek_json_parsing` is a minimal Splunk Technology Add-on for Zeek JSON logs.

Its main purpose is to handle grouped newline-delimited JSON events so Splunk breaks each JSON object into a separate event before JSON field extraction occurs.

## Author

- Name: Kaled Aljebur
- Contact: kaledaljebur@gmail.com

## What It Does

- Defines the `zeek_json` sourcetype parsing rules in `default/props.conf`
- Optionally creates the `zeek` index in `default/indexes.conf`
- Exports the app configuration system-wide through `metadata/default.meta`

## Expected Input Format

This TA is intended for Zeek logs that arrive as newline-delimited JSON, where each event starts on a new line with `{`.

Example:

```json
{ "ts": 1774064684.131214, "uid": "CXp7Om4FBwu7oiTIC4" }
{ "ts": 1774064684.132110, "uid": "CPnoTm2c37jpPqaY39" }
```

## Parsing Behavior

The `zeek_json` stanza applies:

- `SHOULD_LINEMERGE = false`
- `LINE_BREAKER = ([\\r\\n]+)(?=\\{)`
- `INDEXED_EXTRACTIONS = json`
- `KV_MODE = none`

This ensures Splunk breaks the stream into individual events before index-time JSON extraction.

## Deployment

Deploy this TA on the Splunk parsing tier that first processes the Zeek data:

- Heavy Forwarder, if parsing happens there
- Indexer, if parsing happens on the indexer

Do not rely on search-head-only deployment for event breaking.

## Example Universal Forwarder Input

```conf
[monitor:///opt/zeek/logs/current/*.log]
disabled = false
index = zeek
sourcetype = zeek_json
```

## Notes

- This TA is intentionally small and focused on parsing.
- If your environment manages indexes centrally, you may want to remove `default/indexes.conf` before deployment.
