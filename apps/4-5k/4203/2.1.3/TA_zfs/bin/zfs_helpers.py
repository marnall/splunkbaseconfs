import sys
import xml.dom.minidom, xml.sax.saxutils
import subprocess
import logging

# set up logging suitable for splunkd consumption
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(formatter)
logging.root.addHandler(handler)


# empty arg validation
def validate_args():
    pass


# read XML configuration passed from splunkd
def get_config():
    try:
        config = {}
        # read everything from stdin
        config_str = sys.stdin.read()

        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            logging.debug("XML: found configuration")
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    logging.debug("XML: found stanza " + stanza_name)
                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        logging.debug("XML: found param '%s'" % param_name)
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            logging.debug("XML: '%s' -> '%s'" %
                                          (param_name, data))
        if not config:
            raise Exception("Invalid configuration received from Splunk.")

    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: '%s'" % str(
            e)

    return config


def get_pools():
    try:
        pools_cmd = ['zpool', 'list', '-H', '-o', 'name']
        all_pools = subprocess.Popen(
            pools_cmd, stdout=subprocess.PIPE).stdout.readlines()
        all_pools = [s.rstrip() for s in all_pools]
        # get the args from stdio
        config = get_config()
        zpool_list = config["zpool_list"].split()
        # if 'ALL__POOLS' is passed, inspect all zfs pools
        if 'ALL__POOLS' in zpool_list:
            logging.debug("using all_pools as pool list")
            logging.debug("all_pools is set to '%s'" % all_pools)
            pools_out = all_pools
        else:
            pools_out = zpool_list
            logging.debug("using '%s' as pool list" % zpool_list)
            for pool_test in pools_out:
                if pool_test not in all_pools:
                    sys.exit("zpool '%s' is not a valid pool on this host" %
                             pool_test)

        return pools_out

    except Exception, e:
        raise Exception, "Error performing get_pools: '%s'" % str(e)
