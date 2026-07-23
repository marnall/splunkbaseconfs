# Splunk Whiteboard App

<p align="center">
  <img src="assets/listing_icon_400.png" alt="Splunk Whiteboard App icon" width="160" />
</p>

Draw architecture diagrams, workshop sketches, and presentation flows **inside Splunk** — powered by [Excalidraw](https://excalidraw.com), the open-source infinite canvas. No external whiteboard service, no separate login: boards live in Splunk KV Store and are available to everyone on your instance.

**GitHub:** https://github.com/bautt/splunk-whiteboard-app

<p align="center">
  <img src="assets/screenshot.png" alt="Splunk Whiteboard App — Cisco Data Fabric architecture diagram with Splunk shape library" width="900" />
</p>

---

## Get started

<p align="center">
  <img src="assets/screenshot-board-list.png" alt="Whiteboard App board list with thumbnail previews, example boards, and import/export actions" width="900" />
</p>

1. Open **Apps → Whiteboard App** (or go to `/en-US/app/whiteboard_app/whiteboard`).
2. Enter a name and click **Create board** to start from a blank Excalidraw canvas.
3. Draw with the Excalidraw toolbar. Your work **auto-saves** every few seconds.

From the board list you can search boards, filter by visibility, import or export boards, copy a shareable link, or delete boards you no longer need. Each card shows a thumbnail preview of the canvas. Use **Export all** to download every accessible board as individual `.whiteboard.json` files in a ZIP — handy for backup or moving boards to another instance.

---

## Drawing with Excalidraw

The canvas is a full Excalidraw editor embedded in Splunk Web. Use the toolbar at the top of the canvas. Double-click any shape to edit its label. Drag elements freely; hold `Shift` to constrain angles. Group elements with Excalidraw's built-in grouping (`Ctrl+G`). Keyboard shortcuts speed up common tools — see [Keyboard shortcuts](#keyboard-shortcuts) below.

The right sidebar adds Splunk-specific panels on top of Excalidraw — shapes, libraries, build steps, history, and export. Drag the left edge of the sidebar to resize it; your preference is remembered.

---

## Start from scratch, an example, or a copy

### Blank board

The fastest path: **Create board** on the home screen. You get an empty Excalidraw canvas. Add Splunk shapes from the sidebar, draw freehand, or import content (see [Export & import](#export--import) below).

### Example boards

The board list shows a **Example boards** section with ready-made architecture diagrams — Splunk Platform, Cisco Data Fabric, and SVA (C1/C11, C3/C13) reference architectures. Click **Use** to create your own editable copy as a private board and open it.

Example boards are shipped with the app and never change your work: **Use** always clones, so app updates that refresh the examples can't overwrite a board you've edited.

### Duplicate any board

Every board card has a **Duplicate** action that creates a private copy (`<name> (copy)`). Use it to branch off an existing board — including one you made from an example — or to keep a shared board as your own working copy. To reuse a layout across a team, make a board, share it (**Everyone**), and colleagues can duplicate it.

---

## Icons, shapes, and SVGs

Open the **Shapes** tab (Shape library) in the sidebar.

### Splunk infrastructure shapes

Categories include **Data Sources**, **Splunk Infrastructure** (UF/HF, Indexer, Search Head, Cluster Manager, Deployment Server, License Manager, Edge Processor, Ingest Processor, Splunk Cloud, and more), **Network**, and **Output / Destinations**.

Choose how shapes are inserted with the **Insert as** toggle:

| Mode | Best for |
|---|---|
| **Elements** | Editable Excalidraw vector groups — resize, restyle, and ungroup like native shapes |
| **SVG Icon** | A colourable SVG image on the canvas — pick a fill colour first, then click a shape |

In **SVG Icon** mode, use the colour picker, hex/RGB field, or preset swatches before inserting.

### Splunk Marketing Icons

Expand **Splunk Marketing Icons** at the bottom of the Shapes tab. Pick a colour, then click any of the 50 icons to place a tinted SVG on the canvas.

### Brand logos

Expand **Brand logos** for official Cisco, Kubernetes, OpenTelemetry, and Splunk marks. These use fixed brand colours (not tintable) and are useful in reference architectures.

### Excalidraw community libraries

Open the **Libraries** tab to browse [libraries.excalidraw.com](https://libraries.excalidraw.com/). Enable the catalog (one-time consent), then click **Import** on a library. Shapes appear in Excalidraw's library panel (book icon in the bottom-left toolbar) for drag-and-drop onto the canvas.

---

## Export & import

From the board list, **Export** on a card downloads that board as `<name>.whiteboard.json`. **Export all** downloads every accessible board as individual JSON files inside a ZIP archive — ideal for backup or migration. **Import board…** loads one or more `.whiteboard.json` files (or a legacy collection export) as new private boards.

On the canvas, open the **Export** tab in the sidebar.

### Board backup (move between instances)

| Action | What it does |
|---|---|
| **Download board JSON** | Saves a `.whiteboard.json` file with elements, canvas settings, and embedded images — the app's native format |
| **Import board JSON…** | Loads a `.whiteboard.json` file onto the canvas (replaces current content; confirm before import) |

Use board JSON to back up work, share diagrams with colleagues, or move boards to another Splunk instance. After import, the board auto-saves once you return to editing.

### Images and sharing

| Action | What it does |
|---|---|
| **Download PNG** | Raster image of the canvas |
| **Download PDF** | PDF export of the canvas |
| **Copy shareable link** | URL that opens this board directly in Splunk |

### Dashboard Studio

**Dashboard Studio JSON** renders the canvas as a PNG and generates JSON you can paste into Dashboard Studio → Source as a `splunk.image` panel.

---

## Present your diagram

### Build mode (reveal on click)

Open the **Build** tab for PowerPoint-style progressive reveal:

1. Select elements (or a group) and click **Add selection as step N**, or use **Auto** (by group, left→right, top→bottom, etc.).
2. Reorder steps with ↑/↓, focus a step on the canvas, or remove steps.
3. Click **Present**. Each click (or `→` / `Space`) reveals the next step; `←` steps back; `Esc` exits.

Toggle **Fade** and **Follow** (camera pans to each new group) from the presentation bar. Reveal mode does not change your saved board — the scene is restored when you exit.

If a board has no build steps, Present mode steps through Excalidraw **frames** as slides instead.

### Version history

Open the **History** tab. **Save snapshot** captures a named checkpoint; **Restore** rolls the board back to that state.

---

## Sharing & access

Boards can be **private** (default) or **shared**:

| Visibility | Who can access |
|---|---|
| **Just me** (private) | Only you — stored in your Splunk user KV Store namespace |
| **Everyone** (shared) | All users who can open Whiteboard App |

When you create a board, visibility defaults to **Just me**. Open the board and click **Share with everyone** to move it to the shared namespace. Shareable links and the board list copy-link action work only for shared boards.

> **Note on private boards:** "Just me" uses your Splunk user KV Store namespace, so other standard users cannot see it. Splunk administrators with the `admin_all_objects` capability can still view all users' private boards. Private boards are for separation and tidiness, not for storing sensitive secrets.

To restrict who can write shared boards, see [DEVELOPER.md](DEVELOPER.md) (KV Store ACLs).

---

## Requirements

| | |
|---|---|
| Splunk Enterprise | ≥ 9.0.0 |
| Splunk Cloud (Victoria) | ≥ 9.0.0 |

**After install or upgrade:** restart Splunk when Manager shows **Restart Required** (`state_change_requires_restart` in the app package). Opening the app before restart can return HTTP 500.

---

## Reset & uninstall

The **About** tab has a *Danger zone* with **Delete all whiteboard data** — a guarded, type-to-confirm action that purges all boards, version history, snapshots, and preview thumbnails from KV Store. Use it to:

- **Clean up before uninstalling** the app, so no board data is left behind.
- **Reset to factory defaults** — because the shipped **example boards** live in the app bundle (not KV Store), they survive the purge. After a cleanup you're left with a clean board list and the examples ready to clone again.

The purge clears all **shared** boards (for every user) plus **your own private** boards. Other users' private boards live in their own KV namespaces and are removed automatically when an admin uninstalls the app. **This cannot be undone** — export anything you want to keep first.

---

## For developers

Build, deploy, extend shapes, add example boards, and repository layout: **[DEVELOPER.md](DEVELOPER.md)**.

---

## Keyboard shortcuts

Excalidraw keyboard shortcuts work on the canvas: `V` select, `T` text, `R` rectangle, `A` arrow, `P` free-draw, `E` eraser, `Ctrl +/-` zoom, `Shift 1` fit canvas, and more. Tool buttons show their shortcut keys on hover.
