# ABOUT THIS APP

- The App for RST Threat Feed is used to download data from RST Cloud API. It saves the data into lookups for further usage.
- This App contains download/update/cleanup jobs to maintain the lookups on the daily basis
- This App contains 4 examples of detection rules (alerts) to demonstrate how to use Threat Intelligence indicators in your searches.
- After the app is installed, you may want to manually run once download/update jobs to initialise the lookups the first time or wait for the scheduled jobs to populate it for you around 02:00 AM UTC

# Usage

To check values from any logs, you can just use simple lookups like that:

```
| lookup rst_threat_feed_domain_summary ioc_value as domain

| lookup rst_threat_feed_ip_summary ioc_value as dest_ip

| lookup rst_threat_feed_url_summary ioc_value as url

| lookup rst_threat_feed_hash_summary ioc_value as file_hash

```

# REQUIREMENTS

- Splunk version 10.x, 9.3.x, 9.2.x, 9.1.x, 9.0.x, 8.2.x, 8.1.x, 8.0.x
- Python version: python3
- Appropriate API key for collecting data from RST Cloud (send an inquiry to trial@rstcloud.com)

# Release Notes

## Version v.1.0.6

- Excluded `outputlookup` from risky commands for this app.
- Added `python.required` to `commands.conf`.

## Version v.1.0.5
- the `rstdownload` command now supports downloading hourly, 4h and 12h feeds in addition to daily snapshots
- splunklib was upgraded up to v2.1.1

## Version v.1.0.4

- splunklib was upgraded up to v2.1.0

## Version v.1.0.3

- splunklib for python was updated to v2.0.1
- lookup merge logic updates
- added search head replication parameter

## Version v.1.0.2

- splunklib for python was updated to v1.7.4
- filter macros are added to the alert examples
- minor updates

## Version v.1.0.1

- updated to support Splunk Cloud
- now uses Splunk client secret storage mechanism to store RST Cloud API key
- no Splunk restart required after installation

## Version 1.0.0

- Added RST Threat Feed daily sync support

# Uninstall & Cleanup steps

- Remove $SPLUNK_HOME/etc/apps/rstcloud_threatfeed
- To reflect the cleanup changes in UI, restart the Splunk instance

# TROUBLESHOOTING

- Authentication Failure:
  - Check the network connectivity and make sure that the RST Cloud API is reachable: api.rstcloud.net
- Download failure:
  - Check the network connectivity and make sure that Amazon S3 is reachable: profeeds.s3.amazonaws.com

# SUPPORT

- Support Offered: Yes
- Support Email: support@rstcloud.com

### Copyright (C) 2026 RST Cloud Pty Ltd
