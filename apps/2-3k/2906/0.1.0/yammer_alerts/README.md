# Splunk Yammer Modular Alert

## Overview

This is a Splunk Modular Alert for posting alerts to a Yammer group.  Splunk posts to Yammer as a user.  There is no _bot_ support so you will need to setup a dedicated user for alerts.

## Dependencies

* Splunk 6.3+
* Supported on Windows, Linux, MacOS, Solaris, FreeBSD, HP-UX, AIX

## Setup

* Untar the release to your `$SPLUNK_HOME/etc/apps` directory
* Restart Splunk

## Configuration

You will need to register a [client application](https://www.yammer.com/client_applications) with Yammer.  

Then sign authorise the user.  To do this, I went to the [Yammer Developer Portal](https://developer.yammer.com/docs/messagesjson) and clicked "Try It" on the GET messages API call.  This forces you to log into Yammer via OAuth2.  You can then take the token and paste it into the setup screen.  This is horrible and there is [GitHub issue #1](https://github.com/oxo42/SplunkYammerAlert/issues/1) open.

To enter these values in Splunk, just browse to Settings -> Alert Actions -> Yammer Alerts -> Setup Yammer Alerting

## Using

Perform a search in Splunk and then navigate to : Save As -> Alert -> Trigger Actions -> Add Actions -> Yammer Alerts

On this dialogue you can enter the `group_id` to post to and `body` to send.

For the body field, token substitution can be used just the same as for [email alerts](http://docs.splunk.com/Documentation/Splunk/latest/Alert/Setupalertactions#Tokens_available_for_email_notifications)

## Logging

Browse to: Settings -> Alert Actions -> Yammer Alerts -> View Log Events

Or you can search directly in Splunk

    index=_internal sourcetype=splunkd component=sendmodalert action="twilio"

## Troubleshooting

1. Is your `group_id` correct?
2. Are your alerts actually firing?
3. Is your auth token correct?

## Contact

This project was initiated by John Oxley, john.oxley@gmail.com
