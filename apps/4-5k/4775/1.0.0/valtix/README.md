# Overview #

* Valtix Splunk App integrates with the Valtix to provide security and operational insights of valtix data.

## Requirements  
  
* Splunk version 7.1, 7.2 or 7.3
* OS versions: CentOS Linux release 7.3 or Windows Server 2016
* Browser: Chrome, Firefox or Safari. 
* This application should be installed on Search Head.

## Recommended System Configuration  
  
* Standard Splunk configuration of Search Head.
  
## Installation of App
  
* This APP can be installed through UI using following steps.  
  
1. Log in to Splunk Web and navigate to Apps > Manage Apps.  
2. Click `install app from file`.  
3. Click `Choose file` and select the Valtix app installation file.  
4. Click on `Upload`. 

## Custom Command

* This app has a custom command 'formatevent' to expand the events from repeatedEvents. If the count of repeated events in an event is greater than zero than all the events in the repeated events are expanded by replacing the fields that are changed compared to the base event and rest are kept same as the base event.



## Data Model

* The app consist of one data model "Valtix Data Model". The acceleration for the data model is disabled by default. 

* The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer.

## Data Model Configuration

The Data Model used in this application is not accelerated. Admin should manually accelerate the Data Model.
 
Admin can enable/disable acceleration or change the acceleration period by the following steps:
1. On Splunk’s menu bar, Click on Settings -> Data models
2. From the list for Data models, click “Edit” in the "Action" column of the row for the Valtix Data Model.
3. From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
4. Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
5. If acceleration is enabled, select the summary range to specify the acceleration period.
6. To save acceleration changes click on the save button.

## Rebuilding Data Model

* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:
   
    1. On Splunk’s menu bar, Click on Settings -> Data models.
    2. From the list for Data models, expand the row by clicking “>" arrow in the first column of the row for the Valtix Data model. This will display an extra Data Model information in "Acceleration" section.
    3. From the "Acceleration" section click on "Rebuild" link.
    4. Monitor the status of "Rebuild" in the field "Status" of "Acceleration" section. Reload the page to get the latest rebuild status.
    
## Troubleshooting

* If dashboards are not getting populated:
    * Check "valtix_index" macro is updated if, you are using the custom index.
    * Check "summariesonly" macro, if summariesonly=true searches will only return data from the accelerated data model. Try changing it to false.
    * Make sure you have data in the given time range.
    * To check data is collected or not, run " `valtix_index` " query in the search.
    * Try expanding TimeRange.
    * If you are using a custom index, check if the index is created in `valtix app`'s context or the context of the app in which the index is created should be global.

## Support
* Support Offered: Yes
* Support Email: info@valtix.com

## Copyright
* (c) Valtix 2019