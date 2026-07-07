# Endgame API Add-on for Splunk

## This is an Add-on powered by the Splunk Add-on Builder

## OVERVIEW

Endgame Technology add-on (TA) enables Endgame customers to ingest alert data from the Streaming API. This TA also supports and is required for the Endgame App for Splunk.

Author - Endgame, Inc.  
Version - 1.2.1
Build - 29
Creates Index - False  
Splunk Enterprise version: 7.0.x, 7.1.x, 7.2.x
Common Information Model: 4.13.0
OS: Platform independent  
Prerequisites: None

## External Data Sources

We are using Endgame API to collect information of alerts.  

## RELEASE NOTES

### VERSION 1.2.1

* Updated checkpointing mechanism
* Added Accounts Configuration tab

### VERSION 1.2.0

* Enhanced CIM Mapping

### VERSION 1.1.0

* CIM Compliance  
* Added support to collect data over encrypted network  
* Resolved Splunk certification issues  

## INSTALLATION

Follow the below listed steps to install Add-on from bundle:

* Download the App package
* From the UI navigate to `Apps->Manage Apps`
* In the top right corner select "Install app from file"
* Select "Choose File" and select the App package
* Select "Upload" and follow the prompts.

## UPGRADE

### Pre-requisites

Please disable the input before upgrading TA in order to avoid data duplication. Please follow the post upgradation steps in order to avoid data duplication.

* Download the App package
* From the UI navigate to `Apps->Manage Apps`
* In the top right corner select "Install app from file"
* Select "Choose File" and select the App package
* Check Upgrade App
* Select "Upload" and follow the prompts.

### Post upgradation steps

* After successfully upgrading the TA follow the below steps in order to avoid data duplication:
* Navigate to `$SPLUNK_HOME$/etc/apps/TA-Endgame/default.old`
* Move the file `alert.conf` to `$SPLUNK_HOME$/etc/apps/TA-Endgame/local`
* By default, SSL Verification will be true. If you don't want to verify your SSL certificate, follow steps mentioned in Configuration steps or Add certificate by    following steps mentioned in section Adding SSL Certificate
* Restart Splunk

## CONFIGURATION

* After the installation you'll be asked to restart the Splunk. Click on Restart Now.
* After the restart, you need to configure the account and input for data collection. From the UI navigate to `Apps->Endgame API Add-on for Splunk`.
* Navigate to Configuration and click on the Add button to configure a new Account.
* Enter the required details like Account Name (To uniquely identify accounts in splunk), Endgame API, Username and Password.
* Click on Save to save the configuration.
* Navigate to Inputs and click on **Create New Input**. Enter the following details of your Endgame Instance and save it.
  * Name: A unique name of your input.
  * Interval: Data will be collected at provided time interval.
  * Index: Splunk index to ingest data.
  * Endgame Account: The account you configured in Configuration page.
  * By default, SSL Verification will be true. If you don't want to verify your SSL certificate, follow steps:
    * Go to `$SPLUNK_HOME$/etc/apps/TA-Endgame/local`.
    * Open `inputs.conf` file and find stanza with name you have provided while creating input.
    * Add `verify_ssl=false` in that particular stanza.
    * Save the file and restart Splunk.
* TA Endgame is configured and ready to be used.

## ADDING SSL CERTIFICATE

If you have used SSL certificate for your domain, you need to add certificate into Splunk. Follow below listed steps to do the same:

* Go to `$SPLUNK_HOME$/etc/apps/TA-Endgame/bin/ta_endgame/requests/`.
* Open `cacert.pem` file and add your custom certificate details at the end of file.
* Save the file and restart the Splunk.

Note: If your vendor has published the SSL certificate publicly, no need to add that manually.

## SUPPORT

Support Offered: Yes  
Support Email: support@endgame.com

## EULA

Link: https://d38o4gzaohghws.cloudfront.net/static/misc/eula.html

(c) Endgame 2020
