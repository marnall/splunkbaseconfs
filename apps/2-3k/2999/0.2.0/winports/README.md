# [winports](https://github.com/oxo42/splunk-winports)

## Overview

This is a modular input for gathering all information from `netstat -ano` on Windows

## Dependencies

* Splunk 6.3+
* Supported on Windows

## Setup

* Download the release
* `$SPLUNK_HOME/bin/splunk install winports.spl -update 1`
* Restart Splunk
* Enable the `[script://$SPLUNK_HOME/etc/apps/winports/bin/winports.py]` input in `inputs.conf`

## Contact

This project was initiated by John Oxley, john.oxley@gmail.com
