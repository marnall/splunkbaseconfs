# Splunk Command Modular Input v1.5.8
by www.baboonbones.com
May 2022
----

## IMPORTANT

The Python code in this App is dual 2.7/3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.
If running this App on Splunk versions prior to 8 , then Python 2.7 will get executed.


## Overview

This is a Splunk Modular Input for executing commands and indexing the output.

It is quite simply just a wrapper around whatever system commands/programs that you want to periodically execute and capture the output from ie: (top, ps, iostat, tshark, tcpdump etc...). It will work on all supported Splunk platforms.

## Dependencies

* Splunk 5.0+
* Supported on Windows, Linux, MacOS, Solaris, FreeBSD, HP-UX, AIX

## Setup

* Untar the release to your $SPLUNK_HOME/etc/apps directory
* Restart Splunk
* If you are using a Splunk UI Browse to `Settings -> Data Inputs -> Command` to add a new Input stanza via the UI
* If you are not using a Splunk UI (ie: you are running on a Universal Forwarder) , you need to add a stanza to inputs.conf directly as per the specification in `README/inputs.conf.spec`. The `inputs.conf` file should be placed in a `local` directory under an App or User context.

## Activation Key

You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key

## Custom Output Handlers

You can provide your own custom Output Handler. This is a Python class that you should add to the 
command_ta/bin/outputhandlers.py module.


You can then declare this class name and any parameters in the Command Input setup page.

## Encryption of credentials

If you require an encrypted credential in your configuration , then you can enter it on the setup page.

Then in your configration stanza refer to it in the format `{encrypted:somekey}`

Where `somekey` is any value you choose to enter on the setup page to refer to your credential.


## Streaming vs Non Streaming Command Output

Some commands will keep STD OUT open and stream results.For these scenarios ensure you check the "streaming output" option on the setup page.

## Environment variables

Environnment variables in the format $VARIABLE$ can be included in the command name and command arguments and they will be dynamically substituted ie: $SPLUNK_HOME$

## Logging

Modular Input logs will get written to `$SPLUNK_HOME/var/log/splunk/commandmodinput_app_modularinput.log`

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/commandmodinput_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Input logging level can be specified in the input stanza you setup. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.


## Troubleshooting

* You are using Splunk 5+
* You have permissions to execute the command
* The command is on the system PATH if you're just specifying the command name
* The path to the command is correct if you're specifying the full path to the command
* The command arguments are correct
* The command is installed
* You have configured timestamping for the sourcetype correctly

## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.

