Installation and configuration:
In your Splunk installation, go to the app manager screen. Click on 'Install app from file' and upload the IncMan app. 
Now you have to restart Splunk, after restarting  go to the app manager screen. Click `Set up` in the  IncMan integration entry. 
Complete the required  attributes and click `save`.  
Save action’ll start automatically connection testing, so if saving ends successfully  all is up and running and configuration 
script retrieves from your Incman appliance all Inciden templates available. If you add new template, after app configuration you have to reconfigure Incman app. 


Alert Configuration:
Inside "Searches, reports, and alerts" section, select the search in which you want configure Incman  Splunk add on.
Inside Incman app you can configure:
1. If you want new alert triggering’ll create new incident everytimes or after first one it’ll append new as Splunk event to last one with identical Incident Id you have set.
2. If you choose for "append" you can also specify how many minutes must spend to create new one or continue to append splunk events.
3. In case you have chosen “Create new” option you can decide  if you want automatically append to Incident Id date and time (if you have chosen "append" this option’ll be ignored).
4. Configure “Incident ID” value in which you can use tokens that access search metadata and tokens available from results, for correct “append” operation don’t use token that change every  triggering.
5. Configure “Addition Info” value  in which you can use tokens that access search metadata and tokens available from results.
6. Define which “Template” you want to use for new incident.
7. Now, with next fields you can associate CEF fields name to tokens available from results, it is not necessary complete all fields.

Now you can save Alert configuration.

Third-party dependencies:
To use this add-on you need IncMan software 

Python dependency:
Incman Splunk Add-on uses python library 'suds' to manage soap calls, it's provided inside add-on directory.  
