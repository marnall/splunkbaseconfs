# AI Query Assistant for Splunk — v4.0.0 Release Notes

**Release date:** 2026-05-25
**Splunk Enterprise:** 10.0 – 10.5
**Splunk Cloud:** supported

---

## TL;DR

Ask Splunk questions in plain language. Get back the SPL, run it, and read a
human-friendly summary of the results. v4.0.0 turns the app from a one-shot
NL→SPL translator into a real conversational assistant.

> *"count events by sourcetype in `_internal` last hour"* →
> *"Now show me just the top 3 by count"* →
> *"Anything unusual in the splunkd numbers?"*
>
> Three turns. Same thread. The agent remembers what you asked.

---

## What's new

### 💬 Multi-turn conversations
Every query now belongs to a **conversation thread**. Ask a follow-up that
omits earlier context — the agent remembers the index you were looking at,
the time range, the filters. Switch between recent conversations from a
dropdown at the top of the query page; start fresh with **+ New**.

Conversations persist across browser sessions and across cluster nodes
(stored in the app's KV store).

### 🤔 Clarifying questions
When your question is too vague to answer well ("what's broken?"), the
agent flags it and asks for specifics rather than guessing. You can answer
inline and refine on the same thread — no need to start over.

### ✨ Smarter SPL with the new Supervisor pipeline *(opt-in)*
Enable the four-subagent supervisor mode for tougher queries:

| Subagent | What it does |
|---|---|
| **planner** | decides whether to look up real index/sourcetype names before writing SPL |
| **schema_resolver** | discovers actual indexes / sourcetypes / fields in your environment so the SPL doesn't hallucinate names |
| **spl_generator** | composes the SPL, optionally adapting a saved Query Template if one matches |
| **auditor** | independently reviews the SPL for safety before it runs |

Turn it on in `mcp.conf`:
```ini
[ai]
enable_supervisor = true
enable_explainer  = true
```

### 📊 Result narration
With the explainer enabled, the agent reads the rows your SPL returned and
writes a 2-3 sentence summary, lists 2-3 key findings (with actual numbers),
and suggests follow-up searches. Useful when you're triaging unfamiliar data.

### 🛡 Better safety guardrails
- **Pre-flight**: dangerous keywords in your question (`delete`, `drop`,
  `purge`, `truncate`, `wipe`, `shutdown`, …) are blocked **before** any
  LLM call — no API spend on requests that wouldn't be allowed to run.
- **Post-flight**: the generated SPL is scanned for write operations
  (`| outputlookup`, `| delete`, `| script`, `| collect`, `| sendalert`),
  unbounded time ranges, and sensitive-field references. Dangerous SPL is
  refused; risky-but-readable SPL is downgraded to a yellow "caution"
  badge so you can decide whether to proceed.
- The **auditor** subagent (supervisor mode) gives a second LLM-level opinion
  before SPL ever reaches the executor.

### 🤖 New LLM providers
v4 adds first-class support for **Google Gemini** (both Google AI Studio
and Vertex AI) alongside OpenAI-compatible and Anthropic providers. Add
a provider from the **AI Providers** page and pick the backend in the
dropdown.

| Backend | What works |
|---|---|
| OpenAI-compatible | OpenAI, Azure OpenAI, Ollama, vLLM, DeepSeek, Doubao, Qwen, Volcengine Ark (OpenAI-compat endpoint) |
| Anthropic | Anthropic Claude, Volcengine Ark (Anthropic-compat endpoint), Ollama Claude bridge |
| Google | Gemini 1.5 / 2.0 / 2.5 via Google AI Studio API key, OR via Vertex AI with project + service account |

### 📚 Smarter Query Templates
Templates now carry the actual **SPL pattern** plus searchable **tags**.
When you ask a question and a saved template matches, the agent reuses
the template's SPL (adapting time ranges and field filters to your
current question) and tells you which template it pulled from. Great for
codifying your team's preferred query patterns.

### 🔌 MCP Server App integration *(if installed)*
If you also have Splunk's MCP Server App installed on the same instance,
v4 can automatically discover and use its remote tools. Enable in
`mcp.conf`:
```ini
[ai]
enable_remote_tools = true
```
No effect if the MCP Server App isn't installed.

---

## What's improved

### Reliability
- **Automatic retries** on transient LLM errors (Cloudflare 429, brief 5xx,
  gateway timeouts). Three attempts with exponential backoff — one network
  blip no longer fails the whole query.
- **Append-only conversation history** writes only new turns to the KV
  store (was: rewrite the whole thread every turn). Long-lived threads
  stay responsive.
- **Better error visibility**: when a query runs but fails to save to
  history, the UI surfaces it instead of silently failing. Same for the
  AI provider health check on the dashboard.

### Operations
- **Structured logs** for every query: latency, token usage, subagent
  transitions, guardrail decisions. Indexable as `event=agentic.*` events
  in `_internal` for Splunk-on-Splunk dashboards.
- **`mcp_health` endpoint** now distinguishes AI provider connectivity
  from KV store health from file integrity, so you can pinpoint exactly
  what's degraded.

### Developer experience
- **Dev-mode license bypass**: set `[ai] dev_skip_license = true` in your
  local `mcp.conf` to skip the license check during testing. Logged as a
  WARNING. **Never** set this on production.

---

## Compatibility

v4.0.0 is **dual-path** — it works on every Splunk 10.x version you
already have, and lights up the agentic features automatically when it
sees Python 3.13:

| Splunk version | Python | Behaviour |
|---|---|---|
| 10.0 / 10.1 | 3.9 | Runs the v3 code path. NL→SPL works as before. No multi-turn, no supervisor, no explainer. |
| 10.2 / 10.3 | 3.13 (opt-in) | All v4 features once `python.version = python3.13` is selected for the app. |
| 10.4+ | 3.13 (default) | All v4 features out of the box. |

No configuration needed — the app detects at runtime which path to take.

---

## Upgrade procedure

```bash
# 1. Stop Splunk
$SPLUNK_HOME/bin/splunk stop

# 2. Install the new app over the existing one (your KV data is preserved)
$SPLUNK_HOME/bin/splunk install app AI_Query_Assistant_for_Splunk_v4.0.0.tar.gz -update 1

# 3. On Splunk 10.2+: pull the agentic Python dependencies (~150 MB)
$SPLUNK_HOME/bin/splunk cmd python3.13 \
  $SPLUNK_HOME/etc/apps/AI_Query_Assistant_for_Splunk/bin/install_deps.py

# 4. (One-time, idempotent) migrate v3 history rows to v4 schema
$SPLUNK_HOME/bin/splunk cmd python3.13 \
  $SPLUNK_HOME/etc/apps/AI_Query_Assistant_for_Splunk/bin/migrate_v3_to_v4.py

# 5. Start Splunk
$SPLUNK_HOME/bin/splunk start
```

After Splunk is back up, browse to **AI Query Assistant for Splunk →
Smart Query**. Existing AI Provider records, query history, and license
activation carry forward unchanged.

---

## Known limitations

- **Python 3.9 mode** is a feature-frozen v3 fallback. Multi-turn,
  supervisor pipeline, result narration, and Google Gemini are 3.13-only.
- **Supervisor mode is opt-in** (off by default). It costs 3-5 LLM calls
  per query in exchange for the schema-grounding + audit benefits. Enable
  it for users where SPL correctness matters more than per-query cost.
- **Tool-call telemetry is dropped on history reload**. When you continue
  a previous supervisor conversation, the agent sees the prior turns'
  text and SPL but not the internal subagent call traces. (User-visible
  conversation history is intact.)
- **Some AppInspect Cloud findings on bundled `openai` dependency**:
  `openai/lib/.keep` and `openai/helpers/microphone.py` may be flagged.
  These files aren't used by the app and are excluded from the shipping
  tarball, but the post-install `bin/lib/site-packages/` directory
  recreates them when `install_deps.py` runs.

---

## Bug fixes (vs v3.0.7)

- Risk-level audit verdict is now reliably attached to the response
  (was silently dropped when the structured output model was immutable).
- Anthropic-compatible providers whose base URL omits `/v1` (e.g.
  Volcengine Ark) now authenticate correctly instead of returning 401.
- Conversation history records are written even when message content
  contains LLM-specific binary block types (was: turn silently dropped).
- Dangerous-keyword detection works through the new async pipeline (was:
  obscured by async TaskGroup exception wrapping).
- SSL trust store: when Splunk publishes `SSL_CERT_FILE` pointing to a
  path that doesn't exist (some 10.2.x Docker images), httpx now falls
  back to the system trust store instead of crashing on the first
  outbound LLM call.

---

## License & support

- **Licensing**: this app uses online activation against
  <https://license.reallysec.com>. Existing customers' v3 license keys
  remain valid for v4.
- **Trial license**: a 7-day evaluation license is available — contact
  <support@reallysec.com> with your Server GUID (from the License
  Activation page) and company email.
- **Issues / feedback**: <support@reallysec.com>

---

*Developed and maintained by Anhui Reallysec Information Technology Co., Ltd.*
