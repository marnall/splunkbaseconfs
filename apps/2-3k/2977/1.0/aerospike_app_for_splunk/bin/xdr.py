"""The moule is used to get all statistics of cross data center
replication replication(XDR)"""
# $SPLUNK_HOME/etc/apps/myaerospike/bin/latency.py
import sys
from splunklib.modularinput import *
from splunklib.modularinput.event_writer import EventWriter
import citrusleaf as cl
#from aerospike import MyScript
import controller
import constant
import utils


def get_scheme():

    """The method creates xml schema for modular input"""

    scheme = Scheme("Aerospike")
    scheme.description = "Events containing statistics of Aerospike node"
    scheme.use_external_validation = False
    scheme.use_single_instance = False

    name_argument = Argument("name")
    name_argument.data_type = Argument.data_type_string
    name_argument.description = "Name/IP Address of a node"
    name_argument.required_on_create = True
    scheme.add_argument(name_argument)
    return scheme


def stream_events():

    """The method used for get all XDR stat of all connected nodes
    and create a event and write that event to the splunk server"""

    node = utils.get_seed_node()

    if node == "-1":
        print "Error"
        return

    seed_node = node.strip()
    nodes = controller.get_nodes(seed_node)

    if nodes == -1:
        print "Error"
        return

    node_index = 0

    while node_index < len(nodes):
        cur_ip = nodes[node_index]
        node_index = node_index + 1

        statistic = cl.citrusleaf_info(cur_ip, 3004, "statistics")
        if statistic == -1:
            info = cl.citrusleaf_info(cur_ip, constant.PORT, "statistics")
            if info != -1:
                print "\n"

                event = Event()
                event.stanza = cur_ip
                event.data = "Status=Inactive,"
                EventWriter().write_event(event)
            continue
        print "\n"
        event = Event()
        event.stanza = cur_ip
        event.data = "Status=Active," + str(statistic) + ","
        EventWriter().write_event(event)


if __name__ == "__main__":

    args = sys.argv
    if len(args) != 1:
        sys.exit()
    else:
        stream_events()
    sys.exit()
