## 1.0.0

Initial release.

**Boards**
- Create, rename, and delete boards; board description field
- Board picker in the toolbar to switch between boards; optional boardId viz
  option to pin to a single board (hides picker)

**Columns**
- Per-board user-defined columns with order control
- Add, rename, reorder, and delete columns via board settings

**Cards**
- Create, edit, and delete cards within any column
- Card color selection
- Drag-and-drop to reorder cards within a column or move them between columns;
  sort order is persisted in the KV Store

**Custom card fields**
- Per-board field definitions with five field types: text, number, textarea,
  select (dropdown with custom options), and date
- Add, reorder, and delete fields via board settings; field values stored as a
  JSON array on the card record

**Storage**
- All data stored in two KV Store collections: kanban_boards and kanban_cards
- Full audit trail: created, modified, created_by, modified_by on every record
- kanban_cards collection has accelerated indexes on board_id and
  (board_id, column_id)
- Lookups (kanban_boards_lookup, kanban_cards_lookup) exported for SPL reporting
  from any app context

**kanbanwrite command**
- Custom Python 3 streaming command (chunked protocol, vendored splunklib)
- Supported ops: board.upsert, board.delete, card.upsert, card.delete, card.move
- Runs with the searching user's permissions; no privilege escalation
- Emits one ack row per invocation; viz matches acks by nonce
- board.delete cascades to delete all cards for that board
- Exported as export = system so it is callable from any app context

**Permissions and access control**
- Default ACL: read = * (all roles), write = admin, power
- Persistent permission banner displayed on the first failed write attempt;
  banner detects permission errors by inspecting the ack row detail string
- readOnly viz option disables all write interactions regardless of collection
  permissions

**Theming and options**
- Light and dark theme support, following the Dashboard Studio theme
- Viz options: boardId (string), readOnly (boolean), refreshInterval (number,
  seconds; 0 disables)
- Window-focus refresh: data reloads whenever the browser tab regains focus

**Corrupt config recovery**
- Boards with invalid JSON in columns or fields fields render with an error
  indicator and empty column/field arrays instead of crashing; valid cards are
  still shown
