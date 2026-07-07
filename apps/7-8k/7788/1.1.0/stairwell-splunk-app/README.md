# Stairwell App for Splunk

Add Stairwell enrichment data to your Splunk events with the Stairwell App for Splunk. This application uses Stairwell private malware analysis to integrate directly with your Splunk experience. Enrich Splunk events based on analyis of hostnames, IP addresses and file hashes.

The Stairwell App for Splunk requires a valid Stairwell API license and Splunk user privileges required for app installation. The app makes calls to the Stairwell API. When the app is installed, you'll have access to Stairwell commands that provide data enrichment extending your defenses beyond the limitations of traditional SIEM tools.

The Stairwell App for Splunk is compatible with Splunk Enterprise 9.4.0.

For the very latest information on how to use this app, visit [Stairwell App for Splunk](https://docs.stairwell.com/docs/configure-splunk-application).

## Details

### Streaming Command
This command operates on each event resulting from a search independently. It adds Stairwell enrichment data to each event that matches the type of data and the criteria given.

There are 3 types of data currently supported:

#### Hostnames
Example: find any field in the event called "host" and add Stairwell hostname enrichment data to it.

```
| makeresults | eval host = "google.com" | stairwell hostname="host"
```

#### IP Addresses
Example: find any field in the event called "ip" and add Stairwell IP address enrichment data to it.

```
| makeresults | eval ip = "192.168.0.1" | stairwell ip="ip"
```

#### Objects (file hashes)
File hashes currently supported include MD5, SHA1, SHA256.
Example: find any field in the event called "hash" and add Stairwell object enrichment data to it.

```
| makeresults | eval hash = "0385eeab00e946a302b24a91dea4187c1210597b8e17cd9e2230450f5ece21da" | stairwell object="hash"
```

### What Stairwell enrichment data is provided?
See [Stairwell App for Splunk](https://docs.stairwell.com/docs/configure-splunk-application) for details.

## Installation

### Prerequisites

1. To use the Stairwell app, you need an authentication token and an organization ID. If you have an existing Stairwell account, please go to https://app.stairwell.com/settings to generate a token and retrieve your organization ID. If not, please contact __sales@stairwell.com__.
2. To install and set up the app, you require Splunk privileges that allow app installation and configuration.

### Installation Process

1. Download the latest version of the app from [Splunkbase](https://splunkbase.splunk.com/app/7788).
2. Log into your Splunk web interface.
3. Navigate to "Apps" > "Manage Apps."
4. Click install app from file.
5. Use the file explorer to find the file you downloaded.
6. Click on upload. 
7. Once the upload is successful, you can configure the app.
8. Perform a Splunk restart. ```$SPLUNK_HOME/bin/splunk restart```
9. Log into your Splunk web interface again.
10. Navigate to "Apps" > "Stairwell App for Splunk."
11. Click the box that says "Continue to app setup page."
12. Enter your authentication token and organization ID, then click Submit.
13. The Stairwell for Splunk App home page will now appear.

## Development Setup

The Stairwell App for Splunk requires some external Python modules. These dependencies are bundled in with `.tar.gz` distributions of the app, but are not tracked in this repository. So, in order to do development work on the app, you'll need to do the following:

1. Install Stairwell-external dependencies via `pip`. These should be placed in `/bin/lib`, which can be done with the following command:

```bash
# From //integrations/stairwell-splunk-app:
pip install -r requirements.txt -t bin/lib/
```

2. Install the [Stairwell AppAPI Python SDK](https://github.com/stairwell-inc/appapi-python), and move the `stairwell_appapi_client` package into the `/bin/stairwelllib` directory.

Assuming you already have the Splunk SDK accessible in your Python environment, you should now be able to run tests via `pytest` without any errors!

## Troubleshooting
Please contact __support@stairwell.com__ for help.

## Contact
Please contact __support@stairwell.com__.

## Version History
|Version|Release Date|Compatibility|
|-------|------------|-------------|
|1.0.0|03/17/2025|Splunk Enterprise 9.4|
|1.1.0|04/25/2024|Splunk Enterprise 9.4|