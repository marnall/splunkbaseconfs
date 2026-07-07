================================================
Overview
================================================

This app provides a user-interface for editing lookup files in Splunk.



================================================
Configuring Splunk
================================================
Install this app into Splunk by doing the following:

  1. Log in to Splunk Web and navigate to "Apps » Manage Apps" via the app dropdown at the top left of Splunk's user interface
  2. Click the "install app from file" button
  3. Upload the file by clicking "Choose file" and selecting the app
  4. Click upload
  5. Restart Splunk if a dialog asks you to

Once the app is installed, you can use can open the "Splunk App for Lookup File Editing" app from the main launcher.



================================================
Known Limitations
================================================

1) The Splunk App for Lookup File Editing is limited to editing files up to 10 MB. Files larger than this cannot be edited because it consume too much memory on some browsers.

2) The Splunk App for Lookup File Editing does not enforce concurrency with CSV files. This means that if two users edit a lookup file at the same time, someone will lose changes.



================================================
Getting Support
================================================



================================================
Change History
================================================

+---------+------------------------------------------------------------------------------------------------------------------+
| Version |  Changes                                                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 3.5.0   | Officially supported as a Splunk built app                                                                       |
+---------+------------------------------------------------------------------------------------------------------------------+
| 3.6.0   | Resolved appinspect failure for hotlinking splunk web libraries                                                  |
+---------+------------------------------------------------------------------------------------------------------------------+
| 4.0.0   | Upgraded under the hood framework to enhance the performance.                                                    |
|         | Added new functionality of assigning limit to the auto backup.                                                   |
|         | Fixed issues and improved an overall performance of the app.                                                     |
+---------+------------------------------------------------------------------------------------------------------------------+
| 4.0.1   | Fixed issues and improved an overall performance of the app.                                                     |
+---------+------------------------------------------------------------------------------------------------------------------+
| 4.0.2   | Fixed issues and improved an overall performance of the app.                                                     |
+---------+------------------------------------------------------------------------------------------------------------------+