## Description

IBM(R) DataPower(R) Operations Dashboard (DPOD) is a powerful tool providing central self-service, profiling, troubleshooting and management capabilities across all your IBM DataPower Gateways. Using DPOD, you can investigate DataPower services transactions and API-Connect API invocations processed by your DataPower Gateway cluster in near real time, down to the level of a single message.
This Splunk App is an Implementation Reference for demonstrating the value of the integration between DPOD and Splunk.
The detailed and unique information from DPOD about the IBM DataPower gateways and API Connect platform can now be displayed in Splunk, without any investment in development of such an application.

## System requirements

Splunk version 7.0 or greater
Windows, Linux operating system


## Prerequisites

If you are going to send this data to a separate index, please create one and add inputs.conf with its name in the app's local directory.
Otherwise, data will be stored in the default index.


## Installation

App installation requires admin priviledges.
Splunk instance restart is required. 
Navigate to "Manage apps" and click "Install app from file".
Upload the app bundle.
You will be prompted to choose whether to restart now or later.
It is advised to follow configuration instructions beneath prior to the restart. 


## Installation in the Distributed Deployment 

The app provides configurations that are used both at index time and at search time, so if you are installing the app in the distributed deployment you'll need to install it on the instances running the Parsing Pipeline (Heavy Forwarders or Indexers/Peers) and on the Search Heads.


## Configuration

### Splunk side

1. Create TCP data inputs on the instances running the Parsing Pipeline (Heavy Forwarders or Indexers/Peers).
   Use inputs.conf file located in the app's default directory as template.
   Create app's local directory and copy this file into it.
   Edit it to remove comments in the beginning of the lines.
   If needed, adjust the ports according to your DPOD configurations, but keep souretypes names unchanged.		

2. On the Search Head, navigate to "Settings" -> "Advanced Search" -> "Search macros". 
Locate macro named "dpod_index".
For dashboards' underlying searches to run more efficiently, update "index=*" in its definitions with name of the index designated to store DPOD data.
