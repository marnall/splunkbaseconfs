# Upstream Security Add-on for Cybersecurity Alerts

## Overview

This add-on enables Splunk to ingest vehicle cybersecurity alerts from the
Upstream Security platform. It polls the Upstream REST API on a configurable
interval and uses marker-based checkpointing to ensure no duplicate events.

## Prerequisites

- Splunk Enterprise 8.0+ or Splunk Cloud
- An active Upstream Security account with API access
- A valid Bearer token generated from the Upstream Security platform

## Installation

1. Install the add-on via "Manage Apps" > "Install app from file" in Splunk Web,
   or extract the package to $SPLUNK_HOME/etc/apps/.
2. Restart Splunk if prompted.

## Configuration

1. Navigate to the add-on's "Inputs" tab in Splunk Web.
2. Click "Create New Input" and provide:
   - REST API URL: Your Upstream API endpoint (default: https://api.upstream-c4.io/externalApi)
   - Token: Your Bearer token (e.g. "Bearer eyJ...")
   - Max events to pull: Maximum number of events per poll cycle (default: 1000)
   - Interval: Polling interval in seconds (default: 20)
3. Select the destination index and enable the input.

## Sourcetype

Events are ingested with sourcetype "UpstreamData" in JSON format.

## Support

Contact Upstream Security at support@upstream.auto for assistance.

# Binary File Declaration
bin/ta_upstream/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-upstream/bin/ta_upstream/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
