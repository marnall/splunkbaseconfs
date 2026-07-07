# Nordpass Activities App for Splunk

## Overview
The **Nordpass Activities App for Splunk** provides an integration with Nordpass Activities API, allowing you to monitor and visualize user activities directly in Splunk. This app offers real-time insights into user actions, including item accesses, login attempts, and other activities, ensuring better security and compliance monitoring.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Binary Files](#binary-files)
- [Configuration](#configuration)
    - [API Credentials Setup](#api-credentials-setup)
    - [Splunk Inputs Configuration](#splunk-inputs-configuration)
- [Usage](#usage)
    - [Dashboards](#dashboards)
    - [Alerts and Reports](#alerts-and-reports)
- [Troubleshooting](#troubleshooting)
- [Support](#support)
- [Changelog](#changelog)

## Features
- **User Activity Monitoring**: Track user activities, including login attempts, item accesses, and more.
- **Real-time Insights**: Dashboards for real-time monitoring of critical events.
- **Customizable Queries**: Configure queries to fetch data based on your requirements.
- **Integration with Splunk Alerts**: Use Splunk’s alerting mechanism to notify you of suspicious activities.

## Requirements
- Splunk Enterprise version 8.1 or later.
- API access to Nordpass Activities.
- Internet connectivity to communicate with the Nordpass API.

## Installation
### Step 1: Download the App
Download the app package from [Splunkbase](https://splunkbase.splunk.com).

### Step 2: Install the App
1. Log in to your Splunk instance.
2. Go to **Manage Apps**.
3. Click **Install App from File**.
4. Choose the downloaded app package and click **Upload**.

### Step 3: Restart Splunk
After installation, you might need to restart Splunk to enable all the features.

## App Files
The source code for these binaries is included in the `src/` directory. All binaries are built using the Go programming language.

- `bin/nordpass_activities_app-linux` pre-built binary for Linux.
- `bin/nordpass_activities_app-darwin` pre-built binary for macOS.
- `bin/nordpass_activities_app-windows.exe` pre-built binary for Windows.
- `bin/nordpass_activities_app.py` entrypoint for the script, it'll identify OS architecture and execute relevant binary.

## Configuration
### API Credentials Setup
1. Obtain the API credentials (API Token) from your Nordpass account.
2. Go to the **Nordpass Activities App Setup** page in Splunk.
3. Enter the credentials under the **API Settings** section and choose the region of your organization.

### Optional: Splunk Inputs Configuration
By default, the data fetching interval is set to `60 seconds`. To change this:
1. Navigate to **Settings > Data Inputs > Scripts**.
2. Click **Nordpass** script:
    - Set the required **Interval** for data collection.
    - Choose Set Source Type = `Manual`
    - Use `nordpass:activities` value for `Sourcetype` field if not prefilled automatically.
3. Save the configuration.

## Usage
### Dashboards
The app includes pre-built dashboards that provide insights into user activities:
- **Admin Panel Activity Dashboard**: Displays statistics on Nordpass admin panel activities.
- **Logins & Vault Access Dashboard**: Displays statistics on login attempts, success/failure rates.
- **Vault Activity Dashboard**: Highlights activities in Nordpass Vault.

### Alerts and Reports
You can set up alerts for critical events, such as multiple failed login attempts or access to sensitive items.

## Troubleshooting
### Common Issues
- **API Connection Errors**: Check your API credentials and ensure that your Splunk instance has internet access.
- **Data Not Appearing**: Verify that the data inputs are configured correctly, Nordpass script is enabled and that the API endpoint is reachable.

### Log Files
Check the following log files for troubleshooting:
- `$SPLUNK_HOME/var/log/splunk/splunkd.log`
- `$SPLUNK_HOME/var/log/splunk/nordpass_activities_app.log`

## Support
For support, please contact the Nordpass team at [support@nordpass.com](mailto:support@nordpass.com).

## Changelog
### v1.0.2
- Initial release with support for user activity tracking and pre-built dashboards.
### v1.1.0
- Support index changing on setup page of the app.
### v1.2.0
- Added support for new activity types.
### v1.3.0
- Removed redundant items type field from the NordPass Vault Activity dashboard table view
- Introduced new activities to the dashboards
- Covered some edge cases to not miss logs
- Provide an initiator if the action has no user in NordPass Admin Panel activity dashboard
