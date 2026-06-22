AlphaLevel Alert Refinery (TA-alphalevel-alert-refinery) v2.0.0
===============================================================

What's new in v2.0.0
--------------------
Major upgrade. v1.0.0 sent notable events to an S3 bucket and consumed
scored results back via a modular input. v2.0.0 flips the model: Alpha Level
pulls events over the management port and pushes scored results back via
HEC. There is no S3 path anymore.

If you are upgrading from v1.0.0:
  - Remove any IAM roles, S3 buckets, and VPC endpoints created for v1.
  - Disable any v1 alert actions or modular inputs (they no longer exist
    in this TA but may have been cloned into local/).
  - Follow the "Customer setup checklist" below.
  - The KV store schema is new (alphalevel_scores replaces the v1 lookup);
    v1 lookup CSVs can be deleted.

What this is
------------
Conf-only Splunk Cloud Technical Add-on that prepares the environment for
Alpha Level managed alert scoring. NO algorithms, NO Python, NO compiled
binaries. The actual scoring runs on Alpha Level's side; this TA makes
the environment ready and surfaces the scores in Splunk ES Incident Review.

How it works
------------
1. Alpha Level pulls events from this Splunk over the management port
   (REST :8089) using the alphalevel_sources macro and the
   alphalevel_normalise macro to compute a stable join key (al_key).
2. Alpha Level pushes scored results back via HEC to the index defined
   by the alphalevel_results_index macro (default: main), sourcetype
   alphalevel:result.
3. A saved search shipped with this TA reads those events every 5 minutes
   and upserts them into the alphalevel_scores KV store. This gives us
   natural back-pressure - if HEC is unreachable, scores queue on our side
   and resume flowing when it recovers.
4. An auto-lookup on [source::*] computes al_key via sha256(_raw) and joins
   the KV store onto all events, so analysts see Alpha Level scores directly
   in Splunk ES Incident Review.
5. A Readiness Dashboard (default landing page) shows whether the
   environment is ready for the puller, with a green/amber/red verdict
   per check.

Customer setup checklist
------------------------
  [ ] Install this TA via Splunkbase or the Admin Console. No indexes to
      create first - by default the TA writes scored results and heartbeats
      to `index=main`. (Optional, for cleaner separation: create dedicated
      `alphalevel_results` and `alphalevel_internal` indexes in the Splunk
      Cloud Admin Console, then override the `alphalevel_results_index` and
      `alphalevel_internal_index` macros in `local/macros.conf`.)
  [ ] Create a HEC token that accepts sourcetypes `alphalevel:result` and
      `alphalevel:heartbeat` into whichever indexes you're using above.
  [ ] Create a service account and grant it the `alphalevel_svc` role
      shipped with this TA. Then create a long-TTL Splunk auth token bound
      to that service account (Settings → Tokens).
  [ ] Log in to https://admin.alphalevel.ai and set up a new integration.
      You will need the HEC URL, HEC token, Splunk MGMT URL, and auth token.
  [ ] If your alerts live somewhere other than `index=notable`, override
      `alphalevel_custom_sources` in `local/macros.conf`.
  [ ] Open the "Alpha Level - Readiness" dashboard. Once Alpha Level enables
      the puller for your tenant, checks will populate and go green within
      5-15 minutes.

What's in the box
-----------------
  default/app.conf                    - manifest
  default/authorize.conf              - alphalevel_svc role
  default/collections.conf            - KV store collections
  default/transforms.conf             - KV store transforms + lookup
  default/eventtypes.conf             - alphalevel_notable
  default/macros.conf                 - alphalevel_sources, alphalevel_normalise, etc.
  default/props.conf                  - sourcetype parsing + auto-lookup wiring
  default/savedsearches.conf          - lookup builder + readiness checks
  default/data/ui/views/readiness.xml - Readiness Dashboard
  default/data/ui/nav/default.xml     - App nav
  lookups/alphalevel_required_fields.csv
  metadata/default.meta

What's NOT in the box (and why)
-------------------------------
  - No Python / no algorithms. Scoring runs on Alpha Level's side.
  - No license validation. Alpha Level checks licenses server-side.
  - No modular inputs. The puller drives everything from outside.

Compatibility
-------------
  - Splunk Cloud (Victoria stack). Cloud-first; not tested against
    self-managed Splunk Enterprise.
  - Splunk ES recommended but not required (auto-lookup degrades gracefully
    if no notable events exist).

Known limitations (v2.0.0)
--------------------------
  - Multi-search-head clusters: assume a load-balanced URL. Per-member
    health is out of scope for this version.
