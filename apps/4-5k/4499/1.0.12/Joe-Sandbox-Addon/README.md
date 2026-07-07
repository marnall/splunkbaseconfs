# Joe Sandbox Splunk Addon Readme
This plugin downloads json reports into Splunk from a defined Joe Sandbox API endpoint.

## Installation & Setup

1. Download .tgz package
2. Go to Splunk Home > Manage Apps (Apps Cog Icon) > Install app from File > Upload the downloaded File
3. Go to Apps > Joe Sandbox Addon > Inputs > Create New Input
4. Enter Name, Interval, Index, API URL, API KEY, Minimum Report ID and click Add
5. Go to Search and search and Enter `sourcetype=jbx` to see downloaded reports.

## Search command Examples:

### search for dropped file
```
sourcetype=jbx |  search "droppedinfo.hash.@file"="*.bat"
```

### search for md5 hash
```
sourcetype=jbx | search "fileinfo.md5"=3ded354a984ade951e0105d0c3aef347

sourcetype=jbx | search "info.md5"=3ded354a984ade951e0105d0c3aef347
```

### search for destination IP
```
sourcetype=jbx | search "ipinfo.ip{}.@ip"="192.168.1.13"

# Network TCP
sourcetype=jbx "behavior.network.tcp.packet.dstip"="192.168.1.13"

# Network UDP
sourcetype=jbx "behavior.network.udp.packet{}.dstip"="8.8.8.8"
```

### search for URL
```
sourcetype=jbx | search "urlinfo.url{}.@name"="http://www.typography.net"
```

## Visualize Reports
To visualize analysis score over time enter the following line in the search field and click visualize
```
sourcetype=jbx | spath "signaturedetections.strategy{1}.score" | timechart span=1s values("signaturedetections.strategy{1}.score") as Score
```

To visualize analysis detection  over time enter the following line in the search field and click visualize
```
sourcetype=jbx | spath "signaturedetections.strategy{1}.detection"  | timechart span=1s count by "signaturedetections.strategy{1}.detection"
```

## Troubleshooting
The addon saves report Ids that have been downloaded in the Splunk KV Store if in anycase you wanna reset the KV Store you can do so by executing the following command (this may require admin/super user rights):
```
splunk clean kvstore -app Joe-Sandbox-Addon -collection Joe_Sandbox_Addon_checkpointer

```