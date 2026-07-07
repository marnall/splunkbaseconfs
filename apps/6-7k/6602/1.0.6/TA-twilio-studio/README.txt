
# Setup (global)
Add Twilio credential at the app level  Account name can be anything you want.  Username must be the Twilio API SID,  password must be secret.

# Setup (action)
- Specify the Twilio Studio Flow to invoke
- Specify the Username/API SID (saved in app-level config)
- Specify the result field(s) to send to Twilio (the fields can then be used in the Twilio flow)

- Optional:  In some cases (Splunk ES searches over notables),  you may want to provide the sid and rid in the search result, so that you can point back to the original correlation search, not the search for the notable.  In this case,  include sid and rid as fields to send to Twilio and include something like this in the action search

| rename orig_* as *
| table @To @From message_to_user sid rid

# Troubleshooting 

index=cim_modactions  sourcetype="modular_alerts:execute_flow"  action_name=execute_flow
# Binary File Declaration
C:\Program Files\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\markupsafe\_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\cli-32.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\cli-64.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\cli-arm64.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\cli.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\gui-32.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\gui-64.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\gui-arm64.exe: this file does not require any source code
C:\Program Files\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\gui.exe: this file does not require any source code
# Binary File Declaration
C:\nrtsfmIT\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
C:\nrtsfmIT\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\markupsafe\_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
C:\nrtsfmIT\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\cli-32.exe: this file does not require any source code
C:\nrtsfmIT\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\cli-64.exe: this file does not require any source code
C:\nrtsfmIT\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\cli-arm64.exe: this file does not require any source code
C:\nrtsfmIT\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\cli.exe: this file does not require any source code
C:\nrtsfmIT\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\gui-32.exe: this file does not require any source code
C:\nrtsfmIT\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\gui-64.exe: this file does not require any source code
C:\nrtsfmIT\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\gui-arm64.exe: this file does not require any source code
C:\nrtsfmIT\Splunk\var\data\tabuilder\package\TA-twilio-studio\bin\ta_twilio_studio\aob_py3\setuptools\gui.exe: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-twilio-studio/bin/ta_twilio_studio/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-twilio-studio/bin/ta_twilio_studio/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-twilio-studio/bin/ta_twilio_studio/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-twilio-studio/bin/ta_twilio_studio/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-twilio-studio/bin/ta_twilio_studio/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-twilio-studio/bin/ta_twilio_studio/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-twilio-studio/bin/ta_twilio_studio/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-twilio-studio/bin/ta_twilio_studio/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-twilio-studio/bin/ta_twilio_studio/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-twilio-studio/bin/ta_twilio_studio/aob_py3/setuptools/gui.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-twilio-studio/bin/ta_twilio_studio/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
