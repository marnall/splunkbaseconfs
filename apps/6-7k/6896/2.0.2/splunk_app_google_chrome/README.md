# Google Chrome App for Splunk

## Background

Using the Splunk reporting connector for managed browsers, organizations can get additional visibility on the security posture of their organization's managed fleet. This integration between Chrome and Splunk allows IT administrators to send Chrome security events to an HTTP event collector (HEC) endpoint. Chrome administrators can select all or a subset of available Chrome events to send to Splunk. Examples of Chrome security events include User event, device event, unsafe logins, and unsafe transfer  event. 
This solution also gives an UI to trigger workflow action in response to security events based on Chrome events in splunk.


## Development ##

* Use Splunk UI Create to create the App.   
* Choose the option Add a React Splunk app with an existing React component and name your app chrome-browser-app
* Or use slim to package the app slim package output/chrome-browser-app/
* Add necessary components, add coding logic and searches
* Refer the [Splunk UI Documentation](https://splunkui.splunk.com/Create/AppTutorial)for Setup and Configuring the SUIT Application
* Install Dependencies by executing the below command outside the project folder to install the required software components.
	yarn install
	yarn run setup
* Create Symlink inside the project folder (package/chrome-browser-app), run the below command to create a symbolic link in your Splunk apps directory.
	yarn run link:app
	
	
## Build ##

* Build the Package by executing the below command outside the project folder to build the app.
	yarn run build 


## Package

* Run package.sh script

* Navigate to Splunk Apps Directory and execute the following command to create a compressed tar archive, excluding specific files and directories.
	tar -zcvh --exclude='.gitignore' --exclude='.git' --exclude='local/' --exclude='stage/' --exclude='local.meta' --exclude='.DS_Store' -f chrome-browser-app.tar.gz chrome-browser-app


## Splunk Setup ##

### Install ###
Access the app in Splunkbase to get the latest version.

### Google Chrome Add-on for Splunk dependency ###
The Addon's sole purpose is to transform and perform actions on ingested data using HEC and alerts. For data ingestion refer to the Google Chrome Technology Add-on for Splunk.