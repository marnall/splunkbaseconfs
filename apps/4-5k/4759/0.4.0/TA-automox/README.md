# Hurricane Labs Add-on for Automox

This add-on brings in device status information from the Automox API.

## Changes

### Version 0.3.0

* Added input for Automox events endpoint
* Added Field extractions, aliases, calculated fields for CIM compliance (Updates datamodel)
* Updated automox:software endpoint to include server name (for CIM)



## Installation

1. Install add-on on forwarder (or all-in-one search head).
2. Navigate to Hurricane Labs Add-on for Automox and click Configuration->Add-on Settings. Set API key.
3. Navigate to Inputs and create an input for devices - set options as needed. 
4. Navigate to Inputs and create an input for software - set options as needed. 
5. Navigate to Inputs and create an input for events. This should be run no more frequently than once a day.

## Sourcetypes

Device info events are logged to the "automox:devices" sourcetype. Installed software package go into the "automox:software" sourcetype. Automox events are logged to "automox:events". This includes successful/failed patches.
