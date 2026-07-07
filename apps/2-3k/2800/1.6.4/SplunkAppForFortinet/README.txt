*****************************************
*
* App: Fortinet Fortigate App for Splunk
* Current Version: 1.6
* Last Modified: Jun 2021
* Splunk Version: 8.x
* Author: Fortinet Inc.
*
*****************************************

**** Overview ****

The Fortinet FortiGate App for Splunk provides real-time and historical
dashboard and analytical reports on traffic, threats, wireless APs, systems,
authentications and VPNs for all products across the FortiGate physical and
virtual appliances. The integrated solution pinpoints threats and attacks with
faster response times without long exposure in unknown troubleshooting state.

With the massive set of logs and big data aggregation through Splunk, the
Fortinet FortiGate App for Splunk is certified with pre-defined threat
monitoring and performance indicators that guide network security practices a
lot easier in the datacenter. As the de facto trending dashboard for many
enterprises or service providers, IT administrators can also modify the regular
expression query to custom fit for advanced security reporting and compliance
mandates.

This document describes how to set up Fortinet FortiGate App for Splunk as well
as configuration on the appliances to enable log shipping to Splunk.

**** Dependencies ****

This App depend on "Fortinet FortiGate Add-On for Splunk". Please make sure the
Add-on is installed before install this App.

**** Configuration Steps ****

Please refer to https://splunkbase.splunk.com/app/2800/#/details
for detailed configuration steps


**** Release Notes ****

v1.0: July 2015
	- Initial release

v1.1: Aug 2015
	- Change App Name to "Fortinet Fortigate App for Splunk"
	- Move data input processing to "Fortinet Fortigate
		Add-On for Splunk"
	- Change datamodel and dashboard search strings to fit 
		the Add-On sourcetypes and fieldnames

v1.2: Feb 2016
    - Changes for Splunk certification

v1.3: May 2016
    - Changes for Splunk certification

v1.4: Oct 2016
    - Optimize datamodel to make acceleration faster and size smaller
    - add default earliest time 1 month for acceleration

v1.5.0: Aug 2019
    - fix app inspection errors: remove datamodel acceleration from default. User has to enable it manually on GUI or config file.

v1.5.1: Dec 2019
    - consider anomly as threat

v1.6.0: Apr 2021
    - update term fgt to fortigate

v1.6.1: Jun 2021
    - fix duplicate throughput in long sessions

v1.6.2: Aug 2021
    - update jquery version

v1.6.3: Sept 2021
    - fix session by action aggregation
