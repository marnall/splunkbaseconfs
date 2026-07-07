# Splunk REST API Modular Input for Cloud

1.1.2
-----
* updated the custom response handler method signature.Added in backwards compatibility for your existing custom response handlers , or you can update your handlers to use the new `call` method signature. Refer to `rest_ta/bin/responsehandlers.py` for examples.

1.1.1
-----
* added a default response handler for oauth2

1.1
-----
* Removed the standard Modular Inputs Data Inputs setup page.Now you enter the entire REST stanza on a custom setup page which will get automatically and enforceably encrypted.This is to satisfy Cloud vetting constraints.Functionally the App performs identically to the [standard version](https://splunkbase.splunk.com/app/1546/) , it's just the setup/configuration process that is different.

1.0.3
-----
* upgraded logging functionality

1.0.2
-----
* upgraded urllib3 library from 1.25.3 to 1.25.10
* removed some logging debug messages , which are actually disabled by default , but the Splunk cloud folks don't like them

1.0.1
-----
* logging enhancements for default requests messages

1.0.0
-----
* this is a custom version of the REST API Modular Input to satisfy cloud vetting criteria.This version was branched from v1.8.7 of the standard REST API Modular Input App.It is functionally identical to https://splunkbase.splunk.com/app/1546 , with minor tweaks to pass Cloud vetting.

