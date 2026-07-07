## 2.1.1
* Updated Splunk Python SDK
## 2.1.0
* Added option to put HEC URL and HEC Token in the UI, to be used when using SplunkCloud 
## 1.3.0 - 01/29/2021
* Custom sourcetype option for non transforming searches
* Remote HEC option for pushing environment search results to a remote HEC endpoint
* Bug fixes and python3 compatibility updates
## 1.2.0 - 01//2020
* If no index is provided on environment search creation, but index already exists, the environment search will be linked to the existing matching index. This corrects a bug that would show up when environment search creation would initially fail. Thank you @Nicholas Stone for finding this bug!
* Remove authorize.conf warn by setting value to enabled. Thank you @Chris Barrett for finding this bug!
* Bugfix for searches with long name. Thank you @Alan Ivarson for finding this bug
* Configurable global job timeout added to mothership.conf
* Configurable global job status check interval added to mothership.conf
* Search job timeout error messaging supported in the management console 
## 1.1.0 - 09/04/2019
* Allow for the deletion of environment searches and environments with non-existent references (saved search, HEC token. password, etc...).
* Update savedsearches.conf.spec to include args.interval to remove warnings on startup.
* Multi-user timezone configurations reflect correct last run time, use epoch time within metrics logger.
* UI Environment search raw search string moved from Saved Search to Search section.
## 1.0.0 - 08/16/2019
* Initial public release.
