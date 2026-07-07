## How it works

Accellion forwards event data to Splunk or syslog server.
Splunk receives the data.
Splunk indexes and parses the data to be used.
Splunk CISO Dashboard renders the dashboard UI and populate the data by executing queries.

## Structures

Application is divided into 2:

AccellionCiso
AccellionCiso is the main application. It contains the UI, saved searches, data models, etc.

AccellionCisoAddon
AccellionCisoAddon is the indexer. It indexes and parses any data received to extract needed fields.