WeAre RSS App For Splunk

================================================================================
SUMMARY
================================================================================

WeAre RSS App For Splunk is a modular input add-on that collects RSS and ATOM
syndication feeds and indexes feed entries as searchable events in Splunk. It
lets security, IT, and operations teams monitor external news, vendor advisories,
product updates, and other published content alongside the rest of their Splunk
data.

Problem addressed

Many organizations rely on RSS and ATOM feeds for timely information—security
bulletins, regulatory updates, vendor status pages, industry news, and internal
announcements—but that content often lives outside Splunk. Teams either check
feeds manually, use separate tools, or build custom scripts to pull feed data
into indexes. Manual monitoring does not scale, one-off scripts are hard to
maintain, and feed entries are difficult to correlate with alerts, tickets, and
other security or operational events already in Splunk.

WeAre RSS App For Splunk closes this gap by providing a supported, configurable
way to ingest feed content on a schedule, deduplicate entries, optionally strip
HTML markup from entry text, and assign each event to the index and sourcetype
you choose.

Developed by WeAre Solutions.


================================================================================
SHORT DESCRIPTION
================================================================================

Ingest RSS and ATOM feeds into Splunk on a schedule with deduplication,
configurable timestamps, and optional HTML stripping for searchable feed events.


================================================================================
DETAILS
================================================================================

Requirements

- Splunk Enterprise or Splunk Cloud
- A search head or search head cluster member where modular inputs run
- Network access from the Splunk instance to the RSS/ATOM feed URLs you configure
- Permission to create modular inputs and write to the target index(es)

Supported feed formats: RSS 2.0 and ATOM.


Getting started

1. In Splunk Web, open WeAre RSS App For Splunk from the Apps menu.
2. Select Inputs.
3. Click Create New Input.
4. Complete the fields described below (including optional Strip HTML tags) and
   save the input.
5. Enable the input. Splunk polls the feed on the interval you specify and
   indexes new entries.

Each input monitors one feed URL. Create separate inputs for each feed you want
to collect.


Input configuration reference

Name
  A unique name for this data input. Must begin with a letter and contain only
  letters, numbers, and underscores.

URL
  The full HTTP or HTTPS URL of the RSS or ATOM feed.

Verify SSL
  When enabled, the add-on validates the TLS certificate of the feed server.
  Disable only for trusted internal feeds that use self-signed certificates.

HTTP Timeout
  Maximum time in seconds to wait for a feed response (1–300). Default: 30.

Index
  The Splunk index where feed entries are stored.

Sourcetype
  The sourcetype assigned to indexed events. Default: rss:feed

Event timestamp
  Controls the Splunk _time field for each event:
  - Indexing time (poll execution): _time is set to when the feed was polled.
  - Feed entry field: _time is taken from a date field in the feed entry.

Timestamp field
  Used when Event timestamp is set to Feed entry field. Choose one of:
  - published
  - updated
  - created
  If the selected field is missing or cannot be parsed, the add-on falls back to
  indexing time and logs a warning.

Strip HTML tags
  When enabled, HTML markup is removed from title, summary, and content fields
  before events are indexed. HTML entities (for example &amp;) are decoded to
  plain text. Leave disabled to preserve the original markup from the feed.

Interval
  How often the feed is polled, in seconds (10–86400). Default: 300 (5 minutes).


Indexed event format

Each feed entry is indexed as a JSON event with fields such as:

  id          Stable entry identifier (used for deduplication)
  title       Entry title (plain text when Strip HTML tags is enabled)
  link        Entry URL
  summary     Short description or excerpt (plain text when Strip HTML tags is enabled)
  content     Full entry content when available (plain text when Strip HTML tags is enabled)
  published   Published date string from the feed
  updated     Updated date string from the feed
  created     Created date string from the feed
  author      Primary author name, when present
  authors     List of author names
  tags        Entry categories or tags
  feed_format Detected feed format (for example rss20 or atom10)

Example search:

  index=main sourcetype=rss:feed
  | spath
  | table _time, title, link, author


Deduplication

The add-on tracks entry IDs in a Splunk KV Store collection
(rss_feed_checkpoints) in the app namespace. Only entries with an ID not seen
before are indexed on each poll. If you need to re-ingest historical entries,
create a new input with a different name (checkpoints are per input name) or
delete the checkpoint document for that input from the KV Store collection while
the input is disabled.


Configuration page

Open Configuration to adjust add-on logging level.


Managing inputs

From the Inputs page you can create, edit, clone, enable, and disable feed
inputs. Disabled inputs are not polled.


Example configurations

Security advisories
  URL: https://example.com/security/advisories.rss
  Index: security
  Sourcetype: rss:security_advisory
  Event timestamp: Feed entry field
  Timestamp field: published
  Strip HTML tags: enabled (recommended for HTML-heavy advisory feeds)
  Interval: 300

News monitoring
  URL: https://example.com/news/atom.xml
  Index: news
  Sourcetype: rss:news
  Event timestamp: Indexing time
  Interval: 600


================================================================================
INSTALLATION
================================================================================

Splunk Enterprise

1. Download WeAre RSS App For Splunk from Splunkbase (or use your packaged
   .tar.gz from a private build).
2. In Splunk Web, go to Apps > Manage Apps > Install app from file and upload the
   package, or extract the package to $SPLUNK_HOME/etc/apps/ on the search head
   where modular inputs run.
3. Restart Splunk if prompted.
4. Confirm WeAre RSS App For Splunk appears under Apps and is enabled.
5. Open the app, create inputs on the Inputs page, and enable them.

Splunk Cloud

1. Follow your organization's private-app deployment process (for example Splunk
   Cloud self-service app install or Admin Config Service).
2. Install WeAre RSS App For Splunk on the search tier where modular inputs and
   the add-on UI are supported for your Splunk Cloud experience.
3. After installation completes, open the app from the Apps menu and configure
   inputs on the Inputs page.

Post-installation

- Python 3.9 is required on Splunk Cloud for this add-on.
- No additional configuration is required before creating feed inputs.
- Use the Configuration page only if you need to change add-on logging level.


================================================================================
TROUBLESHOOTING
================================================================================

Inputs page shows "Something went wrong" or Not Found

- Check Splunk internal logs for errors from the add-on REST handler or modular
  input introspection:
  index=_internal sourcetype=splunkd
    (WeAre_RSS_App_For_Splunk OR rss_feed_input OR weare_rss_app_for_splunk)
    (ERROR OR stderr)
- Confirm the app package installed completely and that Splunk was restarted or
  the app was reloaded after upgrade.
- On Splunk Cloud, ensure the app is installed on a tier that supports modular
  input configuration for your deployment type.

No events indexed

- Confirm the input is enabled and the polling interval has elapsed.
- Verify the feed URL is reachable from the Splunk instance (firewall, proxy,
  DNS).
- Check that feed entries have stable IDs; entries without an ID are skipped.
- After the first successful run, only new entries are indexed. Use a new input
  name to force a fresh collection, or clear the checkpoint for that input in
  the rss_feed_checkpoints KV Store collection while the input is disabled.

SSL or connection errors

- Confirm Verify SSL is appropriate for the feed server certificate.
- Increase HTTP Timeout for slow or distant feed hosts.
- Review ModularInputs and ExecProcessor messages in _internal for fetch errors.

Timestamp warnings in logs

- Some feeds omit published, updated, or created dates. Switch Event timestamp to
  Indexing time, or choose a timestamp field the feed actually provides.

HTML or encoding issues in indexed events

- Enable Strip HTML tags to index plain-text title, summary, and content when
  feeds include HTML markup.
- If you need raw HTML for analysis, leave Strip HTML tags disabled.

Permission errors

- Ensure the Splunk role can write to the configured index and manage modular
  inputs for this app.
- KV Store access is required for deduplication checkpoints.


Support

WeAre RSS App For Splunk is developed by WeAre Solutions.
