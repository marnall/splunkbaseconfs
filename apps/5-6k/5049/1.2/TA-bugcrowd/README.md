# TA-bugcrowd

A Splunk® add-on providing a modular input for cyclically retrieving submissions from your Bugcrowd programs, creating a Splunk event for each new or updated submission.

Created using the Splunk Add-On builder.

Cross-compatible with Python 2 and 3. Tested on Splunk Enterprise 7.3.5 and 8.0.2.1.

Licensed under http://www.apache.org/licenses/LICENSE-2.0.

## Installation

Just unpack to _$SPLUNK_HOME/etc/apps_ and restart your Splunk instance. Appropriately choose between search heads, indexers and heavy forwarders in distributed environments.

Set _python.version=python2_ or _python.version=python3_ in _inputs.conf_ if you would like to explicitly specify the Python version to use. Otherwise this will be determined by your instance's global settings.

## Requirements

You'll need to provide a valid API key (HTTP Authorization Header token) to your Bugcrowd program(s) when setting up inputs.

Your Splunk instance requires access to the internet (via a proxy) to query https://api.bugcrowd.com.

## Usage

Create a new _Bugcrowd API_ input to cyclically retrieve new and/or updated submissions from each of your Bugcrowd programs.

* Set _Name_ as you please.
* Set _Interval_ to the intervals (in seconds) you wish the input to run in. Recommendation: Not less than 1800.
* Set _Index_ to the Splunk index you wish the retrieved data to end up in.
* Set _API Key_ to the API key (HTTP Authorization Header) of the Bugcrowd program you're creating the input for.
* Set _Starting From_ to the earliest submission state you wish submission data to be pulled from. Default is "triaged", which are submissions reviewed by Bugcrowd staff and purged of duplicates and non-applicable submissions. "new" will pull all new submissions reported to your program, including duplicates and non-applicable submissions. "unresolved" will only pull submissions already reviewed and accepted by your staff.
* Set _Track States_ to "true" (default) if you wish to create a new Splunk event as soon as the state of a submission changed on your Bugcrowd program (e.g. a submission is moved from "triaged" to "unresolved"). Set to "false" if you only wish to create a single Splunk event per submission, when it is first seen.

Default sourcetype for pulled data is _bugcrowd:json_. Edit _inputs.conf_ and _props.conf_ if you prefer a different naming scheme.

Edit _bugcrowd\_submission_ eventtype and _bugcrowd\_data_ macro to your needs.

Disable the app's visibility via _Manage\>Apps_ or _app.conf_ if you wish.

Set _python.version=python2_ or _python.version=python3_ in _inputs.conf_ if you would like to explicitly specify the Python version to use. Otherwise this will be determined by your instance's global settings.

## TODO / Known Issues

* api.bugcrowd.com does currently not return the timestamps of submissions' state transitions (e.g. moving an "unresolved" submission to "resolved"). Thus the add-on will set transition events' timestamps to the observed transition time, which is up to _input interval_ seconds later than the actual state transition. This was reported to Bugcrowd, awaiting enhancement of the API to return the necessary information.

* Add Bugcrowd logo/branding after consent.

* Potentially add showcase dashboard.

## History

### v1.2

* Ensured cross-compatibility for Python 2 and 3

### v1.1.1

* Added "dest" field extraction

* Fixed timestamp recognition

### v1.1.0

* Added mapping to CIM "Vulnerabilities" data model as good as possible

* Changed default visibility to true

* Renamed "source" key to "submission_source" as it was causing conflicts with Splunk's source field

