# Support Add-on for Hyperbaseline
- **Authors**:		Simon Balz <simon@balz.me>, Mika Borner <mika.borner@gmail.com>, Christoph Dittmann <mulibu.flyingk@gmail.com>, Harun Kuessner <h.kuessner@posteo.de>
- **Description**:	Store baseline statistics based on historical data and score current events based on these statistics
- **Version**: 		1.0

## Introduction
The Support Add-on for Hyperbaseline provides two custom search commands which enables the user to store statistical values in a splunk collection based on historical events (fillbaseline) and use these statistics to determine potential outliers in current data (comparetobaseline).

## Features
- store statistics in a splunk collection using fillbaseline
- compare events against statistics using comparetobaseline

## Additional Notes for Apptitude App Contest
- The app uses only portable code and is tested thoroughly on *nix and Windows systems.
- The app will be used within customer projects, and improved according to customer and community needs. Development of the app will happen in public. Bugs/Issues and improvement requests can be opened on the project's Github page (<https://github.com/my2ndhead/SA-hyperbaseline/issues>).

## Release Notes
- **v1.0**	/	2015-07-20
	- Bugfixes and final release for Apptitude2 submission
- **v0.1**	/ 	2015-07-15
	- first initial version committed to github in develop branch

## Credits
- Ron Pearson (http://www.r-bloggers.com/author/ron-pearson-aka-thenoodledoodler/) for his blog about outler detection in R [5]

## Prerequisites
- Splunk v6.2+ (we use the App Key Value Store)

## Installation
1. Download the [latest](https://github.com/my2ndhead/SA-hyperbaseline/archive/master.zip) add-on
2. Unpack and upload the add-on to the search head
   IMPORTANT: Make sure, the App's folder name in $SPLUNK_HOME/etc/apps is SA-hyperbaseline (Downloading apps from git and uploading them to Splunk will result in wrong folder names)
3. Restart Splunk

## Usage
- fillbaseline command:
	- syntax = fillbaseline config_name=<string> variable=<fieldname> [kv_store=<string>] <field-list>
	- config_name: used as a reference to store the statistics in the key value store
	- variable: name the field which will be used to aggregate the statistics based on
	- kv_store (optional): name of the collection the statistics will be stored in
- comparetobaseline command:
	- syntax = comparetobaseline config_name=<string> variable=<fieldname> [kv_store=<string>] [threshold=<float>] [method=ESD|Hampel|SBR|ASBR] [debug=<boolean>] <field-list>
		- config_name: used as a reference to store the statistics in the key value store
		- variable: name the field which was used to aggregate the statistics based on
		- kv_store (optional): name of the collection the statistics will be stored in
		- threshold: adjust the default thresholds to change the sensitivity of the outlier detection
		- method: choose between the methods extreme Studentized deviation (ESD), Hampel, standard boxplot rule (SBR) and asymmetric standard boxplot rule (ASBR). ESD, Hampel and SBR do expect symmetrical distribution of data around mean/median. ASBR tries to adjust for asymmetrical data

## Examples
- fillbaseline:
	- Calculate the statistics based on the average, minimum and maximum splunk UI usage by day. The statistics are calculated for each individual user:
		    index=_internal sourcetype=splunkd_ui_access| bucket span=1d _time
		        | stats avg(date_hour) as avg_hour min(date_hour) as min_hour max(date_hour) as max_hour by user _time
			    | fillbaseline config_name="ui_usage" value=user avg_hour min_hour max_hour
	- Calculate the statistics based on user events connecting a USB drive during off hours. As these off hour events tend to be spares you should fill the gaps in the timeseries using makecontinuous and fillnull commands:
		    index="insiderthreat" sourcetype="insiderthreat:device"  starttime="12/07/2010:00:00:00" endtime="01/06/2011:00:00:00" action=Connect (date_hour>=20 OR date_hour=<6) OR (date_wday="saturday" OR data_wday="sunday")
			    | bucket span=1d _time | chart limit=0 dc(user) as count over _time by user
                | makecontinuous _time span=1d | fillnull | untable _time, user, count
                | fillbaseline config_name="connect_device" value=user count

- comparetobaseline:
	- This search calculates scores for min_hour, avg_hour and max_hour based on the statistics stored in the hyperbaseline collection previously calculate by fillbaseline. If you didn't execute fillbaseline before running comparebaseline search no score will be provided.
		    index=_internal sourcetype=splunkd_ui_access | bucket span=1d _time
			| stats avg(date_hour) as avg_hour min(date_hour) as min_hour max(date_hour) as max_hour by user _time
			| comparetobaseline config_name="ui_usage" variable="user" min_hour avg_hour max_hour

## Roadmap
- add further outlier detection methods which are able to take seasonality and trend into account

## Known Issues
- the outlier detection doesn't take seasonality and trend into account
- statistics are not automatically removed from the collection. Erroneous data must be deleted manually

## License
- **This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.** [1]
- **Commercial Use, Excerpt from CC BY-NC-SA 4.0:**
  - "A commercial use is one primarily intended for commercial advantage or monetary compensation."
- **In case of Support Add-on for Hyperbaseline this translates to:**
  - You may use Support Add-on for Hyperbaseline in commercial environments for handling in-house Splunk alerts
  - You may use Support Add-on for Hyperbaseline as part of your consulting or integration work, if you're considered to be working on behalf of your customer. The customer will be the licensee of Support Add-on for Hyperbaseline and must comply according to the license terms
  - You are not allowed to sell Support Add-on for Hyperbaseline as a standalone product or within an application bundle
  - If you want to use Support Add-on for Hyperbaseline outside of these license terms, please contact us and we will find a solution

## References
[1] http://creativecommons.org/licenses/by-nc-sa/4.0/
[2] https://en.wikipedia.org/wiki/Median_absolute_deviation
[3] https://en.wikipedia.org/wiki/Quartile
[4] https://en.wikipedia.org/wiki/Medcouple
[5] http://www.r-bloggers.com/finding-outliers-in-numerical-data/
