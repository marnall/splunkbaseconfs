# How to Check Your Splunk Version

## Method 1: Via Splunk Web Interface (Easiest)
1. Log into Splunk Web
2. Click on **Help** in the top menu
3. Select **About**
4. You'll see your version like: `Splunk Enterprise 9.4.2 (build e9664af3d956)`

## Method 2: Via Command Line
Run this command on your Splunk server:
```bash
/opt/splunk/bin/splunk version
```

## Method 3: Via Splunk Search
Run this search in Splunk:
```
| rest /services/server/info 
| fields version, build, os_name
| eval compatibility = case(
    match(version, "^7\."), "Limited dashboard support, Python 2.7",
    match(version, "^8\.[0-1]"), "Mixed Python 2.7/3.7 support",
    match(version, "^8\."), "Python 3.7+ support",
    match(version, "^9\."), "Full feature support, Python 3 only",
    1=1, "Unknown version"
)
```

## Method 4: Check App Logs
After installing SOCRadar apps, check the logs:
```
index=_internal source="*socradar*" "SPLUNK VERSION INFORMATION"
```

## Version Compatibility Table

| Splunk Version | Dashboard Support | Python Version | Notes |
|---------------|------------------|----------------|-------|
| 7.0 - 7.3     | Basic            | Python 2.7     | Column alignment not supported |
| 8.0 - 8.1     | Enhanced         | Python 2.7/3.7 | Mixed support |
| 8.2 - 8.x     | Full             | Python 3.7+    | Recommended minimum |
| 9.0+          | Full             | Python 3 only  | Best compatibility |

## Troubleshooting Dashboard Errors

If you see errors like:
```
[/visualizations/viz_high_risk_table/options/columnFormat/*/align]: must be array
```

This means you're on an older Splunk version. Please:
1. Update to SOCRadar Feeds v1.1.54 or later
2. Clear browser cache
3. Restart Splunk

## Need Help?
Contact SOCRadar support with your Splunk version number for assistance.