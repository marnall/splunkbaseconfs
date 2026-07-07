## Databl Windows DHCP App

This app collects DHCP Statistics on Scopes. It has settings to also collect DHCP logs, these are also in the Splunk DHCP app, you can activate them here or there. There are also dashboards and event tagging to see details on the event logs.

The purpose of monitoring scopes is to be be then be able to alert if one is filling up, so if utilization goes above a threshold you can fix it before user impacts.

### Installation

#### Search Heads

Install the App on Search Heads to use the dashboards and interpret data. 
Set the macro search to the index you are sending you DHCP logs to.

Update the macro **dhcp_index** to point to your chosen index.

#### Universal Forwarders

Install the App on the DHCP server itself. On this server you also need to enable collection.
Create a \local directory, and copy over the inputs.conf from default. Set the frequency to what you want, and enable the inputs for Scope Properties, and Scope Utilization on IPV4 and or IPV6 depending on what you need.

Once the data is flowing you should see it in the dashboards

Change disabled=0 to enable the collection, set the index to your environment index.

```
## Below stanza collect DHCP IPv4 Scope properties
[powershell://DHCP_Collect_scope]
index=windows
sourcetype=dhcpScope:properties
script = ."$SplunkHome\etc\apps\Databl_windows_dhcp\bin\powershell\dhcp_scope_properties.ps1"
schedule = 3600
disabled = 0
```

### Field Extractions Acknowledgements

Field extractions are based on previous work in another DHCP app - https://splunkbase.splunk.com/app/4359