Dtex Add-on for Splunk
======================================================================

# Overview

* This Add-on (TA) is designed to work with the Dtex App for Splunk
* Author - Dtex Systems
* Version - 3.1.1
* Build - 1
* Compatible with:
    - Splunk: 8.x, 9.1, 9.2, 9.3, 9.4
    - Browser: Chrome, Firefox, Safari
    - OS: Linux, Windows, Mac
    - Common Information Model: 4.16.0

* This application should be installed on Search Head, Indexer, and Forwarder.

# Release Notes

* Version - 3.1.1
    - Updated compatible versions, reformat readme

* Version - 3.1.0 
    - Updated field extraction for the following CIM fields:
        - user
        - src
        - dest
        - dvc
    - Added field extraction and CIM mapping for the src_nt_domain and dest_nt_domain fields.
    - Enhancement of CIM mappings as per the Splunk standards.
    - Provided CIM compatability for various Windows event codes of Dtex WindowsEventLogActivity Activity Group.


* Version - 3.0.0 
    - CIM mappings added.
    - Added workflow actions - "DTEX InTERCEPT Category Investigation" and "DTEX InTERCEPT Category Investigation for Notable".

# Recommended System Configuration

* Standard Splunk configuration of Search Head, Indexer, and Forwarder.

# Topology and Setting Up Splunk Environment

* This app has been distributed in two parts.

    1. Dtex Add-on for Splunk, which collects data from Splunk Forwarder.
    2. Dtex App for Splunk, which adds dashboards to visualize the Dtex data.

* This app can be set up in two ways:
    
    1. **Standalone Mode**:

        * In case of deploying this App on Stand-alone Splunk Deployment, user would have to install TA on Splunk Forwarder which ideally should be on the same server as Dtex Server and do the configuration for TA as per steps mentioned in the 'Application Setup' section below.
        * Post that, user can install Dtex App on Splunk instance by performing the steps mentioned in 'INSTALLATION' section in App's Readme file.

    2. **Distributed Environment**:

        * In case of deploying Dtex App for Splunk on distributed setup, following are the changes needed on each type of node.
        * Splunk Universal/Heavy Forwarder:
            - On Splunk Universal forwarder, install & configure TA-dtexubi and configure necessary directories as per given in 'Application Setup' section below.
        * On Indexer:
            - On Splunk Indexer, user would have to install TA-dtexubi.
        * On Search-Head:
            - On Splunk Search Head, user would install the TA and App and configure only Dtex App for Splunk.

# Installation

* Dtex Add-on for Splunk can be installed through UI using "Manage Apps" or user can also extract zip directly into $SPLUNK_HOME/etc/apps/ folder.

# Application Setup

* On Splunk Forwarder:
    * Install the TA bundle on Splunk Forwarder as mentioned under installation section.
    * Go to Apps directory under path: $SPLUNK_HOME/etc/apps/ta-dtexubi
    * By default there is an example inputs file as "inputs.conf.example", Which needs to be renamed to "inputs.conf" and the first two batch stanzas needs to be updated as per the directory structure in which the files are coming.
    * In case needed, index name can also be updated here to drive data into specific index name.
    * Splunk Indexer’s IP address needs to be given in outputs.conf to send data to specific Splunk Indexer.
    * Restart the instance once and that should start pushing data onto the Splunk Indexer.
* On Splunk Indexer Nodes:
    * On Splunk Indexer, No TA configurations are needed. Just installation of the TA should give appropriate configuration for Dtex App.
* On Splunk Search Head:
    * On Splunk Search head, No TA configurations are needed. Just installation of the TA should give appropriate configuration for Dtex App.

* Note: If you have used the index other than "dtex" in your batch input stanzas in inputs.conf for collecting Dtex activities and alerts data then kindly update "dtexubi_index" macro definition in Dtex App for Splunk.

# Upgrade

Follow the below steps when upgrading from older version of Add-on.

* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Check the upgrade option.
* Select `Upload` and follow the prompts.
* Restart Splunk.
NOTE : If you are upgrading to version 3.0.0, remove macros.conf ($SPLUNK_HOME/etc/apps/TA-dtexubi/local/macros.conf) from local folder if exists.

# CIM Mappings

* Data from Sourcetype dtex_st_alerts is mapped with DataModel Alerts.alert.

* Data from Sourcetype dtex_st_activities is mapped with the following Datamodels:
    - Endpoint.Ports for NetworkActivity (PortAccessed)
    - Network_Sessions.All_Sessions, All_Traffic, Web for NetworkActivity (WebPageAccessed)
    - Endpoint.Filesystem, Change.All_Changes for FileSystemActivity
    - Endpoint.Processes for ProcessActivity
    - Inventory.User, Inventory.Network, Inventory.Inventory.All_Inventory for All Activities
    - Event_Signatures.Signatures for WindowsEventLogActivity
    - Authentication for SessionActivity
    - DLP_Incidents for All activities with Category_Id related to data loss
    - Endpoint.Registry for RegistryActivity

# Workflow Actions
* Following are the workflow actions provided by this Add-on:
    * DTEX InTERCEPT Category Investigation
    * DTEX InTERCEPT Category Investigation for Notable

# Uninstall and Cleanup Steps

* Remove $SPLUNK_HOME/etc/apps/ta-dtexubi
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# Troubleshooting

* Environment variable SPLUNK_HOME must be set

# EULA

* Custom EULA for Dtex. https://dtexsystems.com/dtex-splunk-app-eula/

# Support

* Support Offered: Yes
* Support Email: support@dtexsystems.com

(c) Copyright Dtex Systems Inc 2025