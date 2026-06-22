# Changelog

All notable changes to DASH Lite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.6] - 2026-05-27

### Fixed
- Added a canonical `[id]` stanza to `default/app.conf` to clear the future-enforcement AppInspect warning `check_version_is_valid_semver`. Splunkbase had flagged this as a check that would eventually start blocking releases.
- Added the `sc_admin` role alongside `admin` on the `views/builder` and `views/documentation` ACLs in `metadata/default.meta`, so Splunk Cloud customers (who use `sc_admin`, not `admin`) can access the app's knowledge objects.

## [1.0.5] - 2026-05-27

### Fixed
- Added `python.required = 3.9` to all REST handler stanzas in `restmap.conf` to satisfy the newly-enforced Splunk Cloud Vetting check `check_script_restmap_conf_python_required`. Kept `python.version = python3` alongside it for backward compatibility.

### Changed
- Aligned the `app.conf` / `app.manifest` version with the Splunkbase release number so the in-app version matches what users see on Splunkbase going forward.

## [1.0.0] - 2026-03-16

### DASH Lite — Free Preview Edition

Initial release of DASH Lite, the free preview of DASH - Styled App Builder for Splunk.

### Included
- **Visual Style Builder** — form-based CSS theme designer with live preview
- **Cybersecurity use case** — Security Posture Overview and Network Security dashboards
- **Color presets** — 10 named palettes for instant color scheme application
- **WCAG Contrast Checker** — real-time AA/AAA contrast ratio indicators
- **Theme Consistency Score** — 0-100 score evaluating contrast, harmony, typography, and coherence
- **Undo/Redo** — full state stack with Ctrl+Z/Ctrl+Y keyboard shortcuts
- **Auto-save drafts** — builder state saved to localStorage with resume prompt
- **Toggle Graph Colors** — switch between greyscale and colorized chart palettes
- **Fullscreen mode** — full-screen live preview
- **Integrated documentation** — in-app guides and CIM Query Reference

### Not included (Full version only)
- App export (Create Styled App, Download .spl)
- Inject Style into existing apps
- Import/Export JSON style configurations
- Style Audit (reverse-engineer CSS from existing apps)
- Style Guide Generator
- Gallery (save, browse, share team styles)
- IT Operations and APM use cases (10 additional dashboards)
- Preferences tab (panel menus, dashboard attributes, query type)

**Upgrade:** [mb2analytics.com/apps/dash](https://mb2analytics.com/apps/dash)
