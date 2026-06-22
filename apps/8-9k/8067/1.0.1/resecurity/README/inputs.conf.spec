[taxii2_ioc://<name>]
*This modular input retrieves IOCs from a TAXII 2.x server and indexes them in Splunk.
description = TAXII 2.x IOC feed reader

collection = <string>
* TAXII collection ID or name

initial_lookback = <string>
* Initial lookback window if no checkpoint present, e.g. 24h, 7d, 1d
* If empty, defaults to 24h

limit = <int>
* Page size per request, default: 200