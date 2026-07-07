# Samhain Addon for Splunk Enterprise
[![Splunk App](https://img.shields.io/badge/version-1.2.0-blue.svg)](https://splunkbase.splunk.com/app/3191) [![Splunk CIM](https://img.shields.io/badge/splunk%20cim-4.6.0-brightgreen.svg)](http://docs.splunk.com/Documentation/CIM/4.6.0/User/Overview)

The Samhain Addon for Splunk Enterprise adds the Splunk knowledge objects required to parse events produced by the [Samhain](http://www.la-samhna.de/samhain/) host-based intrusion detection system and is compatible with the [Splunk Common Information Model](http://docs.splunk.com/Documentation/CIM/latest/User/ChangeAnalysis).

## Source types for the Samhain Addon for Splunk Enterprise
The Samhain Addon for Splunk Enterprise expects the source type ```samhain``` for all incoming events.
The following event types map the samhain events to the Splunk Common Information Model.

| Source type   | Event type    | Description   | CIM data models |
| ------------- | ------------- | ------------- | ------------- |
| samhain  | samhain_filesystem_change  | Samhain events with the ```change_type``` field set to "filesystem" | [Change Analysis](http://docs.splunk.com/Documentation/CIM/latest/User/ChangeAnalysis) |
| samhain  | samhain_process_information | Samhain events relating to the running of the Samhain process | N/A |

## Installing Samhain
It's advisable to read through the full instructions [here](http://www.la-samhna.de/samhain/s_download.html), however, if you're only interested in getting Samhain installed with its default options then simply use the commands below:
```bash
curl -OL http://www.la-samhna.de/samhain/samhain-current.tar.gz
tar -xzvf samhain-current.tar.gz
tar -xzvf samhain-{{version}}.tar.gz
cd samhain-{{version}}
yum install -y gcc audit-libs-devel libattr-devel libacl-devel
./configure
make
make install
make install-boot
samhain -t init
service samhain start
```
