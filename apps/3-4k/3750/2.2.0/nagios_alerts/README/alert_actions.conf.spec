[nagios_alerts]

# nagios master settings

param.alert_destination = <string>
* "livestatus" | "gearman"

param.escape_backslashes = 0 | 1
* escape backslashes for nagios, don't escape backslashes for OMD

param.gearman_key = <string>
* encryption key for gearman

param.gearman_path = <string>
* full path to send_gearman e.g. /usr/lib/nagios/plugins/send_gearman

param.gearman_port = <string>
* gearmand port number. defaults to 4730.

param.livestatus_port = <integer>
* livestatus port number. defaults to 6557.

param.nagios_hostname = <string>
* nagios master hostname.

# nagios alert settings

param.description = <string>
* description for nagios alert.

param.hostname = <string>
* hostname for nagios alert.

param.servicename = <string>
* servicename for nagios alert.

param.status = 0 | 1 | 2 | 3
* status. 0,1,2,3 for ok, warning, critical, unknown.

# other settings

param.sendresults = 0 | 1
* should we append the search results to the description?