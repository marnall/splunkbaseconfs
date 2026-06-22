# products.conf.spec
#
# Splunk Cisco App Navigator — Product Catalog Configuration
#
# Each stanza defines a product card in the SCAN Products page.
# Stanza name = product_id (e.g. [cisco_asa])
#

[<product_id>]

disabled = true | false
* When true, this product stanza is hidden from the UI entirely.
* Default: false.

display_name = <string>
* Card title displayed to the user.

description = <string>
* Short description shown in the card tooltip.
* Supports lightweight inline markup:
*   **bold**              → bold text
*   *italic*              → italic text
*   `code`                → inline code
*   [link text](url)      → clickable link
*   |  or  \n             → line break
*   {small}text{/small}   → smaller text (11px)
*   {large}text{/large}   → larger text (15px)
*   {h}text{/h}           → heading-style text (16px bold)

value_proposition = <string>
* One-liner benefit statement shown below the description.
* Supports the same inline markup as description.

tagline = <string>
* Short tagline displayed beneath the product name on the card.

vendor = <string>
* Product vendor. Typically "Cisco".

category = security | networking | collaboration | infrastructure | observability
* Category used for filtering on the Products page.

version = <string>
* Current version of this product module (e.g. "1.0.0").

date_created = <date>
* Date the catalog entry was first added (YYYY-MM-DD).
* Populated from git history; updated manually when creating new stanzas.
* Example: 2026-02-23

date_updated = <date>
* Date the catalog entry was last modified (YYYY-MM-DD).
* Updated whenever any field in the stanza changes.
* Example: 2026-03-21

status = active | under_development | deprecated | archived | roadmap
* Product lifecycle status.
*   active             — Live product shown in the main grid.
*   under_development  — Shows a Preview badge (use sparingly).
*   deprecated         — Add-on archived or Cisco product retired (see cisco_retired).
*   archived           — Hidden from the UI (disabled = 1).
*   roadmap            — GTM coverage gap; no Splunk integration exists yet.

cisco_retired = true | false
* Whether the Cisco product itself has reached end-of-life / end-of-sale.
* When true, the card shows a "CISCO RETIRED" ribbon and the product is
* placed in the dedicated "Retired Products" section.
* When false or omitted, a deprecated product is just "Add-on Archived"
* (the Cisco product is still active but its Splunk add-on was removed
* from Splunkbase).

coverage_gap = true | false
* Whether this product has zero Splunk coverage (no TA, no app, no
* community integration).  Products with coverage_gap = true are shown
* in the "GTM Roadmap — Coverage Gaps" section to highlight future
* integration opportunities.  Typically paired with status = roadmap.

gap_type = new_integration | rebuild | enhancement
* Type of coverage gap. Only used when coverage_gap = true.
*   new_integration — No Splunk integration exists; needs to be built from scratch.
*   rebuild         — A developer/community add-on exists but needs a Cisco- or
*                     Splunk-supported replacement (build or acquire).
*   enhancement     — Data flows through an existing path (e.g. SC4S syslog or
*                     another TA) but the integration may need field extractions,
*                     CIM mapping, dashboards, or dedicated enrichment.
* Default: (empty).

gtm_pillar = 1 | 2 | 3 | 4 | 5
* Optional. Cisco Secure Networking GTM pillar for roadmap products.
* Only used when coverage_gap = true; shown on the card to map the product
* to the GTM strategy. 1 = Secure Campus & Branch, 2 = Secure WAN Edge,
* 3 = Data Center & Cloud, 4 = End-to-End Visibility & Assurance, 5 = Industrial/OT.
* Reference: https://www.cisco.com/c/en/us/solutions/collateral/transform-infrastructure/secure-networking-so.html

addon = <string>
* The Splunk app_id of the add-on / TA this card is associated with (e.g. "CiscoSecurityCloud").

addon_uid = <string>
* The Splunkbase UID of the add-on (e.g. "7404" for CiscoSecurityCloud).
* Multiple products may share the same addon_uid when they use the same TA.

addon_family = <string>
* Add-on family grouping used by the build-time catalog generator to map
* products to their parent add-on install flow (e.g. "security-cloud",
* "catalyst", "dc-networking", "cloud-security", "collaboration",
* "observability", "standalone", "deprecated").

subcategory = <string>
* Sub-category within the main category, used for sub-category filter pills.
* Based on official Cisco product taxonomy.
* Security: cloud_security | network_security | identity_access | email_security
*           endpoint_security | workload_security | threat_response | compute_infra
* Networking: campus_wireless | routing_wan | data_center_net
* Omit for categories with too few products (collaboration, observability, deprecated).

ai_enabled = true|false
* Whether this product leverages AI technologies.
* Products with ai_enabled = true show an AI badge on the card and appear in the AI filter pill.

ai_description = <string>
* Brief description of how AI is used in this product.
* Shown as a tooltip when hovering over the AI badge or filter pill.

addon_label = <string>
* Human-readable label for the required add-on (e.g. "Cisco Security Cloud").

addon_splunkbase_url = <string>
* Splunkbase URL for the required add-on.

addon_docs_url = <string>
* Documentation URL for the required add-on (install guide, configuration reference, etc.).

addon_troubleshoot_url = <string>
* Optional. URL for a troubleshooting guide specific to this add-on.
* Links to diagnostic steps, common issues, and resolution procedures.

addon_install_url = <string>
* Relative Splunk manager URL to install the required add-on from inside Splunk
* via Browse More Apps. Example: /manager/splunk-cisco-app-navigator/appsremote?order=relevance&query="Cisco+Security+Cloud"
* When empty, the UI falls back to addon_splunkbase_url and opens Splunkbase directly.
* Leave empty for archived apps or apps not available in Browse More Apps.

app_viz = <string>
* Optional. The Splunk app_id of the visualization / dashboard app (e.g. "cisco-catalyst-app").
* When empty, the UI assumes addon provides both data ingestion and visualization.

app_viz_uid = <string>
* The Splunkbase UID of the visualization app (e.g. "7539" for cisco-catalyst-app).
* Multiple products may share the same app_viz_uid when they use the same dashboard app.

app_viz_label = <string>
* Human-readable label for the visualization app (e.g. "Cisco Enterprise Networking for Splunk Platform").

app_viz_splunkbase_url = <string>
* Splunkbase URL for the visualization app.

app_viz_docs_url = <string>
* Documentation URL for the visualization app.

app_viz_troubleshoot_url = <string>
* Optional. URL for a troubleshooting guide specific to the visualization app.
* Links to diagnostic steps, common issues, and resolution procedures.

app_viz_install_url = <string>
* Relative Splunk manager URL to install the visualization app from inside Splunk.
* When empty, the UI falls back to app_viz_splunkbase_url and opens Splunkbase directly.

app_viz_2 = <string>
* Optional. A second visualization / dashboard app (e.g. an ITSI content pack).
* When empty, only the primary app_viz is shown.

app_viz_2_uid = <string>
* The Splunkbase UID of the second visualization app (e.g. "8365").

app_viz_2_label = <string>
* Human-readable label for the second visualization app.

app_viz_2_splunkbase_url = <string>
* Splunkbase URL for the second visualization app.

app_viz_2_docs_url = <string>
* Documentation URL for the second visualization app.

app_viz_2_troubleshoot_url = <string>
* Optional. URL for a troubleshooting guide specific to the second visualization app.
* Links to diagnostic steps, common issues, and resolution procedures.

app_viz_2_install_url = <string>
* Relative Splunk manager URL to install the second visualization app from inside Splunk.

learn_more_url = <string>
* External URL for the "Learn More" button.

legacy_apps = <comma-separated list>
* Comma-separated legacy TA app_ids to detect (e.g. "Splunk_TA_cisco-asa,Splunk_TA_cisco-asa2").

legacy_labels = <comma-separated list>
* Display names parallel to legacy_apps.

legacy_uids = <comma-separated list>
* Splunkbase numeric app IDs for legacy, predecessor, and community/third-party
* apps (e.g. "1808,3662,5543"). One list for all; no separate community_uids.
* Used to construct links: https://splunkbase.splunk.com/app/<uid>

legacy_viz_uids = <comma-separated list>
* Splunkbase numeric app IDs for legacy visualization / dashboard apps that have
* been superseded by the current app_viz. Separate from legacy_uids so the UI
* can show "Legacy Apps" instead of "Legacy Add-ons" for these entries.
* Example: 6657

legacy_urls = <comma-separated list>
* Splunkbase URLs parallel to legacy_apps.

legacy_statuses = <comma-separated list>
* Comma-separated Splunkbase status values parallel to legacy_apps.
* Valid values: "active" (still available on Splunkbase) or "archived" (no longer available).
* Used to split the Legacy Audit modal into Active vs Archived sections.
* Defaults to "active" if omitted or if fewer values than legacy_apps entries.

prereq_apps = <comma-separated list>
* Comma-separated app_ids for prerequisite dependencies (e.g. "splunk_app_stream,Splunk_TA_stream").
* These are required companion apps that the main addon depends on.

prereq_labels = <comma-separated list>
* Display names parallel to prereq_apps.

prereq_uids = <comma-separated list>
* Splunkbase numeric app IDs parallel to prereq_apps.

prereq_urls = <comma-separated list>
* Splunkbase URLs parallel to prereq_apps.

sourcetypes = <comma-separated list>
* Sourcetypes for MTTI health checks (e.g. "cisco:asa,cisco:asa:syslog").

dashboards = <comma-separated list>
* Dashboard view names for the "Launch" button. The first entry is the default.
* Each entry can be a plain view name (e.g. "overview") which resolves to app_viz
* or addon, OR an explicit "app_id/view_name" pair when the dashboard lives in a
* specific app (e.g. "ta_cisco_thousandeyes/application,cisco-catalyst-app/network").

custom_dashboard = <string>
* Optional. Customer-defined dashboard to launch instead of (or alongside) the default.
* Format: "app_id/dashboard_name" (e.g. "search/my_custom_duo_dashboard").
* When set, the Launch button offers both the Cisco default and this custom dashboard.
* Typically lives in local/products.conf so it survives app upgrades.

icon_emoji = <string>
* Emoji or short text used as the card icon placeholder.

icon_svg = <string>
* Base name of the SVG icon file (without .svg extension) in appserver/static/icons/.
* The app loads icons/<value>.svg in light mode and icons/<value>_white.svg in dark mode.
* Example: icon_svg = firewall  →  icons/firewall.svg / icons/firewall_white.svg

aliases = <comma-separated list>
* Comma-separated former/alternate product names (e.g. "IronPort Email Security,Email Security Appliance").
* Displayed as a subtle "Formerly: ..." line on the card and included in search.
* Use this to track Cisco product renames so admins can find products by old names.

keywords = <comma-separated list>
* Comma-separated search keywords for the Universal Finder (e.g. "asa,firewall,ftd,ngfw").

alert_action_label = <string>
* Optional. Human-readable label for a companion alert action app.
* When present, indicates a custom alert action exists for this product.
* Alert actions are standalone add-ons (or built into a TA) that fire from
* Splunk saved searches, ES correlation searches, or notable events.

alert_action_uid = <integer>
* Splunkbase numeric app ID for the alert action.

alert_action_url = <string>
* Splunkbase URL for the alert action.

alert_action_2_label = <string>
* Optional. Human-readable label for a second alert action app.

alert_action_2_uid = <integer>
* Splunkbase numeric app ID for the second alert action.

alert_action_2_url = <string>
* Splunkbase URL for the second alert action.

alert_action_uids = <comma-separated list>
* Comma-separated Splunkbase numeric app IDs for all alert actions associated
* with this product. Used by the UI to look up alert action metadata from the
* Splunkbase CSV catalog.

soar_connector_label = <string>
* Optional. Human-readable label for the SOAR connector.
* When present, indicates a Splunk SOAR connector exists for this product.
* SOAR connectors run in Splunk SOAR (not Splunk Enterprise), so no app
* folder name is tracked.

soar_connector_uid = <integer>
* Splunkbase numeric app ID for the SOAR connector.

soar_connector_url = <string>
* Splunkbase URL for the SOAR connector.

soar_connector_2_label = <string>
* Optional. Human-readable label for a second SOAR connector.

soar_connector_2_uid = <integer>
* Splunkbase numeric app ID for the second SOAR connector.

soar_connector_2_url = <string>
* Splunkbase URL for the second SOAR connector.

soar_connector_3_label = <string>
* Optional. Human-readable label for a third SOAR connector.

soar_connector_3_uid = <integer>
* Splunkbase numeric app ID for the third SOAR connector.

soar_connector_3_url = <string>
* Splunkbase URL for the third SOAR connector.

soar_connector_uids = <comma-separated list>
* Comma-separated Splunkbase numeric app IDs for all SOAR connectors associated
* with this product. Used by the UI to look up SOAR connector metadata from the
* Splunkbase CSV catalog.

itsi_content_pack_label = <string>
* Optional. Human-readable label for an ITSI Content Pack associated with this product.
* ITSI Content Packs are installed via ITSI → Configuration → Data Integrations → Content Library,
* not via Splunkbase. ITSI may run on a dedicated search head.

itsi_content_pack_docs_url = <string>
* Documentation URL for the ITSI Content Pack.

card_banner = <string>
* Optional. Translucent text overlaid on the product card background.
* Used to indicate which platform powers this product.
* Examples: "Powered by Cisco Security Cloud", "Powered by Cisco Catalyst".

card_banner_color = <string>
* Named preset or hex colour for the card banner text.
*   Named presets: blue, green, gold, red, purple, teal, cisco (Cisco blue #049fd9).
*   Hex example: #049fd9
* When empty, the default translucent grey is used.

card_banner_size = small | medium | large
* Controls the font-size of the diagonal banner text.
*   small  — 11px (subtle watermark)
*   medium — 13px (default)
*   large  — 16px (prominent)
* Default: medium.

card_banner_opacity = <float>
* Opacity for the banner text, between 0.0 (invisible) and 1.0 (fully opaque).
* When set, overrides the default translucent value (approx 0.055).
* Useful for making some cards' banners more or less prominent.
* Examples: 0.08, 0.15, 0.25
* Default: (empty) — uses the CSS default.

card_accent = <string>
* Hex colour for a bold left-border accent stripe on the card.
* Draws the eye to highlighted products. Examples: #049fd9, #6abf4b.
* When empty, no accent stripe is shown.

card_bg_color = <string>
* Background colour or shade name for the product card.
*   Named shades: ice, mint, lavender, rose, cream, smoke, sky, pearl.
*   Hex example: #f0f8ff
* Overrides the default card background (white in light mode).
* Pairs well with card_accent and card_banner_color for visual grouping.
* Default: (empty) — uses the theme default.

is_new = true | false
* When true, a bright "NEW!" corner ribbon is shown on the card.
* Use this to highlight recently added or released products.
* Default: false.

secure_networking_gtm = true | false
* When true, this product appears in the "Secure Networking" filter pill.
* Driven by the Cisco Secure Networking GTM strategy.
* Reference CSV: docs/Secure_Networking_gtm.csv
* Default: false.

support_level = cisco_supported | splunk_supported | developer_supported | community_supported | not_supported
* Support tier for the add-on, shown as a badge in the detail modal.
*   cisco_supported    — Officially developed and supported by Cisco.
*   splunk_supported   — Developed or supported by Splunk / Splunkbase.
*   developer_supported — Developed by a third-party developer on Splunkbase.
*   community_supported — Community-maintained; no formal support agreement.
*   not_supported       — No dedicated Splunk integration exists yet, or the add-on is archived/unmaintained.
* Default: (empty). When empty, no support badge is shown.

custom = true | false
* Whether this product card was created by the customer (lives in local/products.conf).
* Custom cards appear in a dedicated "Custom Products" section and can be
* edited or deleted from the UI.  Official Cisco catalog cards should never
* have this flag set.
* Default: false.

sort_order = <integer>
* Numeric sort weight. Lower values appear first. Default 100.

sc4s_url = <url>
* URL to the SC4S (Splunk Connect for Syslog) documentation page for this product.
* When set, an "SC4S" pill appears next to the add-on links in the expanded card,
* and a dedicated SC4S recommendation appears in the Best Practices modal.
* Default: (empty).

sc4s_label = <string>
* Display label for the SC4S link (e.g. "SC4S: Cisco ISE").
* Default: "SC4S documentation".

sc4s_supported = true | false
* Whether this product supports high-scale data onboarding via SC4S.
* When true, the card displays a "Dual-Path Onboarding" section showing both
* the standard (TA + Heavy Forwarder) and high-scale (SC4S) ingestion paths.
* Default: false.

sc4s_search_head_ta = <string>
* App ID of the product-specific TA required on the Search Head tier when
* data is ingested via SC4S. SC4S handles all index-time operations; this TA
* provides search-time CIM mappings and dashboards.
* Example: Splunk_TA_cisco-ise
* Default: (empty).

sc4s_search_head_ta_label = <string>
* Display label for the SC4S search-head TA.
* Example: Splunk Add-on for Cisco ISE
* Default: (empty).

sc4s_search_head_ta_splunkbase_id = <string>
* Splunkbase app ID number for the SC4S search-head TA.
* Example: 1915
* Default: (empty).

sc4s_sourcetypes = <comma-separated list>
* Sourcetypes specific to the SC4S / high-scale onboarding path.
* When SC4S parses data differently from the standard add-on, the sourcetypes
* may differ. This field lets each product declare its SC4S-specific sourcetypes
* separately from the standard "sourcetypes" field.
* Example: cisco:asa, cisco:ftd
* Default: (empty).

sc4s_config_notes = <pipe-delimited string>
* Product-specific configuration notes for the SC4S / high-scale onboarding path.
* Multiple notes are separated by the pipe character (|).
* Shown in the Dual-Path Onboarding section of the card.
* Example: Configure ISE with Log Level 6 (Informational)|Use TCP/IP protocol
* Default: (empty).

netflow_supported = true | false
* Whether this product supports network telemetry onboarding via NetFlow / Splunk Stream.
* When true, the card displays a "NetFlow" tab in the Dual-Path Onboarding section,
* alongside the Standard and SC4S tabs (if SC4S is also supported).
* Default: false.

netflow_addon = <string>
* App ID of the Cisco-specific NetFlow add-on required for this onboarding path.
* Typically the Cisco Catalyst Enhanced Netflow Add-on (splunk_app_stream_ipfix_cisco_hsl).
* Example: splunk_app_stream_ipfix_cisco_hsl
* Default: (empty).

netflow_addon_label = <string>
* Display label for the NetFlow add-on.
* Example: Cisco Catalyst Enhanced Netflow Add-on for Splunk
* Default: (empty).

netflow_addon_splunkbase_id = <string>
* Splunkbase app ID number for the NetFlow add-on.
* Example: 6872
* Default: (empty).

netflow_addon_docs_url = <url>
* Documentation URL for the NetFlow add-on.
* Default: (empty).

stream_docs_url = <url>
* Documentation URL for the Splunk Stream platform.
* Links to the official Splunk Stream documentation covering installation,
* configuration, and operation of all three Stream packages.
* Default: (empty).

netflow_sourcetypes = <comma-separated list>
* Sourcetypes specific to the NetFlow onboarding path.
* Example: stream:cisco_ipfix
* Default: (empty).

netflow_config_notes = <pipe-delimited string>
* Product-specific configuration notes for the NetFlow onboarding path.
* Multiple notes are separated by the pipe character (|).
* Shown in the NetFlow tab of the Dual-Path Onboarding section.
* Example: Configure NetFlow v9 on switches|Export to Stream Forwarder UDP port
* Default: (empty).

best_practices = <pipe-delimited string>
* Custom per-product best-practice tips shown in the Best Practices modal.
* Multiple tips are separated by the pipe character (|).
* These appear after the auto-generated generic tips (platform, add-on, sourcetypes, legacy).
* Example: Tip one goes here|Tip two goes here|Third tip

# ── Splunk Enterprise Security (ES) & CIM ───────────────────────────────────

es_compatible = true | false
* Whether this product's add-on maps its sourcetypes to CIM data models via
* eventtypes.conf and tags.conf, making the data usable by Splunk Enterprise
* Security correlation searches and dashboards.
* When true, the card displays an "ES" badge.
* Default: false.

es_cim_data_models = <comma-separated list>
* CIM data models that this product's add-on maps to via tags.conf.
* Only list models the TA genuinely tags — do not fabricate mappings.
* Valid values: Alerts, Authentication, Certificates, Change, DLP, Email,
*   Endpoint, Intrusion_Detection, Malware, Network_Resolution,
*   Network_Sessions, Network_Traffic, Vulnerabilities, Web
* Example: Authentication,Network_Traffic,Intrusion_Detection
* Default: (empty).

# ── ESCU (Enterprise Security Content Update) ───────────────────────────────

escu_analytic_stories = <comma-separated list>
* Comma-separated names of ESCU analytic story(ies) that ship pre-built
* detections for this product. Only populate for products that have
* actual ESCU detections (matched by macro/sourcetype).
* Example: Cisco Duo Suspicious Activity
* Default: (empty).

escu_detection_count = <integer>
* Number of ESCU detection searches that target this product's sourcetypes.
* Must match the actual count from ESCU content analysis.
* Default: (empty / 0).

escu_detections = <comma-separated list>
* Comma-separated names of individual ESCU detection searches for this product.
* These are the savedsearch names from DA-ESS-ContentUpdate.
* Example: Cisco Duo Admin Login Unusual Browser,Cisco Duo Bulk Policy Deletion
* Default: (empty).

# ── Splunk Security Essentials (SSE) ────────────────────────────────────────

sse_content = true | false
* Whether Splunk Security Essentials contains use cases or detections that
* reference this product's sourcetypes or data.
* SSE is a free Splunkbase app that provides detection guidance and analytics
* stories even without Splunk Enterprise Security.
* When true (alone or combined with es_compatible), the card displays a "SecOps" badge.
* Default: false.

sse_use_cases = <comma-separated list>
* Comma-separated names of SSE showcases / use cases relevant to this product.
* These correspond to summary entries in SSE's ShowcaseInfo.json.
* Example: Cisco Duo Admin Login Unusual Browser,Cisco Duo Bulk Policy Deletion
* Default: (empty).

sse_use_case_count = <integer>
* Number of SSE use cases targeting this product's sourcetypes.
* Default: (empty / 0).

sse_data_sources = <comma-separated list>
* SSE data source category codes relevant to this product.
* Example: VendorSpecific-cisco-duo,DS010NetworkCommunication-ET01Traffic
* Default: (empty).

# ── IT Essentials Learn (ITE Learn) ─────────────────────────────────────────

ite_learn_content = true | false
* Whether IT Essentials Learn contains procedures that reference this product's
* sourcetypes or data.
* ITE Learn is a free Splunkbase app that provides guided ITOps procedures and
* operational intelligence even without Splunk ITSI.
* When true (alone or combined with itsi_content_pack_label), the card displays
* an "ITOps" badge.
* Default: false.

ite_learn_procedures = <comma-separated list>
* Comma-separated names of ITE Learn procedures relevant to this product.
* Example: Hosts with highest log volume,Detect duplicate IP address
* Default: (empty).

ite_learn_procedure_count = <integer>
* Number of ITE Learn procedures targeting this product's sourcetypes.
* Default: (empty / 0).