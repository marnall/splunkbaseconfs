"""The module is used to interact with citrusleaf.py.It act as a
middleware for splunk app"""

import citrusleaf as cl
import constant
import utils


def return_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            args[0].alive = False
            return e
    return wrapper


@return_exceptions
def get_cluster_nodes(seed_node, port=constant.PORT):

    """The method returns dictionary of node 'id:ip'for all the
    connected nodes to a given seed node"""

    services = cl.citrusleaf_info(seed_node, port, "services")
    service = cl.citrusleaf_info(seed_node, port, "service")
    node_list = {}
    if services == -1 or service == -1:
        return node_list
    else:
        nodes = utils.text_to_list(services)
        nodes.append(service.split(";")[0])  # multiple_interfaces_on_node
        for node_address in nodes:
            ip, port = node_address.split(":")
            node_id = cl.citrusleaf_info(ip, port, "node")
            if node_id is not None and node_id != -1:
                node_list[node_id] = node_address
        return node_list


@return_exceptions
def get_nodes(seed_node, port=constant.PORT):

    """The method returns list all the connected nodes to a given seed node"""

    services = cl.citrusleaf_info(seed_node, port, "services")
    service = cl.citrusleaf_info(seed_node, port, "service")
    node_list = []
    if services == -1 or service == -1:
        return node_list
    else:
        nodes = utils.text_to_list(services)
        nodes.append(service.split(";")[0])  # multiple_interfaces_on_node
        for node_address in nodes:
            ip, port = node_address.split(":")
            node_id = cl.citrusleaf_info(ip, port, "node")
            if node_id != -1:
                node_list.append(ip)
        return node_list


@return_exceptions
def get_namespace_stat(ip, namespace, port=constant.PORT):

    """The method return the namespace statistics of a sngle node (i.e ip)"""

    info = cl.citrusleaf_info(ip, port, "namespace/" + namespace)
    if info == -1:
        return -1
    info = str(info)
    statistic = utils.text_to_dict(info)
    return statistic


@return_exceptions
def get_nodes_stat(ip, port=constant.PORT):

    """The method return the whole statistics
    of a node(i.e ip)"""

    info = cl.citrusleaf_info(ip, port, "statistics")
    if info == -1:
        return -1
    info = str(info)
    statistic = utils.text_to_dict(info)
    return statistic


@return_exceptions
def get_namespaces(ip, port=constant.PORT):

    """The method returns all the namespaces present on that node(i.e ip)"""

    namespaces = cl.citrusleaf_info(ip, port, "namespaces")
    if namespaces == -1:
        return -1
    return utils.text_to_list(namespaces)


@return_exceptions
def get_latency(ip, chart, port=constant.PORT):

    """The method is used to get latency hist of a given node"""
    info = cl.citrusleaf_info(ip, port, "latency:hist=" + chart)
    if info == -1:
        return -1
    info = str(info)
    latency = info.split(";")
    if latency[1] is not None:
        latency1 = latency[1].split(",")
        return {"Latency_Name": chart,
        "time": latency1[0],
        "0-1ms": latency1[1],
        "1-8ms": latency1[2],
        "8-64ms": latency1[3],
        ">64ms": latency1[4]
        }

    return -1


@return_exceptions
def get_cluster_namespace_stat(node_list, namespace):

    """The method used to get namespace statistics for a hole cluster"""

    stat = {}
    master_objects = 0
    replica_objects = 0
    total_memory = 0.0
    used_memory = 0.0
    expired_object = 0
    evicted_object = 0
    node_index = 0
    while node_index < len(node_list):
        cur_ip = node_list[node_index]
        node_index = node_index + 1
        info = get_namespace_stat(cur_ip, namespace)
        if info == -1:
            continue
        master_objects += int(info["master-objects"])
        replica_objects += int(info["prole-objects"])
        total_memory += int(info["memory-size"])
        used_memory += int(info["used-bytes-memory"])
        expired_object += int(info["expired-objects"])
        evicted_object += int(info["evicted-objects"])
        ripple = info["repl-factor"]
    stat["objects"] = master_objects + replica_objects
    stat["master-objects"] = master_objects
    stat["prole-objects"] = replica_objects
    stat["memory-size"] = total_memory
    stat["used-bytes-memory"] = used_memory
    stat["expired-objects"] = expired_object
    stat["evicted-objects"] = evicted_object
    stat["repl-factor"] = ripple
    return stat
