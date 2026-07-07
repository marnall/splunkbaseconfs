iDefense Technical add-on
===========================

iDefense Technology Add-on providing an easy way to interact with iDefense Intelgraph API and loading IOCs into Splunk Enterprise Security Threat Intelligence Framework.

========================
Where to install
========================

This package must be installed on

* Search head

========================
Dependencies
========================

* SplunkES version 5.1.0
* Splunk Python SDK version 1.6.4 - should be already installed inside TA-idefense
* iDefense SDK version 1.0.0 - should be already installed inside TA-idefense

====================================
Installation and configuration
====================================

Splunk has to be restarted after app installation.


API feature
--------------------------

To start using API capabilities the API must be configured. Data required:

* iDefense API auth token

Authorization token configuration
----------------------------------------------------

Auth token is stored in **passwords.conf** file in ./local directory of the app (TA-iDefense/local/password.conf).
The token can be proided by:

1. Using the iDefense Set-up page (**prefered way**)
During the first run of iDefense app user will see form that can be used to provide API credentials for the app.
Form will include fields listed below (**the API token can be updated later on using the same setup page**).

.. code-block::

  API Access Token: YOUR_IDEFENSE_API_TOKEN

2. Directly editing the password.conf file.
In the **passwords.conf** change *idefense_auth_token* to your *API Authorization token*
After this change the app must be reloaded (or the whole Splunk can be restarted)

.. code-block::

  [credential:idefense:idefense:]
  password = idefense_auth_token

3. Using Splunk REST API and curl command provided below. If the command is called from other machine than the one Splunk runs on *localhost* has to be replaced by IP address of Splunk instance where the iDefense App is located.
*idefense_auth_token* has to be changed to your *API Authorization token*. Using this method ensures the password will be stored in encrypted form. **BE AWARE THE CURL COMMAND WILL BE IN BASH HISTORY**

.. code-block::

  curl -k -u splunk_admin:splunk_password https://localhost:8089/servicesNS/nobody/TA-idefense/storage/passwords -d name=idefense --data-urlencode password=idefense_auth_token -d realm=idefense


Correlation Searches
-----------------------

Splunk ES *Threat Activity Detected* correlation search has to be enabled for full application functionality.

App Initialization
--------------------------

----------------
Saved searches
----------------

At first run the follow saved searches have to be executed in order to populate the kvstore with threat intelligence and updated threat groups definitions.
1. iDefense-get_domain (ALL)
2. iDefense-get_ip (ALL)
3. iDefense-get_url (ALL)
4. iDefense-update_threat_groups

=======
Usage
=======

Scripts
-----------

List of all supported params can be found in each script docstring.

idefense-get_domain.py
  To execute the script run *|iDefenseGetDomain*. It's possible to enable *debug mode* by providing *debug* as a param *|iDefenseGetDomain debug* or *|iDefenseGetDomain debug=true*


idefense-get_ip.py
  To execute the script run *|iDefenseGetIp*. It's possible to enable *debug mode* by providing *debug* as a param *|iDefenseGetIp debug* or *|iDefenseGetIp debug=true*


idefense-get_url.py
  To execute the script run *|iDefenseGetUrl*. It's possible to enable *debug mode* by providing *debug* as a param *|iDefenseGetUrl debug* or *|iDefenseGetUrl debug=true*


kvstore
------------

This app uses directly the Splunk ES Threat Intelligence KV store.
* ip_intel - for domain and IP intel details
* http_intel - for URL intel details

==================
Compatibility
==================

The app has been tested for these Splunk versions:

2.2.0
----------------
* Splunk 7.1.3
* Splunk ES 5.2.2


2.1.1
----------------
* Splunk 7.1.4
* Splunk ES 5.1.0

2.1.0
----------------
* Splunk 7.1.0
* Splunk ES 5.1.0

==================
Change log
==================

2.2.0
-----------
* Update app.conf
* Update license

2.1.1
-----------
* Do not include sensitive information in log files.
* Updated setup so it doesn't require providing username/realm and the API token can be update later on via the same page.

2.1.0
-----------
* Includes Splunk and iDefense SDK
* Includes Splunk Python scripts
* Includes savedsearches used to populate Splunk ES Threat Intelligence

==================
Known bugs
==================

2.2.0
----------------
* No known bugs

2.1.1
----------------

* API token can be pasted via GUI Set Up page only once.
  Workaround: Edit token directly in passwords.conf or delete passwords.conf to enable GUI Set Up page to work again.
  Affected versions: 2.1.1, 2.1.0

2.1.0
----------------
* No known bugs

-------------------------------
App-Inspect Results
-------------------------------

2.2.0
============
AppInspect Version	1.6.1.post10

+----------------+-------+
| Status         | Count |
+================+=======+
| Failures       | 0     |
+----------------+-------+
| Errors         | 0     |
+----------------+-------+
| Not Applicable | 74    |
+----------------+-------+
| Manual Checks  | 8     |
+----------------+-------+
| Skipped        | 0     |
+----------------+-------+
| Successes      | 56    |
+----------------+-------+


README.rst template version: 1.4 (not delete this line) - update the version when README is updated based on new template version
