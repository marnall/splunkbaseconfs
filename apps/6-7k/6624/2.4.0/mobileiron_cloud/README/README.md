Ivanti Neurons for MDM Splunk App 1.0 Setup Instructioins

A. Requrirments.
Splunk Enterprise v6.4.x
Ivanti Neurons for MDM Instance and a User with API access credentials
Splunk refernce hardware for the Search Head


1. Overview - Monitoring the Ivanti Neurons for MDM Instance device inventory data with Splunk Server( Ivanti Neurons for MDM Splunk App). Currently only one Cloud Instance can be configured to retrive data.

2. Splunk Server Installation : Install the Splunk enterprise Server as per the instalaltion instructions given in Splun website. 

3. Start Splunk Enterprise. (On Mac OS X, launch the Splunk application.)

4. Load http://[splunkservername]:8000 in your browser. *Replace [splunkservername] with the actual DNS name or IP address of your Splunk Server.

5. Navigate to Apps > Find More Apps and search for Ivanti Neurons for MDM.

6. Download the Ivanti Neurons for MDM App For Splunk Enterprise. Since this file is
hosted on support.ivanti.com, your company's download/documentation
credentials are required.

10. Do not unzip or unpack the .SPL file.
11. Navigate to Apps > Manage Apps > Install App From File, and choose the.SPL file you downloaded. The Splunk Enterprise portal will now display the new Ivanti Neurons for MDM App.

7. In the Splunk Enterprise portal, navigate to settings >> Data inputs >> ivanti_neurons_for_mdm screen and provide the details as mentioned in screen and save. This will enable thh App to retrive the device data from Ivanti Neurons for MDM Server at the configured interval.

13. Stark Splunking! - Launch the Ivanti Neurons for MDM App and Drill-down into the menus and start Splunking!
The "Ivanti Neurons for MDM App For Splunk Enterprise" plugin app is provided "as-is". Technical support for this app is available via Developer Support.