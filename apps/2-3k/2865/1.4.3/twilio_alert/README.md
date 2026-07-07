# Splunk Twilio SMS Alerting v1.4.3

## IMPORTANT

The Python code in this App is dual 2.7/3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.
If running this App on Splunk versions prior to 8 , then Python 2.7 will get executed.


## Overview

This is a Splunk Modular Alert for sending SMS messages using Twilio.

## Dependencies

* Splunk 7.0+ Enterprise or Cloud
* Supported on all Splunk platforms

## Setup

* Untar the release to your `$SPLUNK_HOME/etc/apps` directory
* Restart Splunk
* Browse to the App's landing page.
* Browse to the `Setup` menu tab and setup your Twilio credentials.
* Encrypted credentials are saved to `$SPLUNK_HOME/etc/apps/twilio_alert/local/passwords.conf`
* Enter your Activation Key , see below
* Browse to the `Alert Actions` menu tab and setup your alerts.

## Activation Key

* You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key
* Browse to the `Activation Key` menu tab and enter your key.

## Configuration

You will need a Twilio account to use this Modular Alert.

You can sign up at twilio.com

Once your Twilio account is setup you will then be able to obtain your Auth Token and Account SID from your profile.

To enter these values in Splunk , just browse to the `Setup` menu tab in the App

## Using

Perform a search in Splunk and then navigate to : Save As -> Alert -> Trigger Actions -> Add Actions -> Twilio SMS Alerts

On this dialogue you can enter your "from number", "to number" and "SMS message"

"to number" can also be a comma delimited list of numbers

For the SMS message field , token substitution can be used just the same as for email alerts.

`http://docs.splunk.com/Documentation/Splunk/latest/Alert/Setupalertactions#Tokens_available_for_email_notifications`

## App Object Permissions

Everyone's Splunk environment and Users/Roles/Permissions setup are different.

By default this App ships with all of it's objects globally shared (in `metadata/default.meta` )

So if you need to limit access to functionality within the App , such as who can see the setup page , then you should browse to  `Apps -> Manage Apps -> Twilio SMS Alerting -> View Objects` , and adjust the permissions accordingly for your specific Splunk environment.

## Logging

Modular Alert logs will get written to `$SPLUNK_HOME/var/log/splunk/twilioalert_app_modularalert.log`

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/twilioalert_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Alert logging level can be specified on the setup page. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.

Any Splunk internal errors can also be searched like : `index=_internal twilio.py ERROR`

## Troubleshooting

1) Is your "from number" correct and valid for sending SMS messages via Twilio ?
2) Are your alerts actually firing ?
3) Are your Auth token and Account SID correct ?

## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.


