# Nasuni Connector for Splunk

## Overview
Gain centralized visibility into Nasuni storage activity, security events, and ransomware alerts directly within Splunk. This integration ingests and enriches syslog data from Nasuni Edge Appliances and the Nasuni Management Console (NMC) to power search, correlation, and automated response workflows.

## Installation

### Step 1 — Install the app from Splunkbase

1. Log in to your Splunk instance and navigate to **Apps** in the top navigation bar.
2. Click **Find More Apps** to open the Splunkbase browser, then search for *Nasuni*.
3. Select the Nasuni app from the results and click **Install**. Splunk will prompt for your Splunkbase credentials if not already authenticated.
4. Once installed, restart Splunk if prompted. The app will appear in your Apps list.

---

### Step 2 — Enable the syslog listener

1. In Splunk, go to **Settings → Data Inputs → UDP** and click **New Local UDP**.
2. Enter `514` or other available port number. Set the source type to `syslog` and assign an appropriate index (e.g., `default`).
3. Save the input. Refer to the [Splunk documentation on monitoring TCP and UDP ports](https://docs.splunk.com/Documentation/Splunk/latest/Data/Monitornetworkports) for detailed guidance and platform-specific notes.

> **Note:** On Linux, Splunk must run as root (or have elevated privileges) to bind to ports below 1024. If port 514 is already in use by the OS syslog daemon (rsyslog/syslogd), disable that service's network listener first, or configure a port redirect from 514 to a higher port such as `5514`.

---

### Step 3 — Configure the Nasuni Edge Appliance

Before proceeding, ensure the selected UDP/TCP port (e.g. 514) is open between each Edge Appliance and your Splunk instance.

#### Enable syslog export (NMC)

1. Log in to the Nasuni Management Console (NMC).
2. Go to **Filers → Filer Settings → Syslog Export Settings ** in the left navigation.
3. Select the Edge Appliance(s) you wish to configure and click **Edit Filers**.
4. Under **Syslog Export**, enable syslog and enter the IP address or hostname of your Splunk instance as the syslog destination. If the port is not `514` specify as `host:port`.
5. Toggle **Send Auditing Messages**, **Send Notification Messages**, and **Lowest Log Level → Info** to capture all possible
6. Save your changes. The Edge Appliance will begin forwarding generic Edge and NMC events to Splunk. Refer to the [Nasuni NMC Guide - Syslog Export Settings](https://docs.nasuni.com/docs/chapter-8-filers-page#syslog-export) for detailed guidance.

#### (Optional) Enable volume auditing for filesystem audit events (NMC)

1. In the NMC, go to **Volumes → Auditing** under **Volume Services**.
2. Select the volume to audit and click **Edit Volumes**.
3. Set **Auditing Enabled** to **On** and select the event types to track. For ransomware coverage, include **Delete**, **Rename**, and **Security**.
4. Enable **Send Audit messages to syslog** and save. Filesystem audit events will now be included in the syslog stream sent to Splunk. Refer to the [Nasuni NMC Guide - File System Auditing](https://docs.nasuni.com/docs/chapter-7-volumes-page#file-system-auditing) for detailed guidance.

> **Note:** Ransomware protection alerts and antivirus detection alerts are forwarded automatically once syslog export is enabled — no additional configuration is required for those event types.

Deploy using the app published in Splunkbase. You ma

## Configuration
None.

## Compatibility
Splunk Enterprise, Splunk Cloud
Platform Version: 10.3, 10.2, 10.1, 10.0

## Support
Nasuni supports the function and configuration of the outgoing syslog messages. The Splunk app is supported as-is. Contact productintegrations@nasuni.com for feedback or questions about the Nasuni Splunk app. Contact Splunk for support related to the Splunk application.
