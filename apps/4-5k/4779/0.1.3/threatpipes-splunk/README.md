# ThreatPipes App for Splunk

## Why you should download this app

<iframe width="560" height="315" src="https://www.youtube.com/embed/HIgBi644X-c" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

Discover where your (or someone else's) network can be compromised.

> The ultimate offensive and defensive security tool for Splunk.

[Download the ThreatPipes App for Splunk on Splunkbase FREE here](https://splunkbase.splunk.com/app/4779/).

## About ThreatPipes

ThreatPipes is a reconnaissance tool that automatically queries 100’s of data sources to gather intelligence on IP addresses, domain names, e-mail addresses, names and more.

You simply specify the target you want to investigate, pick which modules to enable and then ThreatPipes will collect data to build up an understanding of all the entities and how they relate to each other.

DNS, Whois, Web pages, passive DNS, spam blacklists, file meta data, threat intelligence lists as well as services like SHODAN, HaveIBeenPwned? and many others are used to discover intelligence on a target.

By following chains of intelligence, ThreatPipes also uncovers other affiliated targets that have a relationship to your original target. For example, a domain entered in a scan might resolve to SSL certificates, to known malicious domains, to IP addresses, and so on.

The data returned from a ThreatPipes scan will reveal a lot of information about your target, providing insight into possible data leaks, vulnerabilities or other sensitive information that can be leveraged during a penetration test, red team exercise, blue team activities, or for threat intelligence.

Teamed with Splunk, you can explore and examine this intelligence gathered by ThreatPipes in ways never before possible.

Download ThreatPipes FREE here: [https://www.threatpipes.com](https://www.threatpipes.com).

## Quick start guide

### 1. Install Splunk App

[Install this app on a single Splunk instance in the normal way](https://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall). It should work on distributed deployments too (but we have not tested setup yet).
2. 


### 2. Select how you want to import data

You have two options for this:

1. Stream events from ThreatPipes to Splunk (requires ThreatPipes license) [read 2a]
2. Manually import data from ThreatPipes to Splunk [read 2b]

#### 2a. Stream data from ThreatPipes to Splunk (requires ThreatPipes license)

![Setup ThreatPipes syslog destination](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/appserver/static/docs/threatpipes-syslog-destination.png) "Setup ThreatPipes syslog destination")

Setup your ThreatPipes instance to stream to Splunk by specifying your Splunk server under Server Settings in ThreatPipes.

By default the ThreatPipes Splunk app ships with an input listening on `tcp:514` disabled by default using `sourcetype=threatpipes-syslog`. Make sure at least one input is enabled before attempting to stream data.

![Select stream data on scan start](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/appserver/static/docs/threatpipes-start-scan-log-stream.png) "Select stream data on scan start")

When starting a scan (that you want the intel to be streamed to Splunk) make sure you have checked the "Log Stream".

#### 2b. Export scan data from ThreatPipes and import to Splunk

![Export data from ThreatPipes](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/appserver/static/docs/threatpipes-csv-export-1.png) "Export data from ThreatPipes")

Export all or partial results from a scan in `.csv` format.

![Export data from ThreatPipes](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/appserver/static/docs/threatpipes-csv-export-2.png) "Export data from ThreatPipes")

You can also export scan data for multiple scans in `.csv` format using the scan list view.

![Import ThreatPipes data to Splunk](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/appserver/static/docs/threatpipes-upload-csv-splunk.png) "Import ThreatPipes data to Splunk")

Import the data to Splunk using your preferred method. Be sure to select `sourcetype=threatpipes-csv` and `index=threatpipes`

### 3. Start Splunking

#### Intel overview

![ThreatPipes Splunk Mains Dashboard](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/appserver/static/docs/threatpipes-splunk-mains-dashboard.png) "ThreatPipes Splunk Mains Dashboard")

Start on the Mains dashboard. It will show you an overview of all the intelligence imported from ThreatPipes. Click on any panel to drill down to the Scan Dashboard.

#### Intel analysis

![ThreatPipes Splunk Scan Dashboard](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/appserver/static/docs/threatpipes-splunk-scan-dashboard.png) "ThreatPipes Splunk Scan Dashboard")

Take a deeper look at the intelligence generate for potentially risky data that you can use offensively (e.g. network weaknesses) or defensively (e.g threat intelligence).

#### Cross reference intel

![ThreatPipes Splunk Lookup Dashboard](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/appserver/static/docs/threatpipes-splunk-lookup-dashboard.png) "ThreatPipes Splunk Lookup Dashboard")

See if any of the intel uncovered by ThreatPipes is seen in the logs stored in you Splunk instance to identify potential threats.

#### Filter and export

![ThreatPipes Splunk Export Dashboard](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/appserver/static/docs/threatpipes-splunk-export-dashboard.png) "ThreatPipes Splunk Export Dashboard")

Export the intel as threat lists to use with Splunk Enterprise security (and other tools).

## Release Notes

Version 0.1.1

[Changelog](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/CHANGELOG.md).

Initial release.

## Support

[Contact the Threatpipes team here](https://www.threatpipes.com)

## License

[This code is licensed under an MIT license](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/LICENSE.txt).

[Download the source code on Gitlab](https://gitlab.com/threatpipes/threatpipes-splunk).

## Developer guide

### Testing

You can use this test data to populate dashboards for testing, if needed:

* [Scan 0]](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/appserver/static/test-data/ddf49856-f07d-4087-b4fc-6e1428383daa.csv).
* [Scan 1]](https://gitlab.com/threatpipes/threatpipes-splunk/raw/latest/appserver/static/test-data/ddf49856-f07d-4087-b4fc-6e1428383dbf.csv).

### Packaging

Using MacOS, create a `.tar.gz` for Splunkbase:

```
COPYFILE_DISABLE=1 tar -czv --exclude='.*' -f threatpipes-splunk.tar.gz threatpipes-splunk/
```