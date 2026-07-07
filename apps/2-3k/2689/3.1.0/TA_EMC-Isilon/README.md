# Dell PowerScale Add-on for Splunk
## OVERVIEW

- The Dell PowerScale Add-on for Splunk is used to gather data from Dell Isilon Cluster, do indexing on it and provide the indexed data to the "Dell PowerScale App for Splunk" app which runs searches on indexed data and build dashboards using it.
- Author : Dell
- Version : 3.1.0
- Compatible with:
    - Splunk Enterprise versions: 9.2.x, 9.1.x and 9.0.x
    - OS: Linux, Windows
    - Browser: Google Chrome, Mozilla Firefox
    - OneFS versions: 9.4.x, 9.3.x, 9.2.x, 9.1.x, 9.0.x

## RELEASE NOTES

### Version 3.1.0
  - Migrated to Add-on builder version to 4.2.0

### Version 3.0.0
  - Revamped the User-Interface for uniformity with Splunk integrations of other Dell products.
  - Added support of data collection through Proxy.
  - Added data collection for User Quota.
  - Added compatibility with OneFS versions 9.4.x, 9.3.x, 9.2.x, 9.1.x, 9.0.x

### Version 2.7.0
  - Created custom setup page.
  - Changed branding of the add-on.

### Version 2.6.0
  - Added support of Splunk-8.0.0.
  - Removed ssl check flag and certificate path textbox from UI to suffice Splunk Cloud checks.

### Version 2.5.0
  - Fixed Appcert cloud issues

### Version 2.4.0
  - Added support of new security patch coming in Dell Isilon cluster with oneFS version 8.1.0.4 and above.
  - Added support of pagination in active directory API calls.
  - Fixed 503 Server Error: Service Not Available Error for API calls.

## REQUIREMENTS

- Dell Isilon cluster with any one of oneFS versions among 9.4.x, 9.3.x, 9.2.x, 9.1.x, 9.0.x
- If using a forwarder, it must be a HEAVY forwarder(we use the HF because the universal forwarder does not include python)
- The forwarder system must have network access (HTTPS) to one or more Isilon nodes which are to be Splunked.
- Admin user ID and password for collecting data from the Isilon node.

## RECOMMENDED SYSTEM CONFIGURATION

- Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

  - This app has been distributed in two parts.
    1. Dell PowerScale Add-on for Splunk, which gathers data from Dell Isilon platform.
    2. Dell PowerScale App for Splunk, which uses data collected by Dell PowerScale Add-on for Splunk, runs searches on it and builds dashboard using indexed data.
  - This App can be set up in two ways:
    1. Standalone Mode:
        - Here both the apps reside on a single machine.
        - Install the Dell PowerScale App for Splunk and Dell PowerScale Add-on for Splunk on a single machine.
        - The Dell PowerScale App for Splunk uses the data collected by Dell PowerScale Add-on for Splunk and builds the dashboard on it.
    2. Distributed Environment:
        - On Search Head, install both App and Add-on, and configure Add-on on the Search Head.
        - On Forwarder, install and configure Add-on, and create index manually on Indexer.
        - On Indexer, Create index from menu Settings->Indexes->New. Give the name of index (for eg. isilon), which has been used in Add-on on forwarder system.
        - Execute the following command on forwarder to forward the collected data to the indexer.
       $SPLUNK_HOME/bin/splunk add forward-server <indexer_ip_address>:9997
        - On Indexer machine, enable event listening on port 9997 (recommended by Splunk).
        - Dell PowerScale App for Splunk on search head uses the received data and builds dashboards on it.

## INSTALLATION

Follow the below-listed steps to install an Add-on from the bundle:

- Download the App package.
- From the UI navigate to `Apps->Manage Apps`.
- In the top right corner select `Install app from file`.
- Select `Choose File` and select the App package.
- Select `Upload` and follow the prompts.

    OR

- Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## UPGRADE

Follow the below steps to upgrade the App.

- Go to Apps > Manage Apps and click on the "Install app from file". 
- Click on "Choose File" and select the 'Dell PowerScale Add-on for Splunk' installation file. 
- Check the Upgrade app checkbox and click on Upload.
- Restart the Splunk instance.

### UPGRADE TA to version 3.1.0
- Follow the UPGRADE section.
- No additional steps are required.

### UPGRADE TA to version 3.0.0
- Follow the UPGRADE section
- Go to Configuration page of Add-on and create an account by saving details on 'Cluster Node' tab.
- Refer CONFIGURATION section for detailed steps.

### UPGRADE TA from version 2.2 to version 2.3

Follow below steps to upgrade Dell Isilon Technology addon from version 2.2 to 2.3
- Download tar of Dell Isilon Technology addon from splunk base (v2.3)
- Extract tar of Dell Isilon Technology addon under $SPLUNK_HOME/etc/apps
- Execute upgrade python script under $SPLUNK_HOME/etc/apps/TA_EMC-Isilon/bin/upgrade_from_v2.2_to_v2.3.py. On execution, the      script will ask for input and the user has to provide already setup nodes as comma-separated value.
  for eg. $SPLUNK_HOME/bin/splunk cmd python $SPLUNK_HOME/etc/apps/TA_EMC-Isilon/bin/upgrade_from_v2.2_to_v2.3.py
  User can verify configured nodes from $SPLUNK_HOME/etc/apps/TA_EMC-Isilon/local/passwords.conf
  This script will add stanza for each node in given list in file $SPLUNK_HOME/etc/apps/TA_EMC-Isilon/local/isilonappsetup.conf. Verify entry for each node in this file
- Restart Splunk 

## CONFIGURATION

- After fresh installation, Click on Dell PowerScale Add-on for Splunk from the Splunk Home page and you will be redirected to Configuration Page.
- To use the proxy, go to the Proxy tab in the Configuration section and provide the required details. Don't forget to check the Enable option.
- To configure the Log Level, go to the Logging tab.
- To configure the PowerScale Cluster, provide the below required details in the 'Cluster Node' tab:
    - Name: An unique name for the cluster node.
    - IP Address: IP Address for cluster node without scheme.
    - Username: Username for particular cluster node.
    - Password: Password for particular cluster node.
    - Index: Index in which you want to collect the data.
    - Verify SSL Certificate: Checkbox to verify your SSL Certificate if you are collecting data over encrypted network.
- If all the details are correct, a Cluster Node account will be created.
- Corresponding to above account, multiple inputs will be created as soon as cluster node details gets saved successfully.
- Those inputs will be in disabled mode by default and can be enabled from Inputs page. (Not required if you are on Search Head in distributed environment.)

- To enable forwarding syslog data in any Isilon Cluster version, perform the following steps:

  1. Make following changes in file /etc/mcp/override/syslog.conf (copy from /etc/mcp/default/syslog.conf if not present):
      - Put @<forwarders_ip_address> in front of the required log file and !* at the end of the syslog.conf file.
      - Restart syslogd using this command - /etc/rc.d/syslogd restart.

      - In some cases, syslog.conf file is already placed at /etc/mcp/override directory location but it is empty. In that case,  just put the log file name and the forwarder ip in that file. Below is the content of sample syslog.conf:
        ```
          auth.*    @<forwarders_ip_address>
          !audit_config
          *.*    @<forwarders_ip_address>
          !audit_protocol
          *.*    @<forwarders_ip_address>
          !*
        ```
  2. Run the following commands to enable protocol, config and syslog auditing according to Isilon OneFS version:

      - For Dell Isilon cluster with oneFS version 9.x.x:
        ```
          isi audit settings global modify --protocol-auditing-enabled Yes
          isi audit settings global modify --config-auditing-enabled Yes
          isi audit settings global modify --config-syslog-enabled Yes
          isi audit settings modify --syslog-forwarding-enabled Yes
        ```

- Enable receiving the syslog data at forwarder. To do that, go to Settings -> Data Inputs -> UDP -> New. Provide the port number(514 is recommended by Splunk), sourcetype as emc:isilon:syslog and index same as provided in setup form of TA for same isilon cluster to this data input entry.  
- Make sure while receiving syslogs on you have set following metadata - index=Name of index, same as defined in above UDP data input, sourcetype=emc:isilon:syslog.

### Inputs Configuration

- Go to Inputs page. 
- Created inputs for particular Cluster Node can be seen in disabled mode with all the fields.
- Enable the inputs for which you want to collect the data.
- To create a new input, click on 'Create New Input' tab and provide the below required details:
    - Name: An unique name for the input.
    - Interval: Time after which input gets executed again. By default it is 3600 seconds. Minimum: 60 seconds and Maximum: 86400 seconds.
    - Index: Index in which you want to collect the data.
    - Cluster Node: Cluster Node for which you want to collect the data.
    - Endpoint: Endpoint for which data needs to be collected.

## EXTERNAL DATA SOURCES

We are using Dell Isilon API for data collection purpose.

## TROUBLESHOOTING

- General checks:
    - Note that all log files of this Add-on will be generated in `$SPLUNK_HOME/var/log/splunk/` directory.
    - Check $SPLUNK_HOME/var/log/Splunk/ta_emc_isilon_*.log or user can search `index="_internal" source=*ta_emc_isilon_*.log` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_emc_isilon_*.log ERROR` query to see ERROR logs in the Splunk UI.
    - To get the detailed logs, in the Splunk UI, navigate to `Dell PowerScale Add-on for Splunk`. Click on Configuration and go to the Logging tab. Select the Log level to DEBUG and save it.

- If you are getting the following error while configuring the account - 'SSL Certificate verification failed. Please check the SSL Certificate or if it is not required, then save it to False in TA_EMC-Isilon/bin/const.py file.' then if SSL Verification is not required, change it to False by navigating to bin/const.py file and replacing 'VERIFY_SSL = True' with 'VERIFY_SSL = False' on Line number 4.

- If data is not getting collected:
    - To check whether data is getting collected or not, run this search:
        - isilon_index | stats count by sourcetype
    - In particular, you should see these sourcetypes:
        - emc:isilon:rest
        - emc:isilon:syslog
    - For "emc:isilon:syslog":
        - Check the syslog file in /etc/mcp/override/syslog.conf - it should have @<forwarders_ip_address> in front of the required log file and !* at the end of the syslog.conf file. Also run following command to see whether the syslog forwarding is enabled or not:
          1. For Dell Isilon cluster with oneFS version 9.x.x - isi audit settings view, isi audit settings global view
        - Dell Isilon forward syslog and audit logs on 514 udp port by default. Please make sure port 514 is open and available for Isilon syslogs.
    - Disable/Enable the input to recollect the data.
    - Check the logs. They will be more verbose and will give the user insights on data collection.

## SAMPLE EVENT GENERATOR

- The TA_EMC-Isilon, comes with sample data files, which can be used to generate sample data for testing. In order to generate sample data, it requires SA-Eventgen application.  
- The TA will generate sample data of rest api calls and syslog at an interval of 10 minutes. You can update this configuration from eventgen.conf file available under $SPLUNK_HOME/etc/apps/TA_EMC-Isilon/default/.

## DISABLE ADD-ON

To disable the Add-on, you must be logged in to Splunk as an Administrator and follow the steps below.
  - Go to 'Manage Apps' from Splunk's home page.
  - In the search box, type the name of the add-on, and then click Search. In the Status column, next to Add-on, click Disable.

## UNINSTALL ADD-ON
- Uninstalling from a Standalone Environment
    - Disable the Add-on from the Splunk user interface as detailed above.
    - Log in to the Splunk machine from the backend and delete the Add-on folders. The add-on and its directory are typically located in $SPLUNK_HOME/etc/apps/<appname>.
    - Verify that no local configuration files related to Dell PowerScale Add-on for Splunk are available in the $SPLUNK_HOME/etc/system and $SPLUNK_HOME/etc/users folders. If the local folder is present, remove it as well.
    - Restart Splunk

- Uninstalling from a distributed or clustered environment
    - In a cluster or distributed environment, the Dell PowerScale App for Splunk is installed on all the Search Heads and the Dell PowerScale Add-on for Splunk is installed on Search Heads and Forwarders.
    - The steps to uninstall the App and Add-on are the same as for Standalone.
    - To perform any installation or uninstallation step on all the search nodes of a distributed environment, use a deployer manager.
    - From the deployer machine, go to $SPLUNK_HOME/etc/cluster/apps and remove the App and Add-on folders and execute the luster bundle command. [Refer](https://docs.splunk.com/Documentation/Splunk/latest/DistSearch/PropagateSHCconfigurationchanges)

## OPEN SOURCE COMPONENTS AND LICENSES

- pytz (URL: https://pypi.org/project/pytz)
- requests (URL: https://pypi.python.org/pypi/requests)
- backport (URL: https://pypi.org/project/backports)
- defusedxml (URL: https://pypi.python.org/pypi/defusedxml)

## BINARY FILE DECLARATION

- _speedups.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Splunk's Add-on Builder

## REFERENCES

* Syslog of audit protocol has failure code in case of failed audit action. The description of each failure code can be found in below Url.
  https://msdn.microsoft.com/en-us/library/ee441884.aspx
* We have used external library pytz(version: 2019.3) to manage different timezones.
  https://pypi.org/project/pytz/2019.3/
* We have used external library requests(version: 2.22.0) to make https requests.
  https://pypi.python.org/pypi/requests/2.22.0
* We have used external library backport(version: 1.0)
  https://pypi.org/project/backports/1.0/
* We have used external library defusedxml(version: 0.6.0) to handle security concerns while parsing untrusted XML data.
  https://pypi.python.org/pypi/defusedxml/0.6.0

## SUPPORT

- Access questions and answers specific to Dell PowerScale Add-on For Splunk at https://answers.splunk.com.
- Support Offered: Yes
- Support Email: support@crestdatasys.com
- Please visit https://answers.splunk.com, and ask your question regarding Dell PowerScale Add-on For Splunk. Please tag your question with the correct App Tag, and your question will be attended.

### Copyright (C) 2024 Dell Technologies Inc. All Rights Reserved.