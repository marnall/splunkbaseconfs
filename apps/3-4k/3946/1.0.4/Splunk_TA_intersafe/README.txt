================================================================================
Splunk Technical Add-on for Intersafe version 1.0.4
Release Note (Readme)

                                                                  14 March, 2019                                                 Alps System Integration co. Ltd
                                                          http://www.alsi.co.jp/
================================================================================

Contents
 1.About TA
 2.Products
 3.Installation on Splunk Enterprise
 4.Change History
 5.Support
 6.Other

--------------------------------------------------------------------------------
1. About TA
--------------------------------------------------------------------------------

This Technical Add-on(TA) Maps InterSafe WebFilter Access log data to Splunk CIM. 

--------------------------------------------------------------------------------
2. Products
--------------------------------------------------------------------------------

・InterSafe WebFilter Ver. 9.0

・InterSafe WebFilter Ver. 8.5

・InterSafe WebFilter Ver. 8.0

・InterSafe GatewayConnection 

The access log (InterSafe_http.log or InterSafe_http_XXXXXXXX_XXX.log).

--------------------------------------------------------------------------------
3. Installation on Splunk Enterprise
--------------------------------------------------------------------------------

1. Log into Splunk Web.

2. Select Settings > Data inputs > Files & directories.

3. Click New.

4. Click Browse next to the File or Directory field.

5. Select the log created by InterSafe WebFilter and click "Next".

   Note:
   The default log location for InterSafe WebFilter Access log is 
   /usr/local/intersafe/logs/InterSafe_http.log.

6. Next to Source type, Click to "Source type：Select Source Type" provided 
   in the add-on. 

7. Click on the Select Source Type dropdown and select Network & Security, 
   then intersafe_http select.

8. Click Review.

9. After you review the information, click Submit.

--------------------------------------------------------------------------------
4. Change History
--------------------------------------------------------------------------------

1.0.1

I inserted a Corporate icon (Png Files).

1.0.2

Changed file permissions.

1.0.3

I changed my corporate icon.

Deleted incorrect setting file(eventgen.conf).

I described the procedure to read the InterSafe WebFilter access log file in the Readme.txt file.

I changed the display name of the UI(app.conf).

Added to CIM mapping to Web.Category.

--------------------------------------------------------------------------------
5. Support
--------------------------------------------------------------------------------

We do not support to use this TA.

--------------------------------------------------------------------------------
6. Other
--------------------------------------------------------------------------------

For full information please visit https://www.alsi.co.jp/security/is/ta-for-splunk/

(Sorry for only Japanese)

--------------------------------------------------------------------------------
