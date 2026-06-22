Dropzone AI Add-on for Splunk
=============================

This add-on enables integration with Dropzone AI's security automation platform.

Features
--------
- Health Check: Monitor Dropzone AI instance availability via the /app/api/v1/ping endpoint
- Investigations: Collect completed investigation data from Dropzone AI for analysis in Splunk

Installation
------------
1. Install this add-on via the Splunk UI or by extracting to $SPLUNK_HOME/etc/apps/
2. Restart Splunk
3. Configure your inputs via Settings > Data Inputs

Configuration
-------------
Health Check Input:
- Interval: How often to check health (default: 30 seconds)
- Base URL: Your Dropzone AI instance URL
- API Key: Optional authentication key

Investigations Input:
- Interval: How often to poll for new investigations (default: 300 seconds)
- Base URL: Your Dropzone AI instance URL
- API Key: Required authentication key

Sourcetypes
-----------
- dropzone:healthcheck - Health check status events
- dropzone:investigation - Investigation data events

Support
-------
For support, please contact Dropzone AI.
