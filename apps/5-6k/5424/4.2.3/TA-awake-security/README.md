# [Awake Security](https://splunkbase.splunk.com/app/5424/)

### Changelog

#### version: 4.2.3

Fix access permission for the app

#### version: 4.2.2

Add support for indexes

#### version: 4.2.0

The latest Arista NDR Splunk Application brings the following updates.
1. Migrate from an Add-On to an Application
2. Brand new tabular Dashboard consisting of - An Overview, Models Detected and Device Details
3. 3 New Reports and Alerts for - High severity security events, Devices communicating with multiple risky destinations and Devices with relatively higher number of risky activities


### Configuration

Once the Arista NDR app for Splunk is installed, you must configure the platform to send the detections to the Splunk app.
1. In Arista NDR, navigate to **Detection Management** and click on the **+ Add New Skill**.
2. Add an Expression as <br>`integrations.json.splunkHEC { callParams | verifyCerts = <true/false> }`<br>
   `{ useHttps: <true/false> , token: "<Splunk-HEC-Token>", source: "Awake-Platform-Host" `<br>
   ` host: "<Splunk-Host>", port: <Splunk-HEC-Port> }`
3. Add a Title like `Adversarial Model Detections to Splunk`
4. Add a Reference Identifier like `awake.integrations.splunk`
5. Leave the rest as default and hit **Save**
