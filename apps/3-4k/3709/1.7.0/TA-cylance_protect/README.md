# __CylancePROTECT Add-on for Splunk__

---
# Description  <a name="description"></a>

This is the CylancePROTECT Technology Add-on (TA) designed to support the CylancePROTECT app. 

When you should not use this TA:
This Technology Add-on (TA) is not necessary for simple Splunk installations (e.g. All-in-one Splunk install -- no forwarders or separate indexers)
Instead just install the app located here: https://splunkbase.splunk.com/app/3233/

Also do not use this TA on a forwarder if you are planning on consuming the once-per-day Threat Data Report (TDR) data via the API pull which requires scripted input.  Instead use a full Cylance Splunk app install for that forwarder.

When you should use this TA:
This TA supports the CylancePROTECT App for Splunk. It does not contain any dashboards and should be installed on Splunk indexers and forwaders that are not consuming the once-per-day TDR data via the API.  The app itself should always be installed on the search head.

---
# Support  <a name="support"></a>
Cylance supports the __CylancePROTECT Add-on for Splunk__, but does not support Splunk-specific troubleshooting - an existing, healthy Splunk environment is assumed.

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
