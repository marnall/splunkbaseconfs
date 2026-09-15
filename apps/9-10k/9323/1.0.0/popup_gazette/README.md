# Popup Gazette

Centrally-managed **announcement popups** for Splunk SimpleXML dashboards.

Instead of hand-embedding notice HTML into every dashboard's XML, the fixed popup
template (`popup.js` + modal shell) ships with this app. The content, targeting,
schedule and audience of each notice are managed from a single page and stored in
KV Store — so you update a notice once and every dashboard reflects it, with no XML edits.

## Features

- **One-line attach** — add `script="popup_gazette:popup.js"` to any classic dashboard.
- **Central management UI** — create/edit/schedule notices from one page (React).
- **Targeting** — show a notice globally, per app, or on a single view.
- **Markdown or Raw HTML** — author with a Markdown editor (safe by default); Raw HTML
  is available to admins and sanitized on save.
- **Scheduling & audience** — optional start/end time and role restrictions.
- **Display frequency** — every visit, once a day, or until the reader dismisses it
  (with an optional "don't show again for N days").
- **Re-show to everyone** — one click re-publishes a notice, so readers who already
  dismissed it see it again.
- **Multiple notices at once** — every matching notice is shown as a card stack, ordered
  by priority, each with its own close / link / dismiss controls.
- **Severity styling** — info / warning / critical.
- **Auto-scoped editing** — the management page can be embedded in another app; it then
  manages only that app's notices, while admins in Popup Gazette see everything.
- **English / Korean UI** — follows the user's Splunk locale.

## Requirements

- Splunk Enterprise / Cloud with **classic SimpleXML** dashboards (Dashboard Studio is not
  supported — it does not load custom scripts the same way).
- KV Store enabled (used to store notices).

## Install

1. Install the app (Splunk Web → Manage Apps → Install app from file, or unpack into
   `$SPLUNK_HOME/etc/apps`).
2. **Restart Splunk** once — required to register the REST handlers, custom capabilities
   and the KV Store collection.
3. Grant the capabilities as needed (see Permissions). `admin` / `sc_admin` get them by default.

## Attach a popup to a dashboard

Add one attribute to any SimpleXML `<dashboard>` / `<form>` tag:

```xml
<dashboard version="1.1" script="popup_gazette:popup.js">
```

On load it reads the current app/view, fetches the active notices targeting this page,
and shows them in one modal as a card stack, highest priority first.

## Manage notices

Open **Popup Gazette → Manage** and create a notice with:

- **Title / severity** — info, warning, or critical
- **Target** — Global (all dashboards, admin only), App, or a single View
- **Content** — Markdown (default) or Raw HTML (admin only)
- **Schedule** — optional start / end time
- **Roles** — restrict who sees it (blank = everyone)
- **Display frequency** — every visit / once a day / until dismissed, with an optional
  "don't show again for N days" (0 = forever)
- **Link button** — optional call-to-action (label + URL)
- **Priority** — display order when several notices match

The same management page can be embedded in another app's dashboard via
`script="popup_gazette:management/management.js"`. It auto-scopes to the app it is loaded
from, so app owners manage only their own notices while admins in the Popup Gazette app
manage everything.

## Permissions

| capability | grants |
|---|---|
| `gazette_admin` | full CRUD, global notices, Raw HTML mode, all-apps view |
| `gazette_edit` | notices scoped to the calling app; App/View targets and Markdown only |

Both are granted to `admin` and `sc_admin` by default. Global notices and Raw HTML are
enforced **server-side** — the client-side scoping is a convenience only, never a trust boundary.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
