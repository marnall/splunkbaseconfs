## Splunk Darksky Modular Input v0.5b

## Overview

This is a Splunk Modular Input Add-On for indexing weather data using the Darksky API. It polls the Darksky API every
15 mins (900 seconds) and returns the current weather for the latitude and longitude provided.

## What is Darksky ?

https://darksky.net/about/

## Implementation

This Modular Input utilizes the python-forecast.io thin wrapper, http://zeevgilovitz.com/python-forecast.io/ and is Powered by Dark Sky

## Dependencies

* Splunk 6.3+
* Supported on Windows, Linux, macOS

## Setup

* Untar the release to your $SPLUNK_HOME/etc/apps directory
* Restart Splunk

## Configuration

As this is a Modular Input , you can then configure your Darksky inputs via Settings->Data Inputs->darksky.

## Logging

Any log entries/errors will get written to $SPLUNK_HOME/var/log/splunk/splunkd.log

## Troubleshooting

* You are using Splunk 6.3+
* You are running on a supported operating system
* Look for any errors in $SPLUNK_HOME/var/log/splunk/splunkd.log
* Run this command as the same user that you are running Splunk as and observe console output : "$SPLUNK_HOME/bin/splunk cmd python ../etc/apps/darksky_ta/bin/darksky.py --scheme"

## Contact

This project was initiated by Jeffrey Stone , thejeffreystone@gmail.com


