"""
check_point_block.py

Python script to execute a block action on Checkpoint firewall.

"""

import os
import gzip
import csv
import logging
import logging.handlers
import json
import socket
import time
import sys
import requests
import common

# CORE SPLUNK IMPORTS
try:
    from splunk.clilib.bundle_paths import make_splunkhome_path  # pylint: disable=import-error
except ImportError:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path  # pylint: disable=import-error
from splunk.clilib import cli_common as cli  # pylint: disable=import-error

sys.path.append(make_splunkhome_path(["etc", "apps", "TA-Check_Point_Block",
                                      "lib"]))

from cim_actions import ModularAction # pylint: disable=wrong-import-position,import-error


def setup_logger(level):
    """ Setup logging """
    logger = logging.getLogger('check_point_block')
    logger.propagate = False
    # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    splunk_home = os.environ['SPLUNK_HOME']
    log_path = os.path.join(splunk_home, 'var', 'log', 'splunk', 'ta-checkpoint_blockaction.log')
    file_handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def validate_ip(ip_addr):
    """ Make sure IP is actually an IPv4 IP """
    try:
        socket.inet_aton(ip_addr)
    except socket.error:
        return False

    return True


def get_self_conf_stanza(stanza):
    """ Get creds out of conf file created via setup.xml """
    app_dir = os.path.dirname(os.path.dirname(__file__))
    conf_path = os.path.join(app_dir, "default", "check_point_block.conf")
    conf = cli.readConfFile(conf_path)
    local_conf_path = os.path.join(app_dir, "local", "check_point_block.conf")
    if os.path.exists(local_conf_path):
        local_conf = cli.readConfFile(local_conf_path)
        for name, content in local_conf.items():
            if name in conf:
                conf[name].update(content)
            else:
                conf[name] = content
    return conf[stanza]


class CheckPointBlock(ModularAction):
    """
    This alert block an IP on a Check Point firewall
    """

    def __init__(self, settings, logger, action_name=None):
        super().__init__(settings, logger, action_name)

        self.time_to_block = self.configuration.get('time_to_block', None)
        self.block_ip = self.configuration.get('ip', None)
        self.block_ip_field = self.configuration.get('ip_field', None)
        if self.block_ip == '':
            self.block_ip = None
        if self.block_ip_field == '':
            self.block_ip_field = None
        self.logger.info("Check Point Time to Block = %s", self.time_to_block)
        self.logger.info("IP to Block = %s", self.block_ip)

    def api_call(self, mgmt_ip, port, command, json_payload, sid):  # pylint: disable=too-many-arguments,inconsistent-return-statements
        """ Makes a call to the Checkpoint firewall for auth or block action """
        try:
            url = 'https://' + mgmt_ip + ':' + port + '/web_api/' + command
            if sid == '':
                request_headers = {'Content-Type': 'application/json'}
            else:
                request_headers = {'Content-Type': 'application/json',
                                   'X-chkp-sid': sid}
            request_return = requests.post(url,  # nosec
                                           data=json.dumps(json_payload), # nosec
                                           headers=request_headers, verify=False, # nosec
                                           timeout=60) # nosec
            return request_return.json()
        except Exception as err:  # pylint: disable=broad-except
            self.logger.info(str(err))

    def login(self, user, password, server, port):  # pylint: disable=inconsistent-return-statements
        """ Logs into the Checkpoint firewall """
        try:
            payload = {'user': user, 'password': password}
            response = self.api_call(server, port, 'login', payload, '')

            return response["sid"], response["uid"]
        except KeyError:
            self.logger.error("Invalid credentials")
            sys.exit()
        except Exception as err:  # pylint: disable=broad-except
            self.logger.info(str(err))

    def block(self, block_ip, server, port, server_name, time_to_block, sid):  # pylint: disable=too-many-arguments
        """ Executes the block action """
        fw_sam_command = f"fw sam -v -t {int(time_to_block)} -J any {str(block_ip)} 2> /dev/null"

        sam_result = self.api_call(server, port, 'run-script',
                                   {'script-name': 'Splunk FW SAM',
                                    'script': fw_sam_command,
                                    'targets': server_name
                                   }, sid)

        time.sleep(10)
        # should display results on workflow action
        print("Result")
        print("The block action was executed successfully.")
        return json.dumps(sam_result)

    def discard(self, server, port, uid, sid):  # pylint: disable=inconsistent-return-statements
        """ Ends current session """
        try:
            discard_result = self.api_call(server, port, 'discard', {'uid': uid}, sid)
            return discard_result.json()
        except Exception as err:  # pylint: disable=broad-except
            self.logger.info(str(err))

    def publish(self, server, port, uid, sid):  # pylint: disable=inconsistent-return-statements
        """ Publishes results on Check Point server of current session """
        try:
            publish_result = self.api_call(server, port, 'publish', {'uid': uid}, sid)
            return publish_result.json()
        except Exception as err:  # pylint: disable=broad-except
            self.logger.info(str(err))

    def logout(self, server, port, sid):  # pylint: disable=inconsistent-return-statements
        """ Logs out from Check Point server """
        try:
            logout_result = self.api_call(server, port, 'logout', {}, sid)
            return logout_result.json()
        except Exception as err:  # pylint: disable=broad-except
            self.logger.info(str(err))


def run():  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """ Execute the block """
    if len(sys.argv) > 1 and sys.argv[1] != "--execute":
        print(sys.stderr, ("FATAL Unsupported execution mode"
                           " (expected --execute flag)"))
        sys.exit(1)

    try:
        logger = setup_logger("DEBUG")
        modaction = CheckPointBlock(sys.stdin.read(), logger,
                                    "check_point_block")
        modaction.addinfo()
        session_key = modaction.session_key
        username, password = common.get_credentials(session_key)
        stanza = get_self_conf_stanza("info")
        firewalls = stanza["firewalls"].replace(" ", "").split(",")
        firewall_names = stanza["firewall_names"].replace(" ", "").split(",")
        default_ttb = stanza["default_ttb"]

        # Build dictionary of firewall info including session ID
        firewall_info = {}
        for idx, firewall in enumerate(firewalls):
            firewall_ip, firewall_port = firewall.split(":")
            firewall_name = firewall_names[idx]
            sid, uid = modaction.login(username, password, firewall_ip, firewall_port)
            firewall_info[firewall_ip] = {'port': firewall_port,
                                          'name': firewall_name,
                                          'sid': sid,
                                          'uid': uid}

        time_to_block = modaction.time_to_block
        block_ip = modaction.block_ip
        block_ip_field = modaction.block_ip_field

        if modaction.block_ip:
            # This is being run from search to block a single IP.
            # Don't read in results_file
            for firewall in firewall_info.keys():  # pylint: disable=consider-iterating-dictionary, consider-using-dict-items
                if validate_ip(block_ip):
                    if time_to_block != "":
                        modaction.block(block_ip,
                                        firewall,
                                        firewall_info[firewall]['port'],
                                        firewall_info[firewall]['name'],
                                        time_to_block,
                                        firewall_info[firewall]['sid'])
                    else:
                        modaction.block(block_ip,
                                        firewall,
                                        firewall_info[firewall]['port'],
                                        firewall_info[firewall]['name'],
                                        default_ttb,
                                        firewall_info[firewall]['sid'])

                else:
                    logger.error("Specified IP is not a valid IPv4 address")
                    continue

                modaction.discard(firewall, firewall_info[firewall]['port'],
                                  firewall_info[firewall]['uid'], firewall_info[firewall]['sid'])
                modaction.logout(firewall, firewall_info[firewall]['port'],
                                 firewall_info[firewall]['sid'])

        else:
            with gzip.open(modaction.results_file, 'rt') as result_zip:
                for num, result in enumerate(csv.DictReader(result_zip)):
                    # set rid to row # (0->n) if unset
                    result.setdefault('rid', str(num))
                    logger.info("RESULTS: %s", result)

                    modaction.update(result)
                    modaction.invoke()

                    if modaction.block_ip_field not in result:
                        logger.error("Specified field could not be found in event")

                    if not validate_ip(result[block_ip_field]):
                        logger.error("Specified IP is not a valid IPv4 address")
                        continue

                    logger.debug("Blocking %s", result[block_ip_field])  # pylint: disable=logging-not-lazy

                    for firewall in firewall_info.keys():  # pylint: disable=consider-iterating-dictionary, consider-using-dict-items
                        if time_to_block != "":
                            modaction.block(result[modaction.block_ip_field],
                                            firewall,
                                            firewall_info[firewall]['port'],
                                            firewall_info[firewall]['name'],
                                            time_to_block,
                                            firewall_info[firewall]['sid'])
                        else:
                            modaction.block(result[modaction.block_ip_field],
                                            firewall,
                                            firewall_info[firewall]['port'],
                                            firewall_info[firewall]['name'],
                                            default_ttb,
                                            firewall_info[firewall]['sid'])

            for firewall in firewall_info.keys():  # pylint: disable=consider-iterating-dictionary, consider-using-dict-items
                modaction.discard(firewall, firewall_info[firewall]['port'],
                                  firewall_info[firewall]['uid'], firewall_info[firewall]['sid'])
                modaction.logout(firewall, firewall_info[firewall]['port'],
                                 firewall_info[firewall]['sid'])

    except Exception as err:  # pylint: disable=broad-except
        logger.info(f"Exception: {str(err)}")


if __name__ == "__main__":
    run()
