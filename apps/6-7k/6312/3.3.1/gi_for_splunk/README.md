# Splunk-App
# IBM Security Guardium Insights for Splunk app


## Install and run Splunk Enterprise

### Install Splunk
Install Splunk Enterprise on your system or deploy it in a [Docker](https://docs.docker.com/get-docker/) container.  Refer to the [Splunk documentation](https://docs.splunk.com/Documentation/Splunk/8.2.3/Installation/Beforeyouinstall) for more information.

- [Windows Installation Guide](https://docs.splunk.com/Documentation/Splunk/8.2.1/Installation/InstallonWindows)
- [Linux installation Guide](https://docs.splunk.com/Documentation/Splunk/8.2.1/Installation/InstallonLinux)
- [Mac OSX Installation Guide](https://docs.splunk.com/Documentation/Splunk/8.2.1/Installation/InstallonMacOS)

### Open Splunk Web
Once Splunk is running, access the Splunk Web interface using the host name and port defined during installation: `http://<hostname>:8000/`.

## Install or update the Guardium Insights for Splunk app using a .tar.gz file

### Install the app from a .tar.gz file
- From the Splunk Web home screen, click the gear icon next to `Apps`.
- Click `Install app from file`.
- Locate the downloaded `guardium-insights-for-splunk-<version>.tar.gz` file and click `Upload`
- Confirm that the following app appears in the list of apps or add-ons: `IBM Security Guardium Insights for Splunk`

### Update the app from a .tar.gz file
Note that the app can be updated with or without resetting data imported from Guardium Insights.
- From the Splunk Web home screen, click the gear icon next to `Apps`.
- Click `Install app from file`.
- Select the `Upgrade App` check box.
- Locate the new `guardium-insights-for-splunk-<version>.tar.gz` file and click `Upload`

## Manage the Guardium Insights for Splunk app using the Splunk Web interface
For information about installing, configuring, resetting, or uninstalling the Guardium Insights for Splunk app using the Splunk Web interface, see: [https://www.ibm.com/docs/en/SSWSZ5_3.1.x?topic=configuring-guardium-insights-splunk-app](https://www.ibm.com/docs/en/SSWSZ5_3.1.x?topic=configuring-guardium-insights-splunk-app).

# Binary File Declaration
- `lib/pydantic_core/_pydantic_core.cpython-37m-x86_64-linux-gnu.so`: Binary for `pydantic_core` Python package


