# Hurricane Labs Add-on for Anthropic Compliance API

Splunk Technology Add-on that ingests data from the Anthropic
Compliance API (spec version 2026-03-29) for audit, eDiscovery, DLP,
insider-risk, and governance use cases.

Polls the Activity Feed, organizations/users/groups/roles, Claude.ai
projects, and Claude.ai chats. Adds the `| claudechats` streaming
command for ad-hoc, user-scoped chat retrieval. Ships CIM mappings
for Authentication and Change plus an overview dashboard.

## Inputs

| Input | Sourcetypes | Collects |
|---|---|---|
| Activity Feed | `anthropic:compliance:activity` | Per-event audit stream (auth, file/chat/project lifecycle, admin actions, compliance API usage). |
| Org Users | `anthropic:compliance:organization`, `:org_user`, `:group`, `:group_member`, `:org_role` | Point-in-time snapshot of orgs, members, RBAC groups, group members, and org-level roles. |
| Apps (Projects) | `anthropic:compliance:apps:project`, `:apps:project_attachments` | Project metadata and optional attachment manifests. |
| Chats | `anthropic:compliance:apps:chat`, `:apps:chat_message` | Chat metadata and, optionally, full message threads. Auto-discovers org users to satisfy the API's `user_ids[]` filter. |

All inputs hit `https://api.anthropic.com/v1/compliance/*` over HTTPS
and checkpoint between runs.

## Requirements

- Splunk Enterprise 9.3+ or Splunk Cloud.
- Outbound HTTPS to `api.anthropic.com` from the input host.
- An Anthropic Enterprise plan with the Compliance API enabled
  (Primary Owner enables it in Claude.ai Data and Privacy settings;
  Console / API customers request access via their Anthropic rep).
- A **Compliance Access Key** (`sk-ant-api01-...`) for the Org Users,
  Apps, and Chats inputs, or an **Admin Key** (`sk-ant-admin01-...`)
  for the Activity Feed only. Admin keys return 401 on every other
  endpoint.

### Scopes by input

| Input | Required scopes |
|---|---|
| Activity Feed | `read:compliance_activities` |
| Org Users | `read:compliance_org_data`, `read:compliance_user_data` |
| Apps (Projects) | `read:compliance_user_data` |
| Chats | `read:compliance_org_data`, `read:compliance_user_data` |
| `claudechats` | `read:compliance_user_data` |

Scopes are immutable on an issued key; reissue to change them.

## Install

1. Download Hurricane Labs Add-on for Anthropic Compliance API from Splunkbase.
2. **Apps → Manage Apps → Install app from file**, then restart Splunk.
3. **Hurricane Labs Add-on for Anthropic Compliance API → Configuration**,
   add an account, then enable inputs from the **Inputs** tab. Each input's
   per-field help text describes its options.

## Chats input

`/v1/compliance/apps/chats` requires `user_ids[]` on every call, so
each poll discovers users before fanning out:

1. `GET /v1/compliance/organizations` lists all orgs.
2. `GET /v1/compliance/organizations/{uuid}/users` paginates members
   per org; the union (deduplicated) is the user_id set.
3. `GET /v1/compliance/apps/chats?user_ids[]=...&updated_at.gt=<checkpoint>`
   runs once per batch of up to 10 user_ids (the API caps `user_ids[]`
   at 10 per request), paginated with `after_id`.
4. (Optional) `GET /v1/compliance/apps/chats/{id}/messages` per chat,
   emitting one event per message under
   `anthropic:compliance:apps:chat_message`.

Message events carry `chat_id`, `chat_organization_uuid`,
`chat_organization_id`, `chat_project_id`, `chat_user_id`, and
`chat_user_email_address` for correlation back to the parent chat.

The (lookback start → now) range is split into 24-hour chunks; the
helper writes the checkpoint after each chunk completes, so a failure
mid-run replays at most one day on the next run instead of the entire
backfill.

The default poll interval is 4 hours; raise it for large tenants
since each poll's API volume scales with org count and member count.

### First-run behavior

With no checkpoint, the helper emits the full message thread for
every chat whose `updated_at` falls within `Lookback Hours`, so
historical context for long-running conversations is captured once.
Subsequent runs are incremental: the chat-level event still fires on
every `updated_at` advance (rename, project move, soft-delete), but
only messages whose `created_at` is newer than the previous run's
checkpoint are emitted as `:chat_message` events. To force a re-seed,
stop the input, delete `<input_name>_chats.json` from
`$SPLUNK_HOME/var/lib/splunk/modinputs/anthropic_chats_input/`, and
re-enable.

## `claudechats` command

```
... | <search yielding events with an Anthropic user_id field>
| claudechats userid_field=<field> [account=<name>] [messages=true|false]
```

Hits the same endpoint as the Chats input but takes user_ids from
upstream events instead of auto-discovery. Use it to pivot from an
Activity Feed event to that user's chat history without standing up
a polling input.

### Options

- `userid_field` (required): upstream field containing values of the
  form `user_...`. Multi-value fields accepted.
- `account` (optional when one configured): which add-on account's
  API key to use. Required when multiple accounts exist.
- `messages` (default `true`): when `true`, emits one row per message
  with chat context; when `false`, emits one row per chat (cheaper).

### Example

```
index=anthropic_compliance sourcetype="anthropic:compliance:activity"
    "actor.user_id"=user_01EXAMPLE00000000000000
| claudechats userid_field="actor.user_id"
```

## CIM

`eventtypes.conf`, `tags.conf`, and `props.conf` map sourcetypes to:

- **Authentication** — activity-feed user actions and org-user identity
  records.
- **Change / Audit** — activity-feed create/update/delete events plus
  project, chat, group, and role lifecycle.

The **Overview** dashboard (Apps → Hurricane Labs Add-on for Anthropic
Compliance API → Overview) charts authentication activity, admin change
events, membership, and Claude app data access.

Add-on logs:
`$SPLUNK_HOME/var/log/splunk/ta-anthropic_compliance_api_*.log`.
Per-input log level lives in **Configuration → Logging**.

## Release notes

### 1.1.1

- Initial release.
- Activity Feed, Org Users, Chats, and Apps (Projects) inputs with
  checkpointed incremental ingestion.
- `claudechats` streaming search command.
- CIM mappings (Authentication, Change) and an overview dashboard.

## Support

Support email: splunkapp@hurricanelabs.com
Business hours 9am - 5pm Eastern
Closed on all US Federal holidays

## License

See `TA-Anthropic_Compliance_API/package/LICENSES/LICENSE.txt`.
