# __CylancePROTECT Application for Splunk__

---
# Troubleshooting  <a name="troubleshooting"></a>

In case of issues, such as when the post install test does not result in observable output, then you will need to examine splunkd.log and cylance.log files in the $SPLUNK_HOME/var/logs/splunk directory.

To generate more detailed log data, edit the log level in config.py file (about line 54) in the bin directory (requires commandline access). For example, change:  
 self.log_level = 'WARNING'  
to  
 self.log_level = 'DEBUG'  


__Available Log levels:__

+ DEBUG
+ INFO
+ WARNING
+ ERROR
+ CRITICAL, FATAL

The default is WARNING.
DEBUG will report on most events (generates many log messages) and CRITICAL (same as the level FATAL) will report only the most severe of events (generates few log messages).

You can control various aspects of log file generation by configuring parameters in the config.py:
+ filename - Default is cylance.log
+ level - Described above
+ size - Default is 1000000 (i.e. one million bytes or one megabyte). When the file size exceeds this number, a new log file is created (i.e. logging rotates to a new log file)
+ rotations - How many log files will be created before the oldest is overwritten

---
# Support  <a name="support"></a>

Cylance supports the __CylancePROTECT Application for Splunk__, but does not support Splunk-specific troubleshooting - an existing, healthy Splunk environment is assumed.

## Online Guide  <a name="2support_online_guide"></a>
The __guide__  is available at:  
https://support.cylance.com/s/article/ka044000000Ct64AAC/CylancePROTECT-Application-for-Splunk59

## Email  <a name="2support_email"></a>
Please __email__ any feedback or feature requests to:  
__help@blackberry.com__ .

## Request Guidelines  <a name="2request_guidelines"></a>
To expedite handling of your email (feature enhancement, feature request, bug), please supply the following information:

1) Splunk App version (look in app.conf)  
2) Splunk version (e.g. Splunk Enterprise 6.3.2)  
3) OS and version  
4) Company name  
5) Description: Of the feature, the feature enhancement (which feature and how to invoke it e.g. the menu items clicked to arrive at a dashboard); or the bug (how to reproduce the issue and describe the expected behavior versus the actual (suspected erroneous) behavior  
6) Supporting information: screenshot(s), log file(s)
