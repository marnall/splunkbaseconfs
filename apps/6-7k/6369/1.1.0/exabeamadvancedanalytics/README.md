[comment]: # "Auto-generated SOAR connector documentation"
# Exabeam Advanced Analytics

Publisher: Splunk Community  
Connector Version: 1\.1\.0  
Product Vendor: Exabeam  
Product Name: Advanced Analytics  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.1\.0  

This app supports getting user and asset data as well as managing watchlists

[comment]: # "File: README.md"
[comment]: # "Copyright (c) 2022 Splunk Inc."
[comment]: # ""
[comment]: # "Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "you may not use this file except in compliance with the License."
[comment]: # "You may obtain a copy of the License at"
[comment]: # ""
[comment]: # "    http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # ""
[comment]: # "Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "either express or implied. See the License for the specific language governing permissions"
[comment]: # "and limitations under the License."
[comment]: # ""
## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Exabeam server. Below are the default
ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http         | tcp                | 80   |
|         https        | tcp                | 443  |


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Advanced Analytics asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base\_url** |  required  | string | URL
**verify\_server\_cert** |  optional  | boolean | Verify server certificate
**username** |  required  | string | Username
**password** |  required  | password | Password

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[search assets](#action-search-assets) - Search for assets that contain the keyword specified  
[get asset](#action-get-asset) - Retrieve all asset info for the a given hostname or IP address  
[get user](#action-get-user) - Retrieve all user info for the given username  
[search users](#action-search-users) - Search for users that contain the keyword specified  
[get watchlist](#action-get-watchlist) - Get members of a watchlist  
[list watchlists](#action-list-watchlists) - Retrieve all watchlists and watchlist ids  
[unwatch user](#action-unwatch-user) - Remove user from specified watchlist  
[watch user](#action-watch-user) - Add user to specified watchlist  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'search assets'
Search for assets that contain the keyword specified

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**keyword** |  required  | Keyword to search | string | 
**limit** |  optional  | Maximum number of results | numeric | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.keyword | string | 
action\_result\.parameter\.limit | numeric | 
action\_result\.data\.\*\.assets\.\*\.assetGroup | string | 
action\_result\.data\.\*\.assets\.\*\.assetType | string | 
action\_result\.data\.\*\.assets\.\*\.hostName | string |  `host name` 
action\_result\.data\.\*\.assets\.\*\.ipAddress | string |  `ip` 
action\_result\.data\.\*\.assets\.\*\.riskSession | string | 
action\_result\.data\.\*\.assets\.\*\.riskState | string | 
action\_result\.summary | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'get asset'
Retrieve all asset info for the a given hostname or IP address

Type: **investigate**  
Read only: **False**

One of <b>hostname</b> or <b>IP address</b> are required\. If both are specified, only <b>hostname</b> is used\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hostname** |  optional  | Hostname to fetch | string |  `host name` 
**ip** |  optional  | IP to fetch | string |  `ip` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.hostname | string |  `host name` 
action\_result\.parameter\.ip | string |  `ip` 
action\_result\.data\.\*\.assets\.\*\.assetGroup | string | 
action\_result\.data\.\*\.assets\.\*\.assetType | string | 
action\_result\.data\.\*\.assets\.\*\.hostName | string |  `host name` 
action\_result\.data\.\*\.assets\.\*\.ipAddress | string |  `ip` 
action\_result\.data\.\*\.assets\.\*\.riskSession | string | 
action\_result\.data\.\*\.assets\.\*\.riskState | string | 
action\_result\.data\.\*\.commentCount | string | 
action\_result\.data\.\*\.labels\.\*\.label | string | 
action\_result\.data\.\*\.location | string | 
action\_result\.data\.\*\.topGroups\.confidenceFactor | numeric | 
action\_result\.data\.\*\.topGroups\.groupingFeatureValue | string | 
action\_result\.data\.\*\.topGroups\.hist\.binList | string | 
action\_result\.data\.\*\.topGroups\.hist\.maxX | string | 
action\_result\.data\.\*\.topGroups\.hist\.maxY | numeric | 
action\_result\.data\.\*\.topGroups\.hist\.minX | string | 
action\_result\.data\.\*\.topGroups\.hist\.minY | numeric | 
action\_result\.data\.\*\.topGroups\.hist\.topTalkers\.\*\.topTalker | string | 
action\_result\.data\.\*\.topGroups\.histClassName | string | 
action\_result\.data\.\*\.topGroups\.histSpan | string | 
action\_result\.data\.\*\.topGroups\.histogramDate | string | 
action\_result\.data\.\*\.topGroups\.key | string | 
action\_result\.data\.\*\.topGroups\.lastUpdate | numeric | 
action\_result\.data\.\*\.topGroups\.modelName | string | 
action\_result\.data\.\*\.topGroups\.riskRegions\.maxX | numeric | 
action\_result\.data\.\*\.topGroups\.riskRegions\.minX | numeric | 
action\_result\.data\.\*\.topGroups\.riskRegions\.riskRegions | string | 
action\_result\.data\.\*\.topGroups\.smoothedHist\.binList | string | 
action\_result\.data\.\*\.topGroups\.smoothedHist\.maxX | string | 
action\_result\.data\.\*\.topGroups\.smoothedHist\.maxY | numeric | 
action\_result\.data\.\*\.topGroups\.smoothedHist\.minX | string | 
action\_result\.data\.\*\.topGroups\.smoothedHist\.minY | numeric | 
action\_result\.data\.\*\.topGroups\.smoothedHist\.topTalkers\.\*\.topTalker | string | 
action\_result\.data\.\*\.topGroups\.totalBinCount | numeric | 
action\_result\.data\.\*\.topGroups\.totalCount | numeric | 
action\_result\.data\.\*\.topUsers\.confidenceFactor | numeric | 
action\_result\.data\.\*\.topUsers\.groupingFeatureValue | string | 
action\_result\.data\.\*\.topUsers\.hist\.binList | string | 
action\_result\.data\.\*\.topUsers\.hist\.maxX | string | 
action\_result\.data\.\*\.topUsers\.hist\.maxY | numeric | 
action\_result\.data\.\*\.topUsers\.hist\.minX | string | 
action\_result\.data\.\*\.topUsers\.hist\.minY | numeric | 
action\_result\.data\.\*\.topUsers\.hist\.topTalkers\.\*\.topTalker | string | 
action\_result\.data\.\*\.topUsers\.histClassName | string | 
action\_result\.data\.\*\.topUsers\.histSpan | string | 
action\_result\.data\.\*\.topUsers\.histogramDate | string | 
action\_result\.data\.\*\.topUsers\.key | string | 
action\_result\.data\.\*\.topUsers\.lastUpdate | numeric | 
action\_result\.data\.\*\.topUsers\.modelName | string | 
action\_result\.data\.\*\.topUsers\.riskRegions\.maxX | numeric | 
action\_result\.data\.\*\.topUsers\.riskRegions\.minX | numeric | 
action\_result\.data\.\*\.topUsers\.riskRegions\.riskRegions | string | 
action\_result\.data\.\*\.topUsers\.smoothedHist\.binList | string | 
action\_result\.data\.\*\.topUsers\.smoothedHist\.maxX | string | 
action\_result\.data\.\*\.topUsers\.smoothedHist\.maxY | numeric | 
action\_result\.data\.\*\.topUsers\.smoothedHist\.minX | string | 
action\_result\.data\.\*\.topUsers\.smoothedHist\.minY | numeric | 
action\_result\.data\.\*\.topUsers\.smoothedHist\.topTalkers\.\*\.topTalker | string | 
action\_result\.data\.\*\.topUsers\.totalBinCount | numeric | 
action\_result\.data\.\*\.topUsers\.totalCount | numeric | 
action\_result\.data\.\*\.zone | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'get user'
Retrieve all user info for the given username

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** |  required  | Username to fetch | string |  `user name` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.username | string |  `user name` 
action\_result\.data\.\*\.accountNames\.\*\.accountName | string | 
action\_result\.data\.\*\.commentCount | numeric | 
action\_result\.data\.\*\.executive | boolean | 
action\_result\.data\.\*\.managerInfo\.averageRiskScore | numeric | 
action\_result\.data\.\*\.managerInfo\.firstSeen | numeric | 
action\_result\.data\.\*\.managerInfo\.labels\.\*\.label | string | 
action\_result\.data\.\*\.managerInfo\.lastActivityTime | numeric | 
action\_result\.data\.\*\.managerInfo\.lastActivityType | string | 
action\_result\.data\.\*\.managerInfo\.lastSeen | numeric | 
action\_result\.data\.\*\.managerInfo\.lastSessionId | string | 
action\_result\.data\.\*\.managerInfo\.pastScores | string | 
action\_result\.data\.\*\.managerInfo\.pendingRiskTransfers\.\*\.ruleId\.name | string | 
action\_result\.data\.\*\.managerInfo\.pendingRiskTransfers\.\*\.score | numeric | 
action\_result\.data\.\*\.managerInfo\.pendingRiskTransfers\.\*\.sourceEventId | string | 
action\_result\.data\.\*\.managerInfo\.pendingRiskTransfers\.\*\.sourceSequenceId | string | 
action\_result\.data\.\*\.managerInfo\.pendingRiskTransfers\.\*\.sourceSequenceName | string | 
action\_result\.data\.\*\.managerInfo\.pendingRiskTransfers\.\*\.time | numeric | 
action\_result\.data\.\*\.managerInfo\.riskScore | numeric | 
action\_result\.data\.\*\.managerInfo\.username | string | 
action\_result\.data\.\*\.onWatchlist | boolean | 
action\_result\.data\.\*\.peerGroupFieldName | string | 
action\_result\.data\.\*\.peerGroupFieldValue | string | 
action\_result\.data\.\*\.userInfo\.averageRiskScore | numeric | 
action\_result\.data\.\*\.userInfo\.firstSeen | numeric | 
action\_result\.data\.\*\.userInfo\.labels\.\*\.label | string | 
action\_result\.data\.\*\.userInfo\.lastActivityTime | numeric | 
action\_result\.data\.\*\.userInfo\.lastActivityType | string | 
action\_result\.data\.\*\.userInfo\.lastSeen | numeric | 
action\_result\.data\.\*\.userInfo\.lastSessionId | string | 
action\_result\.data\.\*\.userInfo\.pastScores | string | 
action\_result\.data\.\*\.userInfo\.pendingRiskTransfers\.\*\.ruleId\.name | string | 
action\_result\.data\.\*\.userInfo\.pendingRiskTransfers\.\*\.score | numeric | 
action\_result\.data\.\*\.userInfo\.pendingRiskTransfers\.\*\.sourceEventId | string | 
action\_result\.data\.\*\.userInfo\.pendingRiskTransfers\.\*\.sourceSequenceId | string | 
action\_result\.data\.\*\.userInfo\.pendingRiskTransfers\.\*\.sourceSequenceName | string | 
action\_result\.data\.\*\.userInfo\.pendingRiskTransfers\.\*\.time | numeric | 
action\_result\.data\.\*\.userInfo\.riskScore | numeric | 
action\_result\.data\.\*\.userInfo\.username | string | 
action\_result\.data\.\*\.username | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'search users'
Search for users that contain the keyword specified

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**keyword** |  required  | Keyword to search | string | 
**limit** |  optional  | Maximum number of results | numeric | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.keyword | string | 
action\_result\.parameter\.limit | numeric | 
action\_result\.data\.\*\.users\.\*\.averageRiskScore | numeric | 
action\_result\.data\.\*\.users\.\*\.firstSeen | numeric | 
action\_result\.data\.\*\.users\.\*\.labels\.\*\.label | string | 
action\_result\.data\.\*\.users\.\*\.lastActivityTime | numeric | 
action\_result\.data\.\*\.users\.\*\.lastActivityType | string | 
action\_result\.data\.\*\.users\.\*\.lastSeen | numeric | 
action\_result\.data\.\*\.users\.\*\.lastSessionId | string | 
action\_result\.data\.\*\.users\.\*\.pastScores | string | 
action\_result\.data\.\*\.users\.\*\.pendingRiskTransfers\.\*\.ruleId\.name | string | 
action\_result\.data\.\*\.users\.\*\.pendingRiskTransfers\.\*\.score | numeric | 
action\_result\.data\.\*\.users\.\*\.pendingRiskTransfers\.\*\.sourceEventId | string | 
action\_result\.data\.\*\.users\.\*\.pendingRiskTransfers\.\*\.sourceSequenceId | string | 
action\_result\.data\.\*\.users\.\*\.pendingRiskTransfers\.\*\.sourceSequenceName | string | 
action\_result\.data\.\*\.users\.\*\.pendingRiskTransfers\.\*\.time | numeric | 
action\_result\.data\.\*\.users\.\*\.riskScore | numeric | 
action\_result\.data\.\*\.users\.\*\.username | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'get watchlist'
Get members of a watchlist

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**watchlist\_id** |  required  | Watchlist to retrieve | string |  `exabeam watchlist id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.watchlist\_id | string |  `exabeam watchlist id` 
action\_result\.data\.\*\.category | string | 
action\_result\.data\.\*\.criteria\.\*\.value | string | 
action\_result\.data\.\*\.description | string | 
action\_result\.data\.\*\.numberOfNotableUsers | numeric | 
action\_result\.data\.\*\.outOfBox | boolean | 
action\_result\.data\.\*\.title | string | 
action\_result\.data\.\*\.totalNumberOfUsers | numeric | 
action\_result\.data\.\*\.users\.\*\.user\.averageRiskScore | numeric | 
action\_result\.data\.\*\.users\.\*\.user\.executive | boolean | 
action\_result\.data\.\*\.users\.\*\.user\.firstSeen | numeric | 
action\_result\.data\.\*\.users\.\*\.user\.initials | string | 
action\_result\.data\.\*\.users\.\*\.user\.labels\.\*\.label | string | 
action\_result\.data\.\*\.users\.\*\.user\.lastActivityTime | numeric | 
action\_result\.data\.\*\.users\.\*\.user\.lastActivityType | string | 
action\_result\.data\.\*\.users\.\*\.user\.lastSeen | numeric | 
action\_result\.data\.\*\.users\.\*\.user\.lastSessionId | string | 
action\_result\.data\.\*\.users\.\*\.user\.latestSessionComment\.commentId | string | 
action\_result\.data\.\*\.users\.\*\.user\.latestSessionComment\.commentObjectId | string | 
action\_result\.data\.\*\.users\.\*\.user\.latestSessionComment\.commentType | string | 
action\_result\.data\.\*\.users\.\*\.user\.latestSessionComment\.createTime | numeric | 
action\_result\.data\.\*\.users\.\*\.user\.latestSessionComment\.edited | boolean | 
action\_result\.data\.\*\.users\.\*\.user\.latestSessionComment\.exaUser | string | 
action\_result\.data\.\*\.users\.\*\.user\.latestSessionComment\.text | string | 
action\_result\.data\.\*\.users\.\*\.user\.latestSessionComment\.updateTime | numeric | 
action\_result\.data\.\*\.users\.\*\.user\.latestUserComment\.commentId | string | 
action\_result\.data\.\*\.users\.\*\.user\.latestUserComment\.commentObjectId | string | 
action\_result\.data\.\*\.users\.\*\.user\.latestUserComment\.commentType | string | 
action\_result\.data\.\*\.users\.\*\.user\.latestUserComment\.createTime | numeric | 
action\_result\.data\.\*\.users\.\*\.user\.latestUserComment\.edited | boolean | 
action\_result\.data\.\*\.users\.\*\.user\.latestUserComment\.exaUser | string | 
action\_result\.data\.\*\.users\.\*\.user\.latestUserComment\.text | string | 
action\_result\.data\.\*\.users\.\*\.user\.latestUserComment\.updateTime | numeric | 
action\_result\.data\.\*\.users\.\*\.user\.pastScores | string | 
action\_result\.data\.\*\.users\.\*\.user\.pendingRiskTransfers\.\*\.ruleId\.name | string | 
action\_result\.data\.\*\.users\.\*\.user\.pendingRiskTransfers\.\*\.score | numeric | 
action\_result\.data\.\*\.users\.\*\.user\.pendingRiskTransfers\.\*\.sourceEventId | string | 
action\_result\.data\.\*\.users\.\*\.user\.pendingRiskTransfers\.\*\.sourceSequenceId | string | 
action\_result\.data\.\*\.users\.\*\.user\.pendingRiskTransfers\.\*\.sourceSequenceName | string | 
action\_result\.data\.\*\.users\.\*\.user\.pendingRiskTransfers\.\*\.time | numeric | 
action\_result\.data\.\*\.users\.\*\.user\.riskScore | numeric | 
action\_result\.data\.\*\.users\.\*\.user\.username | string | 
action\_result\.data\.\*\.users\.\*\.username | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'list watchlists'
Retrieve all watchlists and watchlist ids

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.data\.\*\.watchlists\.\*\.title | string | 
action\_result\.data\.\*\.watchlists\.\*\.watchlistId | string |  `exabeam watchlist id` 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'unwatch user'
Remove user from specified watchlist

Type: **contain**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** |  required  | User to remove | string |  `user name` 
**watchlist\_id** |  required  | Watchlist to change | string |  `exabeam watchlist id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.username | string |  `user name` 
action\_result\.parameter\.watchlist\_id | string |  `exabeam watchlist id` 
action\_result\.data\.\*\.success | boolean | 
action\_result\.data\.\*\.username | string |  `user name` 
action\_result\.data\.\*\.watchlistId | string |  `exabeam watchlist id` 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'watch user'
Add user to specified watchlist

Type: **correct**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** |  required  | User to add | string |  `user name` 
**watchlist\_id** |  required  | Watchlist to change | string |  `exabeam watchlist id` 
**duration** |  optional  | Number of days to watch | numeric | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.duration | numeric | 
action\_result\.parameter\.username | string |  `user name` 
action\_result\.parameter\.watchlist\_id | string |  `exabeam watchlist id` 
action\_result\.data\.\*\.success | boolean | 
action\_result\.data\.\*\.username | string |  `user name` 
action\_result\.data\.\*\.watchlistId | string |  `exabeam watchlist id` 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 