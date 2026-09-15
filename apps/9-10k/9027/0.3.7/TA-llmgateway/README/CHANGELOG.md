# TA-llmgateway Changelog

## 0.3.7

**Fixed:** `llmgateway_finish_reason` was never populated for `sourcetype=llmgateway:bifrost`.
`props.conf` only aliased LiteLLM's raw `finish_reason` field
(`FIELDALIAS-llmgateway_li_finish`); Bifrost's equivalent raw field is named
`stop_reason` and had no alias at all. Added
`FIELDALIAS-llmgateway_finish = stop_reason AS llmgateway_finish_reason` to the
`[llmgateway:bifrost]` stanza so `llmgateway_finish_reason` is now populated
consistently across both gateways without requiring
`coalesce(llmgateway_finish_reason, stop_reason)` in every search.

**Operational note (outside this TA, but affects the same field family):**
If you are ingesting Bifrost events via the `bifrost-hec-shipper` sidecar
container in the `splunk-mcp-llm-siemulator` docker-compose stack (as opposed
to this TA's own bundled `bin/bifrost_logs.py` modular input), be aware that
sidecar script previously shipped `llmgateway_output_text` empty for every
non-streaming chat completion. Root cause: Bifrost's SQLite `logs` table
stores single-turn responses in an `output_message` column (a single
`{"role":"assistant","content":"..."}` object), not `output_history` (a list,
used for multi-turn/streamed responses) -- the sidecar only read the latter.
This TA's own `bin/bifrost_logs.py` (see `flatten_record()`) already handled
this correctly via an `output_message` fallback; the standalone sidecar script
had drifted out of sync with it and has since been patched to match.

**Known caveat (upstream, not fixed by this TA):** `llmgateway_key_name` and
`llmgateway_team` can appear as the literal 4-character string `"null"`
(rather than a true empty/absent field) for LiteLLM events sent without a
named virtual key. This happens because `custom_callbacks.py`'s
`metadata.get("user_api_key_alias", "")` only falls back to `""` when the key
is *absent* from the dict -- LiteLLM's metadata already contains the key set
to Python `None`, so `.get()` returns `None`, which serializes to JSON `null`.
Filter with `field!="null"` in addition to `isnotnull(field)` until all
pre-fix events age out of your retention window.

**AppInspect (precert mode, 4.2.1):** 0 errors, 0 failures. Added
`python.required = 3.13` to the scripted input stanza in `inputs.conf` and the
REST handler stanza in `restmap.conf`, resolving 2 `future_failure` findings
(Python 3.13 compatibility declarations that will become hard failures in a
future AppInspect release). Remaining findings are warnings only, not
failures: `sc_admin` role recommendation for Splunk Cloud in
`metadata/default.meta` (not applicable -- this app has no knowledge objects
needing role ACLs beyond the defaults), false-positive "public IP" matches
inside the bundled compiled psycopg2 binaries (byte patterns in X.509/ASN.1
OID sequences, not real IP addresses), and one placeholder RFC 1918 example
address used as documentation sample text in
`README/ta_llmgateway_settings.conf.spec`.

No other files changed from 0.3.6 -- this release is scoped strictly to the
Bifrost `finish_reason` fix and the two `python.required` additions above.

## 0.3.6

Baseline version.
