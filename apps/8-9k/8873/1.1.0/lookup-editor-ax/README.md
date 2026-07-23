# Lookup Editor AX

> 최종 정리: 2026-06-30

> Edit Splunk CSV lookups as easily as a spreadsheet, with per-lookup schemas to govern data structure and editing access. Built on React 18 + Webpack 5.

Lookup Editor AX edits Splunk CSV lookups as easily as a spreadsheet, with per-lookup schemas to govern data structure and editing access.

### Features

- **Five pages**
  - **Manager** — register/edit/delete CSV schemas (allowed columns, backup count, etc.)
  - **Editors** — edit multiple CSVs at once in tabs, with a list / per-app tree toggle
  - **List** — all CSV files with a "registered" badge
  - **Editor** — full-screen single-CSV editing via URL parameters (`?app=&filename=`)
  - **Docs** — in-app guide (KO/EN toggle)
- **Excel-style grid** — `react-data-grid` virtualization scrolls tens of thousands of rows smoothly
- **Field types (String / Number)** — columns are auto-loaded from the file in Manager; Number columns get soft numeric validation while editing (red cells + violation count, never blocks saving). Independent of the allowed-columns restriction
- **Go to row** — jump to a row number and center it, for navigating long files
- **Clipboard (TSV-compatible)** — copy a range in Excel and paste into the grid, or vice versa
- **Cell search** — `Cmd/Ctrl+F`, live filtering, case-insensitive across all columns
- **Undo / Redo** — 25 steps (`Cmd/Ctrl+Z`, `Cmd/Ctrl+Shift+Z` / `Ctrl+Y`)
- **Automatic backup/restore** — mtime-based backup on save, restore by point in time
- **Permission model** — fine-grained control via two custom capabilities
- **KO/EN i18n**

### Capabilities

| Capability | Pages | Allowed actions |
|---|---|---|
| `lookup_ax_admin` | Manager + Editors | Create/edit/delete schemas + edit CSVs |
| `lookup_ax_edit` | Editors (Manager is view-only) | Edit/save/back up &amp; restore CSVs |
| (none) | No access | Shows a lock notice |

By default the **admin** role (on-prem) and the **sc_admin** role (Splunk Cloud) are granted both capabilities. Other roles can be granted them under **Settings → Roles → (role) → Capabilities**.

Automatic app visibility filter: CSVs from apps the user cannot access (outside `/services/apps/local`) are hidden on both pages.

### Shortcuts

| Shortcut | Action |
|---|---|
| `Cmd/Ctrl + F` | Focus search (live filter, ESC to clear) |
| `Cmd/Ctrl + S` | Save (intercepts browser "save page") |
| `Cmd/Ctrl + Z` | Undo (25 steps) |
| `Cmd/Ctrl + Shift + Z` / `Ctrl + Y` | Redo |
| `Cmd/Ctrl + C` | Copy range or single cell → TSV |
| `Cmd/Ctrl + V` | Paste TSV (matrix fill from the anchor cell) |
| `Shift + click` | Select cell range |
| `Enter` / double-click | Cell edit mode (ESC to cancel) |
| **Go to row** + `Enter` | Jump to a row number (left of search) and center it |

### Search Head Cluster (SHC) behavior

| Data | Storage | SHC sync |
|---|---|---|
| Schema | KV Store `lookup_ax_schemas` (`replicate=true`) | ✅ auto-replicated by captain |
| CSV content | Splunk REST `/data/lookup-table-files/` | ✅ knowledge object replication |
| Backup files | Local FS (`lookup_file_backups/...`) | ❌ kept per member locally |

Edits sync to all members, but backup history exists only on the local member where the edit happened.

### Install

1. Install the Splunkbase package (`.tar.gz`) via **Apps → Manage Apps → Install app from file**, or extract it into `$SPLUNK_HOME/etc/apps/`.
2. **Restart Splunk** so the custom capabilities take effect.
3. Sign in as `admin` (or `sc_admin` on Cloud) and register a CSV schema in Manager.

### Package layout (installed)

```
lookup-editor-ax/
├── bin/                  # REST handlers (schema / editor / backup)
├── default/              # app.conf, authorize.conf, collections.conf, restmap.conf, web.conf, views, nav
├── metadata/default.meta # app permissions
├── static/               # app icons
└── appserver/static/     # build output (manager / editors / editor / list / docs)
```

> The source code (`src/`) and build config (`webpack.config.js`, `package.json`, etc.) are **not included in the distribution package — they live only in the GitHub repository.**

### Dependencies / License

- React 18 / Webpack 5
- `react-data-grid` (MIT) — virtualized grid
- `lucide-react` (ISC) — SVG icons
- `papaparse` (MIT) — CSV parsing

App license: **MIT** (see `LICENSE`).
