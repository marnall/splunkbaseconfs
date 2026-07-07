HubSpot Ticket - Splunk Alert Action Integration
Version 1.0.0 


This Application allows users to send triggered alerts within Splunk as tickets in HubSpot.


1. Install the HubSpot App
---------------------------

Install the HubSpot app to the $SPLUNK_HOME/etc/apps folder.  If you have downloaded the tar file from Splunkbase, go to Manage Apps and choose 'Install app from file'.


2. Setup the app
-------------------

From the Splunk interface, click on the app. It will direct you to the 'Configuration' page where you will need to enter the API key value. This can be found with the instructions listed below:

https://knowledge.hubspot.com/integrations/how-do-i-get-my-hubspot-api-key

3. Create a HubSpot alert action
------------------------

For any saved search, create an alert action and select 'HubSpot Ticket Creation'. From here, you can select what ticket priority the triggered alert will have. It is also required to enter the pipeline ID number for where the ticket will be sent to. This number can be found under the HubSpot Portal's Settings -> Service -> Tickets -> "Select a pipeline to Modify" -> Clicking the '</>' Icon.


Questions/Feedback
======================

Please feel free to email at daniel.myong@concanon.com for any questions/issues with the installed application.
