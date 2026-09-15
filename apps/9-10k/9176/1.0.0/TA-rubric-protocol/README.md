# Rubric Protocol Add-on for Splunk

Field extractions and knowledge objects for AI attestation events emitted by
Rubric Protocol (rubric-protocol.com) via HTTP Event Collector.

## What is Rubric Protocol
Rubric Protocol is post-quantum AI attestation infrastructure: every AI
decision is signed with ML-DSA-65 (FIPS 204) and anchored to Hedera Consensus
Service, producing independently verifiable, court-grade evidence of what an
AI system did and when. This add-on parses those events so SOC and GRC teams
can monitor AI activity alongside the rest of their telemetry.

## Sourcetypes
- `rubric:attestation` — JSON events (default emitter format)
- `rubric:cef` — CEF:0 events (RubricProtocol|RubricProof)

## Extracted fields (CEF)
attestation_id, hcs_topic, hcs_sequence, tier, sig_alg, agent_id,
payload_hash, federation_node, action_path, plus a computed `verify_url`
pointing at the public verifier for one-click independent verification.

## Setup
1. Create an HEC token in Splunk (Settings > Data Inputs > HTTP Event Collector).
2. On your Rubric nodes set:
   - `RUBRIC_HEC_URL` — your HEC endpoint (https://splunk:8088/services/collector)
   - `RUBRIC_HEC_TOKEN` — the token
   - `RUBRIC_HEC_FORMAT` — `json` (default) or `cef`
3. Events arrive under sourcetype `rubric:attestation` or `rubric:cef`.

No scripts, no inputs, no stored credentials — this add-on contains only
search-time knowledge objects.

## Support
Issues: https://github.com/0xsims/autogen-rubric/issues
Contact: security@rubric-protocol.com
