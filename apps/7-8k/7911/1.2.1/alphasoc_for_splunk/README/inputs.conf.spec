[a4s_findings://<name>]
*AlphaSOC findings modular input.
*Polls the AlphaSOC Analytics Engine for OCSF-formatted security
*findings and indexes them in Splunk.
*
*API key and API URL are configured globally via
*Settings > Analytics Engine.

index = <string>
*Splunk index to write findings into. When unset, the input falls back
*to alphasoc.conf [findings].index (default: main). Set explicitly here
*only to route a specific input stanza to a different index than the
*one used by the `alphasoc` search command.

sourcetype = <string>
*Sourcetype assigned to ingested findings. Defaults to
*`alphasoc:finding:ocsf` (set in default/inputs.conf). The
*`alphasoc_findings` macro and CIM mappings assume this sourcetype --
*change it only if you have downstream consumers that need a custom
*one.
