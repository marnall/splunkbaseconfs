# apresia connector
import phantom.app as phantom
from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult
from apresia_consts import *
import telnetlib


class ApresiaConnector(BaseConnector):

    '''
    Apresia connector
    this module can test connection, block ip, unblock ip
    '''

    def __init__(self):
        super(ApresiaConnector, self).__init__()
        self._telnet_client = telnetlib.Telnet()
        return

    def _test_connectivity(self):
        self.save_progress("Querying a single device to check connectivity")
        status = self._start_connection()
        self._cleanup()
        if (not status) or phantom.is_fail(status):
            self.save_progress(APRESIA_ERR_CONNECTION_FAILED)
        else:
            self.save_progress(APRESIA_SUCC_CONNECTION_ESTABLISHED)
        return status

    def _start_connection(self):
        config = self.get_config()
        user = config[APRESIA_JSON_USERNAME]
        password = config[APRESIA_JSON_PASSWORD]
        host = config[APRESIA_JSON_HOST]
        port = config[APRESIA_JSON_PORT]
        try:
            self._telnet_client.open(host, int(port), APRESIA_TELNET_TIMEOUT)
            self._telnet_client.read_until("login: ", APRESIA_TELNET_TIMEOUT)
            self._telnet_client.write("%s\n" % str(user))
            self._telnet_client.read_until("Password: ", APRESIA_TELNET_TIMEOUT)
            self._telnet_client.write("%s\n" % str(password))
            self._telnet_client.read_until(APRESIA_TELNET_PROMPT, APRESIA_TELNET_TIMEOUT)
        except Exception as e:
            self._cleanup()
            return self.set_status(phantom.APP_ERROR, APRESIA_ERR_CONNECTION_FAILED, e)
        return self.set_status(phantom.APP_SUCCESS, APRESIA_SUCC_CONNECTION_ESTABLISHED)

    def _cleanup(self):
        if self._telnet_client:
            self._telnet_client.close()
        return

    def _get_commands(self, param, action):
        commands = []
        # Building commands for block ip
        if action == APRESIA_ACTION_ID_BLOCK_IP:
            commands.append("configure aacl portpipe %s:1 parser %s parser-type ipv4-tcp\n" %
                            (str(param["linecard-id"]), str(param["parser-id"])))
            if (param["src_ip"] != "0.0.0.0"):
                commands.append("configure aacl portpipe %s:1 parser %s rule %s condition add ipv4-src %s/255.255.255.255\n" %
                                (str(param["linecard-id"]), str(param["parser-id"]), str(param["rule-id"]), str(param["src_ip"])))
            if (param["dst_ip"] != "0.0.0.0"):
                commands.append("configure aacl portpipe %s:1 parser %s rule %s condition add ipv4-dst %s/255.255.255.255\n" %
                                (str(param["linecard-id"]), str(param["parser-id"]), str(param["rule-id"]), str(param["dst_ip"])))
            commands.append("configure aacl portpipe %s:1 parser %s rule %s %s-port %s\n" %
                            (str(param["linecard-id"]), str(param["parser-id"]), str(param["rule-id"]), str(param["direction"]), str(param["port"])))
            commands.append("configure aacl portpipe %s:1 parser %s rule %s cir-conform-action add discard\n" %
                            (str(param["linecard-id"]), str(param["parser-id"]), str(param["rule-id"])))
        # Building commands for unblock ip
        elif action == APRESIA_ACTION_ID_UNBLOCK_IP:
            commands.append("no configure aacl portpipe %s:1 parser %s rule %s cir-conform-action add discard\n" %
                            (str(param["linecard-id"]), str(param["parser-id"]), str(param["rule-id"])))
            commands.append("no configure aacl portpipe %s:1 parser %s rule %s %s-port" %
                            (str(param["linecard-id"]), str(param["parser-id"]), str(param["rule-id"]), str(param["direction"])))
            if (param["src_ip"] != "0.0.0.0"):
                commands.append("no configure aacl portpipe %s:1 parser %s rule %s condition add ipv4-src\n" %
                                (str(param["linecard-id"]), str(param["parser-id"]), str(param["rule-id"])))
            if (param["dst_ip"] != "0.0.0.0"):
                commands.append("no configure aacl portpipe %s:1 parser %s rule %s condition add ipv4-dst\n" %
                                (str(param["linecard-id"]), str(param["parser-id"]), str(param["rule-id"])))
        self.action_result.add_data(dict({"commands": commands}))
        return commands

    def _unblock_ip(self, param):
        commands = self._get_commands(param, APRESIA_ACTION_ID_UNBLOCK_IP)
        if commands is None:
            return self.action_result.get_status()
        try:
            for cmd_line in commands:
                self.debug_print('send command:', cmd_line)
                self._telnet_client.write(cmd_line)
                self._telnet_client.read_until(APRESIA_TELNET_PROMPT, APRESIA_TELNET_TIMEOUT)
            self._telnet_client.write("write configuration built-in primary\n")
            self._telnet_client.read_until("Write configuration? (y/n)", APRESIA_TELNET_TIMEOUT)
            self._telnet_client.write("y\n")
            self._telnet_client.read_until(APRESIA_TELNET_PROMPT, APRESIA_TELNET_TIMEOUT)
        except Exception as e:
            self._cleanup()
            return self.action_result.set_status(phantom.APP_ERROR, APRESIA_ERR_CMD_EXEC, e)
        self._cleanup()
        return self.action_result.set_status(phantom.APP_SUCCESS, APRESIA_SUCC_CMD_EXEC)

    def _block_ip(self, param):
        commands = self._get_commands(param, APRESIA_ACTION_ID_BLOCK_IP)
        if commands is None:
            return self.action_result.get_status()
        try:
            for cmd_line in commands:
                self.debug_print('send command:', cmd_line)
                self._telnet_client.write(cmd_line)
                self._telnet_client.read_until(APRESIA_TELNET_PROMPT, APRESIA_TELNET_TIMEOUT)
            self._telnet_client.write("write configuration built-in primary\n")
            self._telnet_client.read_until("Write configuration? (y/n)", APRESIA_TELNET_TIMEOUT)
            self._telnet_client.write("y\n")
            self._telnet_client.read_until(APRESIA_TELNET_PROMPT, APRESIA_TELNET_TIMEOUT)
        except Exception as e:
            self._cleanup()
            return self.action_result.set_status(phantom.APP_ERROR, APRESIA_ERR_CMD_EXEC, e)
        self._cleanup()
        return self.action_result.set_status(phantom.APP_SUCCESS, APRESIA_SUCC_CMD_EXEC)

    def _handle_block_ip(self, param, unblock=False):
        self.action_result = self.add_action_result(ActionResult(dict(param)))
        status = self._start_connection()
        if (not status) or phantom.is_fail(status):
            self._cleanup()
            return self.action_result.set_status(phantom.APP_ERROR, APRESIA_ERR_CONNECTION_FAILED)
        if unblock:
            status = self._unblock_ip(param)
        else:
            status = self._block_ip(param)
        self.debug_print('status_code', status)
        return self.action_result.get_status()

    def handle_action(self, param):
        action = self.get_action_identifier()
        self.debug_print('Action is :', str(action))
        if action == APRESIA_ACTION_ID_TEST_CONNECTIVITY:
            status = self._test_connectivity()
        elif action == APRESIA_ACTION_ID_BLOCK_IP:
            status = self._handle_block_ip(param)
        elif action == APRESIA_ACTION_ID_UNBLOCK_IP:
            status = self._handle_block_ip(param, unblock=True)
        return status


# cancheck code by just executing in console
if __name__ == '__main__':
    import sys
    import pudb
    import simplejson as json
    pudb.set_trace()
    if len(sys.argv) < 2:
        print 'No test json specified as input'
        sys.exit(0)
    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print json.dumps(in_json, indent='    ')
        connector = ApresiaConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print ret_val
    sys.exit(0)
