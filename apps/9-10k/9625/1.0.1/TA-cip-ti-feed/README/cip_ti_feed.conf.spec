# Settings spec for the CIP TI Feed app. The Set up screen writes [settings].
# cip_key and slack_webhook are password fields: they are stored in
# storage/passwords, not as keys in this file.

[settings]
cip_env = <string> CIP feed environment: LIVE (default) or TEST.
confidence = <integer> Feed pull confidence floor, 0-100 (default 70).
alert_outbound_established = <boolean> Alert when an outbound session to a malicious IP actually completed (default on).
alert_outbound_attempted = <boolean> Alert when an outbound connection was allowed but never completed (default off, mostly noise).
alert_outbound_blocked = <boolean> Alert on outbound traffic the firewall denied (default off, monitoring only).
alert_inbound_established = <boolean> Alert when an inbound session from a malicious IP actually completed (default on).
alert_inbound_attempted = <boolean> Alert when an inbound connection was allowed but never completed (default off).
alert_inbound_blocked = <boolean> Alert on inbound traffic the firewall denied (default off, very high volume).
alert_min_confidence = <integer> Alert confidence floor, 0-100 (default 80).
web_base_url = <string> Base URL for the Slack "View in Splunk" link. Scheme, host and port only, e.g. https://splunk.example.com:8000. Do not include a path. Optional; blank falls back to Splunk's results_link.

# Legacy: alert_outbound_passed / alert_inbound_passed are no longer written.
# If either value is still present, the scope-sync search reads it as a fallback
# for the matching *_established setting.

feed_limit = <integer>
* Maximum rows fetched per feed (direction x profile). Default 50000.
* The Criminal IP API accepts 1-50000. A value outside that range, or a non-number,
  is replaced by 50000 for the run and recorded as
  cip_ti_feedsync event=config_invalid key=feed_limit (sourcetype cip:ti:feedsync).
* A value inside the range that is under half the feed size makes the download come
  back short. The collector then keeps the previous lookup, records
  event=feed_error reason="shrunk: ..." and event=feed_truncated, and the sync result
  is status=failed reason=kept_stale. Do not lower this below the feed size.
* Completeness is judged by comparing what was delivered against the total the API
  itself reports, not against this limit. Feed health reports that comparison.

fw_vendor = <string>
* Firewall product for this installation: fortigate|panos|asa|other. One per
  installation, not per source.
* This is an input, not a record. It decides the vendor filter appended to each source
  when Set up generates cip_ti_traffic and cip_ti_traffic_local. If it does not match
  the real product, fix it before saving - the wrong filter makes detections zero with
  no error.
* The vendor adapter (cip_ti_normalize) is never written by Set up. Writing it into
  local/ would freeze that definition and permanently shadow later fixes in default/.

fw_index = <string>
fw_sourcetype = <string>
* Legacy record of what Set up last saved, kept only so an upgrade can migrate a
  single-source install into [source:1]. Nothing reads these at search time and editing
  them by hand has no effect. Edit [source:<n>] instead.

[source:<n>]
* One firewall log source. Set up reads these to draw its list and generates the two
  source macros from them, so this is where the searched sources are defined.
* Numbered from 1. Set up renumbers on save.
* No sources ship in default/ - a default filled with someone else's index would be
  indistinguishable from a value the operator chose.

index = <string>
* Index the firewall logs land in. Required.
* May not start with * and may not be this app's summary index. Either one makes the
  detection search read its own output.

sourcetype = <string>
* Sourcetype of the firewall logs. Required.

disabled = <boolean>
* Set to 1 to stop searching this source. Set up disables rather than deletes, so a
  removed source can be restored and a failed write never leaves it half-removed.
