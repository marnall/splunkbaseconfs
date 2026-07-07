# SlashNext CMS App for Splunk

SlashNext CMS App for Splunk enables the Splunk users to have access to a 
complete snapshot of their organization's endpoints with detailed statistics 
and visualizations that provide insights on the security status of all the 
endpoints and the organization as a whole.

The app communicates with SlashNext's CMS Cloud using `https://cms.slashnext.cloud/api`
endpoint.

## Requirements
The only requirement to use the app is a valid API key to authenticate
requests to SlashNext's CMS Cloud. If you do not have a key, please contact
at: [support@slashnext.com](mailto:support@slashnext.com)

## Dependencies
SlashNext App for Splunk relies on the following Python libraries:

* [Splunklib](https://github.com/splunk/splunk-sdk-python/tree/master/splunklib) 
(Available from Splunk Python SDK - version 1.6.13) 

## Installation
SlashNext CMS App for Splunk can be installed either from the GUI
or manually via the CLI. 

### GUI Installation

* Download the SlashNext CMS App for Splunk from Splunkbase.
 The app will be downloaded as tar.gz file
 
* Click on the gear icon under the Apps sidebar on your 
Splunk home to go the Manage Apps page

* On the Manage Apps page, click on "Install app from file" 
button to upload the app file

* Choose the app file that you downloaded earlier and click 
on the Upload button to upload the file

* Splunk will ask you to Restart your instance. Click on the 
Restart Now button to restart the Splunk instance

* After restart is done, login back to your instance and 
SlashNext App for Splunk will now appear under your Apps 
sidebar. At this point, the app has been installed successfully

### CLI Installation

* Download the SlashNext App for Splunk from Splunkbase.

* Copy the output files to your Splunk server and install:

        splunk install <slashnext-cms-app-version.tar.gz>

* Restart the Splunk instance and your app installation will 
be complete

## Configuration
Once the app is installed, you need to configure the 
app with API credentials provided to you by SlashNext. 
In order to configure the app, follow the steps below:

* On your Splunk Home, click on SlashNext CMS App 
for Splunk to launch the app.

* Click on Setup button on the app menu bar to go 
to App Setup page for configurations

* Enter the API key provided to you by SlashNext in the 
API Key field. If you do not have an API key then contact 
at [support@slashnext.com](mailto:support@slashnext.com). 
Optionally, you can also specify an alternate API Base URL, 
if and only if, specifically specified by SlashNext otherwise 
leave it empty. Finally, click on the Save button to finish 
your configuration.

At this point, the configuration for the app is complete and is ready to be used. In case any error occurs, contact Splunk Support for further assistance.

# App Usage

SlashNext CMS App for Splunk has various custom dashboards designed to provide users a detailed
view of the security status of their organization's endpoints. To view a comprehensive detail
on the usage and different data widgets in these dashboards, please refer to 
**SlashNext CMS App Integration Guide Splunk Enterprise** customer guide document.


## Support
This app is being actively maintained and supported by SlashNext, Inc. In order to
request any support or report any issues with the app, please contact the author
of the app: Umair Ahmad ([umair.ahmad.3985@slashnext.com](mailto:umair.ahmad.3985@slashnext.com))

For any other information, send your questions 
to [support@slashnext.com](mailto:support@slashnext.com)

## Changelog
### 1.0.1
Default API Base URL changed and Improved Dashboard UI rendering

### 1.0.0
First version of SlashNext CMS App for Splunk

