#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Uschmann / MuS'
__date__ = '$Sep 4, 2015 10:48:46 AM$'
__version__ = '4.0.0'
__copyright__ = '2015 Michael Uschmann ALL RIGHTS RESERVED'

""" import only basic modules and do some stuff before we start """
import splunk
import sys
import os
import logging.handlers
import splunk.Intersplunk
import xml.dom.minidom
import xml.sax.saxutils
import base64
import collections
from datetime import datetime

""" get SPLUNK_HOME form OS """
SPLUNK_HOME = os.environ['SPLUNK_HOME']

""" get myScript name and path """
myScript = os.path.basename(__file__)
myPath = os.path.dirname(os.path.realpath(__file__))

""" import additional modules """
import pyasn1
import ldap3

SCHEME = """<scheme>
    <title>LDAP inputs</title>
    <description>Configure the LDAP server to be used for queries</description>

    <endpoint>
        <args>
            <arg name='name'>
                <title>Stanza name:</title>
                <description>The name of the modular input</description>
            </arg>
            <arg name='server'>
                <title>Server name:</title>
                <description>WHO will echo the world?</description>
            </arg>
            <arg name='port'>
                <title>Port:</title>
                <description>Provide the LDAP port to connect</description>
            </arg>
            <arg name='binddn'>
                <title>BINDDN:</title>
                <description>Provide the LDAP binddn to be used</description>
            </arg>
            <arg name='basedn'>
                <title>BASEDN:</title>
                <description>Provide the LDAP basedn to be used</description>
            </arg>
            <arg name='password'>
                <title>Password:</title>
                <description>Provide the LDAP password or '0' for anonymouse connect</description>
            </arg>
            <arg name='ldap_filter'>
                <title>LDAP filter:</title>
                <description>Provide the LDAP filter to be used</description>
            </arg>
            <arg name='usessl'>
                <title>Use SSL:</title>
                <description>Use '1' to enable SSL or '0' to disable SSL</description>
            </arg>
            <arg name='response_test'>
                <title>Index results:</title>
                <description>Use '1' to run, index LDAP bind response times or '0' to disable</description>
            </arg>
            <arg name='debug'>
                <title>Debug:</title>
                <description>Use '1' to enable or '0' to disable debugging</description>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

# define the logger to write into log file
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(
        SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = '%s.log' % myScript
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = '%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s'
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE,
                             LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger

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
            logging.info('XML: found configuration')
            stanza = conf_node.getElementsByTagName('stanza')[0]
            if stanza:
                stanza_name = stanza.getAttribute('name')
                if stanza_name:
                    logging.info('XML: found stanza ' + stanza_name)
                    config['name'] = stanza_name

                    params = stanza.getElementsByTagName('param')
                    for param in params:
                        param_name = param.getAttribute('name')
                        logging.info('XML: found param %s' % param_name)
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            logging.info('XML: %s -> %s' % (param_name, data))

        checkpnt_node = root.getElementsByTagName('checkpoint_dir')[0]
        if checkpnt_node and checkpnt_node.firstChild and \
           checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config['checkpoint_dir'] = checkpnt_node.firstChild.data

        if not config:
            raise Exception, 'Invalid configuration received from Splunk.'
            logging.error('Error getting Splunk configuration via STDIN: %s' % str(e) )

    except Exception, e:
        raise Exception, 'Error getting Splunk configuration via STDIN: %s' % str(e)
        logging.error('Error getting Splunk configuration via STDIN: %s' % str(e) )

    return config

def my_start():
    """ calulate start time of script """
    global t1
    t1 = datetime.now();
    return t1;

def my_stop():
    """ calulate stop time of script """
    global t2
    t2 = datetime.now();
    return t2;

def my_time():
    """ calulate duration time of test """
    c = t2 - t1;
    itTook = (c.days * 24 * 60 * 60 + c.seconds) * 1000 + c.microseconds / 1000.0;
    return itTook;

def run_main():
    """ get the config """
    config = get_config()
    # start the logger for troubleshooting
    myDebug = config['debug']
    if myDebug == '1':
        logger = setup_logging()  # logger

    # starting the main
    logging.info( 'Starting the main task ...' )

    # use user provided options or get [default] stanza options
    try: # lets do it
        logging.info( 'read the default options from inputs.conf...' )

        # check [default] stanza if we need ssl
        logging.info( 'reading usessl from inputs.conf...' )
        usessl = config['usessl']
        if usessl == '1':
            server = ldap3.Server(host=config['server'], port=int(config['port']), use_ssl='%s' % usessl)
        else:
            server = ldap3.Server(host=config['server'], port=int(config['port']), use_ssl=False)
        logging.info( 'usessl is : %s ...' % usessl )

        # set timeout to 30 seconds, sizelimit to 10 and search scope base
        logging.info( 'reading basedn from inputs.conf...' )
        timeout = '30'
        sizelimit = 10
        scope = 'sub'

    except Exception, e: # get error back
        logging.error( 'ERROR: unable to get default options from inputs.conf' )
        logging.error( 'ERROR: %s' % e )
        splunk.Intersplunk.generateErrorResults(': unable to get default options from inputs.conf') # print the error into Splunk UI
        sys.exit() # exit on error

    # setup connection string
    logging.info( 'setting up server connection string ...' )
    logging.info( 'connection string : %s' % server)

    # do we use anonymous bind or do we use a password?
    if config['password'] == '0': # no password
        try: # lets do an anonymous bind
            logging.info( 'start anonymous LDAP bind...' )
            my_start(); # get the start time
            conn = ldap3.Connection(server, auto_bind=True, version=3)
            my_stop(); # get the stop time
            ms_bind = my_time(); # get the duration of it
        except: # get error back
            logging.error( 'ERROR: anonymous LDAP bind failed.' )
            splunk.Intersplunk.generateErrorResults(': anonymous LDAP bind failed.') # print the error into Splunk UI
            sys.exit() # exit on error

    else: # we use a password - much better ;)
        try: # lets do an authenticated bind
            logging.info( 'start simple LDAP bind...' )
            decoded_pwd = base64.b64decode(config['password']) # get the password and decode it
            my_start(); # get the start time
            conn = ldap3.Connection(server, user=config['binddn'], password=decoded_pwd, auto_bind=True, read_only=True, version=3)
            my_stop(); # get the stop time
            ms_bind = my_time(); # get the duration of it
        except Exception, e: # get error back
            logging.error( 'ERROR: simple LDAP bind failed.' )
            logging.error( 'ERROR: %s' % e)
            splunk.Intersplunk.generateErrorResults(': simple LDAP bind failed.') # print the error into Splunk UI
            sys.exit() # exit on error

    # perform LDAP search response time test
    try: # lets do it
        logging.info( 'start response time LDAP bind ...' )
        logging.info( 'start timing ...' )
        my_start(); # get the start time
        logging.info( 'start ldap search ...' )
        conn.extend.standard.who_am_i()
        logging.info( 'stop timing ...' )
        my_stop(); # get the stop time
        ms_search = my_time(); # get the duration of it
        my_start(); # get the start time
        conn.unbind()
        my_stop(); # get the stop time
        ms_unbind = my_time(); # get the duration of it
        if config['response_test'] == '1':
            print 'time=\"%s\" server=\"%s\" basedn=\"%s\" ldap_bind=\"%s\" ldap_search=\"%s\" ldap_unbind=\"%s\"' % (t1,config['server'],config['basedn'],ms_bind,ms_search,ms_unbind)
    except Exception, e: # get error back
        logging.error( 'ERROR: response time LDAP bind failed.' )
        logging.error( 'ERROR: %s' % e)
        splunk.Intersplunk.generateErrorResults(': response time LDAP bind failed') # print the error into Splunk UI
        sys.exit() # exit on error
    logging.info( 'response time LDAP bind done...leaving the script' )
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

