"""The module is used to get latency related statistics of all
node connected to the aerospike cluster """

# $SPLUNK_HOME/etc/apps/myaerospike/bin/latency.py
import sys
from splunklib.modularinput import *
from splunklib.modularinput.event_writer import EventWriter
import controller
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

    """The method used for get all latency stat of all connected nodes
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
    charts = ["writes", "reads", "proxy", "udf", "query"]
    while node_index < len(nodes):
        cur_ip = nodes[node_index]
        node_index = node_index + 1
        chart_index = 0
        while chart_index < len(charts):
            chart_name = charts[chart_index]
            chart_index = chart_index + 1
            latency = controller.get_latency(cur_ip, chart_name)
            if latency == -1:
                continue
            print "\n"
            event = Event()
            event.stanza = cur_ip
            event.data = "chart_name =" + latency["Latency_Name"]\
              + ";Time=" + latency["time"] + ";t0-1ms=" + latency["0-1ms"]\
              + ";t1-8ms=" + latency["1-8ms"] \
              + ";t8-64ms=" + latency["8-64ms"]\
              + ";t64ms=" + latency[">64ms"] + ";"

            EventWriter().write_event(event)

if __name__ == "__main__":

    args = sys.argv
    if len(args) != 1:
        sys.exit()
    else:
        stream_events()
    sys.exit()
