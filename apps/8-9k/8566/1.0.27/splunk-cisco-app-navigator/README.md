# Splunk Cisco App Navigator (SCAN) for Splunk

**Codename:** "The Front Door"  
**Author:** Cisco Systems  
**Version:** 1.0.27  
**Compatibility:** Splunk Enterprise / Splunk Cloud 9.0+

## What It Does

The **Splunk Cisco App Navigator (SCAN)** is the unified "Glass Pane" for the Cisco-Splunk ecosystem. It provides a single Product Catalog UI where Splunk administrators can discover, install, configure, and monitor all Cisco integrations — across Security, Observability, Networking, and Collaboration domains.

Each Cisco product is represented by an **intelligent card** that actively inspects the local Splunk environment and surfaces real-time status: installed apps, available upgrades, data flow validation, and legacy debt detection.

## Getting Started

1. Install the app on your Splunk Search Head (or Search Head Cluster).
2. Open the app — the **Products** page is your landing view.
3. Browse the **Available Products** catalog and click **+ Add** to add products to your workspace.
4. Use **Install** buttons to install the required add-ons and visualization apps directly from Splunkbase.
5. Click **Launch** to open dashboards for configured products.
6. Use the **Secure Networking** pill to filter products by Cisco's Secure Networking GTM strategy.

## Key Features

### Product Catalog
- **93 Cisco products** across 4 categories: **Security** (44), **Networking** (35), **Observability** (3), **Collaboration** (12).
- **19 subcategories** for granular filtering within Security, Networking, Collaboration, and Observability.
- **Product lifecycle tracking** via `date_created` and `date_updated` fields on every product card.

### Product Sections
- **Configured Products** — Products the user has added to their workspace.
- **Detected Products** — Products with live data flowing (auto-detected via sourcetype scan).
- **Available Products** — Products available for deployment with supported Splunk add-ons.
- **Integration Needed** — Cisco products without a dedicated Splunk integration (visible in dev/GTM mode).
- **Coming Soon** — Products under active development.
- **Deprecated Products** — Add-ons being sunset or replaced.
- **Retired Products** — Cisco products that have reached end-of-life.
- **GTM Roadmap — Coverage Gaps** — Products in the Secure Networking GTM with no Splunk coverage yet.
- **Custom Products** — Customer-created product cards stored in `local/products.conf`.

### Intelligence Badges (Per Card)
- **Add-on Installed / Not Installed** — Real-time TA detection via `/services/apps/local`.
- **App Installed / Not Installed** — Visualization app detection.
- **Update Available: vX.Y.Z** — Orange badge when a newer version is detected.
- **Data Flowing (N events)** — Live 24h event count per product's sourcetypes.
- **Data Found — No Add-on Detected** — Orphaned data warning.
- **N Legacy Apps Detected** — Red badge with hover tooltip listing each legacy app.
- **SOAR** — Purple badge for products with Splunk SOAR connectors (15 products).
- **SecOps** — Slate badge for products with ES/SSE content (36 products).
- **ITOps** — Indigo badge for products with ITSI/ITE Learn content (12 products).
- **Alert Actions** — Rose badge for companion alert action add-ons (12 products).
- **SC4S** — Blue badge for products with SC4S documentation (23 products).
- **NetFlow** — Badge for products with NetFlow collection guidance (11 products).
- **Platform: Enterprise / Cloud** — SVG platform compatibility badge.

### Version Intelligence & Upgrade Buttons
- Detects installed app versions and highlights available upgrades.
- Separate orange upgrade buttons for TA and viz app upgrades.

### Legacy Debt Auditor
- Scans `/services/apps/local` against the product catalog's legacy app mappings.
- Per-card red badge, page-level legacy banner, and detailed Legacy Audit Modal.

### Optimized Data Validation (MTTI)
- **Single search** validates all 320 unique sourcetypes across products in one SPL query.
- Uses `| metadata type=sourcetypes` for sub-second validation.
- Results distributed to individual cards — green (data flowing), orange (orphaned), or yellow (no data).
- **Mean Time to Innocence (MTTI):** Proves data flow instantly to eliminate finger-pointing.

### FilterDrawer (Sidebar)
- Sidebar drawer with advanced filters: support level, visibility toggles, onboarding (SC4S/NetFlow), platform, version compatibility.
- "No Integration" support level pill (visible in dev/GTM mode only).
- ActiveFilterChips bar shows selected filters with clear-all.
- Splunkbase CSV sync button inside drawer.

### Category Filter Bar
- Horizontal pill-style filter bar with live counts per category.
- **Cross-cutting filters**: SOAR (15), SecOps/ES (36), ITOps (12), Alert Actions (12), SC4S (23), NetFlow (11).
- Each filter pill shows a live count of matching products.

### Universal Finder (Search Bar)
- Keyword-optimized search across 725+ unique keywords.
- Displays result counter (`N of M products`).
- Searches product names, descriptions, aliases, keywords, add-on names, and sourcetypes.

### Custom Dashboard Launch (Split-Button)
- **Main button (Launch)** — Opens the preferred dashboard (custom if set, otherwise Cisco default).
- **Caret button** — Dropdown with all available launch options.
- **Custom dashboard** — Customers set a custom dashboard path via modal. Persists in `local/products.conf`.

### Props.conf Audit (Magic Eight)
- Per-product ingestion health check analyzing 8 critical props.conf settings.
- Educational content: CPU reduction, datetime.xml tax, Recipe Principle, Cascade effect.

### Ecosystem Intelligence Dashboard
- Dashboard Studio v2 with portfolio analytics and Cisco Splunkbase intelligence.
- Two tabs: Product Intelligence + Splunkbase & Operations.

### Dark Mode & Theme Toggle
- Full CSS variable system with dark-mode overrides.
- **Three-state theme toggle**: Light → Dark → Auto (system).
- Theme detection via DOM attributes, body classes, and Splunk REST API.
- Theme-aware warning banners across all product sections.

### Additional Features
- **Indexer Tier Detection** — Validates add-on deployment across SH and indexer tiers.
- **Catalog Vault** — Hidden disabled products accessible via vault toggle.
- **Community App Detection** — Warns when a third-party TA shadows the official Cisco add-on.
- **Prerequisite App Tracking** — Detects companion apps for products requiring dependencies.
- **Best Practices Modal** — Platform-aware guidance per product (Cloud vs. Enterprise).
- **Portal-based Resizable Modals** — Draggable + resizable using ReactDOM.createPortal.
- **Give Feedback** — In-app feedback form stored in Splunk's summary index (`scan:feedback`).
- **42 Saved Searches** — Pre-built reports for catalog analysis accessible from the Reports nav menu.

## App Structure

| Directory | Purpose |
|---|---|
| `default/products.conf` | Product catalog — 93 stanzas defining all card metadata and appearance |
| `default/savedsearches.conf` | 42 saved searches for catalog analysis and troubleshooting |
| `default/app.conf` | App identity and version |
| `default/server.conf` | SHC replication settings for products.conf |
| `default/data/ui/nav/` | Navigation bar with Products view and Reports menu |
| `default/data/ui/views/` | Simple XML views (products.xml, ecosystem_intelligence.xml) |
| `metadata/default.meta` | Permissions and sharing |
| `README/products.conf.spec` | Spec file documenting all products.conf fields |
| `appserver/static/` | React bundle (products.js), CSS (products.css), app icons, SVG badges |
| `appserver/templates/` | HTML template for legacy browser fallback |
| `lookups/scan_splunkbase_apps.csv.gz` | Canonical Splunkbase catalog (synced by SCAN - Splunkbase Catalog Sync) |
| `static/` | Splunkbase listing icons |

## Technology Stack

| Component | Version | Purpose |
|---|---|---|
| React | 18.3.1 | Core UI framework |
| @splunk/react-ui | 5.8.0 | Splunk's official UI component library |
| @splunk/themes | 1.5.0 | Splunk theme tokens |
| @splunk/splunk-utils | 3.4.0 | URL helpers, CSRF tokens, REST utilities |
| Webpack | 5.105.2 | Module bundler (~1s build time) |
| Simple XML | 1.1 | Splunk dashboard container (`products.xml`) |

## Support

For issues, questions, or feature requests, use the in-app **Give Feedback** button or contact your Cisco account team.
