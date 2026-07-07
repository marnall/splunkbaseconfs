Configure Splunk to collect EAA logs

Complete these steps to configure Splunk to retrieve logs from EAA. After completing this procedure, logs appear in the Data Summary in Splunk.

Before you begin:

Generate an API key and secret in EAA: 
1. From the top menu, select "System > Settings".
2. Under API, click "Generate New API Key".
3. Enter a name and description.
4. Click "Generate Key". A dialog with the API key and secret appears. 
5. Copy and paste the key and secret to a secure location. 
6. Click "Done".

Procedure:

1. Create an app in Splunk:
     a. Click the gear icon next to Apps.
     b. Click "Install App from file".
     c. In the Upload an app dialog, browse and locate the akamai_eaa.spl file.
     d. If you are upgrading or reinstalling the app, select "Update app".
     e. Click "Upload". If prompted, restart Splunk.


2. Set the SPLUNK_HOME directory variable on your local machine. Ensure that you have write permissions to this directory.
    --On Mac OS X or Linux, open a terminal window and execute this command: 

    export $SPLUNK_HOME=<Splunk_directory>

    where <Splunk_directory> is the directory where Splunk is installed. For example, /Applications/Splunk.

    --On Windows, open the "Environment Variables" dialog from the Advanced systems settings in the Control Panel. In the dialog, configure a variable for the SPLUNK_HOME directory. Define the variable with the directory where Splunk is installed. 



3. Create a Splunk username and password:
    a. In the main navigation menu in Splunk, select "Settings > Access Controls".
    b. In the Actions column for Users, click "Add new". 
    c. Enter a user name in the Username field.  
    d, In the Assign to role area of the page, double click the "admin" role to add it to the Selected roles column.
    e. Enter a password in the Password field.
    f. Enter the password again to confirm.
    g. Click "Save".


4. In a terminal or command prompt, go to the Splunk application directory:

    --On Mac OS X or Linux, enter this command and press Enter.
      cd $SPLUNK_HOME/etc/apps/akamai_eaa/bin

    --On Windows, enter this command and press Enter.
      cd %SPLUNK_HOME%/etc/apps/akamai_eaa/bin

5. Execute the python application script to set up EAA log collection:

   --On Mac OS X or Linux, enter this command and press Enter.
     $SPLUNK_HOME/bin/splunk cmd python akamai_eaa_app_setup.py

   --On Windows, enter this command and press Enter.
     %SPLUNK_HOME%/bin/splunk cmd python akamai_eaa_app_setup.py

6. When prompted, paste the API key and secret that you generated in EAA.

7. When prompted for the Start Date Time, enter the date and time to configure when you want Splunk to start collecting EAA logs. Ensure that you enter the date and time in this format: yyyy-mm-dd hh:mm
  where:
  -yyyy-mm-dd is the date represented in year (yyyy), month (mm), and day (dd).
  -hh:mm is time represented with a 24-hour clock in hours (hh) and minutes (mm).
  For example, a valid Start Date Time entry is 2018-01-01 13:00

9. Enable the EAA python script that allows Splunk to collect logs from EAA:
   a. In the Splunk navigation menu, select "Settings > Data inputs".
   b. Under Local inputs, click "Scripts".
   c. Depending on the operating system for the Splunk platform, enable the appropriate python file.
     - For Mac OS X or Linux, click "Enable" for the $SPLUNK_HOME/etc/apps/akamai_eaa/bin/etl.py script.
     - For Windows, cick "Enable" for the $SPLUNK_HOME\etc\apps\akamai_eaa\bin\etl-windows.py script.



Notes:

-If there is a login failure, a "Login failed because of invalid credentials." message appears in the list of logs or events. 
-Each EAA log line in Splunk contains this data in the following order: timestamp, user IP address, App, username, request method, content type, response code, URL, OS, device browser, and event type.






Copyright 2018 by Akamai Technologies, Inc. All Rights Reserved. 
