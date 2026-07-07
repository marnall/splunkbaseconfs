Beyond Identity Splunk App
==========================

## Overview
The Beyond Identity Splunk App provides comprehensive monitoring and analysis of authentication and user activities within your Beyond Identity environment. This app enables security teams to gain visibility into authentication events, user behaviors, device information, and potential security threats through an intuitive dashboard interface.

## Version
Current Version: 1.0.15

## Key Features
- **Authentication Analytics**: Track success/failure rates and trends
- **User Activity Monitoring**: Monitor user login patterns and behaviors
- **Device Insights**: View device types, models, and security status
- **Geographic Visualization**: Map authentication attempts by location
- **Real-time Monitoring**: Track authentication events as they happen
- **Security Posture**: Monitor security features like FileVault status

## Requirements
- Splunk Enterprise 8.0.0 or later
- Network access to Beyond Identity API endpoints
- Appropriate permissions to access authentication logs

## Installation
1. Download the latest version of the app
2. Install the app through Splunk Web or manually place in `$SPLUNK_HOME/etc/apps/`
3. Restart Splunk
4. The app is pre-configured to use the `beyond_identity_index` for data

## Configuration
1. The app uses a macro called `beyond_identity_index` to specify the index where Beyond Identity data is stored
2. To customize the index, update the macro in the Splunk Search & Reporting app:
   - Navigate to Settings > Advanced Search > Search Macros
   - Locate and edit the `beyond_identity_index` macro
   - Update the definition to point to your desired index

## Data Collection
The app visualizes the following types of data:
- Authentication success/failure events
- User login patterns and locations
- Device information and security status
- Application versions and platform details
- Geographic distribution of authentication attempts

## Usage
1. Navigate to the Beyond Identity app in Splunk
2. Use the Analytics Dashboard to monitor authentication activities
3. Filter data using the time range selector
4. Drill down into specific events for detailed analysis

## Support
For support, please contact Beyond Identity Support at support@beyondidentity.com

## License
This app is provided under the terms of the Splunk App for Enterprise Security license agreement.

## Changelog
### v1.0.13
- Updated dashboard queries to use `beyond_identity_index` macro
- Removed index selector from UI for simplified configuration
- Improved data visualization and performance

### v1.0.8
- Initial release
- Basic authentication monitoring
- Custom dashboards and reports
