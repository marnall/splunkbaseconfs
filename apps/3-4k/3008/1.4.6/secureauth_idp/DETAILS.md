**Information**

App: SecureAuth Identity Platform
Current Version: 1.4.5
Last Modified: Oct 2022
Splunk Version: 9.x/8.x/7.x
Author: SecureAuth Corporation

**Overview**

SecureAuth IdP for Splunk provides a clear view of user access into your enterprise resources such as VPN and ADC, cloud application access as well as on-premise applications.  All teams in your organization will be able to leverage the dashboards, such as Security teams for suspicious activity and forensics, Operations for health, load and response times, Application teams for application access history and trends, as well as C-Level reporting for management.

The SecureAuth IdP Splunk App supports SecureAuth IdP version 9.0 and greater through syslog or the Splunk Forwarder. Please contact your Sales Representative if you need support for an IdP version prior to 9.0.

![](39c6b926-cc5d-11e5-aa96-023891c2a253.png)

**Prerequisites**

IdP Version Support:

-   The SecureAuth IdP Splunk App supports IdP 9.0 and greater

Setting up SecureAuth IdP (full cloud/SaaS/Hosted):

-   For Full Cloud/SaaS Installations, please contact your support representative for options.

-   The syslog option is not available for full cloud customers

Setting up SecureAuth IdP (on-premise configurations only):

-   Enable Audit logs Syslog option on all Realms (https://docs.classic.secureauth.com/display/91docs/Logs+Tab+Configuration)

-   (Recommend) Rename default Log Instance ID from realm number to meaningful name appended by the realm number

-   Enter the IP address of your Syslog Server

-   Change the default target port (514) if it differs from your Splunk
    listening port

-   Use RFC5424 format

-   (Optional) enter the PEN of your Syslog server (Splunk is 27389)

Utilizing Splunk Universal Forwarder (on-premise, hybrid):

-   Install the Splunk Universal Forwarder (UF)

-   Modify the `$SPLUNK_HOME/etc/apps/search/local/inputs.conf` file:

```
[udp://1514]
connection_host = ip
index = secureauth
sourcetype = secureauth:idp

[tcp://1514]
connection_host = ip
index = secureauth
sourcetype = secureauth:idp
```

- Configure the Secureauth IdP Realms to point to `127.0.0.1` and port `1514`

- Modify the `$SPLUNK_HOME/etc/system/local/outputs.conf`

```
[tcpout]
defaultGroup = mySplunk

[tcpout:mySplunk]
disabled=false
server=<splunk_indexer>:9997
```

- Ensure there is a listener on the Splunk indexer for port 9997 -- Settings | Forwarding and Receiving | Receiving and all appropriate firewall ports allow traffic from the UF to the indexer on 9997

Utilizing Splunk Cloud:

-   Download the appropriate configuration file for the app within Splunk Cloud and install on the IdP server (Apps -> Universal Forwarder in Splunk Cloud and install the resulting `splunkclouduf.spl` as an app on the server with the Universal Forwarder)

![](3ca002f6-cc5d-11e5-9651-023891c2a253.png)

Notes:

-   Audit logging is not enabled on each realm by default

-   Provided all IdP appliances have synchronization enabled, the logging configuration will automatically replicated to all appliances

**Quick Start Guide**

Install the app:

There are three ways to install the app:

1.  Install from Splunk web UI:
    - Manage Apps -> Browse more apps -> Search keyword 'SecureAuth' -> Click Install free button -> Click to restart Splunk service.


2.	Install from file on Splunk web UI:
  - Download the SecureAuth IdP Splunk App from https://splunkbase.splunk.com/app/3008
	- Install via: Manage Apps -> Install from file -> Upload the downloaded .tgz file -> Click to restart Splunk service.


3.	Install from file on Splunk server CLI interface:
	- Download the SecureAuth IdP Splunk App from https://splunkbase.splunk.com/app/3008
	- Change directory to $SPLUNK_HOME/etc/apps -> Extract the .tgz file (`sudo tar zxvf <location_of_tgz_file>`) -> Restart Splunk service (`sudo $SPLUNK_HOME/bin/splunk restart`).

**App Configuration**
**Index**
Due to recent changes by Splunk, you will need to make your own index for the data. You can simple copy the "indexes.conf.sample" from the default folder into the local folder and rename it to "indexes.conf".

By default this app assumes your data will be located in index="secureauth".

You can update all of the dashboards by simply modifying the [secureauth_base] stanza in "macros.conf".

** Sourcetype **
This app requires the sourcetype "secureauth:idp" to render all dashboards.

You can either rename your existing sourcetype by going to "Settings -> Fields -> Sourcetype renaming" or update the props.conf to match your existing sourcetype.

**Set up Splunk to Receive Data - Syslog**

Setting --\> Data Inputs --\> UDP --\> add new-- \> enter 514 for port \# and select UDP --\> Select Secureath.idp for source type and SecureAuth for Index

![](3fc0cbaa-cc5d-11e5-b37d-023891c2a253.png)

** Demo Data **
The app no longer contains demo data.

If you would like to install demo data, please contact your Sales Representative.

**Technical Support Policy and Contact Information**

**Contact Information:**
Support cases can be opened at the following web site or via phone:
https://support.secureauth.com/hc/en-us/requests/new
+1-949-777-6959, select option 2 or 1-866-859-1526

**Hours of Operation:**
SecureAuth support is available 24x7.

**Holidays:**
SecureAuth support is available 24x7 including holidays.

**Response time:**
Case severity is assigned based on the technical importance of the problem. SecureAuth IdP Splunk App issues are considered Low severity. Per SecureAuth Support SLA, response time for Low Severity requests is within one business day.

* **Severity**: Low
* **Description**: A user level fault only affecting one authorized user but not affecting ability to perform business functions – (i.e., no business or “Customer” client impact). Enhancement requests
* **Response Time**: Within 1 business day

**Issue Tracking**
SecureAuth uses a cloud based incident response and customer management application that is available to our worldwide support teams.
