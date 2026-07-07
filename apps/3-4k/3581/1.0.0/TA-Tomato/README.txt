####
## TA-Tomato
## v 1.0.0
## 8/13/2018
## Dan Potter
## @dpotter on slack
####
This app was built for analyzing data from open firmware and open firmware compatible routers, such as Tomato, dd-wrt, Open-WRT, Merlin, Asus, Advanced Tomato, Tomato USB, etc.
The DNS component is also 100% compatible with piHole and other dnsmasq based logs for DHCP/dns.

No support is assumed or provided beyond this README. Please be sure to set the correct onboard sourcetype (tomato) and see other instructions below and consult documentation on your device and firmware if you experience trouble getting the logs.

Due to the vast number of devices, firmware builds, firmware maintainers, and other variables, this app may need tweaking to support your device.  I've tried to develop this to be as moduler as possible, with my current skillset in developing apps.  I have tested this on 3 modern firmwares, Tomato, Advanced Tomato, and 3 different builds of DD-wrt and to my knowledge have those mostly supported for everything currently available in the Dashboard.  However there are plenty of features you may be using which are not currentlyl developed any further than basic extractions.  You have new sourcetype work completed or dashboards to contribute please reach out on Slack.  Suggestions or improvements are also welcome.

***Please onboard your data as sourcetype=tomato. This will sub-sourcetype to various components with their own logic for extractions, event types, dashboards, etc.

**Previous versions of this app required you to onboard data as sourcetype=syslog1 and references to this have been removed. If you do not update your input sourcetype other components may break

This app also assumes your data will exist in index=tomato. If it does not, you will need to update 2 variables.
Settings > macros > tomato_index (index=tomato)
Settings > eventtypes > tomato (index=tomato)

Finally, some of the dashboards were built against datamodels. You must have SA-CIM installed to leverage those dashboards, which use the Network Traffic, Data Model for your netfilter firewall data.

####
## Enable Syslog
## The exact process will differ from device to device.
## Advanced Tomato > Administration > Logging > Host or IP/Port
## DD-wrt > Services > System Log > Syslogd > Remote Server > IPAddress:Port
####
## Enable firewall traffic logs (Network Traffic)
## *Warning* high log levels can cause memory issues with older or less capable devices. Settings below are for highest visibility.
##		Apply accordingly.
## Some dd-wrt builds also require you to enable 
## Logging > Connection Logging > Inbound (Both), Outbound (Both)
## Security > Firewall > Log Management > Enable > Log Level (High) / Dropped (Enabled), Rejected (Enabled), Accepted (Enabled)
####
## Network Resolution (DNS) / Network Sessions (DHCP) Logging - Requires the use of dnsmasq
## Add the following to your advanced dnsmasq config. This will allow us to build CIM compliant DNS information
## 		log-queries=extra
## To ensure all dns queries pass through your router, you should also enable the following settings:
## Use Internal DNS, Use received DNS with user-entered DNS, Intercept DNS port
####
## You may need to enable additional logging options for other system components
####

