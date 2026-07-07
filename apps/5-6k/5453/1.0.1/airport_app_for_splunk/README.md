# Airports App for Splunk

Welcome to the App.

This App should be used in conjuction with the [Airport CIM for Splunk](https://splunk.github.io/airport_cim_for_splunk/)

Please first ensure your data-source conform to this CIM.

Pre-requisites:
- [Sankey Vizualisation](https://splunkbase.splunk.com/app/3112/)
- A functional KV Store
- Your data conforms to the [Airport CIM for Splunk](https://splunk.github.io/airport_cim_for_splunk/)

## Instructions

1) Download the App and install it on your Search Head

2) Download and install the [Sankey Vizualisation](https://splunkbase.splunk.com/app/3112/)

2) Configure the following macros to point to your data:
- flightsBase
- baggageBase
- securityBase
- bagsBase
_Note: You can also include your sourcetype in these base macros if you wish_

3) Run the "Populate airports KV Store from CSV" which is located in the Reports tab.
