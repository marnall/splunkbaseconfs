# Scalr App for Splunk
Splunk app for monitoring Scalr using python API Scripted Input.

Author: Manoj Baba

###Notes:
Splunk Restart is Required after App Install.

After Install, configure Scalr API Credentials (Scalr URL, API Key, Secret) in app Setup page. Login to your Scalr Server as the user you would like to access the API as, and access the URL https://your-scalr-host/#/core/api2 to GENERATE NEW API KEY

By default, the app retrieves data from Scalr API every 20 minutes.
To change the interval, update the same in Settings->Data inputs->Local inputs->Scripts->scalr_dataloader.py

In a distributed environment, install the app on a standalone/clustered Search Heads and create index with name "scalr" on the Indexers.

To uninstall the app, delete the directory $SPLUNK_HOME/etc/apps/scalr_app_for_splunk and restart Splunk.

####More Information:
* This project is open source - https://github.com/dmanojbaba/scalr_app_for_splunk
* The app uses Scalr APIv2 Python client from https://github.com/scalr-tutorials/apiv2-examples/tree/master/python
* The app also uses Python datetime, json, pytz and requests libraries

##Version History:
#####Version: 1.0.2
- Scalr API Secret is now encrypted and stored in passwords.conf
- Storing API Secret as clear text in scalr.conf is now deprecated
- Updated python print statement with print() function

#####Version: 1.0.0
- Initial Release
