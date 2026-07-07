# Scheduled Export of Indexed Data (SEND) to File v1.3.9

## IMPORTANT

The Python code in this App is dual 2.7/3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.
If running this App on Splunk versions prior to 8 , then Python 2.7 will get executed.


## Overview

This is a Splunk Modular Alert used to facilitate scheduled export of indexed data (SEND) to a file location

The exported file is just a gzipped CSV of the search results that triggered the alert.

The real intent of this add-on though is as an example for developers to follow to show how you can essentially leverage the Modular Alerts framework to perform a scheduled data output.

Other types of outputs to consider implementing : ftp,scp,jms,kafka,aws,rdbms,datawarehouse,some other data storage or processing platform etc...

## Activation Key

You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key

## Note from the Modular Alerts engineer

The only thing to keep in mind is constraint of alerts in terms of scalability. The alert action script has a limited lifetime before it’s being killed by the scheduler. The scheduler itself is also not designed for massive output loads. It should be perfectly fine for smaller scale output, though.

## Dependencies

* Splunk 6.3+
* Supported on Windows, Linux, MacOS, Solaris, FreeBSD, HP-UX, AIX

## Setup

* Untar the release to your $SPLUNK_HOME/etc/apps directory
* Restart Splunk


## Using

Perform a search in Splunk and then navigate to : Save As -> Alert -> Trigger Actions -> Add Actions -> SEND to File

On this dialogue you can enter your file output settings.

## Encryption of credentials

If you require an encrypted credential in your configuration , then you can enter it on the  setup page.

Then in your configration stanza refer to it in the format `{encrypted:somekey}`

Where `somekey` is any value you choose to enter on the setup page to refer to your credential.

## Logging

Modular Alert logs will get written to `$SPLUNK_HOME/var/log/splunk/sendfilealert_app_modularalert.log`

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/sendfilealert_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Alert logging level can be specified on the setup page. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.

## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.

