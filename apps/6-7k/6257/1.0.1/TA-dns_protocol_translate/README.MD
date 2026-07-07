# DNS Protocol Translate External Lookup
**December 2021**


## Table of Contents

### OVERVIEW

- About DNS Protocol Translate External Lookup
- Release notes
- Support and resources

### INSTALLATION

- Hardware and OS requirements
- Installation steps

### USER GUIDE

---
### OVERVIEW

#### About DNS Protocol Translate External Lookup

| Author | Hurricane Labs |
| --- | --- |
| App Version | 1.0.0 |
| Has index-time operations | false |
| Create an index | false |
| Implements summarization | false |

The DNS Protocol Translate External Lookup allows the translation of DNS wire-format packet data to a human readable format using Python's dnslib (https://pypi.org/project/dnslib/)

#### Release notes

1.0.0 - Initial release
##### About this release

Version 1.0.0 of the DNS Protocol Translate External Lookup is compatible with:

| Splunk Enterprise versions | 8.0, 8.1, 8.2 |
| --- | --- |
| Platforms | Platform independent |
| Lookup file changes | None |

##### Support

**Support**

Support for this app is provided by Hurricane Labs. Please send questions to splunk-app@hurricanelabs.com
For a more detailed walkthrough of the app's setup and features, please see [the Hurricane Labs website](https://www.hurricanelabs.com/splunk-apps/check-point-block-alert-action-for-splunk)
Note that we will make our best effort to assist you, but as this app relies on an external Python library we did not develop, we cannot guarantee we will be able to fix problems that may occur. 

* Hours: 9AM-5PM EDT Monday-Friday
* Observed Holidays: Major US Holidays


## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

This external lookup works on all Splunk platforms (Linux, macOS, and Windows).

### Installation steps

#### Single-instance
**Install to search head**

1. Install the app normally. No additional configuration is needed.
2. Restart Splunk

#### Distributed/Clustered
**Install to search head and indexer cluster**

1. Install the app to both the search head and in the indexer cluster. The Python portion of the external lookup will run on the indexers, but the addon is required to be on the search head as well.
2. Restart search head and indexers.

### User Guide

The lookup can be called by using | lookup protocol_translation_lookup RDATA record_type OUTPUT translation in a search. RDATA corresponds to the DNS wire-format packet data, and record_type correspondst to the type (ex. A, AAAA, TXT). Both must be present in the data for the external lookup to function.

More information about extending the functionality of this lookup (e.g. make  it automatic) can be found at https://dev.splunk.com/enterprise/docs/devtools/externallookups/createexternallookup/