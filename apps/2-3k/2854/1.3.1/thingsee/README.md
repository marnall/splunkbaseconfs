# Thingsee App for Splunk

- **Authors**:          Mika Borner <mika.borner@gmail.com>
- **Description**:      Thingsee App for Splunk
- **Version**:          1.3.1

## Introduction
The Thingsee App for Splunk collects all Thingsee One metrics and presents them on dashboards.

## Installation

- Install Splunk >=6.2 

- Install Protocol Modular Input from  https://splunkbase.splunk.com/app/1901/ for HTTP Input (Custom cloud)
 or/and
- Install  MQTT Modular Input from https://splunkbase.splunk.com/app/1890/ for MQTT Api

- Install TA-thingsee from https://splunkbase.splunk.com/app/2853/
- Install Thingsee App from https://splunkbase.splunk.com/app/2854/
- Restart Splunk

- For custom cloud:
  - Login to Splunk and go to Setting -> Data inputs -> Protocol Data Inputs
  - Enable and/or adjust the thingsee input. By default, Splunk will listen to Port 8079/tcp 
  - Under Thingsee Creator, select your purpose, and enable the action to send events to the custom cloud URL. \
    e.g. http://mysplunkserver.com:8079

- For MQTT API:
  - Login to Splunk and go to Setting -> Data inputs -> MQTT
  - Edit Stanza thingsee_mqtt
  - To get the right credentials a REST call has to be made:
  - With your app.thingsee.com credentials, run:
        curl -X "POST" -H "Content-Type:application/json" \
        "http://api.thingsee.com/v2/accounts/login" \
        -d $'{"email": "<email>", "password": "<password>" }'

  - Use api.thingsee.com as the Broker Host
  - Use 1883 as the Broker Port
  - Use accountAuthUuid for Topic. The format is: /<accountAuthUuid>/events
  - Use accountAuthUuid as the Username
  - Use accountAuthToken as the Password
  - Save the form
  - Under Thingsee Creator, select your purpose, and enable the action to send events to the cloud
  - Copy the input for every thingsee device
  - Note: AuthTokens may expire from time to time. Currently you have to manually update them.

- Now you should see the dashboards filling up in the Splunk Thingsee App
- Happy Splunking !

## Release Notes
- **v1.0.0**    /       2015-08-24
        - First Release   

- **v1.1.0**   /        2015-08-27
        - Second Release

- **v1.2.0**   /	2015-08-29
        - Third Release

- **v1.3.0**   /        2015-09-08
        - Fourth Release

## Changelog

- **v1.1.0**  
	- More of everything
	- More charts for more sensor data
        - Changed energy dashboard
        - Removed auto-refresh from panels
        - Minor bug fixes and improvements

- ** v1.2.0**
	- Use of optimized field extractions
	- Menu restructured
	- Added First Use Cases incl. configuraton docs
        - Datamodel added for Pivot
        - Minor bug fixes and improvements

- ** v1.2.1**
        - bugfix for ambient light y-axis scale

- ** v1.2.2**
        - bugfix for location dashboard title / panel

- ** v1.3.0**
        - MQTT Support
	- Multidevice Support
        - Tracking Dashboard shows Total Time

- ** v1.3.1**
        - Bugfixed duplicate dropdown entries

## License

Thingsee App for Splunk and Technology Add-On for Thingsee are licensed under CC BY-NC-SA 4.0 http://creativecommons.org/licenses/by-nc-sa/4.0/
