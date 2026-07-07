#!/usr/libexec/platform-python

"""
# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2022 Marco Favero.
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---
#
# PYTHON_ARGCOMPLETE_OK
"""

from __future__ import print_function
import csv
import sys
import socket
import configparser
import os
import logging
import logging.handlers

# Zimbra libs
import sys
sys.path.append(os.path.join(os.path.dirname(__file__),"zimbralib"))
import pythonzimbra.communication
from pythonzimbra.communication import Communication
import pythonzimbra.tools
from pythonzimbra.tools import auth
from pathlib import Path
from io import open

""" An adapter that takes CSV as input, performs a lookup to the Zimbra mailbox
    name resolution facilities, then returns the CSV results.

    Note that the script offers mapping both ways, from mailbox name to mailbox ID
    and from mailbox ID to mailbox name.

    Bidrectional mapping is always required when using an external lookup as an
    'automatic' lookup: one configured to be used without explicit reference in
    a search.
"""

"""
ZIMBRA  lib
"""

def load_config(file):
    config = configparser.ConfigParser()
    config.read(file)
    return config


loggerName = 'name2mid'
log = logging.getLogger(loggerName)
def set_log(handler_type, socketaddr, facility, level='INFO', stdout=False, filepath=False):
    log = logging.getLogger(loggerName)
    log.setLevel(level)
    formatter_syslog = logging.Formatter('%(module)s[%(process)d]: %(message)s')
    formatter_stdout = logging.Formatter('%(module)-16s[%(process)d]/%(funcName)-15s: %(levelname)8s: %(message)s')
    formatter_file   = logging.Formatter('%(asctime)s %(module)s[%(process)d]/%(funcName)s: %(levelname)8s: %(message)s')

    if handler_type == 'syslog':
        handler_syslog = logging.handlers.SysLogHandler(address=socketaddr, facility=facility, socktype=socket.SOCK_STREAM)
        handler_syslog.setFormatter(formatter_syslog)
        handler_syslog.setLevel(level)
        log.addHandler(handler_syslog)
    if handler_type == 'file':
        if not filepath:
            return False
        oldumask = os.umask(0o0026)
        handler_file = logging.handlers.WatchedFileHandler(filepath, encoding='utf8')
        handler_file.setFormatter(formatter_file)
        handler_file.setLevel(level)
        log.addHandler(handler_file)
        os.umask(oldumask)
    if stdout:
        handler_out = logging.StreamHandler(sys.stdout)
        handler_out.setLevel(level)
        handler_out.setFormatter(formatter_stdout)
        log.addHandler(handler_out)
    return True


def zConnect(url, admin, password):
    usr_token = auth.authenticate(
        url = url,
        account = admin,
        key = password,
        admin_auth = True
    )
    comm = Communication(url)
    # comm is None if something was wrong.
    return comm, usr_token

def mailbox_id(conn, usr_token, mailboxName, nullString='void'):
    info_request = conn.gen_request(token=usr_token)
    # Get zimbraId of mailboxName
    info_request.add_request(
        'GetAccountRequest',
        {
            'account': {
                'by': 'name',
                '_content': mailboxName
            },
            'attrs': 'zimbraId,zimbraMailHost'
        },
        'urn:zimbraAdmin'
    )
    info_response = conn.send_request(info_request)
    if not info_response.is_fault():
        zimbraId = info_response.get_response()['GetAccountResponse']['account']['id']
        attrs = info_response.get_response()['GetAccountResponse']['account']['a']
        # Looking for zimbraMailHost in list of attrs ('n' index):
        zimbraMailHost = next((item for item in attrs if item['n'] == 'zimbraMailHost'), None)['_content']
        info_request.clean()
        info_request = conn.gen_request(token=usr_token)
        info_request.add_request(
            'GetMailboxRequest',
            {
                'mbox': {
                    'id': zimbraId
                }
            },
            'urn:zimbraAdmin'
        )
        info_response = conn.send_request(info_request)
        if not info_response.is_fault():
            return zimbraMailHost, info_response.get_response()['GetMailboxResponse']['mbox']['mbxid']
        else:
            log.error(info_response.get_fault_message())
    else:
        log.error(info_response.get_fault_message())
    return nullString, nullString

# Given a mailbox name, find the mailbox id
def lookup(zconn, token, name, nullStr):
    try:
        host,mid = mailbox_id(zconn, token, name, nullStr)
        return host,mid
    except Exception as e:
        log.critical(e)
        return nullStr, nullStr

# Given a mailbox id, return the mailbox name
def rlookup(mid, host):
    try:
        # name = mailbox_name(mid, host)
        return ''
    except:
        return ''


'''
MAIN
'''
def main():
    if len(sys.argv) != 4:
        print("Usage: python {}.py [mailbox_name field] [mailbox_server field] [mailbox_id field]".
              format(sys.argv[0]))
        sys.exit(1)

    '''
    MAIN CONFIGURATION
    '''
    config_file = '../local/zimbra.conf'
    CONFIG_LOCAL = os.path.join(os.path.dirname(__file__), config_file)
    config_file = '../default/zimbra.conf'
    CONFIG_DEFAULT = os.path.join(os.path.dirname(__file__), config_file)
    if not os.path.isfile(CONFIG_DEFAULT):
        log.fatal("I can't find the config file <{}>.\n".format(config_file))
        sys.exit(2)

    config_var = load_config([CONFIG_DEFAULT,CONFIG_LOCAL])
    Soap = config_var["Soap"]
    adminUrl = Soap['adminUrl']
    admin = Soap['admin']
    admin_password = Soap['pwd']
    nullStr = Soap["NullStr"]

    logging_parameters =  config_var["Logging"]
    LOGFILE_NAME = logging_parameters['LOGFILE_NAME']
    LOGSTDOUT = logging_parameters.getboolean('LOGSTDOUT')
    LOGHANDLER = logging_parameters['TYPE']
    SYSLOG_FAC = logging_parameters['SYSLOG_FAC']
    SYSLOG_LEVEL = logging_parameters['LOG_LEVEL']
    SYSLOG_SOCKET = logging_parameters['SYSLOG_SOCKET']


    for confvar in ( LOGFILE_NAME, LOGSTDOUT, LOGHANDLER, SYSLOG_FAC, SYSLOG_LEVEL, SYSLOG_SOCKET, adminUrl, admin, admin_password, nullStr ):
        if confvar is None:
            sys.exit("Please check the config file! Some parameters are missing.")

    LOGFILE_DIR = '/var/log/splunk'
    # Zimbra SOAP doesn't work through proxy

    if LOGHANDLER == 'file':
        if 'SPLUNK_HOME' in os.environ:
            homeSplunk = os.environ['SPLUNK_HOME']
        else:
            homeSplunk = '/opt/splunk'
        LOGFILE_DIR = homeSplunk + LOGFILE_DIR
        LOGFILE_PATH = os.path.join(LOGFILE_DIR, LOGFILE_NAME)
        Path(LOGFILE_DIR).mkdir(exist_ok=True)
        Path(LOGFILE_PATH).touch()
    else:
        LOGFILE_PATH = False

    if not set_log(LOGHANDLER, SYSLOG_SOCKET, SYSLOG_FAC, SYSLOG_LEVEL, LOGSTDOUT, LOGFILE_PATH):
        print("Something wrong in log definition")
        sys.exit(1)

    '''
    INPUT
    '''
    mnamefield = sys.argv[1]
    mserverfield = sys.argv[2]
    midfield = sys.argv[3]

    '''
    MAIN PROCESS
    '''
    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for result in r:
        # Perform the lookup or reverse lookup if necessary
        if result[mserverfield] and result[mnamefield] and result[midfield]:
            # All fields were provided, just pass it along
            w.writerow(result)

        elif result[mnamefield] and not result[mserverfield] and not result[midfield]:
            # only mailbox name was provided, add mailbox ID and host
            (zimbraConn,adminToken) = zConnect(adminUrl, admin, admin_password)
            result[mserverfield],result[midfield] = lookup(zimbraConn, adminToken, result[mnamefield],nullStr)
            if result[midfield] and result[mserverfield]:
                w.writerow(result)

        elif result[mserverfield] and result[midfield]:
            '''
            # TO DO
            # Host and its  mailbox ID was provided, add mailbox name
            # This is not provided by SOAP API.
            result[mnamefield] = rlookup(result[hostfield],result[midfield])
            if result[mnamefield]:
                w.writerow(result)
            '''

main()
