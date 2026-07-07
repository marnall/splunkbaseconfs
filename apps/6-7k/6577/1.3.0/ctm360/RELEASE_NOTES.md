# CTM360 Splunk App - Version 1.0.6 Release Notes

## Release Date
October 27, 2025

## Overview
This release addresses a critical usability issue where users could not easily configure which Splunk index contains their CTM360 data. The app now supports configurable index settings through a macro-based system that persists across app updates.

## What's Fixed

### Issue: Index Configuration Not Supported
**Problem**: The CTM360 Add-on allows users to specify a custom index for storing CTM360 data, but the CTM360 App dashboards and reports only searched by sourcetype without specifying an index. This caused all queries to search only the default index, ignoring custom index configurations.

**Impact**: Users who configured a custom index (e.g., `index=ctm360`) in the add-on inputs would not see any data in the dashboards and reports.

**Solution**: Implemented a macro-based index configuration system that allows users to specify their index in a persistent configuration file.

## New Features

### 1. Configurable Index Macro
- Added `default_index` macro in `default/macros.conf`
- Default value: `index=*` (searches all indexes)
- Users can override by creating `local/macros.conf`
- Configuration persists across app updates

### 2. Setup Page
- New "Setup" page accessible from the navigation menu
- Provides clear instructions for configuring the index
- Shows current macro definition
- Includes data verification search

### 3. Comprehensive Documentation
- `INDEX_CONFIGURATION.md`: Complete user guide
- `CHANGELOG.md`: Detailed change history
- In-app documentation on the Setup page

## Technical Changes

### Dashboard Updates
All dashboard queries have been updated to use the `ctm360_index_filter` macro:

**Before**:
```spl
sourcetype="cbs" source="incident" | spath | ...
```

**After**:
```spl
`ctm360_index_filter` sourcetype="cbs" source="incident" | spath | ...
```

**Files Updated**:
- `cbs.xml`: 47 queries updated
- `hackerview.xml`: 8 queries updated
- `threatcover.xml`: 7 queries updated

### Saved Searches Updates
All saved searches updated to use the macro:
- New Hosts by day
- New IP Addresses by day
- New Incidents by day
- New Issues by day

## Installation Instructions

### New Installations
1. Install the CTM360 Add-on (`Splunk_TA_ctm360`)
2. Install the CTM360 App (`ctm360`)
3. Configure the add-on inputs with your desired index
4. Create `$SPLUNK_HOME/etc/apps/ctm360/local/macros.conf`:
   ```ini
   [default_index]
   definition = index=your_index_name
   iseval = 0
   ```
5. Restart Splunk

### Upgrading from Previous Versions
1. Stop Splunk
2. Backup your current installation
3. Replace the `ctm360` app directory with the new version
4. If you previously created a manual workaround, you can keep your `local/macros.conf` file
5. Start Splunk

**Note**: Your `local/macros.conf` configuration will be preserved during the upgrade.

## Configuration Guide

### Method 1: Manual Configuration (Recommended)

1. Create the local configuration directory:
   ```bash
   mkdir -p $SPLUNK_HOME/etc/apps/ctm360/local/
   ```

2. Create or edit `$SPLUNK_HOME/etc/apps/ctm360/local/macros.conf`:
   ```ini
   [default_index]
   definition = index=ctm360
   iseval = 0
   ```
   Replace `ctm360` with your index name.

3. Restart Splunk:
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```

### Method 2: Using the Setup Page

1. Navigate to the CTM360 App in Splunk
2. Click "Setup" in the navigation menu
3. Follow the instructions to create the configuration file
4. Restart Splunk

## Verification Steps

After configuration, verify the setup:

1. **Check Macro Definition**:
   ```spl
   | rest /services/properties/macros/default_index | fields title definition
   ```

2. **Verify Data Collection**:
   ```spl
   (sourcetype="cbs" OR sourcetype="hackerview" OR sourcetype="threatcover") 
   | stats count by index, sourcetype, source
   ```

3. **Test Dashboards**:
   - Navigate to CBS, HackerView, or ThreatCover dashboards
   - Verify data is displayed correctly

## Backward Compatibility

✅ **Fully backward compatible**
- Default behavior unchanged (searches all indexes)
- No breaking changes
- Existing installations continue to work without configuration

## Known Issues
None

## Support

For issues or questions:
- Documentation: https://help.ctm360.com/docs/splunk-integration
- Review the included `INDEX_CONFIGURATION.md` file
- Check the Setup page in the app

## Files Included

```
ctm360/
├── CHANGELOG.md                          # Change history
├── INDEX_CONFIGURATION.md                # Configuration guide
├── README.md                             # Original README
├── app.manifest                          # App manifest
├── default/
│   ├── app.conf                          # App configuration (v1.0.6)
│   ├── macros.conf                       # NEW: Index macros
│   ├── savedsearches.conf                # UPDATED: With macros
│   └── data/ui/
│       ├── nav/default.xml               # UPDATED: Added Setup link
│       └── views/
│           ├── cbs.xml                   # UPDATED: 47 queries
│           ├── hackerview.xml            # UPDATED: 8 queries
│           ├── threatcover.xml           # UPDATED: 7 queries
│           └── setup.xml                 # NEW: Setup page
├── metadata/
├── appserver/static/
└── static/
```

## Upgrade Path

| From Version | To Version | Action Required |
|--------------|------------|-----------------|
| 1.0.6 or earlier | 1.0.6 | Configure index in local/macros.conf |
| No previous install | 1.0.6 | Configure index in local/macros.conf |

## Credits

This release addresses feedback from CTM360 Splunk app users who identified the need for persistent index configuration.

---

**Version**: 1.0.6  
**Build Date**: October 27, 2025  
**Compatibility**: Splunk Enterprise 8.0+, Splunk Cloud
