Splunk App for Trello version 1.0.0.

Supported Versions
------------------
Splunk Enterprise 7.0+

Dependancies
------------
Timeline - Custom Visualization. Link: https://splunkbase.splunk.com/app/3120/
Bullet Graph - Custom Visualization. Link: https://splunkbase.splunk.com/app/3144/
Trello Add-On - https://splunkbase.splunk.com/app/4141/

Installation and Configuration
------------
1 - Please ensure that you first install all dependancies and have configured the Trello Add-On to collect data. Please ensure you collect at least the default fields in each input. For more information as to how to install this, please refer to the documentation on Splunkbase.
2 - Ensure that any indexes that collect Trello information are added to the default indexes to search through for each user role.
3 - Enjoy!

Troubleshooting
------------
No data is appearing in the app
	- Please check that the add-on is collecting data and that this is being forwarded to your indexer.
	- Data needs to be collected at least every 24 hours for the add-on to work by default. Should your data be older, please change the timescales in each of the dashboards.
	- Indexes are not specified by default. Please ensure that you add any indexes you wish to query to the defaults for the user role. Or you can modify the searches to specify indexes to use.

Should you encounter any other issues. Please contact me at twest.dev@gmail.com