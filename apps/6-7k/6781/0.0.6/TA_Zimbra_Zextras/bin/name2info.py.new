#!/usr/libexec/platform-python

"""
# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2023 Marco Favero.
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---
#
# PYTHON_ARGCOMPLETE_OK
"""

import csv
import sys
import socket
import configparser
import os
import logging
import logging.handlers
import re
sys.path.append(os.path.join(os.path.dirname(__file__),"zimbralib"))
#sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from pathlib import Path

# Zimbra libs
import pythonzimbra.communication
from pythonzimbra.communication import Communication
import pythonzimbra.tools
from pythonzimbra.tools import auth


"""
ZIMBRA  lib
"""

def load_config(file):
    config = configparser.ConfigParser()
    config.read(file)
    return config


loggerName = 'name2info'
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


def getMailbox_id(conn, usr_token, mailboxName, retAttrs='zimbraId'):
    attr = {}
    log = logging.getLogger(loggerName)
    info_request = conn.gen_request(token=usr_token)
    # Get zimbraId of mailboxName
    info_request.add_request(
        'GetAccountRequest',
        {
            'account': {
                'by': 'name',
                '_content': mailboxName
            },
            'attrs': retAttrs
        },
        'urn:zimbraAdmin'
    )
    info_response = conn.send_request(info_request)
    if not info_response.is_fault():
        zimbraId = info_response.get_response()['GetAccountResponse']['account']['id']
        attrs = info_response.get_response()['GetAccountResponse']['account']['a']
        for item in attrs:
            if item['n'] in attr.keys():
                attr[item['n']].append(item['_content'])
            else:
                attr[item['n']] = []
                attr[item['n']].append(item['_content'])
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
            attr['zimbraMailboxId'] = []
            attr['zimbraMailSize'] = []
            attr['zimbraMailboxId'].append(info_response.get_response()['GetMailboxResponse']['mbox']['mbxid'])
            attr['zimbraMailSize'].append(info_response.get_response()['GetMailboxResponse']['mbox']['s'])
            return attr
        else:
            log.error(info_response.get_fault_message())
    else:
        log.error(info_response.get_fault_message())


def getDistributionList(conn, usr_token, listName, retAttrs='mail'):
    attr = {}
    log = logging.getLogger(loggerName)
    info_request = conn.gen_request(token=usr_token)
    # Get info on listName
    info_request.add_request(
        'GetDistributionListRequest',
        {
            'dl': {
                'by': 'name',
                '_content': listName
            },
            'attrs': retAttrs
        },
        'urn:zimbraAdmin'
    )
    info_response = conn.send_request(info_request)
    if not info_response.is_fault():
        attrs = info_response.get_response()['GetDistributionListResponse']['dl']['a']
        for item in attrs:
            if item['n'] in attr.keys():
                attr[item['n']].append(item['_content'])
            else:
                attr[item['n']] = []
                attr[item['n']].append(item['_content'])
        attrs.clear()
        attrs = info_response.get_response()['GetDistributionListResponse']['dl']['dlm']
        if not info_response.is_fault():
            attr['member'] = []
            for item in attrs:
                attr['member'].append(item['_content'])
            info_request.clean()
        else:
            log.error(info_response.get_fault_message())
        return attr
    else:
        log.error(info_response.get_fault_message())


def GetAccountMembershipRequest(conn, usr_token, accountName):
    attr = {}
    log = logging.getLogger(loggerName)
    info_request = conn.gen_request(token=usr_token)
    # Get info on listName
    info_request.add_request(
        'GetAccountMembershipRequest',
        {
            'account': {
                'by': 'name',
                '_content': accountName
            },
        },
        'urn:zimbraAdmin'
    )
    info_response = conn.send_request(info_request)
    if not info_response.is_fault():
        attrs = info_response.get_response()['GetAccountMembershipResponse']['dl']
        if not info_response.is_fault():
            attr['memberOf'] = []
            for item in attrs:
                attr['memberOf'].append(item)
            info_request.clean()
        else:
            log.error(info_response.get_fault_message())
        return attr
    else:
        log.error(info_response.get_fault_message())


@Configuration()
class StreamingZINFO(StreamingCommand):
    """
    The streamingzinfo command returns events with new fields describing
    the Zimbra mailbox account.
    Example:
    ``| makeresults count=5 | eval authz_name=admin@example.com | name2info field=authz_name``
    returns a records with many new fields starting with 'zimbra'.
    """

    field = Option(require=True, validate=validators.Match("validate","authz_name|name|user"))
    get = Option(require=False, default="account", validate=validators.Match("validate","account|list|memberOf"))

    def stream(self, records):
        config_file = '../local/zimbra.conf'
        CONFIG_LOCAL = os.path.join(os.path.dirname(__file__), config_file)
        config_file = '../default/zimbra.conf'
        CONFIG_DEFAULT = os.path.join(os.path.dirname(__file__), config_file)
        if not os.path.isfile(CONFIG_DEFAULT):
            log.fatal("I can't find the config file <{}>.\n".format(config_file))
            sys.exit(2)

        config_var = load_config([CONFIG_DEFAULT,CONFIG_LOCAL])

        logging_parameters =  config_var["Logging"]
        LOGFILE_NAME = logging_parameters['LOGFILE_NAME']
        LOGSTDOUT = logging_parameters.getboolean('LOGSTDOUT')
        LOGHANDLER = logging_parameters['TYPE']
        SYSLOG_FAC = logging_parameters['SYSLOG_FAC']
        SYSLOG_LEVEL = logging_parameters['LOG_LEVEL']
        SYSLOG_SOCKET = logging_parameters['SYSLOG_SOCKET']

        Soap = config_var["Soap"]
        adminUrl = Soap['adminUrl']
        admin = Soap['admin']
        admin_password = Soap['pwd']

        accounts = config_var["Account"]
        lists = config_var["MailingList"]
        attributes = {}
        attributes['account'] = re.sub(",\s*\\\s*\n", ",", accounts['Attributes'])
        attributes['list'] = re.sub(",\s*\\\s*\n", ",", lists['Attributes'])
        proxy = config_var["Proxy"]
        ignoreProxy = proxy.getboolean("IgnoreProxy")

        for confvar in ( LOGFILE_NAME, LOGSTDOUT, LOGHANDLER, SYSLOG_FAC, SYSLOG_LEVEL, SYSLOG_SOCKET, adminUrl, admin, admin_password, accounts, lists, ignoreProxy ):
            if confvar is None:
                print("Please check the config file! Some parameters are missing.")
                sys.exit(2)

        if ignoreProxy:
            if 'HTTP_PROXY' in os.environ:
                del os.environ['HTTP_PROXY']
            if 'HTTPS_PROXY' in os.environ:
                del os.environ['HTTPS_PROXY']

        if LOGHANDLER == 'file':
            if 'SPLUNK_HOME' in os.environ:
                homeSplunk = os.environ['SPLUNK_HOME']
            else:
                homeSplunk = '/opt/splunk'
            LOGFILE_DIR = homeSplunk + '/var/log/splunk'
            LOGFILE_PATH = os.path.join(LOGFILE_DIR, LOGFILE_NAME)
            Path(LOGFILE_DIR).mkdir(exist_ok=True)
            Path(LOGFILE_PATH).touch()
        else:
            LOGFILE_PATH = False

        # Starting to log
        if not set_log(LOGHANDLER, SYSLOG_SOCKET, SYSLOG_FAC, SYSLOG_LEVEL, LOGSTDOUT, LOGFILE_PATH):
            print("Something wrong in log definition")
            sys.exit(1)

        if not adminUrl.startswith('https://'):
            log.critical('The Zimbra admin uri does not start with https://. Only a secure connection is allowed.')
            sys.exit(2)

        (zconn, token) = zConnect(adminUrl, admin, admin_password)
        if zconn is None:
            log.critical("Error in connection")
            sys.exit(2)
        for record in records:
            try:
                if self.get == "account":
                    answer = getMailbox_id(zconn, token, record[self.field], attributes['account'])
                elif self.get == "list":
                    answer = getDistributionList(zconn, token, record[self.field], attributes['list'])
                elif self.get == "memberOf":
                    answer = GetAccountMembershipRequest(zconn, token, record[self.field])
            except Exception as e:
                log.critical(e)
                answer = None

            isThis = 'is' + self.get.capitalize()
            if answer is not None:
                self.add_field(record, isThis, True)
                for name, values in answer.items():
                    self.add_field(record, name, values)
            else:
                self.add_field(record, isThis, False)
        yield record


dispatch(StreamingZINFO, sys.argv, sys.stdin, sys.stdout, __name__)
