#### About analysis_of_splunkbase_apps

Authors: James Donn, Kristofer Hutchinson and Chhean Saur

The analysis_of_splunkbase_apps allows a Splunk® Enterprise administrator to analyze web site content.  This App also provides examples of:
  Multi-search (the entire App is mostly powered by one search)
  Various form options
  Custom CSS and js
  Custom data collection script
  KV Store

After being asked for a list of Splunk Apps in a spreadsheet a few times, I found a need to build this App.  This App provides a simple dashboard with App stats and allows you to search for Splunk Apps within Splunk. It was also designed to work if you are offline, as long as you have been online once to collect data.

Splunk 6.3+ now has most of this built in, but the offline benefits of this App still make it useful.

This was a collaborative effort:
  James Donn - Dashboards and Searches
  Kristofer Hutchinson - Custom CSS and .js
  Chhean Saur - Data Collection script


#### Installation steps

To install and configure this app on your supported platform, follow these steps:

1. Index Settings
Configure the following index within your environment, following your best practices:
[apps]
coldPath = $SPLUNK_DB/apps/colddb
homePath = $SPLUNK_DB/apps/db
thawedPath = $SPLUNK_DB/apps/thaweddb
frozenTimePeriodInSecs = 604800

2. Data Collection
Restart your Splunk Search Head to gather data right away. Data gathering is scheduled to complete once every four hours.

* Note, for Splunk Cloud installations, this script needs to be installed on the Inputs Data Manager (IDM) by Cloud Operations.
This script is also packaged as part of TA-analysis_of_splunkbase_apps.

If you are running Splunk v8.x or greater, the default script will work and is Python 3 compatable. For users running any version before Splunk v8.x, you must manually configure Splunk to use the getSplunkAppsV1-py27.py script to collect data:
Settings -> Data Inputs -> Scripts -> $SPLUNK_HOME/etc/apps/analysis_of_splunkbase_apps/bin/getSplunkAppsV1.py, disable.
Settings -> Data Inputs -> Scripts -> $SPLUNK_HOME/etc/apps/analysis_of_splunkbase_apps/bin/getSplunkAppsV1.py, clone.
Enter $SPLUNK_HOME/etc/apps/analysis_of_splunkbase_apps/bin/getSplunkAppsV1-py27.py as the command. Click save. 

3. Update the KV Store
Run the "Update Splunk Apps KV Store" scheduled search manually to update the KV store. It will also update automatically every four hours.

4. Enjoy!


##### Scripts and binaries

$SPLUNK_HOME/etc/apps/analysis_of_splunkbase_apps/bin/getSplunkAppsV1.py runs every four hours to collect the latest list of Splunk Apps by calling 
Splunkbase's API.  

See the Installation Steps above to obtain backwards compatability for older versions of Splunk.


##### New features

This App version includes the following new features:

- Each tab only loads when cliked on
- Backwards compatability for the data collection script
- In App installation instructions
- Enhanced "Path Forward to Splunk Cloud Compatibility" dashboard

##### Questions and answers

Access questions and answers specific for the analysis_of_splunkbase_apps at http://answers.splunk.com.


##### Support

You can email jim@splunk.com with any comments, questions, or concerns.  I will respond within 5 business days or sooner.


##### Example Use Case 
You have Splunk on your laptop and you are in a meeting where someone asks, "Does Splunk have an App for that?".  The problem is that you do not have wireless access because it is down, or you are a visiting guest.  Just launch up this App and search away.  

