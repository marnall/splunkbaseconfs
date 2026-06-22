# =============================================================================
# xPi-Hole Configuration Specification File
# =============================================================================
# This file describes the settings available in xpihole.conf
# =============================================================================

[logging]
index = <string>
* The Splunk index where Pi-Hole logs are stored.
* Default: main

sourcetype_log = <string>
* Sourcetype for the main Pi-Hole DNS query log (pihole.log).
* Default: pihole:log

sourcetype_ftl = <string>
* Sourcetype for the Pi-Hole FTL daemon log (pihole-FTL.log).
* Default: pihole:ftl

sourcetype_gravity = <string>
* Sourcetype for the Gravity update log.
* Default: pihole:updateGravity

sourcetype_web = <string>
* Sourcetype for the Pi-Hole web interface access log.
* Default: pihole:web
