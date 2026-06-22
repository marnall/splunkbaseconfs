TA_triage
=========

TA_triage is a Splunk custom search command that enriches each event with triage metadata.

Features
--------
- Supports model=claude via Anthropic API using ANTHROPIC_API_KEY
- Supports model=ollama via a local Ollama-compatible HTTP endpoint
- Deterministic heuristic fallback when remote inference is unavailable
- File-based cache with TTL and cache_key_fields
- Context field selection for narrower prompts
- IOC extraction and ATT&CK / kill-chain enrichment

Example searches
----------------
index=edr sourcetype=crowdstrike:*Detection*
| triage model=claude context_fields="UserName,CommandLine,Technique"
| where triage_severity >= 7
| sort -triage_severity

index=edr sourcetype=crowdstrike:*Detection*
| triage model=ollama ollama_url="http://localhost:11434" ollama_model="mistral"

index=edr sourcetype=crowdstrike:*Detection*
| triage model=claude cache=true cache_ttl=3600 cache_key_fields="alert_name,src_ip"

Packaging notes
---------------
- Root folder and [package] id are both TA_triage.
- Archive contains no hidden files that start with a dot.
- check_for_updates remains enabled.
