# CTM360 App for Splunk - Changelog

## Version 1.0.6 (2025-10-27)

### Added
- **Configurable Index Support**: Added support for configuring the Splunk index where CTM360 data is stored
- **Index Macro**: Introduced `ctm360_index_filter` macro for centralized index configuration
- **Setup Page**: Added a new setup page (`setup.xml`) to guide users through index configuration
- **Documentation**: Added `INDEX_CONFIGURATION.md` with comprehensive setup and troubleshooting guide

### Changed
- **Dashboard Queries**: Updated all dashboard queries in `cbs.xml`, `hackerview.xml`, and `threatcover.xml` to use the `ctm360_index_filter` macro
- **Saved Searches**: Updated all saved searches in `savedsearches.conf` to use the `ctm360_index_filter` macro
- **Navigation**: Added "Setup" link to the navigation menu

### Fixed
- **Index Configuration Issue**: Fixed the issue where dashboards and reports only searched the default index, ignoring custom index configurations in the CTM360 Add-on
- Users can now specify a custom index (e.g., `ctm360`) in the add-on inputs and configure the app to search that index

### Technical Details
- Created `/default/macros.conf` with default index macro definitions
- All queries now use `` `ctm360_index_filter` sourcetype="..." `` pattern
- Configuration is stored in `/local/macros.conf` to persist across app updates
- Default behavior (searching all indexes) is preserved when no custom index is configured

### Migration Notes
For existing installations:
1. No action required if using the default index
2. To configure a custom index, create `/local/macros.conf` with:
   ```ini
   [default_index]
   definition = index=your_index_name
   iseval = 0
   ```
3. Restart Splunk after configuration changes

## Version 1.0.6 and earlier
- Previous versions (changelog not available)


## 1.3.0 (2026-06-11)
- CBS dashboard: added Money Mules, Gambling Sites and Social Media Fraud to the Data Source
  dropdown, with summary stats, charts and details tables per source.
- HackerView dashboard: new Attack Surface section (assets by type, potential assets,
  asset-watch change log, unified assets table) and a combined Light Scan + DeepScan issues table.
- Requires CTM360 Add-on for Splunk 1.4.0 (new data sources).
