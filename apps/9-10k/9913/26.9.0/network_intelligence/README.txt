Network Intelligence 26.9.0
===========================

Network Intelligence provides a vendor-neutral view of network topology,
health, and alerts in Splunk. It normalizes data collected by supported Cisco
product add-ons and presents that data through the Network Intelligence user
interface and REST APIs.

Release notes
-------------

Network Intelligence 26.9.0 is the initial release of the application.

Highlights include:

* Site, device, interface, and discovered-neighbor inventory.
* Layer 2 topology visualization and entity drill-down workflows.
* Current and historical health metrics for supported capabilities.
* Normalized alert views for supported data sources.
* Support for Cisco Catalyst Center, Cisco Meraki, and Cisco ThousandEyes data.

Data collection
---------------

Network Intelligence does not collect controller credentials directly. Install
and configure the supported Cisco product add-ons separately, then configure
their inputs to send data to the catalyst, meraki, and thousandeyes indexes as
appropriate. Network Intelligence derives its graph, health, and alert data
from those indexed events and stores materialized state in Splunk KV Store or
KV Service.

Current data-source integrations use these add-on versions or later:

* Cisco Enterprise Networking Add-on for Splunk 4.0.35
* Cisco Meraki Add-on for Splunk 3.5.0
* Cisco ThousandEyes App for Splunk 0.9.0
