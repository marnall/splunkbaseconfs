================================================
Overview
================================================

This app provides a user-interface for analyzing Bazze.io data in Splunk.

================================================
Configuring Splunk
================================================
Install this app into Splunk by doing the following:

  1. Log in to Splunk Web and navigate to "Apps » Manage Apps" via the app dropdown at the top left of Splunk's user interface
  2. Click the "install app from file" button
  3. Upload the file by clicking "Choose file" and selecting the app
  4. Click upload
  5. Add two indexes named "bazze" and "cache"
  6. Restart Splunk if a dialog asks you to
  7. Configure Bazze API input by clicking "New Local Script" in Settings, Data Inputs, Scripts 
  8. Set the Bazze API script to run every 86400 milliseconds
  9. Set the destination index to bazze
  10. Set the sourcetype to bazze_records
  11. Add input arguments to include Bazze API token (-t), record limite (-l), and countries to pull data from (-c)
    - Sample parameters: $SPLUNK_HOME/etc/apps/bazze/bin/bazze_api.py -t 213123421dhfh -l ALL -c ALL
================================================
Change History
================================================

+---------+------------------------------------------------------------------------------------------------------------------+
| Version |  Changes                                                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 1.0     | Initial release                                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|