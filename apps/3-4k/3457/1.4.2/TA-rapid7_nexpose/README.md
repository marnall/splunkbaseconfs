## Rapid7 Add-On for Splunk

###http://www.rapid7.com

## Using this Technology Add-on:
   
### Setup:

Please see [Splunk's official documentation](http://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall) for the initial installation of the add-on.
   
After installation, you may be prompted to proceed to the set-up screen in order to configure the app. Alternatively, this page may be accessed by navigating to the app management screen and selecting the 'Set up' action associated with the Rapid7 Add-On.

On the set-up screen, the following details must be entered:

* Nexpose username
* Nexpose password
* Nexpose address (IP or hostname)
* Nexpose port
       	
		
The application records the latest scan for a site when importing data. This means that whenever the script runs, it has the option of only importing data if a new scan exists. To enable this behaviour, tick the checkbox labelled "*Import data only when a new scan exists*". If this option is not enabled, asset and vulnerability data will be imported even if a new scan has not occurred since the last time the script executed. 

The application also offers the option to import a limited amount of solution information along with each vulnerability. To enable this behavior, tick the checkbox labelled *Import solution data with vulnerabilities*. If this option is enabled, a solution summary, number of related solutions and the solution type(s) will be included with each vulnerability event.

You may notice that some vulnerabilities have no solution data - this is because there is no solution available that is relevant for that particular asset, based on its operating system etc.

## Creating Rapid7 Index

In previous versions of the add-on, the `rapid7` index was automatically generated during installation. From release (v1.2.0) it is necessary to create the index prior to configuring the modular inputs. Following the
Splunk instructions for [Creating a Custom Index](https://docs.splunk.com/Documentation/Splunk/8.0.4/Indexer/Setupmultipleindexes)
and name it `rapid7` in order to leverage the default index name used while configuring the inputs. 

This step can be skipped if an index has already been created for data imported by the Nexpose Technology Add-On.

## Adding a modular input:

In order for the application to index data, you must create a modular input job and specify the IDs of the sites for which data will be imported.

Under *Settings*>*Data inputs*>*Rapid7 Nexpose* choose the 'New' option to create a job. By default, data will be written to the ‘rapid7’ index. To set a custom index, expand the ‘More settings’ panel and change the ‘Index’ value. 
    
### Assets and Vulnerabilities:
 
When creating a job for importing asset and vulnerability info, select the 'Assets and Vulnerabilities' option for the 'Job Type'. 

If you wish to import asset and vulnerability data only for specific sites, enter their site IDs (separated by commas) within the 'Sites' box. Leaving this box blank will import data for all sites.

You may create multiple jobs for importing asset and vulnerability information, containing different site IDs. It is recommended to split large sites into individual, staggered jobs.
    
### Vulnerability Exceptions:
 
To import vulnerability exception information, select the 'Vulnerability Exceptions' option for the 'Job Type'. This will import data for all vulnerability exceptions and therefore it is not necessary to enter site IDs.

Vulnerability exceptions are imported regardless of whether the app is set to only import new scans or not. 
    
## Module details:

### Vulnerability Information:

All Rapid7 Vulnerability data will conform to the Splunk Vulnerability Common Information Model. All Rapid7 vulnerability data events will have the source '*Rapid7_Nexpose_Splunk_Vulnerability_Data*' and will have a sourcetype of '*rapid7:nexpose:vuln*'. 

All fields with multiple values will be separated with a semicolon e.g. a vulnerability with more than one vulnerability category related to it (Apache, Apache HTTP Server, IAVM, Web) will have a Splunk CIM field vulnerabilities.dest value of ‘Apache;Apache HTTP Server;IAVM;Web’. 

These fields are limited to 1250 characters. If such a field has been truncated, the field's value will end with an ellipsis ("..."). 

### Asset Information:

All Rapid7 Asset data will conform to the Splunk Vulnerability Common Information Model. All Rapid7 vulnerability data events will have the source '*Rapid7_Nexpose_Splunk_Asset_Data*' event and will have a sourcetype of '*rapid7:nexpose:asset*'. 

All fields with multiple values will be separated with a semicolon e.g. an asset with multiple services running on it (CIFS, DCE Endpoint Resolution, DCE RPC, Microsoft Remote Display Protocol, SSH) will have a Splunk CIM field inventory.services value of 'CIFS;CIFS Name Service;DCE Endpoint Resolution;DCE RPC;Microsoft Remote Display Protocol;SSH’.

These fields are limited to 1250 characters. If such a field has been truncated, the field's value will end with an ellipsis ("..."). 

### Vulnerability Exception Information:

Vulnerability exception data events will be have the source '*Rapid7_Nexpose_Vulnerability_Exception_Data*' event and will have a sourcetype of '*rapid7:nexpose:vulnexception*'.


   
## Debugging:
Two log files are available to help debug issues contained within <splunk_home>/var/log/splunk/:

* splunkd.log - Splunk general log
* TA\-rapid7\_nexpose.log - Log for the Rapid7 Technology Add-on

Please contact support@rapid7.com for help. Please include both log files.

## Changelog:
1.0 // Initial release.
1.1 // Logger update.
1.1.1 // Temp file clean-up.
1.1.2 // Support for sites without existing scans.
1.1.3 // Logger update.
1.1.4 // Adding CVSS_Vector.
1.1.5 // Update to MAC address formatting.
1.1.6 // Update to import logic for sites with ongoing scans.
1.1.7 // Update to vulnerability import formatting.
1.1.8 // Update to solution query to take the best solution.
1.2.0 // Update to support Splunk 8 | Support for Python 3 | Remove ignoring of proxy settings | Skip Rapid7 Insight Agents site processing unless defined explicitly
1.2.1 // Handle field truncation when multi-byte characters are present. Invalid characters are ignored.
1.2.2 // Fix a bug that could cause the application to crash when neither of ip_address or mac_address were present in vulnerability data.
1.3.0 // Add a setup page for cloud compatibility. Add date published to vulnerabilities.
1.3.1 // Fix a bug to allow rollover of logs.
1.4.0 // Add concurrency configuration option.
1.4.1 // Update request approach from ad-hoc SQL to report generation for assets and vulnerabilities.
1.4.2 // Update request approach from ad-hoc SQL to report generation for site queries and vulnerabilty exceptions.
