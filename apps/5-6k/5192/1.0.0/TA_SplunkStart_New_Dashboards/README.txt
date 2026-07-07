Author: Stephanie Wang

This Add-On Requires the user to download and install the SplunkStart App
from Splunkbase. It is at:

https://splunkbase.splunk.com/app/3577/

After installing SplunkStart, you can use this TA.

Installing the TA

Unpack the downloaded TA in whatever directory it is found in. Then from the command line, cd to the SplunkStart/bin directory. It is located in
$SPLUNK_HOME/etc/apps/SplunkStart/bin.

Run the script from the bin directory of SplunkStart:

./create_content.sh <path to directory of this TA>
Example:
./create_content.sh ~/Downloads/TA_SplunkStart_New_Dashboards

This will append the necessary files from the TA to the local directory and the default.meta in the TA to SplunkStart's metadata/local.meta directory. The titles files will also be copied from the TA to the src/titles directory

IMPORTANT: From command line, run cp <pathway to TA directory>/TA_SplunkStart_New_Dashboards/appserver/static/sw_* $SPLUNK_HOME/etc/apps/SplunkStart/appserver/static/.. This is needed to copy the .js and .css files needed in 3 of the dashboard panels. 
Example: cp ~/Downloads/TA_SplunkStart/New_Dashboards/appserver/static/sw_* /Applications/Splunk/etc/apps/SplunkStart/appserver/static.
Alternatively, just copy the .js and .css files in the appserver -> static folder of the TA into the appserver -> static of SplunkStart


You must now restart Splunk. Once it's up, go to the Web interface of Splunk and do a https://localhost:8000/en-US/_bump

Usage:

Go into the the SplunkStart App from SplunkWeb. Click on Configure Splunk Start App->Modify Dashboard Macros and notice that there are 10 new tabs. Within these 10 tabs, there are 36 macros that you can modify to use your own data with the TA. The common fields you would enter are your index name, your sourcetype, earliest time (-15m, -1d, -2Y, etc) and latest time (now). Some of the dashboard panels require you to download other apps-- to get the full functionality of this TA, download from Splunkbase:

Waterfall Graph
Calender Heat Map
Boxplot Viz
Location Tracker
Splunk Machine Learning Toolkit
Punchcard Viz
Number Display Viz
Semicircle Donut Viz
Status Indicator Viz

For more information about each of the macros and what fields you need to enter, go to the src folder within TA_SplunkStart_New_Dashboards -> macros folder -> macros_new_dashboards.txt 

Note that unlike SplunkStart and the SplunkStart Basic Security Essentials TA, the formatting for the panels are NOT found in the saved search, but rather in the dashboard XML. This means that the search and macro themselves are not associated with the chart type and formatting (in most cases) and that the XML is necessary in order to get the desired appearance of each panel. Changing the macro/saved search will not impact the XML, however, so you can make whatever changes and additions to macros that you want and the formatting of the panel will remain the same. You can also copy the XML and use it for dashboards not in this app! 

Some of the dashboard panel formatting (ie, XML) is taken from Splunk Dashboard Examples or Splunk demo environments.