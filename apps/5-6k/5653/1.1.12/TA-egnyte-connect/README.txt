EGNYTE COLLABORATE ADD-ON FOR SPLUNK

OVERVIEW

The Egnyte Collaborate Add-on for Splunk integrates with the Egnyte Collaborate platform to ingest events from Egnyte Collaborate into Splunk for security monitoring, compliance, and analytics.

REQUIREMENTS

- Splunk Enterprise 7.x.x or 8.x.x
- Splunk Universal Forwarder (if deploying in a distributed environment)
- Network connectivity to Egnyte Collaborate API endpoints
- Valid Egnyte Collaborate account with API access
- This application should be installed on Heavy Forwarder or Universal Forwarder in case of cluster deployment

INSTALLATION

1. Download the add-on package
2. Install via Splunk Web: Settings > Data > Apps > Install app from file
3. Restart Splunk after installation

CONFIGURATION

1. Navigate to Egnyte Collaborate Add-on for Splunk
2. Click on "Configuration" tab
3. Under "Account" section, click "Add"
4. Configure the account with your Egnyte credentials
5. Egnyte Collaborate supports OAuth 2.0 authentication:
   - Click "Generate Code" to begin authorization process
   - A new browser window will open for Splunk authorization
   - Enter your Egnyte Email ID and Password
   - Click "Allow" to authorize the Splunk App
   - Copy the generated authorization code
   - Return to Splunk configuration page and paste the code
   - Complete all required fields and click "Add"

DATA INPUTS

After configuration, the add-on will collect:
- User activity logs
- File access events
- Administrative actions
- Security events

RECOMMENDED SYSTEM CONFIGURATION

- Standard Splunk configuration for Heavy Forwarder or Universal Forwarder
- Adequate disk space for log retention
- Regular monitoring of data ingestion rates

RELEASE NOTES

Version 1.1.10
- Added Egnyte.audit scope parameter to token requests
- Improved debug logging to troubleshoot production issues

Version 1.1.9
- Upgraded Splunk SDK to version 2.1.0
- Updated Python packaging dependencies (packaging-24.2, deprecation-2.1.0)
- Enhanced compatibility with newer Splunk versions
- Library dependencies and security updates

Version 1.1.8
- Link text and version updates
- UI improvements and configuration enhancements

Version 1.1.7
- Link and version changes
- Minor bug fixes and improvements

Version 1.1.6
- Link and version changes
- Configuration updates

Version 1.1.5
- Link and version changes
- Enhanced user interface elements

Version 1.1.4
- Version change and stability improvements
- Bug fixes and performance enhancements

Version 1.1.3
- Link changes and UI updates
- Improved user experience

Version 1.1.2
- Removed verification in progress status
- Enhanced logging and error handling

Version 1.1.1
- Added Egnyte ID to logs for better tracking
- Generated Splunk session ID header for requests
- Increased timeout for retrieving events
- Added session ID to request headers
- Added agent header to requests for events
- Enhanced logging with domain name information

Version 1.1.0
- Major feature enhancements
- Improved data collection mechanisms
- Enhanced authentication flow

Version 1.0.9
- Performance improvements
- Bug fixes and stability enhancements

Version 1.0.8
- Security updates
- Enhanced error handling

Version 1.0.7
- Configuration improvements
- UI enhancements

Version 1.0.6
- Bug fixes and performance improvements
- Enhanced data ingestion reliability

Version 1.0.2
- Upgrade to Add-on Builder (AOB) V1.0.4
- Improved error handling and logging

Version 1.0.1
- Updated start date and interval duration settings
- Enhanced data collection reliability

Version 1.0.0
- Initial release
- Basic Egnyte Collaborate integration
- OAuth 2.0 authentication support

BINARY FILE DECLARATION

The following binary files are included in this add-on:
* _speedups.cpython-37m-x86_64-linux-gnu.so - Part of MarkupSafe package for XML/HTML escaping (https://pypi.org/project/MarkupSafe/)

TROUBLESHOOTING

Common issues and solutions:
- Authentication failures: Verify OAuth credentials and network connectivity
- Data ingestion issues: Check input configuration and Splunk logs
- Performance issues: Monitor system resources and adjust collection intervals

SUPPORT

For technical support and issues:
Email: splunk@egnyte.com

For documentation and updates:
Visit the Egnyte Splunk integration documentation

LICENSE

This add-on is provided under Egnyte's standard licensing terms.
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-egnyte-connect/bin/ta_egnyte_connect/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
