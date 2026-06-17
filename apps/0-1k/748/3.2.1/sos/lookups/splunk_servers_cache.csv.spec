# This file describes the different fields in the splunk_servers_cache.csv
# lookup table, to which rows can be manually added to enable the S.o.S app to
# be aware of Splunk instances not accessible by means of distributed search
# (and therefore, not auto-discovered). Splunk instances manually added to this
# file will, for example, become listed in the "Instance to query" pull-down menu
# that can be found in most S.o.S views.

########
# Description of the fields present in $SPLUNK_HOME/etc/apps/sos/splunk_servers_cache.csv
########

sos_server
* Describes the value of the "host" field that a Splunk instance uses to tag
  events it writes to the "_internal" or "_audit" indexes.
* The S.o.S app determines this value for the instances that it auto-discovers
  by checking the value of "host" set in inputs.conf for file input stanza
  "[monitor://$SPLUNK_HOME/var/log/splunk]". This is done with the
  "get_splunk_servers" search macro, which is executed every 15 minutes by
  scheduled search "sos_refresh_splunk_servers_cache" and which is the primary
  maintainer of this lookup table.
* To determine the correct value of "sos_server" for a given Splunk instance
  that you want to add manually to this file, manually search for events that
  this instance writes to the "_internal" index and get the value of the "host"
  field. 
* Alternatively, you can use the btool command to achieve this goal:
  $SPLUNK_HOME/bin/splunk cmd btool inputs list 'monitor://$SPLUNK_HOME/var/log/splunk' | grep host

server_role
* Describes the role of the instance in the context of the Splunk topology.
* Just like "sos_server", this is also determined for auto-discovered instances
  by the "get_splunk_servers" search macro executed by scheduled search
  "sos_refresh_servers_cache".
* When adding an instance manually to the lookup table, set "server_role" to
  whichever of the following strings describes its role best:
  * "stand-alone indexer"
  * "search-head"
  * "search peer"
  * "forwarder"

server_label
* Internal use only. Do not modify or set.
* This field is calculated by appending and formatting the "sos_server" and
  "server_role" fields.
* It is updated every 15 minutes by scheduled search "sos_refresh_servers_cache".
* It is used almost exclusively to label the entries in the "Instance to query"
  pull-down menu.

sort_rank
* Internal use only. Do not modify or set.
* This field is calculated based on the value of the "server_role" field.
* It is updated every 15 minutes by scheduled search "sos_refresh_servers_cache".
* It is used almost exclusively to sort the entries in the "Instance to query"
  pull-down menu.

_time
* Internal use only. Do not modify or set.
* This field is calculated based on the last time that we were able to gather
  information from the corresponding asset.
* It can be used to answer the question "When is the last time we heard from or
  were we able to contact this Splunk instance?"


########
# Example of manual addition of a Splunk instance record
########

We want to manually add records for two Splunk instances to this lookup table:
* A search-head, which tags its "_internal" events with host="sosdev-sh2"
* A forwarder, which tags its "_internal" events with host="sosdev-fwd18"

Here are the two entries we will append to splunk_servers_cache.csv:
"sosdev-sh2","search-head"
"sosdev-fwd18","forwarder"

It's that simple! Next time the "sos_refresh_servers_cache" scheduled search
runs (15 minutes or less) it will compute the other fields of the lookup from
the values manually populated.
