================================================================================
KANBAN BOARD  v1.0.0
================================================================================

OVERVIEW
========
Kanban Board is a Dashboard Studio extension visualization for Splunk that lets
you create and manage multiple kanban boards directly inside your dashboards.
Each board has user-defined columns, drag-and-drop cards, and configurable card
fields. All data is stored in the App Key Value Store and is accessible via
standard SPL lookups.

Features:
  - Create and manage multiple boards, each with its own column layout
  - Custom card fields (text, number, textarea, select, date)
  - Drag-and-drop cards within and between columns
  - Full CRUD via a dedicated search command (kanbanwrite)
  - Light and dark theme support
  - Read-only mode and single-board pin via viz options
  - Configurable auto-refresh interval
  - Per-write permission enforcement: a persistent banner appears when the
    searching user lacks write access
  - Corrupt column/field config recovery without data loss


REQUIREMENTS
============
  - Splunk Enterprise 9.4+ or Splunk Cloud
  - Dashboard Studio extension support (developed and tested on Splunk 10.4)
  - Modern web browser with JavaScript enabled


INSTALLATION
============
1. Install via Splunk Web (Apps > Manage Apps > Install app from file), or
   extract the app archive directly to $SPLUNK_HOME/etc/apps/kanban_board/.
2. Restart Splunk.
3. Navigate to the Kanban Board app from the home launcher.


QUICK START
===========
1. Open the Kanban Board app and click the "Kanban Board" dashboard.
2. Click the "+ Board" button in the toolbar to create your first board.
3. Add columns and custom card fields through the board settings (gear icon).
4. Click "+ Card" inside any column to add a card.
5. Drag cards between columns to update their status.


USING THE BOARD
===============

Cards
-----
Click "+ Card" inside a column to create a card. Click any card to open it and
edit its title, color, and any custom fields defined for that board. Delete a
card from within the card dialog.

Drag and Drop
-------------
Grab a card by its header area and drag it to any position within the same
column or to a different column. Sort order is preserved in the KV Store.

Board Settings
--------------
Click the gear icon in the top-right of the toolbar to open board settings.
Here you can rename the board, edit its description, add/remove/reorder
columns, and add/remove/reorder custom card fields.

Field types available: text, number, textarea, select (dropdown), date.

Board Picker
------------
The dropdown in the toolbar lists all boards. Use it to switch between boards
or to create a new one. If the viz option "boardId" is set, the picker is
hidden and the viz shows only that board.


ADDING THE VIZ TO YOUR OWN DASHBOARD
=====================================

Quick start (zero manual steps)
--------------------------------
1. Drag the "Kanban Board" visualization from the picker into your dashboard.
   Read access works instantly — your boards are visible immediately.

2. Write wiring (creating/editing/dragging cards) is added AUTOMATICALLY by
   the kanban_autowire modular input, which runs every 60 seconds. A banner
   in the panel tells you wiring is pending. Simply reload the page after
   about a minute and full interactivity will be available.

   The input can be disabled under Settings > Data inputs > Kanban Board
   dashboard auto-wiring if you prefer manual control. The check interval (default 60 seconds) can be tuned in inputs.conf ([kanban_autowire://default] interval). Steady-state cost per cycle is a single filtered REST call plus an in-memory marker check per kanban dashboard; no searches are dispatched.

3. Can't wait, or the input is disabled? Run this search right now:

      | kanbanwire dashboard=<your dashboard name>

   Then reload the page. The command wires all kanban panels in that
   dashboard in seconds, using your own Splunk permissions.

4. You can also clone the bundled "Kanban Board" demo dashboard
   (kanban_demo) as a fully wired starting point — it is ready to use
   out of the box without any additional steps.

Manual wiring (reference)
--------------------------
If you prefer to add the wiring by hand (for example to integrate the panel
into a larger existing dashboard definition), follow the steps below.

Where the JSON lives: open your dashboard, click Edit, then click the
Source icon ( </> ) in the toolbar. This shows the whole dashboard as one
JSON document with top-level sections: "dataSources", "visualizations",
"defaults", "layout", "inputs". You will MERGE entries into three of these
sections — do not replace the whole document. Studio validates the JSON
when you click Back/Apply, so a missing comma is caught immediately.

Scenario A — you already added the panel from the picker (most common)
-----------------------------------------------------------------------
1. In the Source editor, find your kanban panel under "visualizations":
   look for "type": "kanban_board.kanban". Note its id (e.g. "viz_AbC123")
   and the id of its primary data source (e.g. "ds_XyZ789").

2. In the "dataSources" section, find that primary data source and REPLACE
   its "query" value with the tokened read query (one line):

   "| makeresults | eval rectype=\"beat\", r=$kb_refresh|s$ | append [| inputlookup kanban_boards_lookup | eval rectype=\"board\"] | append [| inputlookup kanban_cards_lookup | eval rectype=\"card\"] | fields - _time"

   (Same as the picker query, plus the $kb_refresh$ cache-buster the viz
   uses to request fresh data after each write.)

3. Still in "dataSources", add the writer as a NEW entry (add a comma after
   the previous entry):

   "ds_kanban_writer": {
     "type": "ds.search",
     "name": "kanban writer",
     "options": {
       "query": "| makeresults | kanbanwrite payload=$kb_cmd|s$",
       "queryParameters": { "earliest": "-1m", "latest": "now" }
     }
   }

4. Back in your panel's entry under "visualizations", add the write binding
   and the event handlers, so it looks like this (keep your existing ids):

   BEFORE:
   "viz_AbC123": {
     "type": "kanban_board.kanban",
     "dataSources": { "primary": "ds_XyZ789" },
     "options": {}
   }

   AFTER:
   "viz_AbC123": {
     "type": "kanban_board.kanban",
     "dataSources": { "primary": "ds_XyZ789", "write": "ds_kanban_writer" },
     "eventHandlers": [
       { "type": "drilldown.setToken", "options": { "events": ["any"], "fields": ["kb_cmd"], "tokens": [{ "key": "value", "token": "kb_cmd" }] } },
       { "type": "drilldown.setToken", "options": { "events": ["any"], "fields": ["kb_refresh"], "tokens": [{ "key": "value", "token": "kb_refresh" }] } }
     ],
     "options": {}
   }

5. In the top-level "defaults" section, add the token default. If "defaults"
   already has content, merge — e.g. if it already contains a "dataSources"
   key, add "tokens" alongside it:

   "defaults": {
     ...existing content...,
     "tokens": { "default": { "kb_refresh": { "value": "0" } } }
   }

6. Click Back, then Save. Reload the dashboard; create a test card to
   confirm writes work.

Scenario B — writing a dashboard definition from scratch
--------------------------------------------------------
Use the bundled "Kanban Board" dashboard (kanban_demo) as a complete,
known-good reference: open it, click Edit then the Source icon ( </> ),
and copy its "dataSources", "visualizations", "eventHandlers" and
"defaults" sections wholesale. Rename ids to taste.

What each piece does:

  ds_kanban (primary read source)
    Runs on every refresh. The leading "| makeresults | eval rectype=\"beat\""
    row is required — it guarantees the search produces at least one result row
    so the viz knows the search has completed (an empty result set is
    indistinguishable from a still-loading search). The $kb_refresh$ token is
    a cache-buster: the viz updates this token to force a new search dispatch
    whenever it needs fresh data (after a write, on manual refresh, on timer).
    Board and card rows are tagged with rectype="board" / rectype="card" so the
    viz can separate them.

  ds_kanban_writer (write sink)
    Fires when the viz places a write envelope into the $kb_cmd$ token. The
    kanbanwrite command applies the operation to the KV Store collections with
    the searching user's permissions and emits a single acknowledgement row.
    The viz reads the ack row from the "write" data source binding to confirm
    or report the operation result.

  eventHandlers
    Two drilldown.setToken handlers listen for any drilldown event and copy the
    kb_cmd and kb_refresh fields from the viz into dashboard tokens. These
    handlers are what allow the sandboxed iframe visualization to communicate
    with the Dashboard Studio token layer.

  defaults (kb_refresh)
    Initialises the kb_refresh token to "0" so the read search can run before
    the viz has triggered its first refresh.


VIZ OPTIONS
===========
Set these in the visualization's "options" block in the dashboard JSON.

  boardId (string, default: unset)
    Pin the visualization to one board by its KV Store _key. The board picker
    toolbar is hidden. Example: "options": { "boardId": "abc123" }

  readOnly (boolean, default: false)
    Disable all write interactions (create/edit/delete/drag). The board is
    displayed but no changes can be made. Useful for audience-facing dashboards.
    Example: "options": { "readOnly": true }

  refreshInterval (number, default: 0)
    Automatically refresh board data every N seconds. Set to 0 (or omit) to
    disable. Refresh also fires on window focus regardless of this setting.
    Example: "options": { "refreshInterval": 30 }


DATA STORAGE AND SPL REPORTING
================================
All data lives in two KV Store collections:

  kanban_boards
    One record per board.
    Fields: _key, title, description, columns (JSON array), fields (JSON array),
            created (epoch int), modified (epoch int),
            created_by (username), modified_by (username)

  kanban_cards
    One record per card.
    Fields: _key, board_id, column_id, title, sort_order, color,
            fields (JSON array of {id, value} objects),
            created, modified, created_by, modified_by (all exposed via lookup)

Both collections have accelerated_fields on board_id (board index) and on
(board_id, column_id) (column index) for efficient per-board/per-column reads.

Lookup names (usable in any SPL search from any app):
  | inputlookup kanban_boards_lookup
  | inputlookup kanban_cards_lookup

Example: extract custom field values from a specific board's cards

  | inputlookup kanban_cards_lookup
  | where board_id="<your-board-key>"
  | spath input=fields output=card_fields
  | mvexpand card_fields
  | spath input=card_fields output=field_id path=id
  | spath input=card_fields output=field_value path=value

Audit fields (created, modified, created_by, modified_by) are set by the
kanbanwrite command and are never overwritten by a partial update — created/
created_by are immutable after the record is first inserted.


PERMISSIONS
===========
Write access (create, update, delete boards and cards) requires the user to
have write permission on the KV Store collections. The default ACL is:

  read:  all roles  (*)
  write: admin, power

These ACLs are set in kanban_board/metadata/default.meta and apply to the
collections, lookups, visualizations, and commands objects.

To grant write access to an additional role (e.g. "analyst"):

  1. In Splunk Web, go to Settings > Lookups > Lookup table files.
  2. Find the kanban_boards and kanban_cards collection entries under the
     kanban_board app context and click Permissions.
  3. Add write access for the desired role.

  Or edit kanban_board/metadata/default.meta directly and restart:

    []
    access = read : [ * ], write : [ admin, power, analyst ]

If a user without write access attempts any write operation, the viz displays a
persistent banner: "You don't have permission to modify this board's data —
changes won't be saved." The banner appears on the first failed write and
remains for the session. The viz detects the failure by inspecting the error
detail string from the ack row for permission/403/forbidden patterns.

Users with the readOnly viz option set see a read-only view regardless of their
collection permissions.


THE KANBANWIRE COMMAND AND AUTO-WIRING INPUT
=============================================

kanban_autowire — modular input (auto-wiring)
---------------------------------------------
Installed and enabled by default. Runs every 60 seconds and automatically
adds the write wiring (writer data source, event handlers, token default) to
any Dashboard Studio dashboard that contains a kanban_board.kanban panel, as
long as the dashboard has not been modified in the past 60 seconds (the quiet
period guards against wiring a dashboard mid-edit).

Events are written to the index with sourcetype=kanban:autowire each time a
dashboard is wired. To view them:

  index=* sourcetype=kanban:autowire

To disable: Settings > Data inputs > Kanban Board dashboard auto-wiring,
then click Disable next to the "default" instance.

kanbanwire — on-demand wiring command
--------------------------------------
| kanbanwire [dashboard=<name>] [app=<app>]

Wires all kanban dashboards (or just the named one) immediately, using your
own Splunk session permissions. Use this when you cannot wait for the
auto-wiring input, or when the input has been disabled.

Note: after running kanbanwire you must reload the dashboard page once for
the new wiring to take effect — Dashboard Studio caches the definition at
page load time.

Emits one row per view: {_time, dashboard, app, changed, detail}.

THE KANBANWRITE COMMAND
=======================
kanbanwrite is a custom Splunk streaming command (Python 3, chunked protocol)
that applies a single kanban write operation to the KV Store. It runs with the
permissions of the user executing the search — no elevated privileges are
granted. The command only ever touches the two app collections (kanban_boards
and kanban_cards).

The command accepts a single option:

  payload=<json-envelope-string>

The envelope is a JSON object with these keys:

  op      Required. One of: board.upsert, board.delete, card.upsert,
                             card.delete, card.move
  key     KV Store _key of the record to update/delete. Omit or leave empty
          to create a new record (upsert ops only).
  record  Fields to write (for upsert and move ops).
  nonce   Arbitrary string echoed back in the ack row for correlation.

The command emits exactly one row: {_time, status, op, nonce, key, detail}.
status is "ok" on success or "error" on failure; detail contains the error
message.

See default/searchbnf.conf for the formal syntax reference and examples.

The command depends on splunklib (vendored into kanban_board/lib/); no external
Python dependencies are required.


TROUBLESHOOTING
===============

Viz not visible in the visualization picker
  The visualization requires framework_type = studio_visualization support.
  Verify you are on Splunk Enterprise 10.x or a Splunk Cloud stack that
  supports Dashboard Studio extensions. Splunk 9.x may work but is not
  officially tested.

"kanban_board.kanban is not defined" error after install
  Splunk builds its config registry at startup. Restart Splunk after installing
  the app to register the visualization type.

Writes failing with "Unknown search command 'kanbanwrite'"
  The kanbanwrite command is exported via commands export = system in
  default.meta. If the error persists after install, restart Splunk — the
  command registry is built at boot, not on reload.

Board data briefly disappears / flashes blank on write
  Ensure you are running app version 1.0.0 or later. Earlier development
  snapshots did not include the heartbeat row in the read query, causing the
  viz to misinterpret a still-loading result as an empty data set.

The last action re-applies after a full page reload
  This is expected behavior. The kb_cmd token is encoded in the dashboard URL.
  On reload the writer data source replays the last envelope. The operation is
  effectively idempotent (same data, same key) but will bump the modified
  timestamp on the affected record.


KNOWN LIMITATIONS (v1)
=======================
  - Last-write-wins: there is no conflict detection. If two users edit the same
    card simultaneously the later write silently overwrites the earlier one.
  - Write latency is approximately 1–2 seconds because writes go through a
    search dispatch (token → search → KV Store → ack row → token update).
  - No per-board permissions in v1. All boards in the app share the same
    collection ACLs. Per-board role checks (allowed_roles field, enforced inside
    kanbanwrite) are planned for a future release.
  - No card search/filter, WIP limits, or assignee fields in v1.


SUPPORT
=======
campbell.goodall222@gmail.com
