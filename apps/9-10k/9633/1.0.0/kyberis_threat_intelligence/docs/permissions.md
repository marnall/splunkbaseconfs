# Permissions and roles

## Capability requirements at a glance

| Action | Who | Needs |
| --- | --- | --- |
| Install the app, use the setup page | Admins | An admin role: saving profiles writes `storage/passwords` and `kyberis.conf` and reloads the app |
| Run `| kyberis` / `| kyberischeck` | Any role that runs Kyberis searches | The `list_storage_passwords` capability (to read the API key from secure storage) |
| Own an alert with the Kyberis enrichment action | The role the alert runs as | `list_storage_passwords` **and** write access to the action's destination index |
| Write to the enrichment cache | Admins only (by design) | Write access to the `kyberis_ioc_cache` collection — do not broaden it (see below) |

`list_storage_passwords` is the one capability most deployments need to
grant: admins have it by default, ordinary user roles do not. Without it,
searches fail with the missing-key error even when a key is stored (the
message says so). Note this capability exposes all of secure storage to the
role, not only Kyberis keys — grant it to purpose-built roles rather than
broadly.

## App object permissions

The app's objects (commands, alert action, eventtype, lookups) are exported
system-wide and readable by all roles; write access to app objects and
configuration is admin-only (`admin`, and `sc_admin` on Splunk Cloud). The
setup page is therefore effectively admin-only — see
[Credential setup](credentials.md).

## The cache collection ACL — do not broaden it

Cache writes go to the `kyberis_ioc_cache` KV Store collection, whose write
ACL is admin-only by app default. This is a **security property, not a
convenience default**: cached documents are trusted as authentic Kyberis
verdicts, so any role that can write the collection could plant
benign-looking results for malicious indicators (cache poisoning) that later
searches — including other users' — would serve as truth.

Leave the write ACL alone. Non-admin searches degrade gracefully: they still
get read-side cache hits and full enrichment results; only the write-back is
skipped (one warning in the search log). If broader cache warming is wanted,
schedule the warming search as an admin instead of widening the ACL.

## What runs where

Everything runs on the search head: both commands are search-head only
(`distributed = false`), and the alert action executes on the search head
that ran the alert. No role needs any permission on indexers beyond normal
search, and only the alert action writes events (to its configured
destination index).
