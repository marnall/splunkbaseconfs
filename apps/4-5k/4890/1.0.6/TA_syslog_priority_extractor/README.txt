Syslog Priority Extractor TA

REQUIREMENTS
The TA uses ingest-time eval and won't work on Splunk versions below 7.2.0

INSTALLATION
- Single instance: obvious
- Distributed deployment: install on Indexers/HEavy Forwarders and on Search Heads

CONFIGURATION
No TA configuration requiered
The data inputs should be configured with no_priority_stripping = true

SUPPORT
No support. The TA is provided AS-IS.


