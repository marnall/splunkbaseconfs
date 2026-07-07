# nagios_alerts

nagios_alerts provides a modular alert that notifies Livestatus or Gearman when an alert is fired.

## Parameters

The following parameters are available in the edit alert UI for each alert. Defaults can be set in alert_actions.conf.

* alert_destination - livestatus or gearman
* escape_backslashes - escape backslashes in description - depending on version of nagios or OMD you may or may not need this.
* gearman_key - encryption key for gearman. ignored if alert_destination = livestatus
* gearman_path - full path to send_gearman executable. ignored if alert_destination = livestatus
* gearman_port - port for gearmand on the nagios server. default to 4730.
* livestatus_port - port for livestatus on the nagios server. defaults to 6557.
* nagios_hostname - server that livestatus or gearmand is running on.

* description - Maps to "status information" on the Nagios side.
* hostname - must match a host configured in Nagios.
* servicename - must match the service_description of a service configured in Nagios.
* status - 0,1,2,3 for OK, WARNING, CRITICAL, UNKNOWN.
* sendresults - If true, append results to the description.

## Deployment

* Deploy to search heads that have alerts that should notify Nagios instances.
* If using gearman alert_destination, make sure send_gearman is installed and set gearman_path parameter accordingly.
  On debian you can install mod-gearman-worker from the Consul Labs repo, see https://labs.consol.de/repo/stable/

## Acknowledgements

* Splunk Cloud SRE
* Erik Larkin
* Russell Uman