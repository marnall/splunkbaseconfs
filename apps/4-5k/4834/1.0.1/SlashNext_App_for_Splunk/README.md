#SlashNext App for Splunk

SlashNext App for Splunk enables SOC Analysts and IR teams to enrich 
their existing threat information with SlashNext's 
On-demand Threat Intelligence (OTI) APIs. To know more about SlashNext's 
technology, visit: https://www.slashnext.com/technology/

The app communicates with SlashNext's OTI
Cloud using `https://oti.slashnext.cloud/api/` endpoint. 



##Requirements
The only requirement to use the app is a valid API key to authenticate
requests to SlashNext's OTI Cloud. If you do not have a key, please contact
at: [support@slashnext.com](mailto:support@slashnext.com)

##Dependencies
SlashNext App for Splunk relies on the following Python libraries:

* [Splunklib](https://github.com/splunk/splunk-sdk-python/tree/master/splunklib) (Available from Splunk Python SDK - version 1.6.11) 
* [Python Requests](https://2.python-requests.org/en/master/) (version 2.22.0)

Both of these libraries are bundled within the application and 
do not have to be installed manually by the user.

##Installation
SlashNext App for Splunk can be installed either from the GUI
or manually via the CLI. 

### GUI Installation

* Download the SlashNext App for Splunk from Splunkbase.
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

        splunk install <SlashNext_App_for_Splunk-version.tar.gz>

* Restart the Splunk instance and your app installation will 
be complete

##Configuration
Once the app is installed, you need to configure the 
app with API credentials provided to you by SlashNext. 
In order to configure the app, follow the steps below:

* On your Splunk Home, click on SlashNext App 
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

##Features
SlashNext App for Splunk provides custom search commands and
dashboards that use SlashNext's OTI APIs to provide 
threat information for IP, Domain and URL indicators. They are
briefly explained below: 

###Custom Search Commands
* `snxhostreputation` : Search in SlashNext Cloud database and retrieve 
reputation of a host.

      Syntax: 
      snxhostreputation host=<hostname/ip/fqdn> / host_field=<fieldname>

      Examples:
      | snxhostreputation host=www.slashnext.com
      Execute Host Reputation on Domain: "www.slashnext.com"

      | snxhostreputation host=11.22.33.44
      Execute Host Reputation on IP: "11.22.33.44"
      
      | snxhostreputation host_field=domains
      Execute Host Reputation on "domains" field in all the passed events

      
* `snxhosturls` : Search in SlashNext Cloud database and retrieve list of 
all URLs associated with the specified host.

      Syntax: 
      snxhosturls host=<hostname/ip/fpdn> urls_limit=<int>

      Examples:
      | snxhosturls host=www.slashnext.com urls_limit=10
      Retrieve at maximum 10 URLs with Domain: "www.slashnext.com"

      | snxhosturls host=11.22.33.44 urls_limit=10
      Retrieve at maximum 10 URLs with IP: "11.22.33.44"


* `snxhostreport` : Queries the SlashNext Cloud database and retrieves a 
detailed report for a host and associated URL.

      Syntax: 
      snxhostreport host=<hostname/ip/fqdn>

      Examples:
      | snxhostreport host=www.slashnext.com
      Retreive Host Report for Domain: "www.slashnext.com"

      | snxhostreport host=11.22.33.44
      Retreive Host Report for IP: "11.22.33.44"

* `snxurlscan` :  Perform a real-time URL reputation scan with 
SlashNext's cloud-based SEER Engine.
      
      Syntax: 
      snxurlscan url=<Url> | url_field=<fieldname>

      Examples:
      | snxurlscan url=www.slashnext.com/about/
      Execute URL Scan on URL: www.slashnext.com/about/

      | snxurlscan url_field=urls
      Execute URL Scan on "urls" field in all the passed events

* `snxurlscansync` : Perform a real-time URL scan with SlashNext's 
cloud-based SEER Engine in a blocking mode.

      Syntax: 
      snxurlscansync url=<Url>

      Examples:
      | snxurlscansync url=www.slashnext.com/about/
      Execute a Synchronous URL Scan on URL: www.slashnext.com/about/

* `snxurlscanreport` : Queries the SlashNext Cloud database and 
retrieves a detailed report for a Scan ID.

      Syntax: 
      snxurlscanreport scan_id=<SlashNext Scan ID> extended_info=<boolean>

      Examples:
      | snxurlscanreport scan_id=3b8f8a58-837a-4b81-8a0b-4654ab1e304b
      Retrieve Scan Report against Scan ID: 3b8f8a58-837a-4b81-8a0b-4654ab1e304b

      | snxurlscanreport scan_id=3b8f8a58-837a-4b81-8a0b-4654ab1e304b extended_info=true
      Retrieve Scan Report against Scan ID: 3b8f8a58-837a-4b81-8a0b-4654ab1e304b
      with Extended Information (Screenshot, HTML and Text data)


   
###Enrichment Dashboards
Enrichment Dashboards provide complete threat details of an IP, Domain or URL 
in a customized GUI that runs and renders the output from
 the above mentioned search commands. They can be accessed from 
 the `Enrich` drop-down menu present on the app menu-bar

##Support
This app is being actively maintained and supported by SlashNext, Inc. In order to
request any support or report any issues with the app, please contact the author
of the app: Umair Ahmad ([umair.ahmad.3985@slashnext.com](mailto:umair.ahmad.3985@slashnext.com))

For any other information, send your questions 
to [support@slashnext.com](mailto:support@slashnext.com)

##Changelog
###1.0.1
Minor changes and bug fixes

###1.0.0
First version of SlashNext App for Splunk