## Historical Data Access

You can access historical data using to and from. By setting the to and from parameters to dates in
the past, you automatically query historical data to return results. However, you cannot have a
timeframe that spans from the past to the future and there is a 24-hour synchronization window for
on-call data before it is available. This is to ensure that if you request on-call data for the
current day, the request doesn’t try to simultaneously draw data from both historical data and the
runtime data. For historical data queries, the length of time you can set is limited by your pricing
plan. Please refer [Accessing Data](https://help.xmatters.com/xmapi/#accessing-data) for more
details.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the xMatters server. Below are the default
ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |
