#*******
# GENERAL SETTINGS:
# The following attribute/value pairs are valid for all pinger stanzas.
# You must first enter a stanza header in square brackets, specifying a unique identifier for
# the input. See further down in this file for examples. Unless otherwise specified, an attribute
# may not be used in the [default] stanza.
#*******

location = <string>
* Defines the location of this pinger.  Multiple pingers may be set up in multiple locations
* to provide redundant monitoring of web resources
* May be set in the [default] stanza
* Defaults to "Default"

prod = <boolean>
* Defines whether or not a resource is considered production for reporting
* May be set in the [default] stanza
* Defaults to true

external = <boolean>
* Defines whether or not a resource is considered external for reporting
* May be set in the [default] stanza
* Defaults to true

timeout = <integer>
* Timeout in seconds for the connection
* Should be less frequent than the script run interval
* May be used in the [default] stanza
* Defaults to 2

label = <string>
* Defines the ping monitor label for human-friendly searching.
* If not set, defaults to host

host = <string>
* Hostname to which the pinger should connect.  May be either DNS (i.e. www.splunk.com) or IPv4 address.
* Required.   The pinger will skip all stanzas except [default] for which the host attribute is not specified.

port = <integer>
* Specifies the port to which the pinger should connect.  If not set defaults to 80 (http) or 443 (https)

resource = <string>
* Specifies the resource to request from the specified host.  If not specified, defaults to /.

lookupdns = <boolean>
* Specifies whether or not Pinger should monitor DNS resolution.  Defaults to false

username = <string>
* If set, attempts HTTP Basic Authentication using the value of the username and password attributes. Both attributes
* (username and password) must be set to attempt HTTP Basic Authentication

password = <string>
* See "username" above

ssl = <bool>
* Connect using https instead of http.  Defaults to false.
