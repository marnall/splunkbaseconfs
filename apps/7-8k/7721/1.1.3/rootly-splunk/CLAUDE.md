# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Splunk app that integrates with Rootly's incident management platform. The app creates a custom alert action in Splunk that forwards alerts to Rootly's API to trigger incidents.

## Architecture

### Core Components

1. **Alert Action Handler** (`bin/rootly.py`)
   - Python script that executes when Splunk triggers the Rootly alert action
   - Receives alert payload via stdin when called with `--execute` flag
   - Retrieves integration URL from four sources (in priority order):
     1. Per-alert override (`integration_url_override`)
     2. Conf file on disk (`rootly.conf` via configparser, accessible to all app users)
     3. Stored password (realm: `rootly-splunk`, username: `integration_url`)
     4. Default config (`integration_url` from alert_actions.conf)
   - Sends JSON payload to Rootly API via HTTPS POST request
   - Reads conf files directly from disk (standard Splunk alert action pattern, works for non-admin users)
   - Falls back to Splunk SDK's `storage_passwords` API for backward compatibility
   - Requires Python 3 (configured via `python.version = python3` in alert_actions.conf)

2. **Setup Interface** (`appserver/static/javascript/views/`)
   - Web-based setup dashboard using Backbone.js and Splunk JS SDK
   - Entry point: `setup.js` loads `setup_page.js` which renders the configuration UI
   - `setup_page.js`: Main view controller that handles user input and validation
   - `storage_passwords.js`: Manages secure credential storage in Splunk's storage/passwords endpoint
   - `setup_configuration.js`: Handles app configuration completion and reload
   - Uses Splunk's storage/passwords API to store integration URL with realm `rootly-splunk`
   - Setup view template defined in `setup_page_template.js`

3. **Configuration Files**
   - `default/app.conf`: App metadata (version 1.1.2, setup view configuration)
   - `default/alert_actions.conf`: Defines the "rootly" alert action with integration_url parameter
   - `default/rootly.conf`: Default (empty) integration URL; local/rootly.conf stores the configured value
   - `default/data/ui/alerts/rootly.html`: Alert action configuration form with URL override field
   - `metadata/default.meta`: Permissions (alert_actions/rootly and rootly conf exported to system scope)

### Data Flow

1. User configures integration URL via setup dashboard
2. JavaScript stores URL in both `rootly.conf` (via conf API) and `storage/passwords` endpoint
3. When alert triggers, Splunk calls `bin/rootly.py --execute`
4. Script reads integration URL from `rootly.conf` on disk (no special capabilities needed)
5. Script sends HTTPS POST to Rootly API
6. Script exits with code 0 (success), 1 (usage error), or 2 (notification failure)

## Development Commands

### Validation and Release

```bash
# Install splunk-appinspect (Python package)
pip install splunk-appinspect

# Validate the app (must be run from parent directory with app in subdirectory)
mkdir -p /tmp/splunk-validate
cp -r . /tmp/splunk-validate/rootly-splunk
splunk-appinspect inspect /tmp/splunk-validate/rootly-splunk

# Create release archives (as done in CI)
cd /tmp/splunk-validate
zip -r rootly-splunk.zip rootly-splunk
tar -czvf rootly-splunk.tar.gz rootly-splunk
```

### Local Development

For local development and testing:

```bash
# Install Node.js (required for JavaScript development)
mise install  # Uses mise.toml to install node latest

# Manual testing requires a Splunk instance
# The app directory should be placed in $SPLUNK_HOME/etc/apps/rootly-splunk/
# After changes, restart Splunk or reload the app
```

### Installation

The app must be installed on Splunk search heads (not indexers or forwarders). Installation is typically done through Splunk Web Admin UI.

## Key Technical Details

- **Python version**: Python 3 required (configured in alert_actions.conf)
- **Dependencies**: Uses bundled `splunklib` SDK (Apache License 2.0, in `lib/` directory)
- **Security**: All integration URLs must use HTTPS (enforced in rootly.py:52-54)
- **App namespace**: `rootly-splunk` (used for app context and secret realm)
- **Secret storage realm**: `rootly-splunk` (for storage/passwords API)
- **JavaScript modules**: Uses ES6 modules with Backbone.js and Splunk JS SDK
- **Storage password format**: Passwords stored as `realm:username:` (e.g., `rootly-splunk:integration_url:`)

## JavaScript Architecture

The setup interface uses a modular JavaScript architecture with utility functions:

- **promisify utility** (`utils.js`): Converts callback-based Splunk SDK functions to Promises
- **Storage password management** (`storage_passwords.js`):
  - `write_secret()`: Deletes existing password and creates new one (delete-then-create pattern)
  - `fetch_storage_password()`: Retrieves password by `realm:username:` identifier
  - Uses polling loop to ensure password deletion completes before creation
- **App namespace**: Fixed as `{owner: "nobody", app: "rootly-splunk", sharing: "app"}`
- **Setup completion**: Updates `app.conf` stanza `[install]` with `is_configured=true`, then reloads app

## Release Process

Releases are automated via GitHub Actions (`.github/workflows/release.yml`):
1. Push a tag matching `v*` pattern (e.g., `v1.0.1`)
2. Workflow runs splunk-appinspect validation
3. Creates .zip and .tar.gz archives
4. Publishes GitHub release with artifacts

## Important Constraints

- App must pass `splunk-appinspect` validation before release
- Prohibited files (.git*, .DS_Store, __MACOSX, .github) are automatically removed during release
- App directory structure must have all files inside `rootly-splunk/` subdirectory for packaging
- Alert action script must handle three configuration sources with correct priority

## Common Development Patterns

### Modifying the Alert Action

When editing `bin/rootly.py`:
- Always test with `--execute` flag: `echo '{"configuration": {...}, "session_key": "..."}' | python bin/rootly.py --execute`
- Ensure HTTPS validation remains in place (line 52-54)
- Remember that `session_key` is deleted from payload before sending (line 47)
- Exit codes: 0 = success, 1 = usage error, 2 = notification failure

### Modifying the Setup UI

When editing JavaScript in `appserver/static/javascript/views/`:
- All modules use ES6 imports/exports
- Changes require Splunk app reload to take effect
- Setup view is rendered via Backbone.js at `#main_container` element
- Storage passwords use delete-then-create pattern (never update in place)

### Configuration Priority

Integration URL resolution order (highest to lowest priority):
1. Per-alert override: `action.rootly.param.integration_url_override` (from alert form)
2. Conf file on disk: `rootly.conf` via Python `configparser` (standard Splunk pattern, accessible to all app users)
3. Stored credential: `storage/passwords` endpoint with realm `rootly-splunk` (backward compatibility)
4. Default config: `alert_actions.conf` `param.integration_url`

## Troubleshooting

### Common Issues

1. **"Integration url must be configured" error**
   - Check all three configuration sources in priority order
   - Verify storage password realm is exactly `rootly-splunk` (case-sensitive)
   - Ensure username is `integration_url` (not `integration_url_override`)

2. **"URL must use HTTPS" error**
   - Integration URL must start with `https://`
   - Check both stored passwords and alert_actions.conf

3. **Setup page not saving**
   - Verify app namespace: `{owner: "nobody", app: "rootly-splunk", sharing: "app"}`
   - Check that `is_configured` gets set to `true` in `app.conf [install]` stanza
   - Ensure storage password delete completes before create (polling loop in write_secret)

4. **splunk-appinspect validation failures**
   - Ensure no prohibited files exist (.git*, .DS_Store, __MACOSX, .github)
   - Verify app must be in subdirectory named `rootly-splunk` for inspection
   - Check Python version is set to `python3` in `alert_actions.conf`
