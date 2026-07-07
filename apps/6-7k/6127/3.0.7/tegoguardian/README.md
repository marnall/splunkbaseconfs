Tegoguardian for Splunk
======================================================================

OVERVIEW
------------------------------
This Splunk application helps in visualizing and monitoring your data with the Tego Threat Engine. This application is standalone and does not depend on any other technology add-ons.

* Version - 3.0.7

* Compatible with Splunk Enterprise version: 8.0.x, 8.1.x, 8.2.x, 9.0.x and Splunk Cloud.

INSTALLATION Part 1 - Configure App Threat Feed(S1 Architecture)
------------------------------
1. This app can be installed either through UI from "Manage Apps" or by extracting the compressed file into $SPLUNK_HOME$/etc/apps folder.
2. Restart Splunk.
3. Open the TegoGuardian app, a setup page will appear. Select the indexes you wish to safegard an press submit. 
4. Create a tegoguardian index at Settings > Indexes > New Index
5. Create a HEC to receive data feed from Tego: Settings-->Data Inputs-->HTTP Event Collector
6. Click New Token 
7. On Select Source screen, enter Name: tego_hec, Source name override: tegoguardian and then click Next. 
8. On Input Settings screen under Source Type, click Select and then select tegoguardian.
9. On Input Settings screen under Index, select tegoguardian under Selected Allowed Indexes AND as Default Index.
10. Click Review and then Submit.
11. Note the token value to provide to TegoCyber along with url to HEC receiver... usually https://\<yourhost\>:8088
12. For each Index that will be searched, set-up a field alias for either domain, url, or hash at Settings > Fields > Field Alias. For example, dst ASNEW domain. 
13. For each Index, set-up a field alias called Asset at Settings > Fields > Field Alias. For example, Hostname ASNEW Asset. 
14. Enable permissions for Everyone to Read the the Field Alias for TegoGuardian. Recommended "This App Only" selection.
15. Under Searches and Reports Enable the 4 *list_update searches
16. Provide hec token info to tego. 
17. Watch Tegoguardian Threat List Status dashboard under Admin Tools for relatively complete database (Should see several million events come in and with in few hours see completeness at 100% with over 1 million threats per type).


INSTALLATION Part 2 - Enable Threat Hits Scanning Searches
------------------------------
Version 3.0.x scans raw data and sends hits to tegoguardian index for improved performance. To enable Threat Hits Scanning Searches.

Start by examining the Tegoguardian Threat List Status dashboard under Admin Tools for relatively complete database (Should see several million events come in and within few hours you should see completeness at 100% with over 1 million threats per type). If this is true proceed.

Start Scanning for New Hits
Under Searches and Reports - Enable Tego Hits Summary - This will scan newly arriving data for hits. 

Set Initial Backfill - Run one of the searches below based on how far back you want to backfill your data...
	Tego Summary Backfill - 30 Day Reset
	Tego Summary Backfill - 90 Day Reset
	Tego Summary Backfill - 180 Day Reset
	
Enable the following backfill searches...
	Tego Hits Summary - Backfill Steps: Stepwise backfill for threat hits summary. It will backfill to earliest time set by one of the Tego Summary Backfill Reset searches you ran above. 
	Tego Hits Summary - Backfill Reset Based on New Threats: This will watch threats arriving in threat database during a backfill run. When a backfill reaches in a status of complete, it will set the backfill to search back to the first seen date of threats arrived since last backfill started. This means if a new threat arrives in the threat data was first seen in the wild 2 weeks ago, the backfill will automatically be set to scan back to when a threat was first spotted in the wild, not just moving forward. 

Troubleshooting/Followup
Tego Hits Summary
Review Admin Tools-->Tego Summarized Threat Hits Status and check run_time_mins in Tego Hits Summary | Search Info. If it is less than 1 minute it can be left alone. If longer you may want to consider shortening the time range of Tego Hits Summary search.

Tego Hits Summary - Backfill Steps
Review Admin Tools-->Tego Summarized Threat Hits Status and check run_time_mins_in_progress in Tego Hits Summary - Backfill Steps | Search Info | Search Info. If it is longer than 2 mins, you may want to consider lowering the value in `tego_backfill_span_hours` to reduce the number of hours per backfill fill search run. 

INSTALLATION (Distributed Architectures)
------------------------------
Distributed architectures will require the data inputs be deployed to the Forwarding tier and the indexes.conf be configured at the indexer tier.
1. tegoguardian index needs to be provisioned at the indexer tier (indexes.conf)
2. App should be installed on a SHC via deployer. 
3. App will be split into components however if you have any questions on distributed architectures, please reach out.

SETUP PAGE GUIDE
------------------------------

#### Section 1: Select indexes
* Select the indexes you would like to compare with the Tego threat data.

UPGRADE GUIDE - Post Upgrade Steps if you are upgrading from 1.x.x to 2.x.x
------------------------------
1. Confirm the existence of tegoguardian index under Setting-->Indexes. If it no longer exists, create one. 
2. Run through relevant steps in installation S1 architecture to create HEC token, configure aliases, and send HEC/host info to TegoCyber. 

UPGRADE GUIDE - Post Upgrade Steps if you are upgrading from 2.x.x to 3.x.x
------------------------------
Perform steps in INSTALLATION Part 2 - Enable Threat Hits Scanning Searches above. 



