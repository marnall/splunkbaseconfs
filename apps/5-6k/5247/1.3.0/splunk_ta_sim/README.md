# Splunk Infrastructure Monitoring Add-on
## 

The Splunk Infrastructure Monitoring Add-on provides the following features to ingest Infrastructure Monitoring metrics and event data into Splunk.

For instructions to configure the add-on, see [Configure the Splunk Infrastructure Monitoring Add-on](https://docs.splunk.com/Documentation/SIMAddon/latest/Install/Configure).

**Splunk Infrastructure Monitoring - Modular Input**
The Splunk Infrastructure Monitoring modular input uses Splunk Infrastructure Monitoring SignalFlow computations to stream metrics from Splunk Infrastructure Monitoring into Splunk using a long-standing modular input job. You can use this metrics data in Splunk apps with a persistent cache and query mechanism. For sample inputs and recommendations, see [Configure inputs in the Splunk Infrastructure Monitoring Add-on](https://docs.splunk.com/Documentation/SIMAddon/1.0.0/Install/ModInput).

**Splunk Infrastructure Monitoring - Custom Search Command**
The Splunk Infrastructure Monitoring Add-on includes an SPL command called `sim` that accesses your Splunk Infrastructure Monitoring instance and brings metrics and events data into Splunk without adding the information to any of your indexes. This means you can use SPL to further manipulate and use the Splunk Infrastructure Monitoring data once it's in your Splunk environment. The add-on also enables Splunk IT Service Intelligence (ITSI) correlation searches to bring useful data into ITSI.

For information about the `sim` command and how to use it, see [About the sim command available with the Splunk Infrastructure Monitoring Add-on](https://docs.splunk.com/Documentation/SIMAddon/latest/Install/Commands).


## Release notes
The following section lists the new and changed features for each release:<br/>

**Version 1.0.0**<br/>
* Splunk Infrastructure Monitoring modular input (sim_modular_input) - uses Splunk Infrastructure Monitoring SignalFlow computations to stream metrics from Splunk Infrastructure Monitoring into Splunk. 
* `sim` custom search command with `flow` sub-command with `query`, `format`, `resolution` and `with_derived_metadata` parameters.
*  `sim` custom search command with `event` sub-command with `query`, `limit`, and `offset` parameters.
* Splunk Infrastructure Monitoring modular input and search command Health Check dashboard
* sim command improvements - enhancements to the sim event subcommand to extract the metadata from Splunk Infrastructure Monitoring events
*  Splunk Infrastructure Monitoring add-on configuration page

# Binary File Declaration

| File Name | File Description |
| :--- | :--- |
| libs/external/google/protobuf/pyext/_message.cpython-37m-x86_64-linux-gnu.so | Protocol Buffers are Google's data interchange format