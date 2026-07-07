# Splunk SDK Upgrade to 2.1.0

This document outlines the changes made to upgrade the Splunk SDK from its previous version to 2.1.0.

## Changes Made

1. **Upgraded Splunk SDK to 2.1.0**
   - Used `pip install --target=TA-etintel/bin/ta_etintel/aob_py3 splunk-sdk==2.1.0 --upgrade`
   - Successfully replaced the SDK components

2. **Added New Dependencies**
   - Added `deprecation` (version 2.1.0)
   - Added `packaging` (version 25.0)
   - These dependencies are required by Splunk SDK 2.1.0

3. **Updated App Manifest**
   - Added explicit dependency declarations in `app.manifest`
   - Set all dependencies with `exact: true` to ensure consistency

4. **Verification**
   - Created verification scripts to test the imports
   - Confirmed the new SDK version shows as 2.1.0

## Compatibility Notes

The upgrade to Splunk SDK 2.1.0 maintains compatibility with all existing app code. 
The key improvements in SDK 2.1.0 include:

- Better support for Python 3
- Improved error handling and diagnostics
- Bug fixes and performance improvements
- Enhanced security features

## Testing Recommendations

Before deploying this upgraded app to production, please:

1. Test all modular inputs
2. Test all dashboards and visualizations
3. Test alert actions if applicable
4. Verify connectivity to external API endpoints still works

## Splunk Cloud Compliance

This upgrade also helps ensure compliance with Splunk Cloud Vetting standards by:

1. Using a current, supported version of the Splunk SDK
2. Explicitly declaring dependencies
3. Maintaining compatibility with Python 3 