# Farsight Sentry Manager For Splunk
**Feb 2017**

——-

## Template Table of Contents

### OVERVIEW

- About the Farsight Sentry Manager App For Splunk
- Release notes
- Performance benchmarks
- Support and resources

### INSTALLATION

- Hardware and software requirements
- Installation steps
- Deploy to single server instance
- Deploy to distributed deployment


### USER GUIDE

- Key concepts
- Data types
- Configure Farsight Sentry Manager For Splunk
- Troubleshooting

---
### OVERVIEW

#### About the Farsight Sentry Manager App For Splunk

| Author | Farsight Security, Inc. |
| --- | --- |
| App Version | 1.0.1 |
| Vendor Products | Farsight Sentry Manager |
| Has index-time operations | false |
| Create an index | false |
| Implements summarization | false |

The Farsight Sentry Manager App For Splunk allows a Splunk® Enterprise administrator to index data from Farsight SRA channels and RAD modules. These can be used for various purposes such as monitoring for DNS changes or brand infringement.

##### Scripts and binaries

- sra.py: Modular input which indexes output of configured SRA channel(s)
- rad.py: Modular input which indexes output of configured RAD module(s)

#### Release notes

This is the initial release of The Farsight Sentry Manager App For Splunk.

##### About this release

Version <1.0.1> of the Farsight Sentry Manager App For Splunk is compatible with:

| Splunk Enterprise versions | 1.0 |
| --- | --- |
| CIM | N/A |
| Platforms | Platform independent |
| Vendor Products | Sentry Manager |
| Lookup file changes | None |

##### Change log

1.0.1 - tag for release.
1.0.0 - Rename before launch
0.3.0 - More updates for certification, simplify UX
0.2.0 - Updating for certification
0.1.0 - Rename for release
0.0.3 - Initial code review.

##### Third-party software attributions

Version 1.0.1 of the Farsight Sentry Manager For Splunk incorporates the following third-party software or libraries.

- axamd: Python AXAMD client developed by Farsight Security

#### Performance benchmarks

Description of any performance tests run on the app with a specific version of Splunk. Details of the test(s) performed, the hardware and software used, and the outcome should be clear to a reader.

##### Support and resources

**Questions and answers**

Access questions and answers specific to the Farsight Sentry Manager App For Splunk on Splunkbase.

**Support**

Support for this app is provided by Farsight Security. Please send questions to support@farsightsecurity.com

* Hours: 9AM-5PM Monday-Frday
* Observed Holidays: Major US Holidays


## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

Farsight Sentry Manager For Splunk supports the following server platforms in the versions supported by Splunk Enterprise:

- Windows(Tested on Windows Server 2012)
- Linux (Tested on Ubuntu 15.04)

#### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Installation steps

##### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1. Install the app.
2. Go to the setup page and enter your AXAMD API key.
3. Create any SRA/RAD data inputs.

##### Deploy to distributed deployment

**Install to search head**

1. Install the app.

**Install to forwarders**

1. Install the app.
2. Go to the setup page and enter your AXAMD API key.
3. Create any SRA/RAD data inputs.

## USER GUIDE

For documentation on AXAMD as well as SRA and RAD, please visit https://www.farsightsecurity.com/Technical/.


### Data types

This app provides the index-time and search-time knowledge for the following types of data from AXAMD:

**SRA**

Define SRA channels to monitor and they will go into this data type. Its sourcetype is "sra".

**Data type**

Set up RAD modules to use and their watch hits will go into this data type. Its sourcetype is "rad".


Neither of the sourcetypes that this app generates fit into any of the Common Information Model datamodels.

### Configure Farsight Sentry Manager For Splunk

#### Modular input configuration operations

**SRA**

- Channels: a comma-delimited list of SRA channels to listen on. For a list of channels, visit this page: https://www.farsightsecurity.com/Technical/fsi-sie-channel-guide.pdf

- Watches: a comma-delimited list of watches.

- Socket timeout (Optional): Number of seconds to wait before socket times out

- Sampling rate (Optional): Percent of watch hits to actually ingest.

- Maximum packets per second (Optional): Configurable rate-limit.

- Seconds between emission of server accounting messages (Optional): Number of second to wait before sending each accounting message.

**RAD**

- RAD Module: Name of RAD Module to use. For a list of RAD modules see <TODO>

- Options for selected module: This is a freeform string. The options available depend on the module you choose. Consult the RAD Module documentation.

- Watches: a comma-delimited list of watches.

- Socket timeout (Optional): Number of seconds to wait before socket times out

- Sampling rate (Optional): Percent of watch hits to actually ingest.

- Maximum packets per second (Optional): Configurable rate-limit.

- Seconds between emission of server accounting messages (Optional): Number of second to wait before sending each accounting message.


#### Sample configurations:

**SRA**

- Channels: 212

- Watches: ch=212

- Socket timeout: 3

- Sampling rate: 50

- Maximum packets per second: 1

- Seconds between emission of server accounting messages: 120

**RAD**

- RAD Module: string_match

- Options: watch=farsight

- Watches: dns=*.

- Socket timeout: 3

- Sampling rate: 50

- Maximum packets per second: 1

- Seconds between emission of server accounting messages: 120

### Troubleshoot Farsight Sentry Manager For Splunk

***Problem*** - No events for a configured input

***Resolution*** - Even if no watch hits occur for an input, you should still receive accounting events. If Splunk indexes absolutely no events, check your API key, as well as the parameters you set for the input. Otherwise please contact Farsight at support@farsightsecurity.com.
