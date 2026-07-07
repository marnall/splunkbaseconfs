# CTM360 App - Index Configuration Guide

## Overview

The CTM360 App now supports configurable index settings, allowing you to specify which Splunk index contains your CTM360 data. This resolves the issue where dashboards and reports would only search the default index.

## Configuration Methods

### Method 1: Manual Configuration (Recommended)

1. Create the directory if it doesn't exist:
   ```bash
   mkdir -p $SPLUNK_HOME/etc/apps/ctm360/local/
   ```

2. Create or edit the file `$SPLUNK_HOME/etc/apps/ctm360/local/macros.conf`:
   ```ini
   [default_index]
   definition = index=ctm360
   iseval = 0
   ```

3. Replace `ctm360` with the name of your index (the same index configured in the CTM360 Add-on inputs).

4. Restart Splunk or reload the app:
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```
   or
   ```bash
   $SPLUNK_HOME/bin/splunk reload app ctm360
   ```

### Method 2: Using the Setup Page

1. Navigate to the CTM360 App in Splunk
2. Click on "Setup" in the navigation menu
3. Enter your index name in the "CTM360 Data Index" field
4. Click "Submit"
5. Restart Splunk for changes to take effect

## How It Works

The app uses a Splunk macro called `ctm360_index_filter` that is referenced in all dashboard queries and saved searches. By default, this macro is defined as:

```ini
[default_index]
definition = index=*
iseval = 0

[ctm360_index_filter]
definition = `default_index`
iseval = 0
```

When you configure a specific index, you override the `default_index` macro in the `local/macros.conf` file, which takes precedence over the default configuration.

## Verifying Configuration

### Check Current Macro Definition

Run this search in Splunk:
```spl
| rest /services/properties/macros/default_index | fields title definition
```

### Verify Data Collection

Run this search to see where your CTM360 data is located:
```spl
(sourcetype="cbs" OR sourcetype="hackerview" OR sourcetype="threatcover") 
| stats count by index, sourcetype, source 
| sort -count
```

### Test Dashboard Queries

Navigate to any CTM360 dashboard (CBS, HackerView, or ThreatCover) and verify that data is displayed correctly.

## Matching Add-on Configuration

Make sure the index configured in the CTM360 App matches the index configured in the CTM360 Add-on inputs:

1. Go to **Settings > Data Inputs**
2. Find the CTM360 inputs (CBS Feeds, HackerView Feeds, ThreatCover Feeds)
3. Check the "Index" setting for each input
4. Use the same index name in the CTM360 App configuration

## Troubleshooting

### No Data Showing in Dashboards

1. Verify the index name is correct in `local/macros.conf`
2. Check that the CTM360 Add-on is collecting data: `index=<your_index> sourcetype=cbs OR sourcetype=hackerview`
3. Ensure you've restarted Splunk after making configuration changes
4. Check Splunk's internal logs for errors: `index=_internal source=*splunkd.log* ctm360`

### Configuration Not Taking Effect

1. Ensure the file is in the `local/` directory, not `default/`
2. Verify file permissions allow Splunk to read the file
3. Restart Splunk completely (not just reload)
4. Check for syntax errors in the macros.conf file

## Upgrade Considerations

When upgrading the CTM360 App:

- Your `local/macros.conf` file will **NOT** be overwritten
- The configuration will persist across upgrades
- Always backup your `local/` directory before upgrading

## Support

For additional support, please refer to:
- CTM360 Splunk Integration Documentation: https://help.ctm360.com/docs/splunk-integration
- Splunk Documentation on Search Macros: https://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Definesearchmacros

