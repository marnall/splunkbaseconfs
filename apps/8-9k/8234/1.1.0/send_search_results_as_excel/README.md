# Send Search Results as Excel

## Overview

Send Search Results as Excel is a Splunk custom alert action that sends scheduled search or alert results as an Excel attachment by email.

The app is designed for use cases where Splunk users need to automatically deliver search results, reports, or alert output to one or more recipients in a simple spreadsheet format.

## Main Features

- Send Splunk search results as an Excel `.xls` attachment
- Support multiple recipients separated by commas
- Custom sender, recipient, subject, filename, and message body per alert action
- Uses Splunk email settings from `alert_actions.conf`
- Built-in Delivery Audit dashboard
- Logs generated attachment files, successful sends, SMTP failures, recipients, and SMTP error details
- Compatible with scheduled searches and alert actions

## What's New in Version 1.1.0

- Added Delivery Audit dashboard
- Added successful email delivery logging
- Improved troubleshooting visibility for SMTP and delivery issues
- Added app visibility in Splunk Apps menu
- Added app icons under the `static/` directory
- Updated app metadata for Splunkbase packaging

## Requirements

- Splunk Enterprise 9.0 or later
- Python 3 runtime provided by Splunk
- Working Splunk email configuration
- SMTP relay or SMTP server access from the Splunk Search Head

## Installation

1. Install the app on the Splunk Search Head.

2. Restart Splunk:

```bash
/opt/splunk/bin/splunk restart
