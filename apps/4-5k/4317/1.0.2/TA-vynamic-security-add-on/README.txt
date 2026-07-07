# Vynamic Security Add-on for Splunk version 1.0.2
Copyright (C) 2024 Diebold Nixdorf Inc. All Rights Reserved.

### 1. Introduction
Event data is analyzed and serves as the basis for several reports for Vynamic Security Dashboard.
Current version is based on Intrusion Protection events and framework Ticketing events for Intrusion Protection. Note that Splunk 9.0.1 was the lowest version used for tests.

### 2. Release Notes
The latest available version of the add-on can be retrieved from Splunkbase, the Splunk marketplace for applications and add-ons (https://splunkbase.splunk.com/app/4317).

### 3. Registration and Licensing
For all information regarding product registration and licensing please refer to Vynamic Security Suite - Framework user Manual.

### 4. Installation and Configuration
Vynamic Security add-on can be installed from within the Splunk instance or it can be downloaded and installed from a file.

Install via Splunk: https://docs.splunk.com/Documentation/AddOns/released/Overview/SplunkCloudinstall
Download and Install: https://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall

The add-on will be visible on the left side of the Splunk instance right after it has been installed. Keep in mind that it is possible to set the Vynamic Security Dashboard as your default Splunk dashboard. You can do that by clicking on the Choose a home dashboard area and selecting Vynamic Security Dashboard. Note that you must type a part of the Vynamic Security name for it to appear on the list.
One option to feed event data into Splunk is to make every ATM sent its events line by line via ProAgent to the ProView server. The lines get forwarded to the HTTP Event Collector of the specific Splunk instance.

A default HTTP Event Collector Token (a4d2e5dc-7b7a-4246-ae51-4f0182e7d3f1) is a part of the add-on. However, it can be replaced by a custom HTTP Event Collector Token.
For more information about HTTP Event Collector Token please refer to Splunk's documentation.
It is possible to use a database to store the events coming from the ProView server, and then to retrieve the events via Splunk DB Connect add-on (Splunkbase link: https://splunkbase.splunk.com/app/2686).

### 5. Using Vynamic Security Dashboard
Report panels offered by Vynamic Security Dashboard provide an overview of the current state of the connected automated teller machines. These panels are based on pre-defined filters and provide data that is either derived from a static time frame or is adjusted dynamically. Most of the panels support drilldown functionality that leads to a list of potentially interesting raw events depending on the clicked element.

##### 5.1 Filtering
Vynamic Security Dashboard provides an option to filter the obtained data through the use of a filtering section located on the upper-left corner of the screen. It is possible to filter the ATMs by their full names or parts of their name. Note that it is possible to use an asterisk as a wildcard. Keep in mind that the filter field is not case sensitive.
Example:

ATM*23 will provide information about all automated teller machines that have both ATM and 23 in their names.

##### 5.2 Critical Events
Critical events are shown on two panels. One of the panel shows the total percentage of critical events within the last 24 hours in a gauge chart. Another panel provides information about 10 ATMs where the largest number of critical events happened.

##### 5.3 USB Device Rejection Events
Information about blocked USB devices is shown on three panels. The first panel provides information about three ATMs with most USB device rejections. The second panel shows a line chart of USB device rejections over the last week. The last panel provides a bar chart containing 10 USB devices that were most commonly blocked.

##### 5.4 Denied Process Events
Information about denied processes is shown on two panels. The first panel provides information about three ATMs with most denied processes. The second panel shows a bar chart with 10 processes that were most commonly blocked.

##### 5.5 Integrity Issue Events
Information about integrity issues is shown on two panels. The first panel shows a bar chart with 10 registry entries and files that were most commonly raised issues for. The second panel shows a bar chart of 10 BIOS integrity issues that happened most.

##### 5.6 Ticketing Events
One panel provides a table with all ATMs in scope which are currently unprotected, based on ticketing events for Intrusion Protection and on calls to both IpsOff.exe and IpsOn.exe. ATMs which are unprotected for longer than two hours are marked in orange and change to red for an unprotected time longer than 24 hours. The second panel shows a table where all calls to IpsOff.exe in the last 24 hours are listed.

##### 5.7 File & Registry Access Blocking Events
There are two panels for blocking events with the same target that happened on any ATM in the current scope. The first one shows a table with 10 most commonly blocked file accesses to software installation folders of Diebold Nixdorf and NCR. The second shows a table with most commonly blocked accesses to registry entries of Diebold Nixdorf and NCR.
