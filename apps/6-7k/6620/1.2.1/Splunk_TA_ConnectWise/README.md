## About

The Add-on for ConnectWise Manage uses modular inputs to query Manage objects as a stateful event stream. You can get the latest state from any object by searching on that object's sourcetype and passing | stats latest(*) by id. This can then be written to a KVstore or CSV to enrich other data sources, or you can analyze changes in state over time.

Manage, out of the box, has some limitations on how utilization is reported and BrightGauge does not let you easily join complex data sources. This was designed to bring the power of Splunk to ConnectWise Manage.

## Version History
* 1.0.2: Initial version
* 1.1.0: Consolidated lookups and caching searches from visualization app.
* 1.2.0: Implemented Slack posting of new tickets from ConnectWise. Requires installing [ConnectWise Manage for Slack](https://api.slack.com/apps/A046L33LTC0).
