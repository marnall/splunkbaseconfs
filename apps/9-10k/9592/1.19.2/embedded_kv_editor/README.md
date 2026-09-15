# Panel with Embedded KV Editor

**Version 1.19.2.** The **KV Editable Table** visualization: an editable table
over KV store records for classic Simple XML dashboards, added from the
visualization picker and configured in the Format menu. No scripts in your
dashboards, no server-side code.

## Install

Upload the `.spl` via **Apps → Manage Apps → Install app from file** (or untar
into `$SPLUNK_HOME/etc/apps/`), then **restart Splunk** (the Format options are
not picked up without it). **KV Editable Table** then appears in the
visualization picker of every classic dashboard panel. Splunk Enterprise
9.x/10.x and Splunk Cloud, classic Simple XML dashboards only (Dashboard
Studio does not load custom visualizations).

## Use

1. Run a search over your KV store lookup: `| inputlookup my_kvstore_lookup`.
2. Pick **KV Editable Table** on the Visualization tab.
3. In **Format → KV Editable Table** set the **Collection** and the
   **Editable fields**; save as a dashboard panel.

Every option and behaviour — inline and mass edit, sort, wrapped and
multiline fields, defaults and tokens, tables fed from logs, what gets
written, drilldown, troubleshooting — is documented in the app's **Help**
page (the panel's "?" and the Format menu link to it).

## Languages

The panel (buttons, messages, tooltips, dialogs), its Format menu, the
Help page, the demo dashboard and the visualization picker entry follow the
language of the dashboard (Splunk's locale, as in the URL), for every locale
Splunk ships: `de-DE`, `en-GB`, `en-US`, `fr-FR`, `it-IT`, `ja-JP`, `ko-KR`,
`zh-CN`, `zh-TW`. The Help entry in the app's menu is a normal dashboard
(Splunk chrome and theme included) showing the page in the dashboard's
language.
Anything not translated falls back to English. Field names, values and the
visualization's name (KV Editable Table) are never translated. Typing with
an IME (Japanese, Korean, Chinese) works in cells and in the popup.

Hand-written XML equivalent:

```xml
<viz type="embedded_kv_editor.kv_edit_table">
  <search><query>| inputlookup my_kvstore_lookup</query></search>
  <option name="drilldown">none</option>
  <option name="embedded_kv_editor.kv_edit_table.collection">my_collection</option>
  <option name="embedded_kv_editor.kv_edit_table.collectionApp">my_app</option>
  <option name="embedded_kv_editor.kv_edit_table.editableFields">status, comment</option>
</viz>
```

## Demo

The `kv_editor_demo` dashboard shows the table over the bundled demo
collection `kv_editor_demo` (lookup `kv_editor_demo_lookup`). The collection
is **exported to every app** and **writable by admins** out of the box
(`metadata/default.meta`); delete the demo if you do not use it.

## Security

Hardened by an adversarial audit: Save re-fetches each record and merges only
the fields shown as unsaved; a record someone else changed meanwhile is held
back; keys and field names `__proto__`/`constructor`/`prototype` are refused;
all record data reaches the page as text; writes use the user's own KV store
permissions. Nothing the table did not show you as unsaved is ever written.

## Release notes

- **1.19.2** — A Save or Create refused for lack of permission (HTTP 401/403,
  and a 404 during the write) now ends with *Nothing was written — your unsaved
  edits are kept.*; the mid-batch "Some records may have been written" sentence
  is reserved for failures that can actually leave a partial write. The 404
  message and Help also name the second possible cause (no read access — a
  denied collection answers 404 too). A new edit clears a lingering failure
  message. The Help states that Save counts rows in the table while the status
  line counts records written. Wording polish across all nine locales; the
  demo dashboard says the demo collection ships writable by admins.
- **1.19.1** — The demo collection now ships **writable by admins** rather than
  by everyone (`metadata/default.meta`) — give other roles write access to it
  to try the editor, or delete it; collections you create are unaffected (they keep their own permissions).
  A write refused for lack of permission now reads *Save failed (HTTP 403). You
  need write access to the collection.* without the mid-batch "some rows may
  have been written" note (a permission denial writes nothing). The examples'
  wrapped-column demo fields were renamed to `tags` and `notes`. Verified by a
  live permissions suite.
- **1.19.0** — **All nine Splunk locales.** The panel, the Format menu, the
  Help page, the demo dashboard and the picker entry are translated into
  German, French, Italian, Japanese, Korean, Simplified and Traditional
  Chinese (British English has its own Help page). The locale comes from
  the dashboard's URL; one small catalog is fetched per language, nothing
  for English. Messages carry proper plural forms. Also: every Format
  option now has a help line; IME input no longer closes the editor on the
  confirming Enter; the number-refusal message clears on the next edit and
  explains the decimal point; "(N lines)" markers stay translated; read-only
  text meets WCAG AA contrast; sorted headers announce their order and Save's
  tooltip names the collection; the "Add N missing rows" button is now
  "Create N records".
- **1.18.0** — Help moved to a static page (`appserver/static/help/`, opens from
  the panel's "?", the Format menu and the app's Help nav link) so it can be
  localised: `help/index.html` loads `help/<locale>.html` for the dashboard's
  language (any Splunk locale — de-DE, en-GB, en-US, fr-FR, it-IT, ja-JP,
  ko-KR, zh-CN, zh-TW), falling back to English until that file is added. The
  examples' panel 1 gains wrapped multivalue and multiline columns.
- **1.17.2** — **Wrapped fields** option (cells shown on several lines: line
  breaks kept, one value per line for multivalue). Field lists accept `;` as
  well as `,`. "Create missing records" is a dropdown with short labels. Help
  links work from both view and edit mode. Descriptions and README trimmed.
- **1.17.1** — Visualization renamed **KV Editable Table** (id `kv_edit_table`;
  panels built with 1.17.0 must be re-created). In-app **Help** dashboard,
  linked from the panel's "?" and from the Format menu; Format-menu help
  trimmed to one line per option. Keyboard: Tab/arrows move, Space selects,
  Enter edits; the hint appears only when focus arrives by keyboard. Real
  preview image in the visualization picker.
- **1.17.0** — **KV Editable Table: mass edit.** Press **Select cells**, click the
  cells of one column (Shift-click a range, or the header for all), then
  click a selected cell and edit it: the value
  becomes an unsaved edit on every selected row — Save, Discard, validation
  and conflict checks unchanged. Principle made explicit: only rows the table
  showed you as unsaved are ever written.


## License

MIT — see LICENSE.
