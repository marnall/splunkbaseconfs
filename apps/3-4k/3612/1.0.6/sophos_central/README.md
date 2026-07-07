# Sophos Central App for Splunk

Thank You For Using "Sophos Central App for Splunk"
Notice: This app should be considered depricated


Thank you for using this Splunk App, I hope you have found it useful and I thank the many of you who have offered words of thanks and contributed improvments and bug fixes.

In late 2017 I changed jobs which meant I no longer had access to a Sophos Central subcription which made updating and helping users a bit more challenging. Where possible I had tried to incorporate changes, but this was not always easy.

However...

From 1st August Sophos have released thier own supported TA and Application, and this should be the recommended approach for all existing Sophos users.
You can find the new Sophos Supported Versions here:
TA	Sophos Add-on for Splunk	https://splunkbase.splunk.com/app/4096/
APP	Sophos App for Splunk	https://splunkbase.splunk.com/app/4097/

Thanks once again. Happy Splunking!
Nick


This Splunk App leverages the Sophos Central API to collect events and alert notifications from registered endpoints and devices.

The application provides an overview dashboard, and fields conforming to CIM 4.8 Malware_*

You will need to obtain an API key from your Sophos Central account. On first run the setup screen will prompt you to configure the app with your account details
 
*Icon made by Freepik from www.flaticon.com*

## Configure the Application

You will need to obtain a Sophos Central API token to start reciving events from Sophos Central. To do so, login to your Sophos Central acocunt, and navigate to Global Settings, and then choose "API Token Management"

![alt text](https://github.com/nickhills81/sophos_central/blob/master/readme_content/Sophos_Central01.png?raw=true)

Choose "New Token" and then provide a name for the token.

![alt text](https://github.com/nickhills81/sophos_central/blob/master/readme_content/Sophos_Central02.png?raw=true)

From the resulting credentials you will need to make note of the "api access url", "x-api-key" and authorisation string.

Open the Splunk App, and enter the details as follows
![alt text](https://github.com/nickhills81/sophos_central/blob/master/readme_content/Sophos_Central03.png?raw=true)

