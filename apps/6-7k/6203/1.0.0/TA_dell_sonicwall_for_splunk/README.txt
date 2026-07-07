Dell SonicWall Add-on for Splunk
Copyright (C) 2021 CyberSecThreat Corporation Limited. All Rights Reserved.

================================================
Overview
================================================

This app provides field extraction, cim mapping(network, vpn, dhcp, authentication, ids and change) for Dell SonicWall Add-on for Splunk in Splunk.

The field extraction accepts both Splunk native tcp/udp connections and rsyslog style syslog.

Most of the field extraction and lookup table construction is based on Office Reference Guide and logs observation:
https://www.sonicwall.com/techdocs/pdf/sonicos-6-5-1-log-events-reference-guide.pdf

As the log pattern of Dell SonicWall is a little bit differnt from other firewall, the field extraction process tried to match the behaviour just like other firewall as much as possible.

In summary, there are some possible combination of logs:
1. "Connection Opened" -> "Connection Closed" (No log indicate it is dropped, it can be evalulated as allowed)
2. "Connection Opened" -> "NAT Mapping" -> "Connection Closed" (Address is NAT'ed, No log indicate it is dropped, it can be evalulated as allowed)
3. "Connection Opened" -> "*drop*" -> "Connection Closed" (TCP Connection is dropped)
4. "Connection Closed" (UDP connection is allowed)
5. "*drop*" -> "Connection Closed" (UDP connection is denied)

For ALL stateful protocol such as TCP AND stateless protocol with response such as DNS, NTP: rcvd and rpkt with a value greater than 0 can be evaluated as allowed traffic.

However, for those stateless protocol without response such as syslog, "Connection Closed" without another "Packet Dropped" log indicate it is allowed. 

On the other hand, "Connection Closed" with another "Packet Dropped" log indicate it is blocked.

2 Macros (dell_sonicwall_opened_connection & dell_sonicwall_closed_connection) are included in this app.

In general, the macro `dell_sonicwall_closed_connection` is good enough and it will behave like other firewall log. However, if the connection persists for a long time, there may be some delay to security monitoring. Therefore, the macro `dell_sonicwall_opened_connection` can be used as early detection.

Depending on the use case you are trying to build, you may includes bytes_in to count the number of session more accurately.

================================================
Configuring Splunk
================================================
This app need to install on Splunk Search Head.

Install this app into Splunk by doing the following:

  1. Log in to Splunk Web and navigate to "Apps » Manage Apps" via the app dropdown at the top left of Splunk's user interface
  2. Click the "install app from file" button
  3. Upload the file by clicking "Choose file" and selecting the app
  4. Click upload
  5. Restart Splunk if a dialog asks you to

Configure the input sourcetype as dell:sonicwall.

================================================
Known Limitations
================================================

N/A



================================================
Getting Support
================================================

This is an open source project and no active support is provided. If there is any issues, email to info@cybersecthreat.com during weekday business hours (GMT+8).




================================================
Change History
================================================

+---------+------------------------------------------------------------------------------------------------------------------+
| Version |  Changes                                                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 1.0.0   | Initial release                                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|
