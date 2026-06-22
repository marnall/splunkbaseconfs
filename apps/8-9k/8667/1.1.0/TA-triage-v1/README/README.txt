TA-triage
=========

A Splunk custom search command named `triage` for alert triage workflows.

Features
--------
- Supports `model=claude` (Anthropic API)
- Supports `model=ollama` (local Ollama HTTP API)
- Heuristic fallback when no external model is reachable
- File-based cache with TTL
- Context field selection for prompts
- IOC extraction and ATT&CK / kill-chain enrichment

Installation
------------
1. Package the app directory as .tgz or .spl and install it in Splunk.
2. Restart Splunk.
3. Ensure outbound connectivity and API keys for `model=claude`, or local Ollama access for `model=ollama`.
4. Optional: set environment variable ANTHROPIC_API_KEY for Claude usage.

Example usage
-------------
index=edr sourcetype=crowdstrike:*Detection*
| triage model=claude context_fields="UserName,CommandLine,Technique"
| where triage_severity >= 7
| sort -triage_severity

index=edr sourcetype=crowdstrike:*Detection*
| triage model=ollama ollama_url="http://localhost:11434" ollama_model="mistral"

index=edr sourcetype=crowdstrike:*Detection*
| triage model=claude cache=true cache_ttl=3600 cache_key_fields="alert_name,src_ip"
