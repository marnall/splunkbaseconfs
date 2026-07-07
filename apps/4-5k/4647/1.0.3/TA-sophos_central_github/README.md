Sophos Central SIEM Integration

Add-on Homepage: https://apps.splunk.com/apps/id/TA-sophos_central_github

Author: Hurricane Labs

Version: 1.0.3

### Description ###
You are required to download the Sophos Central script from their GitHub here for this add-on to work: https://github.com/sophos/Sophos-Central-SIEM-Integration
Note: We do not own the rights nor are we a maintainer of this GitHub page. This script runs outside of Splunk, and is NOT included in this add-on. This is the only script that Sophos will provide support for if you have issues. Other add-ons or scripts are not guaranteed to deliver all of your data!

The purpose of this add-on is to provide value to your Sophos Central Event Reports logs, using the official script supported by Sophos. This is done by making the logs CIM compliant, adding tagging for Enterprise Security data models, and other knowledge objects to make searching and visualizing this data easy.

* Built for Splunk Enterprise 6.x.x or higher
* CIM Compliant (CIM 4.0.0 or higher)
* Ready for Enterprise Security
* Built based on the official Sophos Central SIEM integration script (v1.1.0)
    * https://community.sophos.com/kb/en-us/125169
    * https://github.com/sophos/Sophos-Central-SIEM-Integration
        * Supports all three output formats (CEF, JSON, and Keyvalue)
        * Supports file and syslog output methods

### Constraints ###
1. This add-on requires that you initially bring on the data with the correct sourcetype built for your output format (CEF, JSON, or Keyvalue). Respectively those are "sophos:central:cef", "sophos:central:keyvalue", and "sophos:central:json". These sourcetypes will then be transformed into either "sophos:central:events" or "sophos:central:alerts" depending on the endpoint it comes from (Event or Alert endpoint).
2. The script itself will run outside of Splunk, it is not controlled by this add-on in any way. I will provide basic instructions for how to go through the entire setup, but my steps may not work with your environment/OS. You should not need to modify this add-on in any way to get it to work.
3. This was built around v1.1.0 of the release on GitHub. It is possible that the fields or format will change in updates to the GitHub project. Please keep this in mind when using our add-on.

### INSTALLATION AND CONFIGURATION ###
* Search Head: Add-on Always Required (Knowledge Objects)
* Heavy Forwarder: Add-on Possibly Required (Data Collection and/or Event Parsing)
* Indexer: Possibly Add-on Required (Data Collection and/or Event Parsing)
* Universal Forwarder: Add-on Never Required (Data Collection only)
* SH & Indexer Clustering: Supported

This add-on needs to be installed on your Search Head(s) and on the FIRST Splunk Enterprise system(s) that handles the data, traditionally that would be a Heavy Forwarder or Indexer. This add-on should not be deployed to a Universal Forwarder as it won't do anything, even if it's doing the data collection.

#### Script Example Setup Instructions ####
Note: There are installation/configuration instructions here as well: https://github.com/sophos/Sophos-Central-SIEM-Integration
1. Untar the Github folder anywhere. In this example we will use '/opt/sophos-central' and install as root.
2. Configure the `"SOPHOS_SIEM_HOME"` environment variable to point at the script install path.
    `echo 'export SOPHOS_SIEM_HOME=/opt/sophos-central/Sophos-Central-SIEM-Integration' >> /etc/profile.d/20-sophos_home.sh`
3. Configure the config.ini file in the install folder. The comments will explain what settings you can use. If you choose to write to "file", your logs will be stored in 'log' folder of your install folder.
	`nano /opt/sophos-central/Sophos-Central-SIEM-Integration/config.ini`
4. Test the script (you may need to exit and re-enter your root shell to get the export env variable to work from step 2.)
	`/usr/bin/python /opt/sophos-central/Sophos-Central-SIEM-Integration/siem.py -d`
5. Run the command 'env' and copy the output of PATH and SOPHOS\_SIEM\_HOME for the next step.
6. Configure a cron job to run the script every 5 minutes. Paste in your env variables from the last step.
	`nano /etc/cron.d/sophos-central`

    SOPHOS_SIEM_HOME=/opt/sophos-central/Sophos-Central-SIEM-Integration
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/splunk/bin:/snap/bin
    */5 * * * * root /usr/bin/python /opt/sophos-central/Sophos-Central-SIEM-Integration/siem.py

#### Add-on Installation Instructions ####
NOTE: I highly recommend running the script and add-on on a Splunk HF using the file method and JSON output. This makes everything easy and straightforward for install.

1. Install this add-on on the first Splunk Enterprise instance the data touches. This is typically a Heavy Forwarder or Indexer.
    1. Restart Splunk to ensure the add-on settings are in place before proceeding.
2. Install this add-on on your Search Heads where the knowledge objects are required.
	1. A Splunk Restart may be required, you may also attempt a debug refresh.
3. Setup your inputs.conf. This will vary depending on the output method you chose (file or syslog)
	1. File Method
        1. You will need to get your inputs.conf on the system where you installed the Sophos script. You will want to set it up to either monitor or batch the "log" directory of the script install directory. I would recommend using a batch input instead of a file monitor, otherwise your file will grow exponentially.
	    2. It is incredibly important that you pick the correct sourcetype for your inputs.conf. Set the sourcetype to either "sophos:central:cef", "sophos:central:keyvalue", or "sophos:central:json" (no quotes!) Please see the "Constraints" section for more details.
	    3. See the "Example Inputs.conf" section for additional help.
  	2. Syslog Method
		1. You will need to get your inputs.conf on the system where you are forwarding the syslog to. Try to have your syslog solution write these out as true to the raw log format as possible. I would highly recommend CEF if you are forwarding this over syslog.
	    2. It is incredibly important that you pick the correct sourcetype for your inputs.conf. Set the sourcetype to either "sophos:central:cef", "sophos:central:keyvalue", or "sophos:central:json" (no quotes!) Please see the "Constraints" section for more details.
	    3. See the "Example Inputs.conf" section for additional help.
4. Verify data is coming in and you are seeing the proper field extractions & sourcetype transforms by searching the data.
    1. Example Search: `index=* sourcetype=sophos:central:* | dedup sourcetype`
    2. Note: If you see "sophos:central:cef", "sophos:central:keyvalue", or "sophos:central:json" in your search, you did not install the add-on on the first Splunk Enterprise system that touches the data (or didn't restart Splunk). The add-on will not work properly until that is corrected.

#### Example Inputs.conf ####
How you choose to bring the data into Splunk is completely up to you. Here are a couple examples of how you might setup inputs.conf:

##### File Method using CEF output #####
    [batch:///opt/sophos-central/Sophos-Central-SIEM-Integration/log/]
    disabled = 0
    sourcetype = sophos:central:cef
    index = sophos
    move_policy = sinkhole
    crcSalt = <SOURCE>

##### File Method using Keyvalue output #####
    [batch:///opt/sophos-central/Sophos-Central-SIEM-Integration/log/]
    disabled = 0
    sourcetype = sophos:central:keyvalue
    index = sophos
    move_policy = sinkhole
    crcSalt = <SOURCE>

##### File Method using JSON output #####
    [batch:///opt/sophos-central/Sophos-Central-SIEM-Integration/log/]
    disabled = 0
    sourcetype = sophos:central:json
    index = sophos
    move_policy = sinkhole
    crcSalt = <SOURCE>

##### Syslog Method using CEF output #####
    [monitor:///var/log/network/sophos_central/\*/\*.syslog]
    disabled = 0
    sourcetype = sophos:central:cef
    index = sophos


### New features

### Fixed issues
* 1.0.3:
    * Fixed value of 'signature' when it contained a space in CEF format.
    * Fixed missing file_path and file fields in certain events that miss the standard field header.

* 1.0.2:
    * Fixed sourcetype transform, now based on datastream field.
    * Fixed duplicate value for "type" field by renaming the extraction to "vendor_type".
    * Fixed improper dest extraction on CEF events.
    * Fixed bad extract on file.
    * Fixed json/kv user extraction when computer name is absent from suser.

* 1.0.1:
    * Fixed improper event type tagging for Enterprise Security. Only cleaned events were being tagged as malware.
### Known issues

### Third-party software attributions

### DEV SUPPORT
* Reminder: We will provide absolutely no support for the setup of the script or the script itself. Please reach out to Sophos Support or submit an issue on their GitHub page for any issues with the script. Our support is limited to issues/requests with the knowledge objects of the add-on ONLY.
* Contact: splunk-app@hurricanelabs.com
