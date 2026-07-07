# Configuration spec for apl_logging.conf
# This file configures logging levels for ZTAP app components

[<stanza_name>]
* Each stanza represents a component of the ZTAP app

modularinput = <string>
* Log level for modular input components
* Valid values: DEBUG, INFO, WARN, ERROR, CRITICAL
* Default: INFO

restclient = <string>
* Log level for REST client operations
* Valid values: DEBUG, INFO, WARN, ERROR, CRITICAL
* Default: INFO

utilities = <string>
* Log level for utility functions
* Valid values: DEBUG, INFO, WARN, ERROR, CRITICAL
* Default: INFO

kenny_loggins = <string>
* Log level for Kenny Loggins logging module
* Valid values: DEBUG, INFO, WARN, ERROR, CRITICAL
* Default: WARN

ataportal = <string>
* Log level for ATA Portal integration
* Valid values: DEBUG, INFO, WARN, ERROR, CRITICAL
* Default: WARN
