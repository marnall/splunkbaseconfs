# Splunk for Barracuda Networks Web Application Firewall

* Supported Splunk versions: 8.1, 8.0, 7.3
* Requires Web Application Firewall firmware version 7.9.x or higher

## Installing Splunk App for Barracuda Web Application Firewall

1. Navigate to App -> Manage Apps.
   * If you have already downloaded the Splunk for Barracuda Web Application Firewall app from Splunkbase, you can click the "Install app from file".
   * Otherwise, Click on "Find more apps online" button.
2. This will load a list of apps from splunkbase. Search for Barracuda Web Application Firewall. You will get the splunk app listed.
3. Click on the "Install free" button, enter your splunk.com credentials, and the app will be installed.
4. Then Splunk may request for restart, so click on restart splunk.
5. After restart, Login back and check whether the "Barracuda Web Application Firewall" app is listed in the "App" menu present in the right hand side of the Splunk UI.
6. Click on the "Barracuda Web Application Firewall" listed in the "App" menu and the UI will land on the "Overall Summary" Screen of the App.

## Configuring Inputs to the Barracuda Splunk App

By default, the Barracuda Splunk app is configured to listen on port 514 over UDP and TCP. You can pass syslog data from a Barracuda WAF on port 514 over UDP and TCP.

To configure local input settings:

1. Being in the app, Click on the "Manager" present in the top right hand side of the screen.
2. Then, Click on the "Data inputs" under "Data".
3. Click on "Add Data" Button or directly you can click on "Add new" Under Actions Column.
4. Configure the input and click on "Save".
5. Next step is pass the syslog data from an existing WAF to the splunk server.

## Configuring Syslog on Web Application Firewall:

1. Navigate to Advanced -> Export Logs.
2. Click on "Add Syslog Server" in Syslog title bar.
3. Add your Splunk Server and Select the connection type as UDP or TCP.
4. That's it.

