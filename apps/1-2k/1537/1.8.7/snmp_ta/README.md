# SNMP Modular Input v1.8.7

## IMPORTANT

The Python code in this App is Python version 3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.

## Overview

This is a Splunk modular input add-on for polling SNMP attributes and catching traps.

## Activation Key

You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key

## Features

* Simple UI based configuration
* Capture SNMP traps (Splunk becomes a SNMP trap daemon in its own right)
* Poll SNMP object attributes (GET , GETNEXT and GETBULK)
* SNMP version 1,2c and 3 support
* Declare objects to poll in textual or numeric format
* Ships with a wide selection of standard industry MIBs
* Add in your own Custom MIBs
* SNMP Walk object trees or whole MIBs
* Optionally index bulk results as individual events in Splunk
* Monitor 1 or more Objects per stanza
* Create as many SNMP input stanzas as you require
* IPv4 and IPv6 support
* Indexes SNMP events in key=value semantic format
* Plug in your own custom response handler for formatting or pre-processing
* Ships with some additional custom field extractions
* Full encryption support for declaring any sensitive credentials

## Dependencies

* Splunk 8.0+
* Supported on all Splunk Operating Systems

## Setup

* Untar the release to your $SPLUNK_HOME/etc/apps directory
* Restart Splunk
* Login and Browse to the SNMP App's landing page


## Using SNMP Version 3 

Because the Python version shipped with Splunk doesn't have the required libraries (namely `pycryptodomex` & `ctypes`) , you need to use a System Python installation when using SNMP Version 3.

So , under your System Python installation : 

1) Install the `pycryptodomex` package 

`pip install pycryptodomex`

2) Then when you configure your v3 input or trap listener in Splunk , select the option to use the System Python runtime

## Setting up SNMPv3 USM Users

If you only need to setup a single SNMPv3 USM User for polling attributes or receiving traps then you can do so via the Data Inputs SNMP stanza setup page, or by editing inputs.conf manually.

If you need to setup multiple USM Users for receiving traps on the same port , then you can do so in the `snmp_ta/default/snmpv3_usm_users.conf` file. 

**IMPORTANT** : For receiving traps , SNMPv3 USM Username and SNMPv3 USM Engine ID **must** match what is configured in the Trap sending device.

## Adding Custom MIBs

Many industry standard MIBs ship with the Modular Input.

You can see which MIBs are available by default by looking in `SPLUNK_HOME/etc/apps/snmp_ta/bin/mibs/pysnmp_mibs`

Any additional custom vendor MIBs can be added by :

1) placing the plaintext MIB file in `SPLUNK_HOME/etc/apps/snmp_ta/bin/mibs/user_plaintext_mibs` , they will be automatically compiled at runtime

or

2) precompiling the plaintext MIB into a python module and placing in `SPLUNK_HOME/etc/apps/snmp_ta/bin/mibs/user_python_mibs`

You can use the utility script `SPLUNK_HOME/etc/apps/snmp_ta/bin/mibdump.py` to precompile plaintext mibs. 

Example : This command will compile the plaintext MIB `CISCO-SMI.txt` from the `mibs/user_plaintext_mibs` directory into a python module and output it to `mibs/user_python_mibs/CISCO-SMI.py`

Change into the `snmp_ta/bin` directory and run :

`python mibdump.py --destination-directory=mibs/user_python_mibs --mib-source=mibs/common_plaintext_mibs --mib-source=mibs/user_plaintext_mibs CISCO-SMI`

Then , on the configuration screen for the SNMP input , there is a field called “MIB Names”.

Here you can specify the MIB names you want applied to your OIDs ie: IF-MIB,DNS-SERVER-MIB,BRIDGE-MIB

## Sourcetypes

The following sourcetypes are available by default :

* `snmp_attributes`
* `snmp_traps`

These sourcetypes just have some basic timestamp and field extractions based on the out of the box functionality and data formats. Of course , you are free to create your own custom sourcetypes as you require also.

## Encryption of credentials

If you require an encrypted credential in your configuration , then you can enter it on the  setup page.

Then in your configration stanza refer to it in the format `{encrypted:somekey}`

Where `somekey` is any value you choose to enter on the setup page to refer to your credential.

### Custom Response Handlers

You can provide your own custom Response Handler. This is a Python class that you should add to the `snmp_ta/bin/responsehandlers.py` module.

You can then declare this class name and any parameters in the SNMP Modular Input setup page.

For the most part the Default Response Handler should suffice.

But there may be situations where you want to format the response in a manner that is more convenient for handling your data ie: CSV or JSON.

Furthermore , you can also use a custom Response Handler implementation to perform preprocessing of your raw response data before sending it to Splunk.

## Logging

Modular Input logs will get written to `$SPLUNK_HOME/var/log/splunk/snmpmodinput_app_modularinput.log`

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/snmpmodinput_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Input logging level can be specified in the input stanza you setup. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.


## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.
