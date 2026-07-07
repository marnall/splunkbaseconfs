# QRadar SOAR Add-On for Splunk
v2.4.1
*splunklib==2.1.1*

## Description

The QRadar SOAR Add-On for Splunk provides the capability of escalating a Splunk alert or Splunk ES notable event to a QRadar SOAR case.

## Release Notes
<!--
  Specify all changes in this release. Do not remove the release
  notes of a previous release
-->

### v2.4.1
- **ES 8.3.0 Compatibility**: Added support for Splunk Enterprise Security 8.3.0 Detection Editor
- **New Artifact Format**: Introduced pipe-delimited artifact format (`type|value|description`) for ES 8.3.0 Detection Editor
- **Backward Compatibility**: Maintained full backward compatibility with existing separate-field artifact configuration
- **Documentation**: Added comprehensive artifact configuration guides:
  - `README_ARTIFACT_FORMAT.md` - Detailed artifact configuration guide
  - `ARTIFACT_QUICK_REFERENCE.txt` - Quick reference for daily use
  - `IMPLEMENTATION_SUMMARY.md` - Technical implementation details
- **Bug Fix**: Fixed artifact field visibility issue in ES 8.3.0 Detection Editor (SOARAPPS-9404)

### v2.4.0
- Increasing splunklib version to 2.1.1
- Fix bug setting custom fields to null when updating existing SOAR case with same splunk_notable_event_id

## System Requirements

- Splunk version 8.0 or later for Python 3 support
- Splunk ES 6.1.0 or later for Python 3 support (ES 8.3.0+ supported with workaround)
- Splunk CIM Framework. **Note: The Add-On depends on Splunk CIM. Please install CIM before installing the Add-On.**
- QRadar SOAR platform version 35 or later
- Ability to connect directly from Splunk to your QRadar SOAR server with HTTPS on port 443
- A dedicated QRadar SOAR Administrator or equivalent account on the QRadar SOAR platform. This can be any account that has the permission to create incidents and simulations, and view and modify administrator and customization settings. You need to know the account username and password.

    NOTE: Should you later change the dedicated QRadar SOAR account to another user, the new user must also have the permission to edit incidents, in addition to the permission to create incidents and view and modify administrator and customization settings. The edit permission is necessary so that the integration can continue to modify or synchronize the incidents escalated by the original user account.
    
    You can refer to the [ibm.biz/soar-docs](https://ibm.biz/soar-docs) for more information about simulations.

- Splunk admin role for the user that will install and set up QRadar SOAR Add-on and for all other users that need to add the Add-On as an Alert Action or an Adaptive Response action for a correlation search.

## Splunk Enterprise Security 8.3.0 Compatibility (Workaround)

**Important:** This version includes a **workaround** for Splunk Enterprise Security 8.3.0 compatibility. ES 8.3.0's new Detection Editor uses a different rendering system that does not automatically display complex multi-field parameters. This is not the final polished solution but provides immediate functionality while maintaining full backward compatibility.

### Background
ES 8.3.0's Detection Editor dynamically generates UIs from configuration metadata and cannot automatically render the three separate artifact fields (Type, Value, Description) that were visible in previous versions. This workaround consolidates these fields into a single pipe-delimited format that ES 8.3.0 can display.

### ES 8.3.0 Detection Editor (Pipe-Delimited Format - Workaround)
When configuring alerts in the ES 8.3.0 Detection Editor, use the pipe-delimited format for artifacts:

```
type|value|description
```

**Example:**
```
IP Address|192.168.1.100|Suspicious source IP
```

**With Splunk tokens:**
```
IP Address|$src_ip$|Source IP from failed login attempts
```

**Note:** This format requires manual entry of the pipe-delimited string. There is no dropdown or helper UI in ES 8.3.0.

### Standard Splunk Interface (Separate Fields - Original Format)
When configuring alerts in the standard Splunk interface, continue using the three separate fields as before:
- Artifact Type (dropdown)
- Artifact Value (text field)
- Artifact Description (text field)

### Backward Compatibility
Both formats are fully supported and can coexist:
- ✅ Existing alerts with separate fields continue working without modification
- ✅ New alerts can use the pipe-delimited format in ES 8.3.0
- ✅ No migration is required for existing configurations
- ✅ Both formats can be used simultaneously in the same Splunk instance

### Known Limitations
1. **Manual Format Entry**: Users must manually enter the pipe-delimited format in ES 8.3.0; there is no dropdown or helper UI
2. **Pipe Character Conflicts**: If an artifact value legitimately contains a pipe character, use the separate fields format in standard Splunk interface instead
3. **ES Detection Editor Only**: The consolidated format is primarily for ES 8.3.0 Detection Editor; standard Splunk interface still shows separate fields

### Future Enhancement
For a permanent solution, a custom React component or UI schema definition would be needed to properly render the three separate fields in ES 8.3.0's Detection Editor. This workaround provides immediate functionality while such enhancements are considered.

### Documentation
For detailed information about artifact configuration, see:
- [`README_ARTIFACT_FORMAT.md`](README_ARTIFACT_FORMAT.md) - Comprehensive artifact configuration guide
- [`ARTIFACT_QUICK_REFERENCE.txt`](ARTIFACT_QUICK_REFERENCE.txt) - Quick reference for daily use
- [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md) - Technical implementation details and testing instructions

## Installation and Setup

For Splunk Cloud and Splunk ES Cloud users, contact Splunk Support to create a ticket for installing the QRadar SOAR Add-On for Splunk.

If you have installed Splunk or Splunk on-premises, you can download and install the add-on from Splunkbase. Alternatively, you can request an installer from IBM.
After installing the add-on and restarting Splunk, navigate back to the App Manager screen. Click Set up in the QRadar SOAR row. Fill out the required attributes for your QRadar SOAR platform and click Save. When you save, the Set Up program performs the following:

- Retrieves the case definition from the QRadar SOAR platform, so that all fields, including custom fields, are catalogued.
NOTE: If a QRadar SOAR administrator adds custom fields after you run Set Up, you need to run Set Up again to capture the fields. 
- Tests the configuration to verify that the connection is successful. If the configuration saves successfully, you are up and running.


## Support

For additional support, go to [IBM Support](https://ibm.com/mysupport). 

Including relevant information will help us resolve your issue:
- version of Splunk server
- version of Enterprise Security Add-On
- version of QRadar SOAR Add-On
- if using Splunk 8 - which Python interpreter your server is using
- steps/screenshots that will help us reproduce your issue

Including log files located in $SPLUNK_HOME/var/log/splunk:
- splunkd.log
- python.log 
- qradar_soar_config_handler.log
- qradar_soar_modalert.log
