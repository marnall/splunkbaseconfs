## ![Splunk Fit Icon](/../master/static/fiticon.png?raw=true "Splunk Fit Icon")&nbsp;&nbsp;Fitbit Add-on for Splunk® v3.0

**Description:** This add-on allows you to gather data from Fitbit devices to analyze trends in health and activity performance over time in Splunk®.

# Author information
       Original Author: Justin Boucher
       Current Author: Patrick O'Connell
       Version/Date: 3.0.1 / June 19, 2018
       Sourcetype: Fit:Activity
       Sourcetype: Fit:HR
       Sourcetype: Fit:FoodLogging
       Sourcetype: Fit:Sleep
       Sourcetype: Fit:User
       Sourcetype: Fit:Body
       Sourcetype: Fit:BodyGoals
       Has index-time ops: false

# Update History
       3.0.1 June 19, 2018
       --------
       Adding TA-fitbit/static directory that was forgotten in app build.

       3.0.0 June 14, 2018
       --------
       Took ownership from Justin Boucher, who was no longer interested in maintaining 
       this. There may be a number of outstanding issues as this hasn't been updated 
       in some time. Please send in any found issues. 

*__NOTE:__ Uses heavily modified version of magnific0's Fitbit classes'. The magnific0 project is at [this link](https://github.com/magnific0/FitBit.py)*

## Supported Source types:
+ Fit:Activity
+ Fit:FoodLogging _(Includes Water Logs)_
+ Fit:HeartRate
+ Fit:Sleep
+ Fit:User
+ Fit:Body _(Compliments of [noisufnoc](https://github.com/noisufnoc))_
+ Fit:BodyGoals _(Compliments of [noisufnoc](https://github.com/noisufnoc))_

## Supported Devices:
+ Fitbit Flex
+ Fitbit Alto
+ Fitbit Charge
+ Fitbit ChargeHR
+ Fitbit ChargeHR2
+ Fitbit Surge
+ Fitbit Aria

## Script Files
- /bin/fitbit.py - Python class for handling data and token requests
- /bin/access_generator.py - Command line utility for gaining initial access to your Fitbit account data
- /bin/CherryPy-4.0.0.egg - Egg file for token verification. Prevents install of requests in your Splunk Environment
- /bin/requests-2.0.0-py2.7.egg - Egg file for requests. Prevents install of requests in your Splunk Environment
- /bin/*&lt;endpoint type&gt;*.py - Worker files for ingesting different data sources from Fitbit

## Requirements
- Python Requests2 - Egg file provided
- CherryPy - Currently there is an issue loading this module dynamically. Please see the Issues tab for more information and a workaround.

#### ToDo
- Add advanced config to setup
- Fix CherryPy module issue

## Installation Instructions

### Preparation
Before using this TA, you must create a Fitbit app at [https://dev.fitbit.com](https://dev/fitbit.com) using the _Personal_ App type. This will provide you with all the necessary OAuth2 credentials required to gain access to your data. Additionally, the *Personal* will allow you to gain access to the intraday time series information used by this TA's Activity and Heart Rate monitoring. Please see the Fitbit Application documents on the Fitbit web site for information on completing this step. Be sure that the callback URL for your app is http://127.0.0.1:8080.

### Install the TA in Splunk
Install the TA on your Splunk indexers via any Splunk provided means. Install from file is preferred, however any installation procedure can be followed. If you are unfamiliar with Splunk app installation see the following [Splunk Answers Post](https://answers.splunk.com/answers/51894/how-to-install-a-splunk-app.html). Then restart Splunk in order to continue installation.

Next, configure the setup of the TA by navigating to _http://**mysplunkserver**:8000/en-US/manager/search/apps/local_ and select the **"Setup App"** option for the TA. This screen provides the OAuth2 setup information required to obtain data from Fitbit.

_**Advanced Config:** $SPLUNK_HOME/etc/apps/TA-fitbit/default/appconfig.conf contains additional advanced setup information. These settings can be copied to the /local/appconfig.conf file for further tweaking of the TA. All advanced information in the default/appconfig.conf file have been commented. This configuration information will eventually be added to the setup file._

#### Create Access Token:
Run the __access_generator.py__ from your terminal or command line located in the _$SPLUNK_HOME/etc/apps/TA-fitbit/bin_ folder. This file creates the necessary access tokens and permissions in order for the Technology Addon to consume user data. This utility requires that you have already configured during the setup steps previously performed within your Splunk environment. Run the following commands in your terminal:

    cd $SPLUNK_HOME/etc/apps/TA-fitbit/bin/
    chmod +x access_generator.py
    python access_generator.py

Note, if you are running this TA on a remote Linux Splunk instance, CherryPy will not be able to launch the browser window in step 1. Instead, you will need to create a SSH tunnel to the server and copy and paste the URL that step generates and outputs in terminal to a local browser window. The tunnel would be in the form of: ssh  -N -L 8080:localhost:8080 USER@SPLUNKINSTANCE.

1. The __access_generator__ will provide a browser window with a code. Copy this code to your clipboard. See screenshot:
![Access Generator Code](/../master/static/CodeRef.png?raw=true "Access Generator Code")

2. At the prompt in the __access_generator__ utility, paste the code that you copied from the previous step:
![Access Generator Prompt](/../master/static/RunAccessGen.png?raw=true "Access Generator Prompt")

3. Once the code has been submitted then you should see the screenshot below:
![Access Generator Complete](/../master/static/Complete.png?raw=true "Access Generator Complete")

When the process above has been completed, you should see a file called __user_settings.txt__ has been created in the _$SPLUNK_HOME/etc/apps/TA-fitbit/bin_ directory. This file contains all the required access and refresh tokens needed to access your Fitbit account information.

### Configure local/inputs.conf
The final installation step is to configure your __inputs.conf__ file that tells Splunk which data to request from your Fitbit account. To configure this, you must first create a __local__ folder in the _$SPLUNK_HOME/etc/apps/TA-fitbit/_ directory. This __local__ directory is where you will make specific changes to your TA-fitbit environment.

A sample __inputs.conf__ file has been provided in the _$SPLUNK_HOME/etc/apps/TA-fitbit/default/_ directory. Please note that the scripts in the default file have been disabled and you will need to turn the _disabled=true_ setting to _false_ in each stanza. Please follow the guidance in the __default/inputs.conf__ file for more information.

Now restart Splunk and you should start receiving data within a few minutes!

### Index Location and User Roles
This TA will create a standard index called __fit__ inside your indexer(s). The permissions to view this index by default have already been added to the __fit_analyst__ role created during the installation process. You will need to assign this role to any user account that would need access to your fitbit data. By design, this role will not have access to perform the TA setup operations inside of __Manage Apps__, and only the Admin will have this capability.

---

*Fitbit is a registered trademark and service mark of Fitbit, Inc. Fitbit Add-on for Splunk® is designed for use with the Fitbit platform. This product is not put out by Fitbit, and Fitbit does not service or warrant the functionality of this product.* ![Fitbit Icon](/../master/static/FitbitLogo.png?raw=true "Fitbit Icon")

