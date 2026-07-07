# Microsoft Edge for Business App for Splunk

## Background

Using the Splunk reporting connector for managed browsers, organizations can get additional visibility on the security posture of their organization's managed fleet. This integration between Microsoft Edge for Business and Splunk allows IT administrators to send Edge security events to an HTTP event collector (HEC) endpoint. Edge administrators can select all or a subset of available Edge events to send to Splunk. Examples of Edge security events include User event, device event, unsafe logins, and unsafe transfer  event.


## Development ##

* Use Splunk UI Create to create the App.   
* Choose the option Add a React Splunk app with an existing React component and name your app microsoft-edge-for-business-app-for-splunk
* Or use slim to package the app slim package output/microsoft-edge-for-business-app-for-splunk/
* Add necessary components, add coding logic and searches
* Refer the [Splunk UI Documentation](https://splunkui.splunk.com/Create/AppTutorial)for Setup and Configuring the SUIT Application
* Install Dependencies by executing the below command outside the project folder to install the required software components.
	yarn install
	yarn run setup
* Create Symlink inside the project folder (package/microsoft-edge-for-business-app-for-splunk), run the below command to create a symbolic link in your Splunk apps directory.
	yarn run link:app
	
	
## Build ##

* Build the Package by executing the below command outside the project folder to build the app.
	yarn run build 


## Package

* Run package.sh script

* Navigate to Splunk Apps Directory and execute the following command to create a compressed tar archive, excluding specific files and directories.
	tar -zcvh --exclude='.gitignore' --exclude='.git' --exclude='local/' --exclude='stage/' --exclude='local.meta' --exclude='.DS_Store' -f microsoft-edge-for-business-app-for-splunk.tar.gz microsoft-edge-for-business-app-for-splunk


## Splunk Setup ##

### Install ###
Access the app in Splunkbase to get the latest version.

### Microsoft Edge for Business Add-on for Splunk dependency ###
The Addon's sole purpose is to transform and perform actions on ingested data using HEC and alerts. For data ingestion refer to the Microsoft Edge for Business Technology Add-on for Splunk.