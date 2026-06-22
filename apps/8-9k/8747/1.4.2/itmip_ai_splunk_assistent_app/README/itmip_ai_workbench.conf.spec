# itmip_ai_workbench.conf.spec
#
# Specification for itmip_ai_workbench.conf — install-time-only
# operational knobs for the AiWorkbench app. Read by btool / IDE
# tooling locally; not vetted by Splunk Cloud (this spec lives under
# README/ and never reaches splunkd).

[kvstore_backup]

enabled = <bool>
* Master switch for the KVStore backup subsystem.
* When 0 the modular input is a no-op (returns immediately) and no
  snapshot or change-log events are produced.
* Toggling requires a Splunk restart because the scripted-input
  disabled flag is read on startup.
* Defaults to 1.

daily_time = <HH:MM>
* Local time (24-hour) when the daily snapshot fires.
* The modular input wakes every 600 seconds and runs the snapshot on
  the first tick whose local time has crossed this value within the
  current day.
* Defaults to 02:00.

emission_mode = best_effort | mandatory
* Change-log emission failure semantics.
* best_effort — failure to write to itmip_changes is logged
  to _internal and does NOT fail the user's KVStore write.
* mandatory — change-log write must succeed; failure causes the
  user's write to fail with a 500. Use only when zero-loss audit is
  required.
* Defaults to best_effort.

retention_critical_days = <int>
* Daily-snapshot retention window for critical-tier collections.
* Defaults to 30.

retention_critical_weekly_weeks = <int>
* Weekly-snapshot retention window (Sunday backups kept) for
  critical-tier collections.
* Defaults to 26 (~6 months).

retention_critical_monthly_months = <int>
* Monthly-snapshot retention window (1st-of-month backups kept) for
  critical-tier collections.
* Defaults to 24 (~2 years).

retention_history_days = <int>
* Retention for snapshots of itmip_user_history. No weekly/monthly
  archive is kept for this collection.
* Defaults to 14.

verify_email_recipients = <comma-separated emails>
* Recipients for the snapshot-verification failure alert.
* Empty = fall back to the License-tab configured recipients.

secrets_backup.mode = inventory_only | cleartext_restricted
* Whether the scripted input emits an inventory of credential names
  referenced by KVStore rows (Option A, default) or also exports
  cleartext to the admin-only index itmip_kvstore_secrets_backups
  (Option B, Phase 9.6 — opt-in).
* Defaults to inventory_only.

secrets_backup.include_per_user_tokens = <bool>
* When secrets_backup.mode = cleartext_restricted, controls whether
  per-user OAuth tokens are included in the cleartext backup.
* Tokens expire so the default is off.
* Defaults to 0.

[ui]

unassigned_message = <string>
* Message shown to a non-admin user who lands on the app but does NOT
  resolve into any configured Org. The shell greys out every tab and
  renders this message in the centre instead of letting the user stare
  at an empty Ask tab.
* Admins are never marked unassigned — they always fall through to
  DFLT/DFLT.
* Default text: a generic "contact your Splunk admin team" message.
  Replace with your organisation's actual contact instructions in
  local/itmip_ai_workbench.conf.

[concise_mode]

feature_concise_mode = <bool>
* Master switch for Concise Mode (v0.9.3+).
* When 0 the dispatcher ignores every template's style_profile field
  and never injects the concise style block.
* When 1 the dispatcher honours per-template style_profile, the
  follow-up rule below, and per-LLM disable_style_profiles overrides.
* Defaults to 0.

followup_concise_mode = <bool>
* When the feature flag is on, controls whether follow-up turns
  (conversation length > 0) get the concise style block appended
  regardless of the active template's own style_profile.
* Off-by-default templates produce a full-quality artefact on turn 1
  (Simple XML, SPL, alert config, MLTK config); follow-up turns are
  pure chat about that artefact — the natural place to compress.
* Defaults to 1.

[branding]

msp_badge_label = <string>
* Header license-badge text shown when the EFFECTIVE license tier is MSP
  (v1.4.1+). Plain text, no markup.
* MSPs run one license across many customer environments and frequently
  white-label, so only the MSP edition badge is configurable; the free /
  PoV / NFR / Professional / Enterprise badge texts are fixed in the
  product.
* Examples: "Powered by Acme - Enterprise", "Acme Managed AI".
* A blank or absent value falls back to the default.
* Defaults to "MSP Enterprise Edition".
