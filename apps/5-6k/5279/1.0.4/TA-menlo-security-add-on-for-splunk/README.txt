This is an add-on powered by the Splunk Add-on Builder.

1. This addon currently covers the menlo security audit log and web logs that is collected via REST API.
2. The following is the sourcetypes used by this addon:
        a) menlosecurity:audit:json is used for the audit log.

[version 1.0.4]
- Updated splunklib to use the latest python library

[version 1.0.3]
- Increased collection hard limit from 10000 events to 100000 events.

[version 1.0.2]
- Increased collection hard limit from 1000 events to 10000 events.

[version 1.0.1]
- Due to no data available in the JSON file result, checkpointing has been removed. Instead the input will run every 5 minutes to return data of the past 5 minutes.


1. Install this addon on the Search Head and Indexer. If you are collecting the logs from the Heavy forwarder, then it needs to be installed there as well.
2. After installation:
        a) On the Search Head and Indexer, in the addon folder/local , create app.conf file and set the following:

        [ui]
        is_visible = 0

        b) On the Heavy Forwarder, where the logs is being collected from, Open the app via web ui. Then, in there:
                - Click the Configuration tab
                - Click the Add-on Settings and add your Menlo Security Token here and click Save.
                - Click the Inputs tab
                - Click Create New Input and Select accordingly whether you want to onboard Web Logs or Audit Logs
                - Specify a name for the input
                - Set the Interval as 300. This would be every 300 seconds.
                - Specify the index name which you want to send the logs to.

[version 1.0.0]

1. This addon currently covers the menlo security audit log and web logs that is collected via REST API.
2. The following is the sourcetypes used by this addon:
	a) menlosecurity:audit:json is used for the audit log.
3. Install this addon on the Search Head and Indexer. If you are collecting the logs from the Heavy forwarder, then it needs to be installed there as well.
4. After installation:
	a) On the Search Head and Indexer, in the addon folder/local , create app.conf file and set the following:
	
	[ui]
	is_visible = 0

	b) On the Heavy Forwarder, where the logs is being collected from, Open the app via web ui. Then, in there:
		- Click the Configuration tab
		- Click the Add-on Settings and add your Menlo Security Token here and click Save.
		- Click the Inputs tab
		- Click Create New Input and Select accordingly whether you want to onboard Web Logs or Audit Logs
		- Specify a name for the input
		- Set the Interval as 60. This would be every 60 seconds.
		- Specify the index name which you want to send the logs to.
		- Specify the start date. This would be from which point you wish to collect your log from. It is based on UTC time in epoch format. For example, setting 1601510400, will tell it to collect from 1 Oct 2020 @ 12:00am (UTC)
		- Set the checkpoint type as File
		

# Binary File Declaration
/Applications/Splunk/var/data/tabuilder/package/TA-menlo-security-add-on-for-splunk/bin/ta_menlo_security_add_on_for_splunk/aob_py2/markupsafe/_speedups.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-menlo-security-add-on-for-splunk/bin/ta_menlo_security_add_on_for_splunk/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-menlo-security-add-on-for-splunk/bin/ta_menlo_security_add_on_for_splunk/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-menlo-security-add-on-for-splunk/bin/ta_menlo_security_add_on_for_splunk/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-menlo-security-add-on-for-splunk/bin/ta_menlo_security_add_on_for_splunk/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-menlo-security-add-on-for-splunk/bin/ta_menlo_security_add_on_for_splunk/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-menlo-security-add-on-for-splunk/bin/ta_menlo_security_add_on_for_splunk/aob_py3/setuptools/cli.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-menlo-security-add-on-for-splunk/bin/ta_menlo_security_add_on_for_splunk/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-menlo-security-add-on-for-splunk/bin/ta_menlo_security_add_on_for_splunk/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-menlo-security-add-on-for-splunk/bin/ta_menlo_security_add_on_for_splunk/aob_py3/setuptools/gui.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-menlo-security-add-on-for-splunk/bin/ta_menlo_security_add_on_for_splunk/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
