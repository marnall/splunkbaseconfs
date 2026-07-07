TA-ivanti-ism
----------------------------

       Original Author: Greg Ford
       Current maintainers: Greg Ford
       Version/Date: 1.42 Jun 10, 2025
       Sourcetype: ivanti:ism:incident, ivanti:ism:servicereq, ivanti:ism:problem, ivanti:ism:change
       Has index-time ops: false

Update History
----------------------------
       1.42 Jun 10, 2025
       --------
       Removed ability for admin to disable TLS verification

       1.40 May 27, 2025
       --------
       Updated AOB scripts and addressed other Splunk Cloud vetting issues
       
       1.37 Feb 04, 2022
       --------
       Added basic support for polling the Changes endpoint

       1.33 Dec 21, 2021
       --------
       Addressed logging issues raised by Cloud Vetting

       1.31 Dec 2, 2021
       --------
       Added redundant checks to ism.py to appease the cloud vetting https-only requirement

       1.30 Aug 18, 2021
       --------
       Rebuilt using Add-On Builder 4 to address jQuery and Python dependencies.

       1.20 May 5, 2021
       --------
       Uploaded to github from latest SplunkBase release and fixed issue where password redaction was affecting the payload.

       1.1.0 Jun 30, 2020
       --------
       Recreated using Add-On Builder and alert action added

       1.0.1 Oct 17, 2019
       --------
       Removed local.meta.

       1.0.0 Aug 22, 2019
       --------
       First release.

Using this App
----------------------------
Configuration: Install TA-ivanti-ism and configure inputs for Incidents and Service Requests. Ensure users of the app search the relevant index by default.

# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-ivanti-ism/bin/ta_ivanti_ism/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-ivanti-ism/bin/ta_ivanti_ism/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-ivanti-ism/bin/ta_ivanti_ism/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-ivanti-ism/bin/ta_ivanti_ism/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-ivanti-ism/bin/ta_ivanti_ism/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-ivanti-ism/bin/ta_ivanti_ism/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-ivanti-ism/bin/ta_ivanti_ism/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-ivanti-ism/bin/ta_ivanti_ism/aob_py3/setuptools/gui.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-ivanti-ism/bin/ta_ivanti_ism/aob_py2/markupsafe/_speedups.so: this file does not require any source code
