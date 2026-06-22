# Changelog -- Ensign Akamai Web Security Add-on (TA-ensign_waf_akamaisiem)

All notable changes to this add-on will be documented in this file.

---

## [1.0.9] -- 2026-04-14

### Added
- **LICENSE** (Apache 2.0) and **NOTICE** file with full third-party attribution and trademark disclaimers.
- **Post-upgrade cache clearing guide** in CLI Configuration Guide (3 methods: browser `_bump`, REST API, CLI).

### Changed
- **Rebranding:** Display label renamed from "Ensign Akamai SIEM Add-ons" to **"Ensign Akamai Web Security Add-on"** with "(powered by Akamai SIEM API)" tagline for clarity.
- **Source format:** Changed from `akamai_siem://{configId}` to `ensign_akamaisiem://{inputName}_{configId}` for easier event filtering.
- **Input name validation:** Now allows hyphens (`-`) in addition to alphanumeric and underscores.
- Updated all UI labels and help text to reflect "Web Security" branding.

### Compatibility
- Verified working on **Splunk 9.4.0** and **Splunk 10.0.1**.
- AppInspect: **0 errors, 0 failures** (precert mode).

---

## [1.0.8] -- 2026-04-13
**Build:** 1776104177

### Added
- **Custom Sourcetype field** -- new optional `custom_sourcetype` field in the input form allows overriding the default sourcetype (`ensign_akamaisiem`). Useful for migrating from existing sourcetype configurations.

### Fixed
- **Critical (Splunk 9.4 compatibility):** Downgraded bundled libraries that used Python 3.10+ union type syntax (`X | Y`), causing `SyntaxError` on Splunk 9.4 (Python 3.9):
  - `urllib3`: 2.6.3 -> 1.26.20
  - `charset_normalizer`: 3.4.7 -> 3.3.2
  - `requests`: 2.33.1 -> 2.31.0
- Fixed `lib/splunktaucclib/rest_handler/util.py` -- `print()` output to stdout redirected to `stderr` to prevent REST handler XML corruption.
- Fixed garbled help text encoding (triple UTF-8) in `globalConfig.json` for Akamai Account field.
- Fixed default index in REST handler from `default` to `main`.

### Changed
- Reverted `disabled = true` from `default/inputs.conf` -- this was inadvertently disabling all existing inputs during upgrades.

### Compatibility
- Verified working on **Splunk 9.4.0** and **Splunk 10.0.1**.

---

## [1.0.7] -- 2026-04-13
**Build:** 1776100467

### Changed
- Default index changed from `default` to `main`.
- Added `disabled = true` to default `inputs.conf` -- inputs no longer auto-start on installation.

### Added
- **CLI Configuration Guide** (`README/CLI_CONFIGURATION_GUIDE.conf.example`) -- step-by-step guide for configuring the add-on via conf files, including Deployment Server usage and verification queries.
- Completed all `.spec` files with proper field descriptions:
  - `ta_ensign_waf_akamaisiem_akamai_accounts.conf.spec` (new, replaces old mixed file)
  - `ta_ensign_waf_akamaisiem_proxy_servers.conf.spec` (new)
  - `ta_ensign_waf_akamaisiem_settings.conf.spec` (updated with descriptions)
  - `inputs.conf.spec` (fixed default values, removed reserved field)

### Removed
- Deleted old `ta_ensign_waf_akamaisiem_account.conf.spec` (contained mixed accounts + proxy fields).

---

## [1.0.6] -- 2026-04-13
**Build:** 1776100045

### Changed
- **Sourcetype renamed:** `akamaisiem` -> `ensign_akamaisiem` for Ensign branding consistency.
- Updated `props.conf` stanza from `[akamaisiem]` to `[ensign_akamaisiem]`.
- Updated default sourcetype value in `input_module_akamai_siem_source.py`.
- Updated `inputs.conf.spec` documentation.

---

## [1.0.5] -- 2026-04-13
**Build:** 1776099093

### Changed
- `state_change_requires_restart` set to `true` in `app.conf` -- Splunk now displays a restart required banner after install/upgrade.

### Fixed
- Name field validators updated: **spaces no longer allowed** in Account Name, Proxy Name, and Input Name. Users must use underscores (e.g., `Production_Account` instead of `Production Account`).
- Updated error messages to guide users: *"Use underscores instead of spaces"*.
- Backend REST handler validators synchronized with UI validators.

---

## [1.0.4] -- 2026-04-13
**Build:** 1776098435

### Fixed
- **Critical:** Fixed `globalConfig.json` corruption caused by serialization tool adding non-standard double-spacing. UCC schema parser rejected the formatting as "configuration file should be pure JSON".
- **Critical:** Restored missing closing bracket for `proxy_server` entity's `options` object -- was accidentally removed during reserved field cleanup.
- Replaced Unicode arrow character with ASCII `>` in help text for cross-platform compatibility.
- Removed unsupported `mapping` property from table headers (not available in UCC schema version `0.0.10`).
- File written without UTF-8 BOM (Byte Order Mark) to prevent UCC parsing errors.

---

## [1.0.3] -- 2026-04-13
**Build:** 1776095820

### Fixed
- **Critical:** Removed `sourcetype` from modular input entry point `get_scheme()` -- `sourcetype` is a reserved Splunk argument that caused XML parsing errors when defined as a modular input parameter.
- Removed `sourcetype` `RestField` from inputs REST handler.
- Removed `sourcetype` entity from `globalConfig.json` UI schema. Sourcetype is still applied automatically (`ensign_akamaisiem`) via `props.conf` and `input_module`.
- Created missing conf files required by REST handlers:
  - `ta_ensign_waf_akamaisiem_akamai_accounts.conf` (empty default)
  - `ta_ensign_waf_akamaisiem_proxy_servers.conf` (empty default)
- Added `sortedcontainers` library to `lib/` -- required dependency for `solnlib.timer_queue` (UCC framework).

---

## [1.0.2] -- 2026-04-13
**Build:** 1776094045

### Changed
- Version bump for production readiness review.

### Security
- **Deep scan passed:** All legacy hardcoded Config IDs removed from package.
- **Deep scan passed:** All legacy hardcoded proxy IPs removed from package.
- **Deep scan passed:** All legacy API hostnames removed from package.
- **Deep scan passed:** All client-specific identifiers and references sanitized.
- Cleaned test/sample files from `edgegrid` library (conftest.py, test files, sample configs, etc.).

---

## [1.0.1] -- 2026-04-13
**Build:** 1776093322

### Changed
- **Rebranding complete:** Renamed package to `TA-ensign_waf_akamaisiem`.
- Updated all REST endpoint references to match new package naming convention.
- Updated `props.conf` log source patterns to match new naming convention.
- Updated release notes in `app.manifest` -- removed client-specific script names.
- Generic index default set to `default` (user configurable).
- Author set to `Ensign Infosecurity Indonesia`.

---

## [1.0.0] -- 2026-04-13

### Added -- Initial Release
- **Framework:** Built on Splunk UCC (Universal Configuration Console) v6.3.0.
- **Modular Input:** Single configurable `akamai_siem_source` input replacing multiple legacy scripted inputs.
- **Multi-Account Management:** CRUD operations for multiple Akamai accounts with encrypted credential storage (Client Token, Client Secret, Access Token).
- **Account Enabled/Disabled Toggle:** Per-account enable/disable control with runtime validation.
- **Multi-Proxy Support:** Multiple proxy server configurations (HTTP, HTTPS, SOCKS4, SOCKS5) with per-proxy enable/disable toggle.
- **Proxy Enforcement:** Runtime validation -- if enabled proxies exist in the system, input must select one (FATAL error if not configured).
- **SSL Verification:** Configurable SSL verification toggle with custom CA certificate path support.
- **Centralized Logging:** Configurable log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
- **Offset-based Checkpointing:** Persistent offset tracking for data collection continuity.
- **Library:** `edgegrid-python` v2.0.5 (official Akamai library, Apache 2.0 license).
- **Compatibility:** Splunk Enterprise 8.x / 9.x / 10.x, Python 3.x.

### Migrated From
- Multiple hardcoded scripted inputs consolidated into 1 dynamic modular input.
- Removed hardcoded hostname-to-configID mappings from `transforms.conf`.
- Retained `country_codes.csv` lookup and `drop_summary_event` transform.
