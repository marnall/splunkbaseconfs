# Configure Splunk to collect Akamai MFA logs
Complete these steps to configure Splunk to retrieve logs from Akamai MFA. 
After completing this procedure, logs appear in the Data Summary in Splunk.

## Create required integration in  Akamai control center
Generate an Integration Id and Signing Key in Akamai MFA: 

1. In the Akamai MFA navigation menu, select Integrations.
2. Click Add integration.
3. Select logging_control integration type and enter a unique name for the integration.
4. Click Save and Deploy.
5. Copy your Integration ID and Signing Key to a secure location.

## Install Akamai MFA in Splunk
1. Click the gear icon next to Apps. 
2. Click "Install App from file". 
3. In the Upload an app dialog, browse and locate the akamai_mfa.spl file. 
4. If you are upgrading or reinstalling the app, select "Update app". 
5. Click "Upload". If prompted, restart Splunk.


Set the SPLUNK_HOME directory variable on your local machine. Ensure that you have write permissions to this directory.
    --On Mac OS X or Linux, open a terminal window and execute this command: 

    `export SPLUNK_HOME=<Splunk_directory>`

    where <Splunk_directory> is the directory where Splunk is installed. 
    For example, **/Applications/Splunk**.

On Windows, open the "Environment Variables" dialog from the Advanced systems settings in the Control Panel. In the dialog, configure a variable for the SPLUNK_HOME directory. Define the variable with the directory where Splunk is installed. 

 - In a terminal or powershell, go to the Splunk application directory:

   --On Mac OS X or Linux, enter this command and press Enter.
     `cd $SPLUNK_HOME/etc/apps/akamai_mfa/bin`

   --On Windows, enter this command and press Enter.
     `cd %SPLUNK_HOME%/etc/apps/akamai_mfa/bin`

 - Execute the python application script to set up Akamai MFA log collection:

   --Enter this command and press Enter.
     `python config.py`
   - When prompted, paste the Integration ID, Signing Key, Akamai MFA Host (https://mfa.akamai.com) that you generated
     in Akamai MFA. Configs will be saved into akamai_mfa/config folder. Files created:
       - settings.json
       - auths.json
       - session_history.json
       - resource.json

 - Enable the python script that allows Splunk to collect logs from Akamai MFA:
   a. In the Splunk navigation menu, select "Settings > Data inputs".
   b. Under Local inputs, click "Scripts".
   c. Click "Enable" for Scripts you want to run.
     - Auths - Gets logs for authentication events.
     - Session History - Gets historical data for user authentication sessions
     - Resource - Gets historical data for actions taken on resources managed by Akamai MFA

 - Logs generated from Akamai MFA plugin can be searched using following sourcetypes:
   - index="akamai_mfa" sourcetype="akamai_mfa_session_auths" for authentication events
   - index="akamai_mfa" sourcetype="akamai_mfa_session_history" for session history
   - index="akamai_mfa" sourcetype="akamai_mfa_resource_action" for resource actions

## Requirements
- Splunk Enterprise 8.0 or later
- Python 3.x (any version >= 3.0)

## Python 2 Deprecation
Starting with release 2.0.0 of Akamai MFA splunk app, Python 2 will not be supported.

## Migrate from older plugin
The older v1.x.x plugin settings aren't compatible with v2.x.x. Install the new plugin and follow [setup](#install-akamai-mfa-in-splunk).
To migrate existing data:
1. Export all data into `csv` from Splunk search.
2. Go to Settings > Add Data > Upload.
3. Select your CSV file.
4. Choose index as `akamai_mfa` and sourcetype as `akamai_mfa_session_auths`.
5. Finish. Splunk ingests the file.


## Guides
- [Indexes](index_guide.md)

##### Copyright 2025 by Akamai Technologies, Inc. All Rights Reserved.