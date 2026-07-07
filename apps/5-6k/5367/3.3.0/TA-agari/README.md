# OVERVIEW

Agari Add-on For Splunk integrates with the Agari platform and ingest events from Agari into Splunk.


# REQUIREMENTS

* Splunk version 8.x.x.
* This application should be installed on Forwarder in case of cluster.

# Release Notes

## Version: 3.0.0
- Added support of Splunk v8
- Added support of Agari Brand Protection

## Version: 3.1.0
- Adding data collection support for Agari Phishing Defense
- Adding support for data collection of additional alert types for Agari Brand Protection
- Minor bug fixes

## Version: 3.1.1
- Bug Fix for Proxy Support
- Minor Bug Fixes

## Version: 3.1.2
- Bug Fix for slow loading of data in Splunk.

## Version: 3.2.0
- Adding data collection support for Agari Phishing Response

## Version: 3.3.0
- AoB migration update.


# RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk configuration of Forwarder.


# Updating Macro configuration

Agari Add-on by default works on ```default``` index. In case during Add-on setup new index have been created then follow the below steps to update the Macro configuration.

- Go to Settings → Advanced Search
- Click on “Search Macros”
- Set App Context to “Agari App for Splunk”, The macro name “macro_main_agari” should be displayed, and click on the name of the macro.
- Macro is now in Edit Mode, Update Index value as per the Index created while setting up Add-on input. Click on “Save”.
>The Update to Macro is required only in case the events are pushed into a separate Index.

# Binary File Declaration

* cli-32.exe - This file is part of setuptools and code can be found at https://pypi.org/project/setuptools/
* cli-64.exe - This file is part of setuptools and code can be found at https://pypi.org/project/setuptools/
* gui-64.exe - This file is part of setuptools and code can be found at https://pypi.org/project/setuptools/
* gui-32.exe - This file is part of setuptools and code can be found at https://pypi.org/project/setuptools/
* pvectorc.cpython-37m-x86_64-linux-gnu.so - This file is part of setuptools and code can be found at https://pypi.org/project/cPython/
* gui.exe - This file is part of setuptools and code can be found at https://pypi.org/project/setuptools/

# Support
Additional support for this application is available at the following URL:
https://agari.zendesk.com/hc/en-us/articles/115001959803

