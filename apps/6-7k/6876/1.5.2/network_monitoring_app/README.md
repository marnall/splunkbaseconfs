### About

This application contains dashboards for self-service analysis of network logs.

### Installation

The application is meant to be installed on the Splunk search heads where you want to use the network dashboards. The dashboards utilizes the Network Traffic datamodel and macro from the Splunk Common Information Model (CIM), so installing and configuring the CIM application is a good idea, including defining the macro for the Network Traffic datamodel. Some of the panels also use the Splunk Sankey Diagram, so that should be installed as well.

### Configuration

- Change the permission of the application to your needs.
- Add the appropriate indexes to the macro `cim_Network_Traffic_indexes` in the Splunk Common Information Model (CIM).
- Make sure you have logs in the Network Traffic datamodel, from the Splunk Common Information Model (CIM).
- Run the saved search "Network Indexes Lookup Gen" to generate a network index lookup.
- Change the static indexes in the index dropdowns on the dashboards, if needed.
- Change the static actions in the firewall action dropdowns on the dashboards, if needed.

Note that not all these steps are required for the application to work. If not all steps are done properly some panels or filters in some dashboards might not work as intended.
