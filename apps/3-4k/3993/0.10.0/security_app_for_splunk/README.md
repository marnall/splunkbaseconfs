# PAVO Security App For Splunk

|                           |                                                |
|---------------------------|------------------------------------------------|
| Author                    | Aplura, LLC                                    |
| App Version               | 0.10.0                                         |
| App Build                 | 16                                             |
| Vendor Products           | Aplura PAVO                                    |
| Has index-time operations | false                                          |
| Creates an index          | false                                          |
| Implements summarization  | Currently, the app does not generate summaries |

Provides a holistic view of PAVO resources.

## About this release

Version 0.10.0 of PAVO Security App For Splunk is compatible with:

|                            |                                 |
|----------------------------|---------------------------------|
| Splunk Enterprise versions | 9.0, 8.2, 8.1, 8.0              |
| Platforms                  | Splunk Enterprise, Splunk Cloud |

# Lookups

The PAVO Security App For Splunk contains the following lookup files.

1.  available_apps_list.csv

    1.  contains the list of recommended apps that may be installed as part of the PAVO Security App For Splunk

# Event Generator

PAVO Security App For Splunk does not include an event generator.

# Acceleration

1.  Summary Indexing: No

2.  Data Model Acceleration: No

3.  Report Acceleration: No

# Installation

Install the PAVO Security App For Splunk on Search Heads only.

# Software requirements

## Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## Download

Download PAVO Security App For Splunk at <https://splunkbase.splunk.com/3993>.

# Scripts and Binaries

The PAVO Security App For Splunk contains the following scripts and binaries.

|                            |                                                            |
|----------------------------|------------------------------------------------------------|
| Script                     | Description                                                |
| Diag.py                    | `splunk diag` integration script.                          |
| app_properties.py          | Python variables for inclusion in any other Python scripts |
| security_app_for_splunk.py | Python variables for use with other Python scripts         |
| version.py                 | Backwards compatability with `app_properties.py`           |

# Release Notes

1.  Version 1.0.0

    1.  Removal of various integration libraries

# Deprecated or Removed Features

1.  Version 1.0.0

    1.  removes various API integration components

# Support and resources

# Questions and answers

Access questions and answers specific to PAVO Security App For Splunk at <https://answers.splunk.com>. Be sure to tag your question with the App.

## Support

- Support Email: None

- Support Offered: Splunk Answers, Community Engagement
