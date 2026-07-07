# Speedtest Addon for Splunk Universal Forwarder

Is a Splunk Addon to schedule and execute speedtest with your Universal Forwarder and log you bandwidth speed and quality.
This addon use a speedtest.net platform to execute several scheduled test from workstations with Universal Forwarder installed, metering your connection speed and quality, and send results to Splunk Enterprise.

The purpose of this addon is metering bandwidth of employe's connection in remote office, log it, and use this information in several analytics analysis.

## What i need to use this addon?
- Splunk Universal Forwarder version 7.0.0 or higher.
- Splunk Enterprise 7 or higher or Splunk Cloud.
- A workstation using Windows x86_64 version.

## Instalation:

You can install this package using Deployment Server strategy on Splunk Environment or copy  speedtest_ta_windows's directory to %SPLUNK_DIR%/etc/apps on your Universal Forwarder.

## Configuration:

Remember that all configuration changes must be made on local directory, always.

```bash
local/inputs.conf

[script://.\bin\speedtest.exe --format=json --accept-license --accept-gdpr]
interval -> 'Use crontab format to configure a scheduled execution of speedtest.'
index -> "This field configure a index to store logs of this addon."
disable -> Select true of false to disable or enable this log extraction

```
Default Configuration:
- This addon will run speedtest every hour at minute zero.
- All logs will be sended to index speedtest.
- We will use a global outputs configurations present on Universal Forwarder.

## Trobleshooting
If you dont receive logs or receive any error messages on logs please verify:
- If Universal Forwarder have a output Forwarding configuration to send logs to Splunk Indexers.(https://docs.splunk.com/Documentation/Forwarder/8.1.1/Forwarder/Configureforwardingwithoutputs.conf)
- If Universal Forwarder Service are running.
- If Universal Forwarder Service are running with a user with permitions to read addon's folder.
- If Splunk Indexers have receiving configuration in ports that Universal Forwarder are sending data.
- If Splunk Indexers have a speedtest's index or other configured.