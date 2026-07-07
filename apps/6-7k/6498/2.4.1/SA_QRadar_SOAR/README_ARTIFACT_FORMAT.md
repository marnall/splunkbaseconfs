# SA_QRadar_SOAR Artifact Configuration Guide

## Overview

This document explains how to configure artifacts when creating QRadar SOAR incidents from Splunk alerts, particularly when using Splunk Enterprise Security 8.3.0 or later.

## Background

Splunk Enterprise Security 8.3.0 introduced a new Detection Editor that uses dynamic UI generation. This change affects how third-party alert actions display their configuration fields. To ensure compatibility with ES 8.3.0's Detection Editor while maintaining backward compatibility with standard Splunk interfaces, the SA_QRadar_SOAR app now supports two artifact configuration formats.

## Artifact Configuration Formats

### Format 1: Pipe-Delimited (ES 8.3.0 Detection Editor)

**Use this format when configuring alerts in ES 8.3.0 Detection Editor.**

Each artifact is configured using a single field with pipe-delimited values:

```
type|value|description
```

**Example:**
```
IP Address|192.168.1.100|Suspicious source IP from failed login attempts
```

**Field Breakdown:**
- **type**: The artifact type (e.g., IP Address, Email Address, URL, etc.)
- **value**: The actual artifact value (e.g., 192.168.1.100)
- **description**: Optional description of the artifact

**Available Artifact Fields:**
- Artifact 1 through Artifact 8 (configurable via Setup)

**Important Notes:**
- All three components (type, value, description) should be separated by the pipe character `|`
- The description is optional; you can use just `type|value` if no description is needed
- Whitespace around the pipe characters will be automatically trimmed
- You can use Splunk tokens in any component (e.g., `IP Address|$src_ip$|Source IP from event`)

**Examples:**

1. IP Address artifact:
   ```
   IP Address|$src_ip$|Source IP from security event
   ```

2. Email artifact without description:
   ```
   Email Address|$user_email$|
   ```

3. URL artifact:
   ```
   URL|$malicious_url$|Phishing URL detected in email
   ```

4. Artifact with comma-separated values:
   ```
   IP Address|$result.src_ip$,$result.dest_ip$|Source and destination IPs
   ```

5. Multiple artifacts in one alert:
   - Artifact 1: `IP Address|$src_ip$|Attacker IP`
   - Artifact 2: `User Account|$user$|Compromised account`
   - Artifact 3: `File Name|$file_name$|Malicious file`

### Format 2: Separate Fields (Standard Splunk Interface)

**Use this format when configuring alerts in standard Splunk saved searches.**

Each artifact has three separate fields:

1. **Artifact Type** (dropdown): Select from available artifact types
2. **Artifact Value** (text field): Enter the artifact value
3. **Artifact Description** (text field): Enter optional description

**Example Configuration:**
- Artifact 1 Type: `IP Address`
- Artifact 1 Value: `$src_ip$`
- Artifact 1 Description: `Source IP from failed login`

## Backward Compatibility

The SA_QRadar_SOAR app automatically detects which format you're using:

1. **Pipe-delimited format detected**: When an artifact field contains a pipe character `|`, it's parsed as `type|value|description`
2. **Separate fields format detected**: When no pipe character is present, the app looks for the legacy `artifactNtype`, `artifactNvalue`, and `artifactNdescription` fields

This means:
- Existing alerts configured with separate fields will continue to work
- New alerts can use the pipe-delimited format in ES 8.3.0
- You can have some alerts using one format and other alerts using the other format

## Common Artifact Types

Here are some commonly used artifact types in QRadar SOAR:

- **IP Address**: IPv4 or IPv6 addresses
- **Email Address**: Email addresses
- **URL**: Web URLs
- **User Account**: Usernames or account identifiers
- **File Name**: File names or paths
- **File Hash**: MD5, SHA1, or SHA256 hashes
- **DNS Name**: Domain names or hostnames
- **MAC Address**: Network MAC addresses
- **Process Name**: Process or service names
- **Registry Key**: Windows registry keys
- **System Name**: Computer or system names

**Note**: The exact list of available artifact types depends on your QRadar SOAR configuration. Check with your QRadar SOAR administrator for the complete list.

## Troubleshooting

### Issue: Artifacts not appearing in QRadar SOAR incidents

**Possible causes:**
1. Empty artifact values
2. Incorrect pipe-delimited format
3. Artifact type doesn't exist in QRadar SOAR
4. Exceeded maximum number of artifacts (check Setup configuration)

**Solutions:**
1. Verify artifact values are not empty after token substitution
2. Check format: `type|value|description` with proper pipe separators
3. Verify artifact type names match exactly with QRadar SOAR (case-sensitive)
4. Check the "Maximum Number of Artifacts" setting in Setup

### Issue: Error "The value for the artifact type X is invalid"

**Symptom:** QRadar SOAR API returns 400 error with message like:
```
The value for the artifact type IP Address is invalid: IP
```

**Cause:** The artifact value field contains the entire pipe-delimited string instead of just the value portion.

**Solution:** This was a bug in the initial implementation that has been fixed. The code now properly skips legacy value fields that contain pipe characters (which indicates they're actually new format data). Update to the latest version of the code.

**Workaround if issue persists:** Ensure you're using the pipe-delimited format correctly:
- Correct: `IP Address|192.168.1.1|Description`
- Incorrect: `IP Address|192.168.1.1|Description` in the value field of separate fields format

### Issue: Pipe character in artifact value

If your artifact value legitimately contains a pipe character, you have two options:

1. **Use separate fields format** (standard Splunk interface only)
2. **Escape or replace the pipe character** before passing to the alert action

### Issue: Comma-separated values in artifact

**Q: Can I use comma-separated tokens like `$result.src_ip$,$result.dest_ip$` in the value field?**

**A: Yes!** The value field supports any content including commas. Only the pipe character `|` is used as a delimiter.

**Example:**
```
IP Address|$result.src_ip$,$result.dest_ip$|Source and destination IPs
```

**Important:** This creates a **single artifact** with a comma-separated value. If you need **separate artifacts** for each value, configure them individually:
```
Artifact 1: IP Address|$result.src_ip$|Source IP
Artifact 2: IP Address|$result.dest_ip$|Destination IP
```

### Issue: ES 8.3.0 Detection Editor only shows one field per artifact

This is expected behavior. ES 8.3.0's Detection Editor consolidates the three fields into one for better compatibility. Use the pipe-delimited format as described above.

## Configuration Examples

### Example 1: Phishing Email Alert

**ES 8.3.0 Detection Editor:**
- Artifact 1: `Email Address|$sender$|Phishing email sender`
- Artifact 2: `URL|$malicious_url$|Phishing URL in email body`
- Artifact 3: `Email Subject|$subject$|Email subject line`

### Example 2: Failed Login Alert

**ES 8.3.0 Detection Editor:**
- Artifact 1: `IP Address|$src_ip$|Source of failed login attempts`
- Artifact 2: `User Account|$user$|Target user account`

### Example 3: Malware Detection

**ES 8.3.0 Detection Editor:**
- Artifact 1: `File Hash|$file_hash$|MD5 hash of malicious file`
- Artifact 2: `File Name|$file_name$|Malicious file name`
- Artifact 3: `System Name|$dest$|Infected system`

## Additional Resources

- QRadar SOAR Documentation: Consult your QRadar SOAR administrator
- Splunk Token Substitution: [Splunk Documentation](http://docs.splunk.com/Documentation/Splunk/latest/AdvancedDev/ModAlertsIntro#About_token_replacement_in_custom_alert_actions)
- ES 8.3.0 Detection Editor: Splunk Enterprise Security documentation

## Support

For issues or questions:
1. Check the Splunk logs: `index=_internal sourcetype=splunkd qradar_soar`
2. Review QRadar SOAR incident creation logs
3. Contact your Splunk or QRadar SOAR administrator

---

**Version**: 1.0  
**Last Updated**: 2026-04-24  
**Compatible with**: Splunk Enterprise Security 8.3.0+, Standard Splunk 8.x+