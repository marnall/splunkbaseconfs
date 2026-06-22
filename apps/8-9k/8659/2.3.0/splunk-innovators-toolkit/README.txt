Innovators Toolkit
==================

A community toolkit from the Splunk Innovators Network.
Add professional polish to Splunk Classic dashboards — premium themes,
animated backgrounds, interactive controls, and a visual Design Studio.

Quick Start
-----------
1. Install the app from Splunkbase (or upload the .tar.gz package).
2. Open any Classic Simple XML dashboard and add a theme:
       <dashboard stylesheet="splunk-innovators-toolkit:themes/gradient-luxury.css">
3. Or open the Design Studio (Apps > Innovators Toolkit > Design Studio) to
   visually import and polish your existing dashboards.

Requirements
------------
- Splunk Enterprise 9.0+ or Splunk Cloud
- Classic Simple XML dashboards (version="1.1") — NOT Dashboard Studio
- Modern browser (Chrome, Edge, Firefox, Safari)

Configuration
-------------
This app is configuration-free for the visual layer (CSS themes/backgrounds).
Interactive controls (toggles, widgets) are configured per-dashboard by adding
data-* attributes to an element INSIDE an <html> panel on that dashboard
(attributes on the <dashboard> root element itself are not rendered by Simple
XML and have no effect). Example:

  <html>
    <div data-sit-refresh-interval="300"></div>
  </html>

See appserver/static/toggles/ and appserver/static/widgets/ for the exact
attribute names in each component's header comment.

Cloud Mode
----------
On Splunk Cloud, the Design Studio defaults to Cloud Mode. Saving works the
same as on Enterprise: pick an app + dashboard name in the Save dialog and
the dashboard is created directly. If your Cloud role does not permit view
writes (the save is rejected with a 403), the dialog falls back to the
Download XML flow — upload the generated XML via Splunk's Source Editor.

Note: the demo dashboards search index=_internal, which requires a role
allowed to search internal indexes (admin/sc_admin or equivalent). Users
without that capability will see empty demo panels.

Data Privacy
------------
This app stores small amounts of user-preference data in the browser's
localStorage. No data is transmitted off the user's browser. See PRIVACY.txt
for the full disclosure.

Troubleshooting
---------------
- "JS features don't work in Cloud" — Splunk Cloud restricts certain JS
  patterns. Stick to CSS-only (themes/backgrounds) on Cloud, or use the
  Design Studio in Cloud Mode.
- "Apps menu icon is missing" — Hard-refresh your browser to bust cached
  static assets (Cmd+Shift+R / Ctrl+Shift+R).
- "Preview leaves the screen cut off" — fixed in v2.0.3+. Upgrade if you
  see this on older builds.

Support
-------
- Community: Splunk Innovators Network on LinkedIn
            (https://www.linkedin.com/groups/16364058/)
- Email:     steve@datadaytech.com
- Issues:    Contact DataDay Technology Solutions

License
-------
MIT License — see LICENSE.txt.

Trademark Notice
----------------
This is a community-created toolkit. Not affiliated with or endorsed by
Splunk Inc. "Splunk" is a trademark of Splunk Inc. This app is designed
to work with Splunk software.
