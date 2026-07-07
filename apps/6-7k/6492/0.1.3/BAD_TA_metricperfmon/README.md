# BAD_TA_metricperfmon
Splunk Multi Metrics Perfmon for Windows - https://splunkbase.splunk.com/app/6492/

This app is middleware for the Splunk Universal Forwarder perfmon collector, that transforms its perfmon data into multi-metrics.

Every instance you collect will consume a maximum of 150 bytes of license, regardless of how many counters you enable. The raw data is reduced to only the values, and decimal values have unnecessary zeros removed, to reduce disk usage as much as possible

## Installation
Deploy this application to your Windows Universal Forwarders either manually or using a deployment server. There is no parsing or search time configuration in this app, so it should not be installed on your Search Heads, Indexers, or any Splunk Cloud instances.

## Configuration
Deploy an inputs.conf to your Universal Forwarders exactly as you would with perfmon, however use the **metricperfmon** stanza.
```
[metricperfmon://CPU]
disabled = 0
index = metrics
instances = _Total

[metricperfmon://Memory]
disabled = 0
index = metrics
formatString = %.6f

[metricperfmon://Network]
disabled = 0
index = metrics
counters = Bytes Total/sec; Bytes Received/sec; Bytes Sent/sec
```

For more reference, see inputs.conf.spec or https://docs.splunk.com/Documentation/Splunk/latest/Data/MonitorWindowsperformance

## Usage
The data has a sourcetype of **metricperfrmon** and a source of **metricperfmon:[type]**. The easiest way to understand this data is to send it to an event index first, or use `mpreview`.

```| mpreview index=metrics | search sourcetype=MetricPerfmon```

## Compile Sourcecode
This app ships with a Python 3.10.2 compiled version of `metricperfmon.py`. If you would like to compile your own version, you can easily do so with `pyinstaller`. This script is also included in the app named `recompile.cmd` for convience.

```
pip install pyinstaller
pyinstaller --onefile --distpath .\etc\apps\BAD_TA_metricperfmon\bin --workpath %temp% .\etc\apps\BAD_TA_metricperfmon\bin\src\metricperfmon.py
```
