# Jamf Protect Add-on for Splunk

The [Jamf Protect](https://www.jamf.com/products/jamf-protect/) Add-on for Splunk empowers security teams with in-depth visibility into Mac security events, providing integrated visualization for enriched investigation into macOS threat alerting with tuned endpoint telemetry data streams. This add-on supports data streams from the macOS Security & Jamf Security Cloud portals, resulting in a single collection point for all endpoint and network based events occurring across your Apple device fleet. 

[Jamf Protect Administrators Guide](https://www.jamf.com/resources/product-documentation/jamf-protect-administrators-guide/)

[Jamf Security Documentation](https://learn.jamf.com/bundle/jamf-security-documentation/page/Jamf_Security_Documentation.html)

## Deployment

> **Important**
> The base [event type](#eventtype) _must_ be updated before enabling this Add On.

### Supported Splunk Deployment

Learn more about [About installing Splunk add-ons](https://docs.splunk.com/Documentation/AddOns/released/Overview/Installingadd-ons) in your environment.

|Splunk Component|Supported|Required|Notes|
|------------|--------|--------|-----|
|Search Heads | Yes | Yes |
| Indexers | Yes | Optional | Not needed when using a Heavy Forwarder
| Heavy Forwarder | Yes | Optional

### Data Inputs

See [Splunk Integration with Jamf Protect](https://learn.jamf.com/bundle/jamf-protect-documentation/page/Splunk_Integration.html) to learn more how to configure Jamf Protect to send events to Splunk. 

The Jamf Protect Add-on expects an initial source type of:

- Jamf Protect Alerts & Unified Logs: `jamf:protect:alerts`
- Jamf Protect Telemetry V2: `jamf:protect:telemetry:v2`
- Jamf Protect Telemetry: `jamf:protect:telemetry`
- Jamf Security Cloud: `jamf:protect:web`
    - Threat Events Stream 
    - Network Traffic Stream

For compatibility with existing Splunk objects such as source types, field names, and similar you may need to make a search time rename for the Jamf Splunk object. To do this, follow these steps:

#### Splunk Cloud

**Jamf Protect Alerts** 
- Click **Settings** &rarr; **Source types**
- “Find your current conflicting source type
    - Click **Edit**
    - Click **Advanced**
    - Click **New setting**
        - **Name:** rename
        - **Value:** `jamf:protect:alerts`

**Jamf Protect Telemetry** 
- Click **Settings** &rarr; **Source types**
- “Find your current conflicting source type
    - Click **Edit**
    - Click **Advanced**
    - Click **New setting**
        - **Name:** rename
        - **Value:** `jamf:protect:telemetry`

**Jamf Security Cloud** 
- Click **Settings** &rarr; **Source types**
- “Find your current conflicting source type
    - Click **Edit**
    - Click **Advanced**
    - Click **New setting**
        - **Name:** rename
        - **Value:** `jamf:protect:web`

#### Splunk On Premises
Copy the top line from the text chunk in [ ] you want to modify from `default/props.conf` to `local/props.conf` and set the appropriate original source type. 

Example:

    ###
    [EXISTING-SOURCETYPE]
    rename = jamf:protect:alerts

This will not change your data, it will only allow you to use the search time extractions from this app with your existing source type. PLEASE make sure that your new data is using the source types of `jamf:protect:alerts`,`jamf:protect:telemetry`, or `jamf:protect:web`, depending on your Jamf Protect deployment, for best compatibility with the addon.

### <a id="eventtype"></a>Event Type Modification

For Jamf Protect Alerts and Jamf Protect Web the base event types _must_ be updated, so the correct index value is set. This is not necessary for the Telemetry event types. Follow these steps:

**Splunk Cloud**
- Click **Settings** &rarr; **Event types**
- App &rarr; **Jamf Protect (TA-JamfProtect)**
    - Click **jamf_protect**
        - **Search String**: `index="CORRECTINDEX" sourcetype="jamf:protect:alerts"`
        - Click **Save**
    - Click **jamf_protect_web**
        - **Search String**: `index="CORRECTINDEX" sourcetype="jamf:protect:web"`
        - Click **Save**

**Splunk On Premises**
Copy the setting below from `default/eventtypes.conf` to `local/eventtypes.conf`. Replace `index=*` with the index your `jamf:protect` data is in.

Example: 

    [jamf_protect]
    search = index=CORRECTINDEX sourcetype="jamf:protect:alerts"

    [jamf_protect_web]
    search = index=CORRECTINDEX sourcetype="jamf:protect:web"

> **Important**
> The index _must_ also be updated within the Telemetry Lookup Workflow Action before it can be used.

### Data Models 

The Jamf Protect Add-on requires the [Splunk Common Information Model](https://splunkbase.splunk.com/app/1621) be installed. Once in place, ensure the data models are accelerated and have been updated to support the indexes for Jamf Protect data.

The following CIM Data Models are supported by this Add-on:

**Jamf Protect Alerts**
- Alerts
- Intrusion Detection
- Malware

**Jamf Protect Telemetry V2**
- Authentication
- Change
- Endpoint
- Intrusion Detection
- Network Sessions
- Network Traffic (BETA)
- Malware

**Jamf Protect Telemetry**
- Application State
- Authentication
- Change
- Compute Inventory
- Endpoint
- Intrusion Detection
- Network Sessions
- Network Traffic
- Performance
- Vulnerabilities

**Jamf Security Cloud**
- Intrusion Detection
- Malware
- Network Resolution (DNS)
- Network Traffic