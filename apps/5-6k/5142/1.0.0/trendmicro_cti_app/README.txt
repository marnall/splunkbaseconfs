Trend Micro Threat Indicator Assessment for Splunk
======================================================================

OVERVIEW
------------------------------
Trend Micro Threat Indicator Assessment for Splunk helps customers match latest indicators from Trend Micro threat research with 3rd party EDR telemetry such as Sysmon in their Splunk.

* Author - Trend Micro Inc.
* Version - 1.0.0
* Build - 1
* Creates Index - False
* Prerequisites - This application is dependent on the splunk apps produce CIM-compliant data
* Compatible with:
   Splunk Enterprise version: 8.0.x
   Common Information Model: 4.6
   OS: Platform independent


OPEN SOURCE COMPONENTS AND LICENSES
------------------------------
  pyans1 version 0.4.8 https://pypi.org/project/pyasn1/ (LICENSE https://github.com/etingof/pyasn1/blob/master/LICENSE.rst)
  python-rsa version 4.1 https://pypi.org/project/rsa/ (LICENSE https://github.com/sybrenstuvel/python-rsa/blob/master/LICENSE)
  pyaes version 1.6.1 https://pypi.org/project/pyaes/ (LICENSE https://github.com/ricmoo/pyaes/blob/master/LICENSE.txt)
  jQuery version 2.1.0 http://jquery.com/ (LICENSE https://github.com/jquery/jquery/blob/master/LICENSE.txt)
  Underscore JS version 1.6.0 http://underscorejs.org (LICENSE https://github.com/jashkenas/underscore/blob/master/LICENSE)
  Require JS version 2.1.15 http://github.com/jrburke/requirejs (LICENSE https://github.com/requirejs/requirejs/blob/master/LICENSE)


EULA
------------------------------
Please check End User's License Agreement at http://release-us1.mgcp.trendmicro.com/pkg/app-splunk-cti-ui/latest/doc/EULA.pdf


DATA COLLECTION NOTICE
------------------------------
Trend Micro Threat Indicator Assessment for Splunk will collect your information, including
- Application list
- Source type list

If you do not want to allow Trend Micro to collect this personal data, do not install this app.


RELEASE NOTES
------------------------------
Trend Micro Threat Indicator Assessment for Splunk version 1.0.0 Copyright © 2020 Trend Micro. All Rights Reserved.


SUPPORT
------------------------------
* Contact information for reporting an issue:
  vincent_ky_lin@trendmicro.com


DOWNLOAD
------------------------------


INSTALLATION
------------------------------
* This application needs to be installed on Splunk Search Head in the case of Distributed environment.
* This app can be installed either through UI from "Manage Apps" or by extracting the compressed file into $SPLUNK_HOME$/etc/apps folder.
* Restart Splunk after installation.
* Refer to the DATA MODEL CONFIGURATION section to accelerate datamodels.


LOG FILES
------------------------------
* Application setup logs are written in $SPLUNK_HOME/var/log/trendmicro_cti_app/trendmicro_cti_app.log


Copyright © 2020 Trend Micro