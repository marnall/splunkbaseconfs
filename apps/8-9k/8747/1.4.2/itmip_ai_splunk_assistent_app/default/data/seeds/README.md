# KVStore seed files

These JSON files are loaded by `bin/itmip_llm_setup.py` (the
`/services/itmip_llm/setup` endpoint) on first run to populate the
matching KVStore collections **only when they are empty**.

| File | Target collection | What it should contain |
|---|---|---|
| `itmip_organisations.json` | `itmip_organisations` | Tenants. Ships with a single `DFLT` org. |
| `itmip_business_units.json` | `itmip_business_units` | Business units. Ships with one `DFLT_DFLT` BU. |
| `itmip_ai_use_cases.json` | `itmip_ai_use_cases` | Prompt templates. Empty by default — populate from your dev Splunk via `tools/export_kvstore_seeds.sh`. |
| `itmip_llm_configs.json` | `itmip_llm_configs` | LLM endpoint configurations. Empty by default — admins create these in the UI. The bootstrap Anthropic config is synthesised in code (see `src/services/llm/providers.ts`). |
| `itmip_tool_assignments.json` | `itmip_tool_assignments` | Per-Org/BU tool enable/disable rules. Empty by default. |

## Generating seed files from your dev Splunk

Run `tools/export_kvstore_seeds.sh` against your dev Splunk to overwrite
these files with the actual content of your collections. Commit the
result so every fresh install reproduces the same starting state.

## Refreshing on demand

Trigger the setup endpoint manually if you change the seed files and
need a fresh install to pick them up immediately:

```bash
curl -k -u <admin>:<pass> -X POST \
  "https://localhost:8089/services/itmip_llm/setup?output_mode=json"
```

The endpoint is idempotent: collections that already have data are
skipped, so it's safe to call repeatedly.

## What goes in a seed record

The JSON is the same shape KVStore returns — an array of objects, each
optionally with a `_key`. If you set `_key`, it acts as the primary key
on insert; on a re-seed it acts as an upsert key. Without `_key`,
Splunk auto-generates one.

Always include `created_at` / `updated_at` fields (UNIX epoch seconds)
to keep the schema consistent. Use `0` for synthetic defaults.
