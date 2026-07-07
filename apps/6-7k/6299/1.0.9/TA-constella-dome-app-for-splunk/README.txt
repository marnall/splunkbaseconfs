The Constella Dome App for Splunk
=================================
Febryary 1, 2022 v1.0.6

The Constella Dome App for Splunk v1.0.3 provides organizations with a Dashboard, Event Mapping and Data Input to show Dome Digital Risk Findings in Splunk. 


  
What is Constella Dome
----------------------

Dome is an automated digital risk protection platform that accelerates your ability to detect and block external cyber threats targeting your organization. Its unmatched automation and scalability protects all your employees and executives from cyber threats by continuously mapping and monitoring your external digital footprint across the surface, deep, and dark web, and social media. 

Dome delivers actionable intelligence that mitigates external cyber threats from compromised credentials, exposed personal information, social media impersonations, or leaked confidential data. Its Machine Language-powered analysis identifies exposed data and correlates malicious activity generated from proprietary and open data source across 53 languages and 125 countries in real-time, seamlessly integrating with your security technologies and workflows to mitigate risk before damage can occur.  
For more information visit www.constellaintelligence.com.



Configuration of the Constella Dome App for Splunk
--------------------------------------------------
To configure the App:
  1) Ensure the hostname on the Configuration Tab is set properly for your Dome Environment. Constella Intelligence Support can assist with this if necessary
  2) on the Inputs Tab:
       - Specify a unique name for the Dome Finding (i.e. DomeFinding)
       - Specify a collection Interval, recommended every 600 seconds (10 Minutes)
       - Enter the API queue ID; refer to the Settings Menu in the Constella Dome Portal
       - Enter the API Token for the API Queue



Known issues
------------
The first time you access the App the Splunk Dashboard will be shown but will appear empty. Refer to the above steps to properly configure the app. 



# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/gui.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/cli-32.exe: this file does not require any source code
# Binary File Declaration
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/cli.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/gui.exe: this file does not require any source code
# Binary File Declaration
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/cli.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/gui.exe: this file does not require any source code
# Binary File Declaration
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/cli.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-constella-dome-app-for-splunk/bin/ta_constella_dome_app_for_splunk/aob_py3/setuptools/gui.exe: this file does not require any source code
