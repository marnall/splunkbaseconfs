<!-- Copyright (c) 2026 Joshua Specht. All rights reserved. -->
# TA Studio

A browser-based GUI for building Splunk add-ons. TA Studio wraps the [UCC Framework](https://splunk.github.io/addonfactory-ucc-generator/) so you can create inputs, alerts, sourcetypes, field extractions, CIM mappings, and setup pages through a browser instead of editing JSON by hand or using the CLI.

---

## Screenshots

![Home page — project list](docs/screenshots/home.png)

![Add-on overview](docs/screenshots/addon-overview.png)

---

## Features

**Full add-on authoring workflow:**

| Step | What you can do |
|---|---|
| Create add-on | Name, author, version, description, icon, theme color |
| Data inputs | REST API, Python modular input, or shell command — with live test runner |
| Setup pages | Accounts, proxy, logging, and custom configuration tabs |
| Source types | KV_MODE, timestamp format, line-breaking rules |
| Field extractions | Regex builder with sample-data testing |
| Field transforms | Delimited (`DELIMS`), multivalue (`MV_ADD`), and reusable `transforms.conf` + `REPORT-` extractions for formats inline regex can't express |
| CIM mappings | Map fields to Common Information Model data models |
| Event types & tags | Define event type searches and assign CIM constraint tags — writes `eventtypes.conf` + `tags.conf` |
| Lookups | CSV **and KV Store** lookups — `transforms.conf` + `package/lookups/` or `collections.conf`; edit CSV data in-browser |
| Workflow actions | Drilldowns from search results to a URL or a secondary search (`workflow_actions.conf`) |
| Saved searches & reports | Bundle reports and scheduled searches — writes `savedsearches.conf` |
| Dashboards | Package Dashboard Studio (default) and Classic Simple XML views (`data/ui/views/`) with a built-in import guide |
| Alert actions | Adaptive response for Enterprise Security, with full field editor |
| Libraries | Vendor Python packages into `package/lib/` — importable in inputs, alerts, and the browser test runner |
| Build & package | UCC-gen build, AppInspect validation, Splunkbase-ready `.tar.gz` |

**Splunkbase compliance helpers:**
- **Third-party license attribution** — when you install a Python library on the Libraries page, TA Studio auto-generates `package/LICENSES/<lib>-<version>.LICENSE.txt` (and `.NOTICE.txt` if the wheel ships one) plus a top-level `package/THIRD-PARTY-LICENSES.md` summary. Required by Apache-2.0 and similar licenses when libraries are redistributed in the packaged add-on; cleared on remove. Manually regenerate via the Libraries page.

**AI assistance (optional, bring your own API key):**
- Generate input/alert action Python code from a plain-English description, get CIM field-mapping suggestions, make AI-assisted edits in the raw `globalConfig.json` and raw `.conf` file editors (the conf assistant prefers search-time settings and flags index-time ones), and **generate an app icon** from a short description (a flat SVG, sanitized and rasterized locally)
- Supported providers: Anthropic, OpenAI, Google Gemini, Groq, and xAI (Grok) — configure under **Settings → AI Assistant**
- Your API key is stored in Splunk's encrypted credential store and never returned to the browser; AI features stay hidden until a key is added

**Additional capabilities:**
- Raw `globalConfig.json` editor with live UCC schema validation
- Raw `.conf` file editor — edit any conf in `package/default/` (props, transforms, `app.conf`, `server.conf`, …) with parse validation, stanza counts, and AI assist for conf snippets
- **Code Files editor** — edit handler code and other text files under `package/bin/` directly, including custom collectors and alert helpers imported from an existing add-on that the wizards can't model, with AI assist for code edits (Python is syntax-checked on save, but a warning never blocks the save)
- **View source for imported handlers** — inputs/alerts imported from an existing add-on are read-only in the wizard, but their real handler code is always viewable (and editable from the Code Files editor)
- Drag-and-drop reorder on every list
- Optimistic delete with 5-second undo
- Wizard auto-save and dirty-state guard (your work survives a mis-click)
- AppInspect history with diff view (last 10 runs per project)
- Build/package job history
- Cmd/Ctrl-K command palette
- Light and dark themes
- Docs page — view and edit `README.md` and `CHANGELOG.md` with auto-generation from the current add-on shape

**Open any add-on — Windows & Linux:**

One **Open Add-on** dialog handles everything. Drag in or pick a **packaged add-on** (`.tar`, `.tar.gz`, `.tgz`, `.spl`, `.zip`, or a TA Studio `.ta-studio.zip` bundle) and TA Studio detects, as best it can, how it was built and opens it as a new project. **The file uploads straight from your browser, so there are no server paths or file permissions to set up** — the add-on can live anywhere, including your Desktop or Downloads. Installed apps under `$SPLUNK_HOME/etc/apps/` open in one click from the Home page (and are the route for add-ons larger than the 100 MB upload cap). It's all pure Python, so it runs on Windows and Linux alike (Splunk's own `import_from_aob` is a Linux-only shell script).

What you get depends on how the source add-on is structured:

| Source type | Detected by | What's migrated |
|---|---|---|
| Add-on Builder (AOB) | `addon_builder.conf` / compiled `globalConfig.json` | Inputs (modular + REST) — **Python inputs open editable**, converted to TA Studio's handler model — plus alert actions, accounts & proxy, and `lib/requirements.txt` |
| UCC add-on | `globalConfig.json` present | Opened as-is; recognizable Python handlers become editable, custom ones stay viewable/raw-editable |
| Conf-based / third-party | No AOB/UCC scaffolding | Whole app copied; `globalConfig.json` synthesized from `app.conf` + `inputs.conf`; **modular-input** stanzas become inputs; sourcetypes, field extractions, event types/tags, and lookups are read from their conf files |

**Custom handler code is never lost or hidden.** Handlers TA Studio can't model in a wizard (a hand-written UCC collector, a custom modular-alert helper) are shown **read-only** with a "View source" button, and are fully editable as raw files from the **Code Files** editor. Built-in inputs (`monitor://`, `script://`, `tcp/udp`, …) are preserved in the conf files but aren't turned into input forms.

All source files are preserved by the copy; opening never edits the original. Detection is automatic, and if a workspace already exists for the target name, TA Studio asks before overwriting.

---

## Requirements

| Dependency | Requirement | Notes |
|---|---|---|
| Splunk Enterprise | 9.2.0 or later | First release shipping Python 3.9 (required by the services layer). Tested through Splunk **10.4.0** |
| Python | Splunk's bundled `python` (3.9+) | Used by ucc-gen, AppInspect, and build subprocesses — no separate install |
| ucc-gen (`splunk-add-on-ucc-framework`) | 6.5.1 (managed) | TA Studio installs and manages an exact, tested version — see below |
| splunk-appinspect | 4.2.1 (managed) | TA Studio installs and manages an exact, tested version — see below |

The **About** page inside TA Studio reports the live, authoritative versions of Splunk, Python, ucc-gen, AppInspect, and pip on your server, with green/yellow/red compatibility status. Versions of the bundled web libraries are listed in [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).

---

## Installation

### 1. Install TA Studio from Splunkbase

In Splunk Web: **Apps → Find more apps**, search "TA Studio", click **Install**.

Or, install a downloaded `.tar.gz` directly:

- Splunk Web: **Apps → Manage Apps → Install app from file** → choose the `.tar.gz`.
- CLI:
  ```bash
  $SPLUNK_HOME/bin/splunk install app /path/to/ta_studio-<version>.tar.gz
  ```

### 2. Install Python dependencies into Splunk

TA Studio needs `ucc-gen` and `splunk-appinspect` accessible inside Splunk's Python environment. The easiest way is the built-in managed install: open TA Studio and it will offer to install them (also available any time from **Settings → Build Toolchain**). Each TA Studio release pins **exact, tested versions** of both tools so builds are reproducible.

To install manually instead, use the same pinned versions:

```bat
"C:\Program Files\Splunk\bin\splunk.exe" cmd python -m pip install splunk-add-on-ucc-framework==6.5.1 splunk-appinspect==4.2.1
```

On Linux:

```bash
$SPLUNK_HOME/bin/splunk cmd python -m pip install splunk-add-on-ucc-framework==6.5.1 splunk-appinspect==4.2.1
```

If you ever need a different version of either tool (for example, Splunkbase begins enforcing a newer AppInspect than the pin), set an override in **Settings → Build Toolchain → Advanced: override the managed versions** and click **Install managed versions**.

### 3. Restart Splunk

```bat
"C:\Program Files\Splunk\bin\splunk.exe" restart
```

```bash
$SPLUNK_HOME/bin/splunk restart
```

### 4. Open TA Studio

Navigate to **Apps → TA Studio** in Splunk Web.

### 5. Grant Splunkd access (only if needed)

Splunk runs under a service account (`NT SERVICE\Splunkd` on Windows, `splunk:splunk` on Linux/macOS). If you installed via Splunkbase or the standard `Apps → Manage Apps` flow, permissions are already correct and this step can be skipped.

This step is only needed if you manually placed the app under a path the service account can't read (e.g. a user-profile directory). In that case:

**Windows:**
```bat
icacls "C:\path\to\ta-studio" /grant "NT SERVICE\Splunkd:(OI)(CI)RX" /T
```

**Linux / macOS:**
```bash
chown -R splunk:splunk /path/to/ta-studio && chmod -R u+rx /path/to/ta-studio
```

---

## How workspaces work

Each add-on you build in TA Studio lives in its own **workspace** directory — a folder on disk holding the UCC project files (`globalConfig.json`, `package/`, etc.). TA Studio is an editor over that directory: open it, edit through the UI, build a Splunkbase-ready `.tar.gz`.

**Default location:** `$SPLUNK_HOME/var/run/ta_studio/workspace/` — owned by the Splunk service account, always writable. Bundle imports and AOB conversions land here automatically.

**Why this matters:** Splunkd needs read + write on the workspace directory. The default location is always writable, and add-ons now **upload from your browser** rather than being read off disk — so opening an add-on from your Desktop or Downloads, and saving edits, just work. The only way to hit a permission problem is to override `APPBUILDER_WORKSPACE_DIR` to a directory the service account can't write (or, for a manual dev install, to place the app itself under a path it can't read); you'll then see a "Workspace is not writable" banner on the Home page with the platform-appropriate fix.

**Recommendation:** keep workspaces in the default location unless you have a specific reason to move them. To override globally, set `APPBUILDER_WORKSPACE_DIR` and restart Splunk.

---

## Quick start

1. Click **New Add-on** on the Home page and fill in the project details.
2. Go to **Data Inputs → New Input** and choose REST, Python, or Shell mode.
3. Add fields to the input form using the widget builder, then click **Test** to run it against live data.
4. Continue through **Setup**, **Source Types**, **Field Extractions**, **CIM**, and **Alerts** as needed.
5. When ready, open the **Build** page → **Build & Validate** → **Package**.
6. Download the generated `.tar.gz` — ready for AppInspect or Splunkbase submission.

The bundled **TA TVMaze** example project covers every widget type and build step. Open it from the Home page to see a complete working add-on.

---

## Access control

TA Studio uses two Splunk capabilities to control access:

| Capability | Gates | Default grants |
|---|---|---|
| `view_ta_studio` | Reading projects, configs, lists | admin, sc_admin, power |
| `edit_ta_studio` | Creating/editing/deleting; build, validate, package | admin, sc_admin |

If you need additional roles to use TA Studio, create a `[role_<name>]` stanza in `$SPLUNK_HOME/etc/apps/ta_studio/local/authorize.conf`:

```ini
[role_developer]
view_ta_studio = enabled
edit_ta_studio = enabled
```

Users with no capability granted will see a 403 from the API. The SimpleXML view that hosts TA Studio is open to all users by default (so the tile appears in the apps list), but the API calls will fail without the capability.

---

## Troubleshooting

### "Splunk rejected the request — usually a permission or path access issue"

Add-ons now upload straight from your browser, so **selecting one from your Desktop or Downloads no longer needs any special access**. This message now points at the **workspace directory**, which the Splunk service account (`NT SERVICE\Splunkd` on Windows, `splunk:splunk` on Linux) must be able to write. You'll only see it if you've overridden `APPBUILDER_WORKSPACE_DIR` to a location Splunkd can't write, or (manual dev installs) placed the app under a path it can't read. Two fixes:

- **Use the default workspace** (`$SPLUNK_HOME/var/run/ta_studio/workspace/`) — owned by the service account, always writable, no ACL grant needed.
- **Grant write access** to your custom workspace directory with `icacls` (Windows) or `chown` + `chmod` (Linux/macOS).

### Imported add-on shows up empty (no inputs, no sourcetypes, blank metadata)

Usually a workspace-write problem: Splunkd registered the project but couldn't finish writing the converted files into the workspace. The Home page banner will say "Workspace is not writable" with the platform-appropriate fix command. (The whole add-on is uploaded up front, so a source that's only partially readable is no longer a cause.)

### Imported add-on's Configuration or Inputs tab shows "Something went wrong"

Some third-party add-ons ship files that disagree with their own `globalConfig.json` — a stale REST handler missing a setting, or an input pointing at a handler that reads a data input the add-on no longer registers — which surfaces after a build as a broken Configuration or Inputs page. TA Studio reconciles this when the add-on is opened; open the **Reconciliation** page (from the add-on's Overview hub, or the banner shown there) to see what was fixed automatically and to resolve anything that needs a decision, then rebuild and redeploy. Automatic fixes can be undone from the same page. Note: an add-on that ships native libraries built for a different Python version (e.g. Python 3.9 binaries that won't load on Splunk 10's Python 3.13) is an upstream limitation of that add-on — TA Studio reports it on the Reconciliation page but can't rewrite the add-on's bundled binaries.

### "API unreachable — check that the PSCA endpoint is registered and Splunk has been restarted"

Generic fallback from the SPA when splunkweb returns an error body that isn't JSON. Possible causes in order of likelihood:

1. **Splunkd hasn't restarted since installing TA Studio** — `splunk restart`.
2. **`restmap.conf` failed to load** — check `$SPLUNK_HOME/var/log/splunk/splunkd.log` for parse errors.
3. **The `edit_ta_studio` capability isn't granted to your Splunk role** — write requests will fail. Grant via Settings → Access controls → Roles.

### "Workspace is not writable" banner on the Home page

Same as the import-path permission issue but for an already-imported project. The banner includes the exact fix command for your platform. Either run it or delete and re-import the project under the default workspace location.

### Opened add-on is missing its Python libraries

Third-party libraries (vendored into `package/lib/`) aren't copied when opening a `.ta-studio.zip` bundle, and an add-on you open may reference libraries that aren't installed. The `requirements.txt` is preserved in `package/lib/` either way — reinstall from the **Libraries** page on the opened project. (An imported handler's `import` lines, e.g. `requests` or `dateutil`, are also listed there as commented entries to install.)

### Frontend changes don't appear after an update

The browser cached the old assets. Most assets are content-hashed and refresh automatically, but `index.css` has a stable filename. Hard-refresh with **Ctrl+Shift+R** (Windows/Linux) or **Cmd+Shift+R** (macOS).

### Build hangs or AppInspect doesn't finish

`ucc-gen` and `splunk-appinspect` must be installed into Splunk's bundled Python (step 2 above), not your system Python. Verify:
```bat
"C:\Program Files\Splunk\bin\splunk.exe" cmd python -m pip show splunk-add-on-ucc-framework splunk-appinspect
```

### "pip is not available in Splunk's Python" on the Libraries tab

Some Splunk builds ship a bundled Python without `pip`, which the Libraries tab needs to install third-party packages (and which `ucc-gen` needs to bundle them at build time). Add it from an elevated shell on the Splunk server, then reload the page:

```bat
REM Windows
"%SPLUNK_HOME%\bin\splunk.exe" cmd python -m ensurepip --upgrade
```
```bash
# Linux / macOS
"$SPLUNK_HOME/bin/splunk" cmd python -m ensurepip --upgrade
```

If `ensurepip` isn't available, download `get-pip.py` and run it with that same Python. The About page shows the current pip status.

### Input or alert "Test" output is hard to read

The Define & Test step uses a three-pane layout — **Parameters** (left), the code editor (middle), and **Output** (right). The Parameters and Output panes are collapsible (click the chevron in the pane header) and resizable (drag the divider); the Output pane opens automatically when you click **Test**. Your pane sizes are remembered.

### AI features return an error or "AI is off"

- **"AI is off" after switching provider** — API keys are stored per provider. Selecting a different provider in Settings requires pasting your key again and saving.
- **401 "Invalid API Key"** — make sure the key matches the selected provider. **Groq and xAI/Grok are different companies**: Groq keys start with `gsk_` (console.groq.com), xAI keys start with `xai-` (console.x.ai).
- **404 "model does not exist"** — the Model field has a stale or mistyped model id. Leave it blank to use the provider's default, or copy the exact id from your provider's model list (Groq Llama models need the `meta-llama/` prefix).
- AI calls are made by splunkd, so the Splunk server (not your browser) needs outbound HTTPS access to the provider's API.

---

## Support

Questions, bug reports, and feature requests — email <tastudiodev@outlook.com> or leave a comment on the TA Studio Splunkbase listing.

For licensing inquiries and commercial use permissions, email <tastudiodev@outlook.com> or see the License section below.

---

## Acknowledgements

TA Studio builds on the open-source [Splunk UCC Framework](https://splunk.github.io/addonfactory-ucc-generator/) (`splunk-add-on-ucc-framework`, Apache-2.0), invoked as a build tool. Its web interface bundles open-source JavaScript libraries (React, CodeMirror, dnd-kit, SWR, and others) — see [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) for the full list and their license texts.

Development of this project was assisted by AI tools, helping to accelerate building and bring this vision to life faster than one person could alone.

---

## Trademarks & affiliation

TA Studio is an independent project. It is **not affiliated with, endorsed by, sponsored by, or otherwise associated with Splunk Inc. or Cisco Systems, Inc.**

"Splunk" and "Splunkbase" are trademarks or registered trademarks of Splunk Inc. (a Cisco company) in the United States and other countries. All other product names, logos, and brands are property of their respective owners and are used here only for identification and to describe interoperability (nominative fair use). Use of these names does not imply endorsement.

"TA Studio"™ is an unregistered trademark claimed by Joshua Specht.

---

## License

Proprietary — free to use, no modification or redistribution permitted. See the LICENSE file shipped with the app.
