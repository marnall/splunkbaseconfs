BluVector Reporting App for Splunk
===============================

Use Cases:
Here are the current use cases that have been built into the app.
- Accept logs (performance, health, content, events) and parse the results.
- Build dashboards to represent reports from the logs.

## Pre-requisites
- Splunk Enterprise server with user that can install the app.
- BluVector >= v3.2 
- BluVector admin credentials that can setup the output.

### Installation
- In the App Manager in Splunk, and press the **Install app from file** button.
- Choose the app an upload it.
- Back in the App manager, make sure the BluVector App is enabled and visible.
- Create the TCP listener for event from the BluVector (sourcetype = bvlogs).

### Configuration
On the BluVector CLI, in the bvintegrations container set the logstash destination IP address (i.e. the splunk IP address), the port, and the BluVector hostname (to be sent in the logs).

### Support
Email support available at support@bluvector.io.
