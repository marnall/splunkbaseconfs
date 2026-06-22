RSS Feeder for Splunk
Fetch and index RSS/Atom feeds directly into Splunk. This modular input lets you monitor security advisories, news, blogs, or any other RSS source in near real‑time, with dashboards to visualize feed activity, top authors, tags, and more.

✨ Features
Modular input written in Python using splunklib.modularinput

Fetches RSS/Atom feeds with checkpointing (avoids duplicates)

Extracts title, link, author, published date, summary, and tags

Options to strip HTML from summaries or keep raw HTML

Configurable SSL verification, proxy, user agent, and polling interval

Prebuilt RSS Feed Summary dashboard:

Events over time

Feed status (last event age)

Top feeds, authors, and tags

Latest items with drill‑down to original link


📦 Installation
Copy the app folder into $SPLUNK_HOME/etc/apps/rss_feeder_app/.

Restart Splunk.

Verify the app appears in Splunk Web under Apps.

⚙️ Configuration
1. Create a new input
Go to Settings → Data Inputs → RSS Feeder.

Click New Input.

Fill in:

Name: unique identifier for this feed

RSS/Atom URL: feed URL (e.g. https://feeds.feedburner.com/TheHackersNews)

Interval: polling frequency in seconds (e.g. 300)

Index: target index (default: main)

Sourcetype: rss_feed (default)

History size: checkpoint history (default: 500)

Verify SSL: true or false

User Agent: HTTP user agent string

Proxy: optional host:port

Timeout: HTTP timeout in seconds (default: 20)

Clean summary: strip HTML (true/false)

Include raw summary: include raw HTML (true/false)

🛠️ Troubleshooting
Check Search & Reporting with index=_internal RSSFeeder for errors.

Common issues:

SSL errors → set verify_ssl = false if feed uses self‑signed certs.

Proxy needed → configure proxy = host:port.

No tags → some feeds don’t provide <category> elements; tags may be empty.

By default, all events go to the main index.

If you configure a different index in your input stanza, you must also update the RSS Feed Summary dashboard# Binary File Declaration
