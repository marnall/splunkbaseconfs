Copyright (C) 2020 Muegge Technology Services, LLC All Rights Reserved.

Add-on:			FRED Add-On for Splunk
Current Version:	0.1.2
Last Modified:		2021-01-02
Splunk Version:		7.x, and 8.x
Author:			David Muegge - Muegge Technology Services, LLC

The FRED® Add-On for Splunk provides a way to easily retrieve FRED (Federal Reserve Economic Database) data and send into Splunk.

##### What's New #####

0.1.2 (2021-01-02)
Resolved the following issues:
- Added additional error handling for data removed from FRED API
- Removed series ID's GOLDAMGBD228NLBM & SLVPRUSD from default list
    they are no longer available via the FRED API
- Updated sourcetype configuration
- Added fred custom command to query API in realtime
- Updated sourcetype names for future interoperability

0.1.1 (2020-09-05)
Resolved the following issues:
- Corrected issues for AppInspect

0.1.0 (2020-08-15)
- Initial Release.


##### Technology Add-on Details ######

Sourcetype(s):				fred:series, fred:series:list
Supported Technologies:		Federal Reserve Economic Data API
Compatible Solutions:		Economic Analysis App for Splunk