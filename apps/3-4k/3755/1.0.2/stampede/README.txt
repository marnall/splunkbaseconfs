# Stampede Threat Hunting

Stampede Threat Hunting is our first stab at a scoping app for more effective detection of unknown threats. 
The app collects reports of particularly suspicious transactions and files from Windows hosts, based on public and private sources of knowledge about the hackers TTPs. 

Simply export the results into your tool of choice or continue your threat hunt with Splunk.

It is geared towards Windows-based environments for now, just because it was easier to get the necessary sources. We are listening to your complaints, suggestions and bug reports and will constantly improve this and other future products.

Inquiries at admin@rommaan.com. 

## Getting Started

First download Stampede Threat Hunting from the Splunkbase or install it from within your Splunk instance. Read this to the end and ask questions at admin@rommaan.com before you start. The app is pretty straight forward, it uses simple filters and transforms to produce the limited and highly scoped "hunting grounds". 

### Prerequisites

- Windows Security Event Log. 
You have to be collecting Windows Security Event Logs. Sometimes Event 5145 is not enabled in the OS and if you don't see any of those you might wanna check if it is enabled in Windows.

- Sysinternals installed on endpoints with the following functions in particular:

 --autoruns (write task to export into .csv daily and ingest into Splunk, index=winautoruns)
 --sysmon (monitor in Splunk as a local log source with sourcetype="wineventlog:microsoft-windows-sysmon/operational" | fillnull  ---needed to properly populate datasets.
 --PSTools:
   ---psservice (write task to export into .csv at daily and ingest into Splunk, index=windows_services)
   ---listdlls (write task to export into .csv daily and ingest into Splunk, index=windows_services)

- Run with cmd "driverquery /s /fo csv /v and export results in drivers.csv; ingest in Splunk daily
- Run with cmd "driverquery /s /fo csv /si and export results in driverssignatures.csv; ingest in Splunk daily

## Built With

* Splunk 7.x.x

## Complaints and bugs

Email us at admin@rommaan.com

## Versioning

We will use x.x.x versioning style. Upgrade X.x.x, update x.X.x, bug fixes etc. x.x.X

## Authors

* **Rommaan LLC**

## License

This project is licensed under the Splunk licensing terms and conditions.

