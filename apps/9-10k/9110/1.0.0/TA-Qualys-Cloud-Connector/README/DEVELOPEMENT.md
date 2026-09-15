# UCC-Based Splunk Add-on — Development Guide

> **Audience:** Developers familiar with Splunk and Python but **new to UCC-based add-ons**.
> This document uses `TA-Qualys-Cloud-Connector` as a concrete reference implementation.

---

## Table of Contents

1. [What Is UCC?](#1-what-is-ucc)
2. [Prerequisites](#2-prerequisites)
3. [Project Directory Structure](#3-project-directory-structure)
4. [The Central Piece: `globalConfig.json`](#4-the-central-piece-globalconfigjson)
5. [How UCC Generates the Add-on](#5-how-ucc-generates-the-add-on)
6. [Anatomy of a UCC Add-on (File-by-File)](#6-anatomy-of-a-ucc-add-on-file-by-file)
7. [End-to-End Data Flow (How an Input Runs)](#7-end-to-end-data-flow-how-an-input-runs)
8. [How-To: Add a New Field to an Existing Input](#8-how-to-add-a-new-field-to-an-existing-input)
9. [How-To: Add a Brand-New Input Type](#9-how-to-add-a-brand-new-input-type)
10. [How-To: Add a New Configuration Tab](#10-how-to-add-a-new-configuration-tab)
11. [How-To: Add a New Account Field](#11-how-to-add-a-new-account-field)
12. [Build, Package & Install](#12-build-package--install)
13. [Debugging Tips](#13-debugging-tips)
14. [Quick Reference: File Change Matrix](#14-quick-reference-file-change-matrix)
15. [Appendix: Official UCC Documentation](#15-appendix-official-ucc-documentation)

---

## 1. What Is UCC?

**UCC (Universal Configuration for Custom Add-ons)** is an open-source framework by Splunk that **auto-generates the UI, REST handlers, and configuration scaffolding** for Splunk add-ons.

Instead of hand-writing:
- Splunk XML dashboards for configuration pages
- Custom REST handlers for every field
- `restmap.conf`, `web.conf`, spec files, etc.

…you declare everything in **one JSON file** (`globalConfig.json`), and UCC generates all the boilerplate for you.

### UCC vs Traditional Add-on

| Aspect | Traditional Add-on | UCC Add-on |
|---|---|---|
| UI pages | Hand-written Splunk XML/JS | Auto-generated from `globalConfig.json` |
| REST endpoints | Custom Python REST handlers | Auto-generated `_rh_*.py` files |
| Config validation | Manual | Declarative validators in JSON |
| `.conf` / `.spec` files | Hand-maintained | Generated from JSON schema |
| Adding a field | Touch 5-8 files | Touch 1 JSON + 2-3 Python files |

---

## 2. Prerequisites

- **Python 3.9+**
- **Git** (UCC uses git tags for versioning; or use `--ta-version`)
- **pip** / **virtualenv**

```bash
# Create and activate a virtual environment
python3 -m venv .venv
# Windows (PowerShell)
.venv\Scripts\activate.ps1
# macOS/Linux
source .venv/bin/activate

# Install UCC
pip install splunk-add-on-ucc-framework
```

### Starting a New Add-on from Scratch

```bash
ucc-gen init \
  --addon-name "TA-My-Addon" \
  --addon-display-name "My Add-on for Splunk" \
  --addon-input-name my_input
```

This creates a `TA-My-Addon/` directory with the starter scaffold.

---

## 3. Project Directory Structure

Below is the layout of our `TA-Qualys-Cloud-Connector` addon. Every UCC-based addon follows this same pattern:

```
TA-Qualys-Cloud-Connector/
│
├── appserver/
│   ├── static/
│   │   └── js/build/
│   │       └── globalConfig.json    ★ THE HEART OF THE ADD-ON
│   └── templates/
│
├── bin/
│   ├── import_declare_test.py       # Path setup (auto-generated, do not delete)
│   │
│   ├── TA-Qualys-Cloud-Connector_rh_account.py   # REST handler for Accounts tab
│   ├── TA-Qualys-Cloud-Connector_rh_settings.py  # REST handler for Settings tabs
│   ├── TA-Qualys-Cloud-Connector_rh_vmdr.py      # REST handler for VMDR input
│   ├── TA-Qualys-Cloud-Connector_rh_was.py       # REST handler for WAS input
│   │
│   ├── vmdr.py                      # Modular input entry point for VMDR
│   ├── vmdr_helper.py               # UCC-generated helper (unused in our case)
│   ├── was.py                       # Modular input entry point for WAS
│   ├── was_helper.py                # UCC-generated helper (unused in our case)
│   │
│   ├── common/                      # Shared code (API clients, logging, etc.)
│   │   ├── api/                     # API client implementations
│   │   ├── checkpoint.py            # KV-store checkpoint management
│   │   ├── log.py                   # Logging utilities
│   │   ├── proxy.py                 # Proxy configuration
│   │   └── utility.py              # Common helpers
│   │
│   └── modinputs/                   # Actual data collection logic
│       ├── vmdr/
│       │   └── collector.py         # VMDR collection logic (VmdrCollector)
│       └── was/
│           └── collector.py         # WAS collection logic (WasCollector)
│
├── default/
│   ├── app.conf                     # App metadata
│   ├── inputs.conf                  # Default input stanza definitions
│   ├── restmap.conf                 # Maps REST endpoints → Python handlers
│   ├── web.conf                     # Exposes REST endpoints via Splunk Web
│   ├── props.conf                   # Source type / extraction config
│   ├── server.conf                  # Server config
│   ├── ta-qualys-cloud-connector_settings.conf  # Default settings values
│   └── data/ui/
│       ├── nav/                     # Navigation XML
│       └── views/                   # Dashboard XML views
│
├── lib/                             # Third-party Python libraries
│   ├── splunktaucclib/              # UCC REST handler framework
│   ├── splunklib/                   # Splunk SDK for Python
│   ├── solnlib/                     # Splunk solution library
│   ├── aiohttp/                     # Async HTTP (used by our collectors)
│   └── ...                          # Other dependencies
│
├── metadata/
│   ├── default.meta                 # Permissions and access control
│   └── local.meta
│
├── README/
│   ├── inputs.conf.spec             # Spec file documenting input parameters
│   ├── ta-qualys-cloud-connector_account.conf.spec
│   └── ta-qualys-cloud-connector_settings.conf.spec
│
├── LICENSES/
│   └── LICENSE.txt
│
├── app.manifest                     # Splunkbase manifest
├── VERSION                          # Current version string
└── README.txt
```

### Key Directories at a Glance

| Directory | Purpose |
|---|---|
| `appserver/static/js/build/` | Contains `globalConfig.json` — the single source of truth for UI |
| `bin/` | All executable Python — entry points, REST handlers, business logic |
| `bin/modinputs/` | Your actual data collection code (the "real work") |
| `bin/common/` | Shared utilities — API clients, logging, checkpoints |
| `default/` | Splunk `.conf` files — mostly auto-generated by UCC |
| `lib/` | Vendored Python packages (UCC lib, Splunk SDK, etc.) |
| `README/` | `.conf.spec` files documenting every parameter |
| `metadata/` | App permissions |

---

## 4. The Central Piece: `globalConfig.json`

Location: `appserver/static/js/build/globalConfig.json`

This single JSON file defines **everything** about your add-on's UI:

### Top-Level Structure

```json
{
    "pages": {
        "configuration": { ... },   // Configuration page (tabs: Account, Proxy, Logging, etc.)
        "inputs": { ... },          // Inputs page (each input type is a "service")
        "dashboard": { ... }        // Optional monitoring dashboard
    },
    "meta": {
        "name": "TA-Qualys-Cloud-Connector",
        "restRoot": "TA-Qualys-Cloud-Connector",
        "version": "1.0.0",
        "displayName": "Qualys Universal Technology Add-on (TA) for Splunk",
        "schemaVersion": "0.0.10",
        "_uccVersion": "6.1.0"
    }
}
```

### Configuration Page (`pages.configuration`)

Contains **tabs** — each tab is a section on the Configuration page:

```json
"configuration": {
    "tabs": [
        {
            "name": "account",       // Tab identifier
            "title": "Accounts",     // Display label
            "table": { ... },        // Table columns for listing
            "entity": [ ... ],       // Form fields (see below)
            "options": { ... }       // Optional: saveValidator JS function
        },
        { "name": "proxy", ... },
        { "name": "logging", ... },
        { "name": "additional_settings", ... }
    ]
}
```

### Inputs Page (`pages.inputs`)

Contains **services** — each service is a separate input type:

```json
"inputs": {
    "services": [
        {
            "name": "was",           // Must match the modular input script name
            "title": "WAS",
            "entity": [ ... ],       // Form fields for this input
            "inputHelperModule": "was_helper"  // Links to bin/was_helper.py
        },
        {
            "name": "vmdr",
            "title": "VMDR",
            "entity": [ ... ],
            "inputHelperModule": "vmdr_helper"
        }
    ],
    "table": { ... }                 // Column definitions for the inputs list table
}
```

### Entity Field Types

Each field in `entity` looks like this:

```json
{
    "type": "text",                 // text | singleSelect | checkbox | multipleSelect | radio
    "label": "Start Date (RFC3339)",
    "field": "start_date",          // The conf key name stored in inputs.conf / settings.conf
    "help": "Optional help text shown below the field",
    "required": false,
    "defaultValue": "",
    "encrypted": false,             // true for passwords/secrets → stored encrypted
    "validators": [
        {
            "type": "string",       // string | number | regex
            "minLength": 0,
            "maxLength": 64,
            "errorMsg": "Max length of text input is 64"
        },
        {
            "type": "regex",
            "pattern": "^$|^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$",
            "errorMsg": "Use RFC3339 UTC format: YYYY-MM-DDTHH:MM:SSZ"
        }
    ]
}
```

#### Field Types Reference

| Type | Renders As | Use For |
|---|---|---|
| `text` | Text input | Free-form strings, numbers |
| `singleSelect` | Dropdown | Pick one from a list |
| `checkbox` | Checkbox | Boolean on/off |
| `multipleSelect` | Multi-select dropdown | Pick many from a list |
| `radio` | Radio buttons | Small set of mutually exclusive options |

#### Validator Types Reference

| Validator | Parameters | Purpose |
|---|---|---|
| `string` | `minLength`, `maxLength` | Length validation |
| `number` | `range: [min, max]` | Numeric range |
| `regex` | `pattern` | Regular expression match |

#### singleSelect with Static Options

```json
{
    "type": "singleSelect",
    "field": "authentication_type",
    "options": {
        "disableSearch": true,
        "autoCompleteFields": [
            { "value": "basic", "label": "basic" },
            { "value": "oidc", "label": "oidc" }
        ]
    }
}
```

#### singleSelect Referencing Another Entity (e.g., Account)

```json
{
    "type": "singleSelect",
    "field": "account",
    "options": {
        "referenceName": "account"     // Populates from the "account" configuration tab
    }
}
```

---

## 5. How UCC Generates the Add-on

When you run `ucc-gen build`, UCC reads `globalConfig.json` and generates:

```
globalConfig.json
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  UCC Generator (ucc-gen build)                              │
│                                                             │
│  Reads entity definitions and produces:                     │
│                                                             │
│  1. bin/<ADDON>_rh_<tab>.py     → REST handler per tab      │
│  2. bin/<ADDON>_rh_<input>.py   → REST handler per input    │
│  3. bin/<input>.py              → Modular input entry point │
│  4. bin/<input>_helper.py       → Helper stub for your code │
│  5. default/restmap.conf        → Endpoint routing          │
│  6. default/web.conf            → HTTP method exposure       │
│  7. default/inputs.conf         → Default input values      │
│  8. default/<settings>.conf     → Default settings values   │
│  9. README/*.conf.spec          → Parameter documentation   │
│ 10. appserver/static/js/build/  → Frontend JS bundle        │
│ 11. lib/                        → Vendored Python packages  │
└─────────────────────────────────────────────────────────────┘
```

### What Is Auto-Generated vs What You Write

| File | Generated by UCC? | You Edit? |
|---|---|---|
| `globalConfig.json` | No — **you write this** | ✅ Yes |
| `bin/<ADDON>_rh_*.py` | ✅ Yes | ⚠️ Rarely (advanced customization only) |
| `bin/<input>.py` | ✅ Initially | ✅ Yes — we override with custom logic |
| `bin/<input>_helper.py` | ✅ Yes (starter stub) | ✅ Optional — UCC's simple entry point |
| `bin/modinputs/*/collector.py` | No — **you write this** | ✅ Yes — your core business logic |
| `bin/common/*` | No — **you write this** | ✅ Yes |
| `default/restmap.conf` | ✅ Yes | ❌ Rarely |
| `default/web.conf` | ✅ Yes | ❌ Rarely |
| `default/inputs.conf` | ✅ Yes | ⚠️ Only for defaults |
| `README/*.conf.spec` | ✅ Yes | ⚠️ Rarely |
| `lib/` | ✅ Yes (pip install) | ❌ No |

> **Key Insight:** For day-to-day development, you primarily edit `globalConfig.json` and your code in `bin/modinputs/` and `bin/common/`.

---

## 6. Anatomy of a UCC Add-on (File-by-File)

### 6.1 `import_declare_test.py`

```python
# Sets up sys.path so that lib/ (third-party packages) is importable
ta_name = 'TA-Qualys-Cloud-Connector'
# ... manipulates sys.path to include lib/ at the top
```

**Every** Python file in `bin/` starts with `import import_declare_test` to ensure `lib/` packages (splunklib, solnlib, splunktaucclib, etc.) are importable.

### 6.2 REST Handlers (`_rh_*.py`)

These files define the REST endpoints that Splunk Web calls when the UI saves/loads data.

**Example — Account REST handler (`TA-Qualys-Cloud-Connector_rh_account.py`):**

```python
from splunktaucclib.rest_handler.endpoint import field, validator, RestModel, SingleModel

fields = [
    field.RestField('api_server', required=True, encrypted=False, default='...', validator=...),
    field.RestField('password',   required=False, encrypted=True,  default=None, validator=...),
    # ... one RestField per entity field in globalConfig.json
]
model = RestModel(fields, name=None, special_fields=special_fields)

endpoint = SingleModel('ta-qualys-cloud-connector_account', model, config_name='account')
```

**Example — Input REST handler (`TA-Qualys-Cloud-Connector_rh_vmdr.py`):**

```python
from splunktaucclib.rest_handler.endpoint import field, validator, RestModel, DataInputModel

fields = [
    field.RestField('interval', ...),
    field.RestField('account', ...),
    field.RestField('start_date', ...),
    # ... matches entity fields in globalConfig.json
    field.RestField('disabled', required=False, validator=None),  # Always include this
]

endpoint = DataInputModel('vmdr', model)
```

**Pattern:**
- `SingleModel` → for configuration tabs (accounts, settings)
- `MultipleModel` → for settings with multiple sections (proxy + logging + additional_settings)
- `DataInputModel` → for input types

### 6.3 Modular Input Entry Point (`vmdr.py`, `was.py`)

This is the script Splunk's `splunkd` daemon invokes on each interval. It:

1. Defines `get_scheme()` — declares the input's arguments (must match `globalConfig.json` fields)
2. Loads the account credentials from the encrypted conf
3. Delegates to the real collector in `modinputs/<input>/collector.py`

```python
class VMDR(smi.Script):
    def get_scheme(self):
        scheme = smi.Scheme('vmdr')
        scheme.add_argument(smi.Argument('name', required_on_create=True))
        scheme.add_argument(smi.Argument('account', required_on_create=True))
        scheme.add_argument(smi.Argument('start_date', required_on_create=False))
        # ... one argument per field in the input's entity
        return scheme

    def stream_events(self, inputs, ew):
        # Load account, call collector
        import collector
        ac = collector.VmdrCollector()
        ac.run(input_items[1], account_info, event_writer, session_key)
```

### 6.4 Collector (`modinputs/*/collector.py`)

This is where your **actual business logic** lives — API calls, data transformation, event writing, checkpointing.

UCC doesn't generate this. You write it entirely.

### 6.5 Configuration Files in `default/`

| File | Purpose |
|---|---|
| `restmap.conf` | Maps REST endpoint names to their Python handler scripts |
| `web.conf` | Exposes endpoints via HTTP methods (GET, POST, DELETE) |
| `inputs.conf` | Default values for each input type |
| `ta-qualys-cloud-connector_settings.conf` | Default values for settings tabs |
| `app.conf` | App metadata, reload triggers |
| `props.conf` | Source type definitions and field extractions |

### 6.6 Spec Files in `README/`

These are `.conf.spec` files that document every parameter:

```
[vmdr://<name>]
account = Account to use for this input.
start_date = Optional RFC3339 UTC timestamp ...
interval = Time interval of the data input, in seconds. (Default: 3600)
```

---

## 7. End-to-End Data Flow (How an Input Runs)

Here is the complete lifecycle when a user creates and runs a VMDR input:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SPLUNK WEB UI                                                         │
│                                                                        │
│  1. User opens Configuration → Accounts tab                           │
│     → UI rendered from globalConfig.json "configuration.tabs[account]" │
│     → User fills in API server, username, password                     │
│     → Save → POST to REST endpoint                                    │
│     → TA-Qualys-Cloud-Connector_rh_account.py validates & stores      │
│     → Stored in: ta-qualys-cloud-connector_account.conf (encrypted)   │
│                                                                        │
│  2. User opens Inputs → clicks "Create New Input" → VMDR             │
│     → UI rendered from globalConfig.json "inputs.services[vmdr]"      │
│     → User fills in: name, interval, index, account, start_date, etc. │
│     → Save → POST to REST endpoint                                    │
│     → TA-Qualys-Cloud-Connector_rh_vmdr.py validates & stores         │
│     → Stored in: inputs.conf as [vmdr://<input_name>]                 │
└────────────────────┬────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  SPLUNKD (on each interval)                                            │
│                                                                        │
│  3. splunkd reads inputs.conf, sees [vmdr://my_vmdr_input]            │
│     → Launches bin/vmdr.py with the input config                      │
│                                                                        │
│  4. vmdr.py (Modular Input Entry Point)                               │
│     → import_declare_test.py sets up sys.path → lib/ is importable    │
│     → get_scheme() tells splunkd which arguments to expect            │
│     → stream_events() is called:                                      │
│        a. Reads account name from input_item['account']               │
│        b. Loads encrypted account credentials via solnlib/conf_manager│
│        c. Imports modinputs/vmdr/collector.py                         │
│        d. Creates VmdrCollector() and calls .run()                    │
│                                                                        │
│  5. collector.py (Your Business Logic)                                │
│     → Authenticates to Qualys API using account credentials           │
│     → Loads checkpoint (last collection timestamp)                    │
│     → Calls API to fetch new data since last checkpoint               │
│     → Transforms data → writes events via event_writer.write_event() │
│     → Updates checkpoint with new timestamp                           │
│     → Events arrive in the configured Splunk index                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Where Settings Are Stored at Runtime

| What | Stored In | Read By |
|---|---|---|
| Account credentials | `ta-qualys-cloud-connector_account.conf` (encrypted) | `conf_manager.ConfManager` |
| Proxy / Logging / Additional | `ta-qualys-cloud-connector_settings.conf` | `conf_manager.ConfManager` |
| Input definitions | `inputs.conf` (`[vmdr://name]`, `[was://name]`) | `splunkd` → passed to `stream_events()` |
| Checkpoint state | Splunk KV Store or file-based checkpoint | `bin/common/checkpoint.py` |

---

## 8. How-To: Add a New Field to an Existing Input

**Example:** Add a `page_size` field to the VMDR input.

### Files to Change (in order)

### Step 1: `globalConfig.json` — Add UI Field

**File:** `appserver/static/js/build/globalConfig.json`

Find the VMDR service's `entity` array and add:

```json
{
    "type": "text",
    "label": "Page Size",
    "field": "page_size",
    "help": "Number of records to fetch per API call.",
    "required": false,
    "defaultValue": "500",
    "validators": [
        {
            "type": "number",
            "range": [100, 5000],
            "errorMsg": "Value must be between 100 and 5000"
        }
    ]
}
```

### Step 2: `_rh_vmdr.py` — Add REST Field

**File:** `bin/TA-Qualys-Cloud-Connector_rh_vmdr.py`

Add to the `fields` list:

```python
field.RestField(
    'page_size',
    required=False,
    encrypted=False,
    default='500',
    validator=validator.Number(
        max_val=5000,
        min_val=100,
    )
),
```

### Step 3: `vmdr.py` — Add Scheme Argument

**File:** `bin/vmdr.py`

Add in `get_scheme()`:

```python
scheme.add_argument(
    smi.Argument(
        'page_size',
        required_on_create=False,
    )
)
```

### Step 4: `inputs.conf` — Add Default

**File:** `default/inputs.conf`

```ini
[vmdr]
...
page_size = 500
```

### Step 5: `inputs.conf.spec` — Document It

**File:** `README/inputs.conf.spec`

```
[vmdr://<name>]
...
page_size = Number of records per API call (Default: 500)
```

### Step 6: Use It in Your Collector

**File:** `bin/modinputs/vmdr/collector.py`

The field value arrives in `input_item`:

```python
page_size = int(input_item.get('page_size', 500))
```

### Summary: 6 Files for a New Input Field

| # | File | Change |
|---|---|---|
| 1 | `globalConfig.json` | Add entity to the service's array |
| 2 | `bin/<ADDON>_rh_<input>.py` | Add `field.RestField(...)` |
| 3 | `bin/<input>.py` | Add `scheme.add_argument(...)` |
| 4 | `default/inputs.conf` | Add default value |
| 5 | `README/inputs.conf.spec` | Add spec documentation |
| 6 | `bin/modinputs/<input>/collector.py` | Read and use `input_item['field']` |

---

## 9. How-To: Add a Brand-New Input Type

**Example:** Add a new `cs` (Container Security) input.

### Step 1: `globalConfig.json`

Add a new service under `pages.inputs.services`:

```json
{
    "name": "cs",
    "title": "Container Security",
    "entity": [
        { "type": "text", "field": "name", "label": "Name", "required": true, ... },
        { "type": "text", "field": "interval", "label": "Interval", "required": true, ... },
        { "type": "singleSelect", "field": "index", "label": "Index", ... },
        { "type": "singleSelect", "field": "account", "label": "Account to use",
          "options": { "referenceName": "account" }, ... },
        { "type": "text", "field": "start_date", "label": "Start Date", ... }
    ],
    "inputHelperModule": "cs_helper",
    "title": "Container Security"
}
```

### Step 2: Create REST Handler

**New file:** `bin/TA-Qualys-Cloud-Connector_rh_cs.py`

```python
import import_declare_test
from splunktaucclib.rest_handler.endpoint import field, validator, RestModel, DataInputModel
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging

util.remove_http_proxy_env_vars()

special_fields = [
    field.RestField('name', required=True, encrypted=False, default=None,
        validator=validator.AllOf(
            validator.Pattern(regex=r"""^[a-zA-Z]\w*$"""),
            validator.String(max_len=100, min_len=1)
        )
    )
]

fields = [
    field.RestField('interval', required=True, encrypted=False, default='3600',
        validator=validator.AllOf(
            validator.Pattern(regex=r"""^((?:-1|\d+(?:\.\d+)?)|..."""),
            validator.Number(max_val=86400, min_val=60)
        )
    ),
    field.RestField('index', required=False, encrypted=False, default='main', ...),
    field.RestField('account', required=True, encrypted=False, default=None, ...),
    field.RestField('start_date', required=False, encrypted=False, default='', ...),
    field.RestField('disabled', required=False, validator=None),
]

model = RestModel(fields, name=None, special_fields=special_fields)
endpoint = DataInputModel('cs', model)

if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(endpoint, handler=AdminExternalHandler)
```

### Step 3: Create Modular Input Entry Point

**New file:** `bin/cs.py`

Follow the pattern of `vmdr.py` — define `get_scheme()` with matching arguments, and in `stream_events()` delegate to your collector.

### Step 4: Create Helper Stub

**New file:** `bin/cs_helper.py`

Minimal implementation (can be a no-op if you override in `cs.py`).

### Step 5: Create Collector

**New file:** `bin/modinputs/cs/collector.py`

Your actual data collection logic.

### Step 6: Update `restmap.conf`

```ini
[admin:TA-Qualys-Cloud-Connector_inputs]
match = /
members = TA-Qualys-Cloud-Connector_vmdr, TA-Qualys-Cloud-Connector_was, TA-Qualys-Cloud-Connector_cs

[admin_external:TA-Qualys-Cloud-Connector_cs]
handlertype = python
python.version = python3
handlerfile = TA-Qualys-Cloud-Connector_rh_cs.py
handleractions = edit, list, remove, create
handlerpersistentmode = true
```

### Step 7: Update `web.conf`

```ini
[expose:TA-Qualys-Cloud-Connector_cs]
pattern = TA-Qualys-Cloud-Connector_cs
methods = POST, GET

[expose:TA-Qualys-Cloud-Connector_cs_specified]
pattern = TA-Qualys-Cloud-Connector_cs/*
methods = POST, GET, DELETE
```

### Step 8: Update `inputs.conf` and `inputs.conf.spec`

```ini
# default/inputs.conf
[cs]
python.version = python3
interval = 3600
index = main
start_date =
```

```ini
# README/inputs.conf.spec
[cs://<name>]
account = Account to use for this input.
start_date = Optional RFC3339 UTC timestamp ...
interval = Time interval (Default: 3600)
```

### Summary: Files for a New Input Type

| # | File | Action |
|---|---|---|
| 1 | `globalConfig.json` | Add service to `inputs.services` |
| 2 | `bin/<ADDON>_rh_cs.py` | Create REST handler |
| 3 | `bin/cs.py` | Create modular input entry point |
| 4 | `bin/cs_helper.py` | Create helper stub |
| 5 | `bin/modinputs/cs/collector.py` | Create collector (your logic) |
| 6 | `default/restmap.conf` | Add endpoint mapping |
| 7 | `default/web.conf` | Expose REST endpoint |
| 8 | `default/inputs.conf` | Add default stanza |
| 9 | `README/inputs.conf.spec` | Add spec |

---

## 10. How-To: Add a New Configuration Tab

**Example:** Add a "Rate Limiting" settings tab.

### Step 1: `globalConfig.json`

Add to `pages.configuration.tabs`:

```json
{
    "name": "rate_limiting",
    "title": "Rate Limiting",
    "entity": [
        {
            "type": "text",
            "label": "Max Requests Per Minute",
            "field": "max_rpm",
            "defaultValue": "60",
            "required": false,
            "validators": [{ "type": "number", "range": [1, 600] }]
        }
    ]
}
```

### Step 2: `_rh_settings.py`

Add a new fields + model section:

```python
fields_rate_limiting = [
    field.RestField('max_rpm', required=False, encrypted=False, default='60',
        validator=validator.Number(max_val=600, min_val=1)
    )
]
model_rate_limiting = RestModel(fields_rate_limiting, name='rate_limiting')

# Add to the endpoint's models list:
endpoint = MultipleModel(
    'ta-qualys-cloud-connector_settings',
    models=[model_proxy, model_logging, model_additional_settings, model_rate_limiting],
)
```

### Step 3: `ta-qualys-cloud-connector_settings.conf`

```ini
[rate_limiting]
max_rpm = 60
```

### Step 4: `ta-qualys-cloud-connector_settings.conf.spec`

```ini
[rate_limiting]
max_rpm =
```

### Step 5: Use in code

```python
from solnlib import conf_manager

cfm = conf_manager.ConfManager(session_key, ADDON_NAME,
    realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta-qualys-cloud-connector_settings")
settings = cfm.get_conf("ta-qualys-cloud-connector_settings")
max_rpm = int(settings.get("rate_limiting").get("max_rpm", 60))
```

---

## 11. How-To: Add a New Account Field

**Example:** Add a `platform` dropdown to the account configuration.

### Step 1: `globalConfig.json`

Add to the account tab's `entity` array:

```json
{
    "type": "singleSelect",
    "label": "Platform",
    "field": "platform",
    "required": true,
    "defaultValue": "US1",
    "options": {
        "disableSearch": true,
        "autoCompleteFields": [
            { "value": "US1", "label": "US Platform 1" },
            { "value": "US2", "label": "US Platform 2" },
            { "value": "EU1", "label": "EU Platform 1" }
        ]
    }
}
```

### Step 2: `_rh_account.py`

Add to `fields`:

```python
field.RestField('platform', required=True, encrypted=False, default='US1', validator=None),
```

### Step 3: `ta-qualys-cloud-connector_account.conf.spec`

```ini
[<name>]
...
platform =
```

### Step 4: Use in Collector

Account info is loaded via `conf_manager` — the new field is automatically available:

```python
platform = account_info.get("platform", "US1")
```

---

## 12. Build, Package & Install

### Build (from source)

```bash
ucc-gen build --source <package_dir> --ta-version 1.0.0
```

This reads `globalConfig.json` and regenerates all auto-generated files into `output/<ADDON>/`.

### Package

```bash
ucc-gen package --path output/TA-Qualys-Cloud-Connector
```

Produces a `.tar.gz` archive ready for Splunkbase or manual install.

### Install on Splunk

1. Go to **Splunk Web → Manage Apps → Install app from file**
2. Upload the `.tar.gz`
3. Restart Splunk when prompted

### Manual Development Install (Without Build)

For iterative development, you can skip the full UCC build and directly:

1. Edit `globalConfig.json` for UI changes
2. Edit the corresponding `_rh_*.py`, `<input>.py`, `.conf` files
3. Copy/symlink the add-on folder into `$SPLUNK_HOME/etc/apps/`
4. Restart Splunk (`splunk restart`)

---

## 13. Debugging Tips

### Log Locations

```
$SPLUNK_HOME/var/log/splunk/ta_qualys_cloud_connector_*.log     # Add-on logs
$SPLUNK_HOME/var/log/splunk/splunkd.log                          # General splunkd logs
```

Search in Splunk:
```spl
index=_internal sourcetype=splunkd component=ModularInputs "vmdr"
```

### Common Issues

| Symptom | Likely Cause |
|---|---|
| UI field doesn't appear | Missing entry in `globalConfig.json` entity |
| "Field not found" on save | Missing `RestField` in `_rh_*.py` |
| Input fails to start | Missing `scheme.add_argument()` in `<input>.py` |
| `ModuleNotFoundError` | Missing `import import_declare_test` or lib not vendored |
| REST 404 | Missing entry in `restmap.conf` or `web.conf` |
| Field value always None | Field name mismatch between `globalConfig.json` and code |
| Encrypted field returns `******` | Use `conf_manager` to read — it decrypts automatically |

### Restart Required?

| Change | Restart Needed? |
|---|---|
| `globalConfig.json` | **Yes** (browser hard-refresh may also be needed) |
| `_rh_*.py` | **Yes** |
| `<input>.py` | **Yes** |
| `collector.py` | **Yes** (new collection runs pick it up) |
| `.conf` file defaults | **Yes** |
| Logging level (via UI) | No — takes effect on next input run |

---

## 14. Quick Reference: File Change Matrix

| Task | globalConfig.json | _rh_*.py | <input_name>.py | inputs.conf | .conf.spec | collector.py | restmap.conf | web.conf |
|---|---|---|---|---|---|---|---|---|
| Add field to existing input | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | - | - |
| Add new input type | ✅ | ✅ (new) | ✅ (new) | ✅ | ✅ | ✅ (new) | ✅ | ✅ |
| Add config tab | ✅ | ✅ | - | - | ✅ | - | - | - |
| Add account field | ✅ | ✅ | - | - | ✅ | ✅ | - | - |
| Change field validation | ✅ | ✅ | - | - | - | - | - | - |
| Change default value | ✅ | ✅ | - | ✅ | - | - | - | - |

---

## 15. Appendix: Official UCC Documentation

- **UCC Framework Docs:** https://splunk.github.io/addonfactory-ucc-generator/
- **Quick Start:** https://splunk.github.io/addonfactory-ucc-generator/quickstart/
- **globalConfig.json Schema:** https://splunk.github.io/addonfactory-ucc-generator/entity/
- **Splunk Add-on Builder:** https://dev.splunk.com/enterprise/docs/developapps/manageknowledge/
- **Splunk SDK for Python:** https://github.com/splunk/splunk-sdk-python
- **Naming Conventions:** https://dev.splunk.com/enterprise/docs/releaseapps/splunkbase/namingguidelines/
