The objective of the Activu app is to add custom Activu alert action, that allows users to:
1. Add additional data to the standard Splunk alert payload.
2. Define the Activu webhook to send the alerts to.
3. Choose the action to invoke on the Activu side.

System Requirements:
- There are no special requirements, app is compatible both with the Splunk Cloud and On-Premise environments.

Configuration:
- Once you installed the app when you get the “App setup required” prompt - choose "Set up later".
- Before configuring and using the app, you need to contact an Activu representative to set up your Display(s) and get the required configuration settings.
- Once everything is in place on the Activu side, configure all the required settings from the Splunk Web UI ->  Apps -> Manage apps -> Set Up action on Activu alerts

Additional public information about this software can be found at: https://activu.com/splunk-documentation

Troubleshooting:
- Any problems with pulling the available action names from Activu REST API will be shown in the Activu alert dropdown or in <SPLUNK_HOME>/var/log/splunk/getactivuactions.log
- If the alerts do not arrive in Activu, search for "sendmodalert - action=Activu" errors and status codes in <SPLUNK_HOME>/var/log/splunk/splunkd.log

For any technical difficulties or for more documentation, contact us:
- Email: linksupport@activu.com
- Web: https://activu.com/clients/


RELEASE HISTORY
================================================================================

1.0.2 - 07-12-21
--------------------------------------------------------------------------------
Reconfiguration for better Splunk Cloud compatibility.

1.0.1 - 07-08-21
--------------------------------------------------------------------------------
Initial upload to Splunk base.

Features:
- Custom Activu alert action available for alerts that allows to define the Activu webhook, the additional data for payload, and the action to invoke on Active side
- Custom getactivuactions search command used by Activu alert UI that pulls from Activu REST API the available Activu actions to choose
- Setup page that allows to configure all the required settings from the Splunk Web UI
- Proper logging to help with troubleshooting
