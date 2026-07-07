#!/usr/bin/env python2.7
""" dummy place holder modular input to enable Splunk Web config """
__author__ = 'Michael Uschmann / MuS'
__date__ = 'Copyright $Aug 25, 2017 7:48:46 PM$'
__version__ = '1.2.4'

import sys
import splunk.Intersplunk
import logging
import logging.handlers
import xml.dom.minidom
import xml.sax.saxutils

""" do we want debug output into splunkd.log? """
""" search with 'index=_internal  sourcetype=splunkd component=ExecProcessor' """
#myDebug = 'yes'
myDebug = 'no'

""" set up logging """
logging.root
logging.root.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s %(message)s')
""" with zero args , should go to STD ERR """
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

SCHEME = """<scheme>
    <title>GET</title>
    <description>Configure server to be used with the GET command</description>

    <endpoint>
        <args>
            <arg name="name">
                <title>Stanza name:</title>
                <description>The name of the modular input</description>
            </arg>
            <arg name="server">
                <title>Server name:</title>
                <description>The URL we use to get data</description>
            </arg>
            <arg name="token">
                <title>API token:</title>
                <description>Provide your API token to access the data</description>
            </arg>
            <arg name="debug">
                <title>Debug:</title>
                <description>Enable or disable debugging</description>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def do_scheme():
    """ show a different setup screen """
    print SCHEME

def validate_arguments():
    """ we don't do any validation - yet """
    pass

def get_config():
    """ read XML configuration passed from splunkd """
    config = {}

    try:
        """ read everything from stdin """
        config_str = sys.stdin.read()

        """ parse the config XML """
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        conf_node = root.getElementsByTagName('configuration')[0]
        if conf_node:
            if myDebug == 'yes' : logging.info('XML: found configuration')
            stanza = conf_node.getElementsByTagName('stanza')[0]
            if stanza:
                stanza_name = stanza.getAttribute('name')
                if stanza_name:
                    if myDebug == 'yes' : logging.info('XML: found stanza ' + stanza_name)
                    config['name'] = stanza_name

                    params = stanza.getElementsByTagName('param')
                    for param in params:
                        param_name = param.getAttribute('name')
                        if myDebug == 'yes' : logging.info('XML: found param %s' % param_name)
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            if myDebug == 'yes' : logging.info('XML: %s -> %s' % (param_name, data))

        checkpnt_node = root.getElementsByTagName('checkpoint_dir')[0]
        if checkpnt_node and checkpnt_node.firstChild and \
           checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config['checkpoint_dir'] = checkpnt_node.firstChild.data

        if not config:
            raise Exception, 'Invalid configuration received from Splunk.'
            logging.error('Error getting Splunk configuration via STDIN: %s' % str(e))

    except Exception, e:
        raise Exception, 'Error getting Splunk configuration via STDIN: %s' % str(e)
        logging.error('Error getting Splunk configuration via STDIN: %s' % str(e))

    return config

def run_main():
    """ get the config """
    config = get_config()

    # now we get data
    try: # lets do it
        if myDebug == 'yes': logging.info( 'getting data ...' )

    except Exception, e: # get error back
        logging.error( 'ERROR: unable to get data.' )
        logging.error( 'ERROR: %s ' % e )
        splunk.Intersplunk.generateErrorResults(': unable to get data.') # print the error into Splunk UI
        sys.exit() # exit on error

if __name__ == '__main__':
    """ Script must implement these args: scheme, validate-arguments """
    if len(sys.argv) > 1:
        if sys.argv[1] == '--scheme':
            do_scheme()
        elif sys.argv[1] == '--validate-arguments':
            validate_arguments()
        else:
            pass
    else:
        run_main()
