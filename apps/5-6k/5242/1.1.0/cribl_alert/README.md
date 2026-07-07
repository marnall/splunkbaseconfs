# Cribl Modular Alert v1.1.0

## IMPORTANT

The Python code in this App is dual 2.7/3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.
If running this App on Splunk versions prior to 8 , then Python 2.7 will get executed.

## Overview

This is a Splunk Modular Alert used to export Splunk search results to Cribl.

The search results are pushed to Cribl using the [Cribl HTTPs Bulk API](https://docs.cribl.io/docs/sources-https)

## Cribl LogStream

[Cribl LogStream](https://docs.cribl.io/docs/about) helps you process machine data – logs, instrumentation data, application data, metrics, etc. – in real time, and deliver them to your analysis platform of choice. It allows you to:

* Add context to your data, by enriching it with information from external data sources.
* Help secure your data, by redacting, obfuscating, or encrypting sensitive fields.
* Optimize your data, per your performance and cost requirements.

## Activation Key

You require an activation key to use this App. Visit [http://www.baboonbones.com/#activation](http://www.baboonbones.com/#activation) to obtain a non-expiring key

## Dependencies

* Splunk 8+
* Supported on all Splunk operating systems

## Setup

* Untar the release to your $SPLUNK_HOME/etc/apps directory
* Restart Splunk

## Using

Perform a search in Splunk and then navigate to : Save As -> Alert -> Trigger Actions -> Add Actions -> Push Data to Cribl

On this dialogue you can enter your Cribl settings.

## Encryption of credentials

If you require an encrypted credential in your configuration , then you can enter it on the  setup page.

Then in your configration stanza refer to it in the format `{encrypted:somekey}`

Where `somekey` is any value you choose to enter on the setup page to refer to your credential.

## Data pushed to Cribl

The default fields pushed to Cribl are : 

* \_time
* \_raw
* host
* source
* sourcetype
* index
* eventtype

These can be overridden with any custom fields in your setup that you want to push to Cribl.

## Performance

By default , events are HTTP POSTed to Cribl in chunks of 100 events. This value can be overriden in your setup.

## Logging

Modular Alert logs will get written to `$SPLUNK_HOME/var/log/splunk/criblalert_app_modularalert.log`

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/criblalert_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Alert logging level can be specified on the setup page. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.

## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.

