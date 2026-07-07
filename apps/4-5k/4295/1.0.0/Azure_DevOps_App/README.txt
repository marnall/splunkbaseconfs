Azure DevOps App for Splunk 1.0.0.

Supported Versions
------------------
Splunk Enterprise 7.0+

Dependancies
------------
Force Directed App For Splunk. Link: https://splunkbase.splunk.com/app/3767/

Installation and Configuration
------------
1 - Install and configure the Azure DevOps Add-On. Documentation as to how to do this can be found on Splunkbase here: https://splunkbase.splunk.com/app/4254/
2 - Include the indexes for which you are importing data into the Indexes searched by default for the user roles using the app.
3 - Install all dependancies.
4 - Install the App
3 - Enjoy!

Troubleshooting
------------
No data is appearing in the app
	- Please check that the add-on is collecting data and data is being ingested in your indexer.
	- Data needs to be collected at least every 24 hours for the add-on to work by default. Should your data be older, please change the timescales in each of the dashboards.
	- Indexes are not specified by default. Please ensure that you add any indexes you wish to query to the defaults for the user role. Or you can modify the searches to specify indexes to use.

Should you encounter any other issues. Please contact me at twest.dev@gmail.com