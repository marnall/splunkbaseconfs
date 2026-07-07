
"""The module is used to get statistics from aerospike node,
analyse that stat and extract important stat from that all stat.
Create event of that extracted stat and write that event to
splunk server.
It use Modular Input concept of splunk for sending data to splunk"""

# $SPLUNK_HOME/etc/apps/myaerospike/bin/aerospike.py
import sys
import controller
from splunklib.modularinput import *
from splunklib.modularinput.event_writer import EventWriter
import citrusleaf as cl
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

    """The method used for get all stat of all connected nodes
    and the stat of hole cluster and analyse it.after that it
    create a event and write that event to the splunk server"""

    node = utils.get_seed_node()
    if node == "-1":
        return
    seed_node = node.strip()
    nodes1 = controller.get_nodes(seed_node)
    prev_nodes = utils.get_previous_node_list()
    if nodes1 == -1:
        return
    build1 = []
    build1.append(cl.citrusleaf_info(seed_node, constant.PORT, "build"))
    read_req = 0
    read_sucess = 0
    write_req = 0
    write_sucess = 0
    total_disk = 0
    used_disk = 0
    total_memory = 0
    used_memory = 0
    node_index = 0
    max_ns = 0

    while node_index < len(nodes1):
        cur_ip = nodes1[node_index]
        node_index = node_index + 1
        statistic = controller.get_nodes_stat(cur_ip)
        if statistic == -1:
            continue
        if seed_node in prev_nodes:
            if cur_ip not in prev_nodes:
                status = "Up"
            else:
                status = "Running"
        else:
            status = "Running"
        build = cl.citrusleaf_info(cur_ip, constant.PORT, "build")
        if build not in build1:
            build1.append(build)

        total_ns = controller.get_namespaces(cur_ip)
        if len(total_ns) > max_ns:
            max_ns = len(total_ns)
        read_req += int(statistic["stat_read_reqs"])
        read_sucess += int(statistic["stat_read_success"])
        write_req += int(statistic["stat_write_reqs"])
        write_sucess += int(statistic["stat_write_success"])
        total_disk += float(utils.bytes_to_gb(statistic["total-bytes-disk"]))
        used_disk += float(utils.bytes_to_gb(statistic["used-bytes-disk"]))
        cluster_size = str(statistic["cluster_size"])
        total_memory += float(utils.bytes_to_gb(statistic["total-bytes-memory"]))
        used_memory += float(utils.bytes_to_gb(statistic["used-bytes-memory"]))

        disk = float(utils.bytes_to_gb(statistic["total-bytes-disk"]))

        event = Event()
        event.stanza = cur_ip
        #event_data = '';
        #event_data += "Status =" + status
        #event_data += ",Total_read_request =" + statistic["stat_read_reqs"]

        event.data = "Status =" + status + ",Total_read_request =" \
        + statistic["stat_read_reqs"]\
        + ",Total_read_success =" + statistic["stat_read_success"]\
        + ",Total_write_request =" + statistic["stat_write_reqs"]\
        + ",Total_write_success =" + statistic["stat_write_success"]\
        + ",Namespaces =" + str(len(total_ns))\
        + ",Cluster_size=" + cluster_size\
        + ",Build_version=" + build\
        + ",Total-bytes-disk=" + str(disk)\
        + ",Used-bytes-disk=" \
        + utils.bytes_to_gb(statistic["used-bytes-disk"])\
        + ",Total-GB-memory="\
        + utils.bytes_to_gb(statistic["total-bytes-memory"])\
        + ",Used-GB-memory="\
        + utils.bytes_to_gb(statistic["used-bytes-memory"])\
        + ","
        EventWriter().write_event(event)
        print "\n"
    version = ""

    for record in build1:
        if record != -1:
            version = version + record + " "
    event = Event()
    event.stanza = "cluster"
    event.data = "Total_read_request =" + str(read_req)\
      + ",Total_read_success =" + str(read_sucess)\
      + ",Total_write_request =" + str(write_req)\
      + ",Total_write_success =" + str(write_sucess)\
      + ",Namespaces =" + str(max_ns)\
      + ",Cluster_size=" + cluster_size\
      + ",Build_version=" + version\
      + ",Total-bytes-disk=" + str(round(total_disk, 3))\
      + ",Used-bytes-disk=" + str(round(used_disk, 3))\
      + ",Total-GB-memory=" + str(total_memory)\
      + ",Used-GB-memory=" + str(used_memory)\
      + ","
    EventWriter().write_event(event)

    if seed_node in prev_nodes:
        for ip in prev_nodes:
            if ip not in nodes1:
                print "\n"
                event = Event()
                event.stanza = ip
                event.data = "Status = Down,"
                EventWriter().write_event(event)
    total_ns = controller.get_namespaces(seed_node)
    utils.write_new_node_list(nodes1)
    index = 0
    while index < len(total_ns):
        info = controller.get_cluster_namespace_stat(nodes1, total_ns[index])
        print "\n"
        event = Event()
        event.stanza = "Namespace"
        event.data = "Namespace_name =" + total_ns[index]\
          + ",No_of_objects =" + str(info["objects"])\
          + ",Master_objects =" + str(info["master-objects"])\
          + ",Replica_objects =" + str(info["prole-objects"])\
          + ",Total_memory ="\
          + utils.bytes_to_gb(info["memory-size"])\
          + ",Used_memory="\
          + utils.bytes_to_gb(info["used-bytes-memory"])\
          + ",Ripple_factor=" + str(info["repl-factor"])\
          + ",Expired_object=" + str(info["expired-objects"])\
          + ",Evicted_object=" + str(info["evicted-objects"]) + ","
        EventWriter().write_event(event)
        index = index + 1


if __name__ == "__main__":

    args = sys.argv
    if len(args) != 1:
        sys.exit()
    else:
        stream_events()
    sys.exit()
