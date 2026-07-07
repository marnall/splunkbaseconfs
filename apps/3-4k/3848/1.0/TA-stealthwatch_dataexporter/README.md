Technology Add-on for Cisco Stealthwatch Data Exporter by Discovered Intelligence Inc.

## Overview ############################
Using the Cisco Stealthwatch Data Exporter application, de-duplicated, stitched, flow records can be retrieved from the Flow Forwarder Dock Container on the Flow Collector over a web socket to registered clients. This Technology Add-on provides the necessary knowledge objects to ensure the flow events collected are common information model compliant. Furthermore, the add-on provides the necessary index-time configurations to perform the proper line break, time extractions, etc.

## Prerequistes ############################
1. Cisco Stealthwatch Data Exporter installed and configured -- https://developer.cisco.com/docs/stealthwatch/

## Installation ############################
The following steps are all thats required to install this application:
1. Install the application to your search head and indexers using standard deployment procedures for your environment.
2. Restart Splunk.
3. Create an inputs configuration to onboard the flow events collected by the Data Exporter. The sourcetype is expected to be 'stealthwatch:fc:flow'.

## Technical Support ######################

For support, please email support@discoverdintelligence.ca

App developed by Discovered Intelligence Inc.
www.DiscoveredIntelligence.ca
