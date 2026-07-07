The ObserveIT Technology Add-on for Splunk provides security analysts and 
investigation teams with powerful user activity meta-data and smart user 
behavior alerts. By correlating this powerful user context with the other data
sources in Splunk, a complete picture a user's activities will emerge, allowing
for creation of smarter alerts and quicker threat elimination. 

Data collected by ObserveIT TA can be searched using the Search App or 
ObserveIT App for Splunk

RELEASE NOTES
Version 2.2.1
* Removed all python2-based code

Version 2.1.0
* Added Email Activity to collected reports
* Default timeout changed to 360 seconds.

Version 2.0.1
* Rebuild for supporting python3

Version 1.0.1 
* Initial release
* New: 
  ObserveIT Alerts and User Activities events in Splunk  


  
INSTALLATION AND CONFIGURATION

REQUIREMENTS
- Hardware Requirements:
Refer to System Requirements document
http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements

- Software Requirements:
1. ObserveIT version 7.5.1 and up
2. Splunk Enterprise or Splunk Cloud  v8.0 and above

LIMITATIONS
Add-on installation on SHC is not supported

INSTALLATION INSTRUCTIONS
- Installing on stand-alone Splunk instance
Refer to Splunk Documentation for instructions
http://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall
 
- Installing TA-ObserveIT in a distributed Splunk Enterprise deployment
Install the TA on a non-clustered search head or a heavy forwarder. 

CONFIGURATION
* Open TA-ObserveIT app
* Optional: If proxy is required for connecting to ObserveIT API - navigate to 
  Configuration -> Proxy tab and configure proxy before defining inputs.
* Navigate to "Inputs" tab and click "Create New Input"
* Fill in the fields
  - Name                Input name
  - Interval            API polling interval in seconds
  - Index               Destination index. Either select index name from a 
                        drop-down list or type index name. Make sure the index 
                        exists at your deployment's indexing tier before saving
                        input configuration.
  - Reports API URL     ObserveIT API URL.Non-secure connections are not 
                        supported. 
                        e.g.:https://<Machine name>/v2/apis/report;realm=observeit/reports. 
  - API Token           ObserveIT API token. To obtain the token: 
                        1. Navigate to https://<Machine Name>/v2/apps/portal/home.html
                        2. Press on 'Credentials' tab
                        3. Press on 'Create App' button
                        4. Press on the create application name
                        5. Press on Generate Token button
                        6. Look for "access_token" in JWN Token area
  - Initial checkpoint  Value
                        Timestamp of the earliest event to pull upon input 
                        configuration. Can be either ISO8601 datetime formated
                        string (2018-05-06T12:25:07+00:00), epoch milliseconds
                        (1525609507000) or "now" (without quotes) if only new
                        data is needed.
                        The TA will collect all available historical data if 
                        initial checkpoint value is 0 (zero)
  - Collected reports   Reports data to collect. Can be "User Activity", 
                        "Alerts" or both 
  - SSL Verification    Uncheck to bypass SSL verification (in case server uses
                        self-signed certificate)

TROUBLESHOOTING
Search ta_observeit_observeit_api.log for non-INFO messages: 
index=_internal sourcetype="ta:observeit:log" NOT "INFO"  
    
SUPPORT
For support configuring or using the ObserveIT Add-On for Splunk, please 
contact us at oit-support@proofpoint.com. Support is provided during weekday 
business hours (US, West Coast)

For help using the ObserveIT platform, please contact the ObserveIT support 
organization. https://www.observeit.com/support/

LICENSE
TA-ObserveIT is provided under Apache License version 2.0

CREDITS
The TA was created using Splunk Add-on Builder App. Refer to URL below for 
third-party software credits 
https://docs.splunk.com/Documentation/AddonBuilder/4.0.0/UserGuide/Thirdpartysoftwarecredits
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-ObserveIT/bin/ta_observeit/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-ObserveIT/bin/ta_observeit/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-ObserveIT/bin/ta_observeit/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
