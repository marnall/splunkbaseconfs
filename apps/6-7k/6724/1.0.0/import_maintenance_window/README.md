# ITSI Maintenance Window Importer
> This app was adapted from the Splunk Webhook alert action app. 
## Overview
This app exposes an alert action which enables Maintenance Windows to be imported from tools like ServiceNow, Remedy, or any other data source that contains maintenance window information.
It is a requirement that entities / services are passed as a comma sperated list. Entities / services are also required to be sent as their _key as stored in itsi. For entities, the easiest way to get this is:
~~~spl
| ```base search```
| lookup itsi_entities identifier.values as <host / ci / entity name field> OUTPUT _key ```This assumes that the host value is stored as an alias. Can replace identifier.values with title if you're sure they all align.```
~~~

## Required Fields:
* **Title** --> The title that the new maintenance window will received. Do yourself a favour - make this descriptive :)
* **Description** --> The optional description. As above, use this if you can.
* **Start Time** --> The epoch start time of the maintenance window, **in utc**.
* **End Time** --> The epoch end time of the maintenance window, **in utc**.
* **Object Type** --> Entity or Service. Only one mode at a time is supported, so make sure the objects are all in that category.
* **Object Keys** --> This should be a comma seperated list that contains all the entity or service keys that should be in maintenance.


## Usage
Your best bet is to have a search per type of object - e.g. ITSI Entity or Service. You'll then need to correlate and aggregate them together, lookup the entity keys, and lastly pull them together, with the entities in a comma seperated list:  
~~~spl
| ```Base search```
| eval title = "Maintenance is fun!"
| eval description = "Please. Stop. The. Alerts. I've not seen my partner and kids for 4 months."
| lookup itsi_entities identifier.values as <host / ci / entity name field> OUTPUT _key ```Get the entity key```
| stats values(_key) as object_keys min(start) as start_time max(end) as end_time values(description) as description values(object_type) as object_type by title
| eval object_keys = mvjoin(object_keys, ",")

```Depending on source data, it is probably best to split by the start and end epoch, so you're not putting CIs in maintenance before or after they should be.```
~~~

## Prerequisites:
* Splunk ITSI
* Patience, or a being a gluton for punishment. I won't yuck your yum.
* A Splunk datasource that contains maintenance window data for import

## More Info & Support
> Created by Josh Simonis, Australia 🇦🇺
> For support, contact me at simonisjoshua+splunk@gmail.com  
> [Connect with me on LinkedIn](https://www.linkedin.com/in/simonisjoshua/) 