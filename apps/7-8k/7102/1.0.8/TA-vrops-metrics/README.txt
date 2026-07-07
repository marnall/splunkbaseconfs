VROPS Metrics Scraper

Scrapes Metrics from VROPS using the vCenter Adapter

Suggested indexes.conf:
```
[vrops_metrics]
datatype = metric
metric.timestampResolution = <s | ms>
homePath = $SPLUNK_DB/vrops_metrics/db
coldPath = $SPLUNK_DB/vrops_metrics/colddb
thawedPath = $SPLUNK_DB/vrops_metrics/thaweddb
```
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-vrops-metrics/bin/ta_vrops_metrics/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-vrops-metrics/bin/ta_vrops_metrics/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
