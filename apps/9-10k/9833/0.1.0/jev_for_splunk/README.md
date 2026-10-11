# Jev for Splunk (unofficial)

Adds one search command, `| jev`, which asks TypeSafe's Jev model typed questions about each
result row and returns the answers as fields you can filter, sort, threshold and store.

Not an official TypeSafe product. "Jev" and "TypeSafe" are marks of TypeSafe AI. Licensed under the
Apache License 2.0 (see `LICENSES/LICENSE.txt`).

## What leaves Splunk

**Every `| jev` search sends data to a third party.** For each row, the command sends the values
of the fields named in `state=`, together with the questions, over HTTPS to the base URL on the
Configuration page (default `https://api.typesafe.ai`). Nothing else from the row is sent. The
API key is sent as a bearer token to that URL only.

TypeSafe states that it does not train on customer requests, and offers zero data retention as an
enterprise option. Read their current terms before sending anything sensitive:
https://docs.typesafe.ai and https://typesafe.ai.

The app limits what can leave:

- **Capability.** Only roles holding `run_jev` can run the command. Only `admin` holds it after
  installation. A role that uses the command also needs `list_storage_passwords`, because the
  command reads the stored key as the searching user.
- **Row ceiling.** A search sends at most `maxrows` rows (default 1,000) and never more than the
  hard ceiling an administrator sets (default 10,000). Further rows pass through with `jev_skipped=1`.
- **Audit.** Each search writes to `jev_for_splunk.log`, indexed in `_internal`: user, search id,
  app, question set or inline question, the names of the state fields (never their values), rows,
  API calls, rows served from cache, failures, rows skipped, input tokens, duration and whether the
  cache was on. A long search writes one line per chunk of rows; sum them by `sid`.
  `index=_internal source=*jev_for_splunk.log action=jev | stats sum(sent) sum(input_tokens) by user`
- **Risky command.** `jev` is marked `is_risky`, so Splunk Web asks before running it from a link
  or a dashboard the user did not write. Dashboards should read stored answers instead.
- **Nothing runs by itself.** The only scheduled search deletes expired cache entries and sends nothing.

## Use

```
... | jev noul="Does this message report a failed login?" state=_raw as=failed_login
... | jev choice="Which team should handle this?" options="network,security,platform,other" state="short_description,description"
... | jev score="How urgently should an operator act?" levels="nothing to do|look next shift|act today" state="mnemonic,examples"
... | jev questions=<set> state="<field>,<field>,..."
```

| Option | Meaning |
|---|---|
| `questions` | A question set from `jev.conf`. Not combined with the inline forms. |
| `noul`, `choice` + `options`, `score` + `levels` | One inline question. Options are comma-separated, levels pipe-separated. The answer field is `jev_answer`; `as=<name>` renames it. |
| `state` | Required. Fields sent as state. `a.b` nests, `a.*` takes a prefix, a multivalue field becomes a list, empty fields are omitted. |
| `maxrows` | Rows this search may send. Rows answered from the cache do not count. |
| `cache` | `true` (default) or `false`. |
| `workers` | Parallel requests, 1 to 32. |

Per question `q` the command returns `jev_q` (the option, the score, or the probability),
`jev_q_confidence` (Choice and Score), `jev_q_label` (Score), `jev_q_probabilities` (JSON), plus
`jev_model` and `jev_cached`. A row whose request failed keeps its fields and gains `jev_error`.

A Noul near 0.5 means "could be either", not "medium". Set thresholds on your own data.

## Question sets

One stanza per question in `jev.conf`, named `<set>/<question>`. Any app can contribute sets by
shipping its own `jev.conf`. See `README/jev.conf.spec`. Write one narrow judgment per question,
describe score levels as situations rather than degrees, and give every choice an "other" option.

## The answer cache

Answers are stored in the KV store collection `jev_cache` as each slice of 200 rows completes,
keyed by a SHA-256 of the model, the questions and the state. The state itself is never stored.
A cancelled search keeps what it paid for, and a repeated search costs nothing. Entries older
than the configured lifetime are ignored, and deleted nightly by `| jevpurge`. Roles outside
`admin`, `sc_admin` and `power` are served from the cache but cannot write to it, unless you grant
write access to the collection in `local.meta`.

## Requirements

Splunk Enterprise 9.2 or later, outbound HTTPS from the search head to the API host, and a
TypeSafe API key. The command runs on the search head only.
