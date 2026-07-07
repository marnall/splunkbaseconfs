# Splunk App for SOAR Export

User documentation: https://docs.splunk.com/Documentation/SOARExport/latest/UserGuide/Introduction

Release notes:
https://docs.splunk.com/Documentation/SOARExport/latest/UserGuide/ReleaseNotes

Splunk Support Portal: Visit https://support.splunk.com for support or installation issues.

System requirement: A functional installation of the Splunk SOAR platform.

This app imports Splunk_SA_CIM and SA_Utils libraries, version 4.8.0.

Third party libraries included in this app:
- Select2 https://select2.org/

# =============  UPGRADE NOTES  =============
- Always clear browser cache after updating the Splunk App for SOAR Export to avoid UI functional issues.
- To begin upgrade, login as user with admin role. Verify that this user also has the 'phantom' role - https://my.phantom.us/kb/49/.

# =============  Adaptive Response and Alert Actions  =============
- Create the index 'phantom_modalert' for log info
- A maximum of 1,000 artifacts can be sent in a single 'Send to SOAR' or 'Run Playbook in SOAR' action
- Field values are correlated and sent individually in cases where events have multiple values for a given field
- A maximum of 1,000 playbooks can be listed in 'Run Playbook in SOAR' to maintain dropdown performance

# =============  HTTPS Certificate Validation  =============

This app performs HTTPS certificate validation when communicating with a SOAR instance.
In some cases it may be necessary to install a custom certificate along with the app
in order to allow proper certificate verification.

If adding a certificate AFTER installing the app:
In order to successfully validate self-signed certs or certs from internal certificate
signers, place a PEM formatted certificate bundle under the app's local or default directories.

$SPLUNK_HOME/etc/apps/phantom/local/cert_bundle.pem
or
$SPLUNK_HOME/etc/apps/phantom/default/cert_bundle.pem

You can also add the certificate to the app installation tarball by creating the local or default folder
and placing the certificate inside the folder:
local/cert_bundle.pem
or
default/cert_bundle.pem

Splunk Cloud users will have to follow the above step to modify the app tarball and then
can send this app installer to Splunk support for installation.


The following only applies to on-prem installations and is strictly prohibited for Splunk Cloud:

You can disable the certificate validation entirely by POSTing to the Splunk REST API
https://splunk-server:8089/servicesNS/nobody/phantom/configs/conf-phantom/verify_certs
with the following as the request body:
value=0

For example, via CURL:
curl -ku 'username:password' https://splunk:8089/servicesNS/nobody/phantom/configs/conf-phantom/verify_certs\?output_mode\=json -d value=0

To re-enable certificate validation, you can post to the same endpoint but change "value" to 1.

SOAR recommends using certificates, and only disabling certificate verification in development
or test environments only. Never disable certificate verification for a production system.


# =============  Clustered Environments  =============

For clustered environments, it is recommended to save server configurations, data model exports, and saved search exports
at the search heads. Configuring these items on the deployer can cause unexpected app behavior as configurations get
pushed to app’s default directory on each search head. See usage guidelines described at the link below for deploying Splunk App for SOAR Export in clustered environments:

https://docs.splunk.com/Documentation/Splunk/latest/DistSearch/PropagateSHCconfigurationchanges
