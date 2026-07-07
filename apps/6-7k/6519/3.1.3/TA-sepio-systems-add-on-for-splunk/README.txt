Sepio Add-on For Splunk 3.0.0

What's New in 3.0.0:

1. Fix for future timestamps.
2. Collection from multiple Sepio Platforms.
3. Audit trail data collection.

Prerequisites:

1. Splunk 8.2 or higher.
2. Sepio account and host URL. Please contact Sepio support for the details.
3. Create indexes to store the Sepio logs (default is main).

Upgrade Instructions:

Steps to follow to upgrade from version 2 when you currently have an input configured:

1. Disable all inputs (to avoid errors being logged in `_internal`).
2. Follow Splunk best practice and upgrade the TA via UI or CLI (Splunk Enterprise only).
3. After the upgrade, under the configuration tab, configure the account in the Sepio platform and save.
4. Navigate to the original inputs tab and edit your input. (Select the Sepio platform to use and the log type)
5. Save and re-enable the input.

New Installation:

Via UI:

1. Search for the Sepio Systems add-on for Splunk by clicking on `Apps` --> `Find More Apps` in your Splunk GUI, or browse to https://<Your Splunk Server>:8000/en-US/manager/system/appsremote. Perform a search for "Sepio," and the Sepio Systems add-on for Splunk will be displayed in the results. Click 'Install,' and complete the displayed dialog.
2. After installation is complete, you will be prompted to restart your Splunk server. Click `Restart Now` or `Restart Later` depending on your preference. Continue with the configuration steps once the restart is complete.
3. Login into the Splunk UI, you will see the Sepio Systems add-on for Splunk listed in the `Apps` menu.

Via CLI (Splunk Enterprise only):

1. Find the Sepio Systems add-on for Splunk on Splunkbase.
2. Uncompress the file in `$SPLUNK_HOME/etc/apps/`.
3. Restart the Splunk instance.
4. See Splunk docs for further details on add-on installations: https://docs.splunk.com/Documentation/AddOns/released/Overview/AboutSplunkAdd-ons
5. For Splunk Search Head Clusters/ Distributed Environment Installation, refer to Splunk docs: https://docs.splunk.com/Documentation/AddOns/released/Overview/Distributedinstall

Configuration:

Sepio Platform Account Settings

1. Navigate to Sepio Platform tab and click `Add`.
2. Add a unique Sepio Platform name, Sepio Platform URL (must start with https), token, and click `Add` to save. (url and token provided by Sepio support)

Proxy Setting (If required):

1. Navigate to the Proxy tab in the Configuration page.
2. Check `Enable` and fill in the required fields.

Logging (Default logging level is INFO)

1. If logging levels need to be changed, navigate to Logging in the Configuration page.
2. Select Log level and click `Save`.

Add Sepio Input for Data Collection

1. Click 'Create New Input' in the Inputs page.
2. Give the input a unique name.
3. Add an interval in seconds, e.g., 60 (recommended is 60+).
4. Search and select the index to send the data to.
5. Using dropdowns, select Sepio Platform to use during the configuration of collection and Log Type.
6. Select the Min Severity to start ingesting from (Default Warning).
7. Click `Add`.

Troubleshooting:

PersistentScript Error Workaround

Via UI

1. Navigate to the Proxy tab in the Configuration page.
2. Type `None` on Password textbox. and `Save`

Via CLI (Splunk Enterprise only):

1. Edit `$SPLUNK_HOME/etc/apps/TA-sepio-systems-add-on-for-splunk/local/ta_sepio_systems_add_on_for_splunk_settings.conf`.
2. Add the following stanza to the file:

   [proxy]
   proxy_password = None

# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-sepio-systems-add-on-for-splunk/bin/ta_sepio_systems_add_on_for_splunk/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-sepio-systems-add-on-for-splunk/bin/ta_sepio_systems_add_on_for_splunk/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-sepio-systems-add-on-for-splunk/bin/ta_sepio_systems_add_on_for_splunk/aob_py3/setuptools/gui.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-sepio-systems-add-on-for-splunk/bin/ta_sepio_systems_add_on_for_splunk/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-sepio-systems-add-on-for-splunk/bin/ta_sepio_systems_add_on_for_splunk/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-sepio-systems-add-on-for-splunk/bin/ta_sepio_systems_add_on_for_splunk/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-sepio-systems-add-on-for-splunk/bin/ta_sepio_systems_add_on_for_splunk/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-sepio-systems-add-on-for-splunk/bin/ta_sepio_systems_add_on_for_splunk/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-sepio-systems-add-on-for-splunk/bin/ta_sepio_systems_add_on_for_splunk/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-sepio-systems-add-on-for-splunk/bin/ta_sepio_systems_add_on_for_splunk/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-sepio-systems-add-on-for-splunk/bin/ta_sepio_systems_add_on_for_splunk/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
