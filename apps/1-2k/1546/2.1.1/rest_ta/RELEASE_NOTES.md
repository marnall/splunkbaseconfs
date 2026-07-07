# Splunk REST API Modular Input

2.1.1
-----
* just a version bump for Splunkbase requirements

2.1.0
-----
* updated the Splunk Python SDK version
* updated global write permissions in default.meta to meet new AppInspect criteria

2.0.9
-----
* robustified the logic to determine the Splunk management port value

2.0.8
-----
* in some rare circumstances , and only on Windows , there may be permission errors rolling log files when you have configured multiple stanzas.Added a patch to uniquely name log files on a per stanza basis.

2.0.7
-----
* for OAuth2 refresh_token flows , you can now configure if the client_id/client_secret is sent in the Base64 encoded  Basic Authentication header (default) or in the request body. Previous versions of the App put the client_id/client_secret in BOTH the header and request body.

2.0.6
-----
* some code checks to catch null passwords in environments with passwords.conf files that can't be decrypted

2.0.5
-----
* option to use the default bundled "certifi" CA Bundle rather than having to declare your own path to a CA Bundle

2.0.4
-----
* upgraded the Splunk Python SDK to v 1.6.18 to meet the latest App Inspect/Cloud Vetting rules.

2.0.3
-----
* by default ,for refresh_token flows, the client_id and client_secret will get placed as parameters in the request body. Added some code so that the client_id and client_secret will also be included as a Base64 encoded Basic Auth header , https://www.oauth.com/oauth2-servers/access-tokens/refreshing-access-tokens/
                       
2.0.2
-----
* added a configuration option to select the grant type for OAuth2 flows

2.0.1
-----
* updated the oauthlib backwards compatibility to python2.7

2.0.0
-----
* upgraded the internal OAuth libraries

1.9.9
-----
* ensure any http/https proxies are available for OAuth2 Refresh Token URL requests

1.9.8
-----
* increase page size from 30 to unlimited for the list of encrypted keys.

1.9.7
-----
* updated the custom response handler method signature.Added in backwards compatibility for your existing custom response handlers , or you can update your handlers to use the new `call` method signature. Refer to `rest_ta/bin/responsehandlers.py` for examples.

1.9.6
-----
* upgraded logging functionality
* added a default response handler for oauth2

1.9.5
-----
* upgraded logging functionality

1.9.4
-----
* upgraded urllib3 library from 1.25.3 to 1.25.10
* removed some logging debug messages , which are actually disabled by default , but the Splunk cloud folks don't like them

1.9.3
-----
* logging enhancements for default requests messages

1.9.2
-----
* enforced Python3 for execution of the modular input script.If you require Python2.7 , then download a prior version (such as 1.9.1).

1.9.1
-----
* python3 compatibility tweaks.

1.9
-----
* general appinspect tidy ups
* removed setup.xml and replaced with a custom JS/HTML dashboard for app setup

1.8.7
-----
* added code to prevent passwords from other apps that might have their sharing set to Global from being concatenated into the rest_ta namespace.

1.8.6
-----
* minor fix to encryption logic

1.8.5
-----
* improved the usability of the setup page for encrypting credentials

1.8.4
-----
* can now pass oauth2 session through to a custom response handler
* added config field for oauth2 expires_in
* added a custom setup page if you require encryption of credentials

1.8.3
-----
* bundled in python modules that are not packaged into Splunk versions pre 8 : urlib3 , certifi , chardet , idna

1.8.2
-----
* updated the bundled version of the requests library to version 2.23.0
* stateful variables/settings used to get persisted back to inputs.conf , now they get persisted to a custom config file reststate.conf , which should solve any unwanted auto restarting of the app by splunkd.
* made error logging more verbose by adding stanza name
* minor tweak to authhandlers.py for python 2/3 dual compatibility

1.8.1
-----
* no changes , changes for this build got pushed up to 1.8.2

1.8
-----
* Python 2.7 and 3+ compatibility

1.7
-----
* added support for Certificate verification using a supplied CA Bundle file

1.6
-----
* fixed Splunk 8 compatibility for manager.xml file

1.5.7
-----
* added client certificate config options

1.5.6
-----
* updated docs

1.5.5
-----
* added trial key functionality

1.5.4
-----
* added a triggers stanza to app.conf to prevent reloading after saving state back to inputs.conf

1.5.3
-----
* patched a bug to callbacks to Splunk for persisting state that required the activation key in the payload

1.5.2
-----
* minor manager xml ui tweak for 7.1

1.5.1
-----
* Corrected a build bug with responsehandlers

1.5
-----
* Added an activation key requirement , visit http://www.baboonbones.com/#activation to obtain a non-expiring key
* Added support for HEAD requests
* Docs updated
* Splunk 7.1 compatible

1.4
----
* Delimiter fix

1.3.9
-----
* Can now declare a CRON pattern for your polling interval.
* Multiple requests spawned by tokenization can be declared to run in parallel or sequentially.
* Multiple sequential requests can optionally have a stagger time enforced between each request.

1.3.8
-----
* Minor code bug with logging

1.3.7
-----
* Added support for token replacement functions in the URL to be able to return a list
of values, that will cause multiple URL's to be formed and the requests for these
URL's will be executed in parallel in multiple threads. See tokens.py

1.3.6
-----

* Added a custom response handler for rolling out generic JSON arrays
* Refactored key=value delimited string handling to only split on the first "=" delimiter

1.3.5
-----

* Ensure that token substitution in the endpoint URL is dynamically applied for each
HTTP request

1.3.4
-----

* Added support for dynamic token substitution in the endpoint URL  
  
ie : /someurl/foo/$sometoken$/goo  
  
$sometoken$ will get substituted with the output of the 'sometoken' function
in bin/tokens.py  

1.3.3
-----
* Added support to persist and retrieve cookies

1.3.2
-----
* Changed the logic for persistence of state back to inputs.conf to occur directly after polling/event indexing has completed rather than waiting for the polling loop frequency sleep period to exit. This potentially deals with situations where you might terminate Splunk before the REST Mod Input has persisted state changes back to inputs.conf because it was in a sleep loop during shutdown.