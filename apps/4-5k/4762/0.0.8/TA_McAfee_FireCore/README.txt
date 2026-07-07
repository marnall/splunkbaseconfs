ABOUT
This Add-On provides inputs of McAfee FireCore Logs

Together with McAfee FireCore App (https://splunkbase.splunk.com/app/4763/) this Add-On helps to setup and maintain McAfee Client Proxy (MCP) deployment.

MCP has the very limited logging capability. One of the components that MCP based upon, the McAfee FireCore, has the logging functionality, but it disabled by default. This Add-On enables FireCore logging.

This app allows to collect FireCore logs from one or many systems and shows which connections are being redirected to which proxies and which connections bypass proxy.

During the MCP setup it is not just enough to install/deploy the MCP executable and configure proxy settings. Sooner or later some exceptions need to be configured. Usually (bad practice) exceptions are configured only after a user complains that something doesn't work. Much better way is to be proactive and to configure exceptions in advance.

This add-on provides the CIM-compatible knowledge to use with other Splunk apps, such as Splunk Enterprise Security and the Splunk App for PCI Compliance.

Discuss the Splunk Add-On for McAfee FireCore on Splunk Answers at http://answers.splunk.com/answers/app/4762

This is a first public release, consider it Beta.

INSTALLATION
For a single desployment (to collect FireCore logs from one system only) you need to install Splunk Enterprise + TA_McAfee_FireCore Add-On + McAfee_FireCore App on the system where MCP is installed.

For a distributed desploymeint (to collect FireCore logs from many systems):
  *install Splunk Universal Forwarder + TA_McAfee_FireCore Add-On on each client system where MCP is installed
  *install Splunk Enterprise + TA_McAfee_FireCore Add-On + McAfee_FireCore App on a separate server to collect logs
  *configure (if not yet done) input on Splunk Enterprise
  *configure output on each Universal Forwarder
  *restart Universal Forwarder to enable FireCore Logging

This Add-On tested for MCP 2.x and 3.x version on x64 Windows platform.

KNOWN ISSUES
  *mcpservice.exe process cannot be filtered out.

TODO
  *enable name resolution for ip addresses.

CONTACT
splunk@compek.net
