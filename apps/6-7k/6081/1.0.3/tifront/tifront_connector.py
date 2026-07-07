# tifront connector
import phantom.app as phantom
from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult
from tifront_consts import *
import os
os.sys.path.insert(0, "{}/pexpect".format(os.path.dirname(os.path.abspath(__file__))))  # noqa
os.sys.path.insert(0, "{}/ptyprocess".format(os.path.dirname(os.path.abspath(__file__))))  # noqa
import pexpect
import sys


class TifrontConnector(BaseConnector):

    def __init__(self):
        super(TifrontConnector, self).__init__()
        self.pe = None
        return

    def _send_commands(self, commands, hostname):
        prompt = hostname + TIFRONT_SSH_INCOMMAND_PROMPT
        try:
            for cmd_line in commands:
                self.debug_print("send command:", cmd_line)
                self.pe.sendline(cmd_line)
                self.pe.expect(prompt)
            self.pe.sendline("exit")
            self._cleanup()
        except Exception as exept:
            self._cleanup()
            self.debug_print(str(type(exept)) + ' : ' + str(exept), sys.version_info)
            return self.action_result.set_status(phantom.APP_ERROR, TIFRONT_ERR_CMD_EXEC, exept)
        return self.action_result.set_status(phantom.APP_SUCCESS, TIFRONT_SUCC_CMD_EXEC)

    def _start_connection(self, action=None, host=None, port=None, user=None, password=None, hostname=None):
        prompt = hostname + TIFRONT_SSH_NORMAL_PROMPT
        try:
            self.pe = pexpect.spawn(TIFRONT_SSH_COMMAND.format(**locals()), timeout=TIFRONT_SSH_TIMEOUT)
            index = self.pe.expect([TIFRONT_SSH_PW_PROMPT, TIFRONT_SSH_PUBKEY_YN])
            if index == 1:
                self.pe.sendline("yes")
                self.pe.expect(TIFRONT_SSH_PW_PROMPT)
            self.pe.sendline(password)
            index = self.pe.expect([prompt, TIFRONT_SSH_PW_PROMPT])
            if index == 1:
                self.debug_print("Invalid Password!")
                self._cleanup()
                self.action_result.set_status(phantom.APP_ERROR, TIFRONT_ERR_CONNECTION_FAILED)
                return phantom.APP_ERROR
            if action == TIFRONT_JSON_ACTION_ID_TEST_CONNECTIVITY:
                self.pe.sendline("exit")
                self._cleanup()
                self.save_progress(TIFRONT_SUCC_CONNECTION_ESTABLISHED)
            self.debug_print("Login Successfully")
        except Exception as exept:
            self._cleanup()
            self.debug_print(str(type(exept)) + ' : ' + str(exept), sys.version_info)
            if action == TIFRONT_JSON_ACTION_ID_TEST_CONNECTIVITY:
                return phantom.APP_ERROR
            else:
                return self.action_result.set_status(phantom.APP_ERROR, TIFRONT_ERR_CONNECTION_FAILED, exept)
        if action == TIFRONT_JSON_ACTION_ID_TEST_CONNECTIVITY:
            return phantom.APP_SUCCESS
        else:
            return self.action_result.set_status(phantom.APP_SUCCESS, TIFRONT_SUCC_CONNECTION_ESTABLISHED)

    def _cleanup(self):
        self.pe.terminate()
        self.pe.expect(pexpect.EOF)
        return

    def _build_commands(self, action=None, acl_no=None, sip=None, dip=None, interface=None):
        if sip == TIFRONT_JSON_IP_ANY:
            sip = "any"
        else:
            sip = sip + "/32"
        if dip == TIFRONT_JSON_IP_ANY:
            dip = "any"
        else:
            dip = dip + "/32"
        commands = []
        commands.append("enable")
        commands.append("configure terminal")
        if action == TIFRONT_JSON_ACTION_ID_BLOCK_IP:
            commands.append("access-list {acl_no} deny any {sip} {dip}".format(**locals()))
            commands.append("no access-list {acl_no} permit any any any".format(**locals()))
            commands.append("access-list {acl_no} permit any any any".format(**locals()))
            commands.append("access-list {acl_no} interface {interface}".format(**locals()))
        elif action == TIFRONT_JSON_ACTION_ID_UNBLOCK_IP:
            commands.append("no access-list {acl_no} deny any {sip} {dip}".format(**locals()))
        commands.append("exit")
        commands.append("copy running-config startup-config")
        self.action_result.add_data(dict({"commands": commands}))
        return commands

    def _test_connectivity(self):
        config = self.get_config()
        self.save_progress(TIFRONT_PROG_USING_SWITCH_ADDRESS, switch_address=config[TIFRONT_JSON_SWITCH])
        status = self._start_connection(action=TIFRONT_JSON_ACTION_ID_TEST_CONNECTIVITY,
                                        host=config[TIFRONT_JSON_SWITCH],
                                        port=config[TIFRONT_JSON_SSH_PORT],
                                        user=config[TIFRONT_JSON_USERNAME],
                                        password=config[TIFRONT_JSON_PASSWORD],
                                        hostname=config[TIFRONT_JSON_HOSTNAME])
        if phantom.is_fail(status):
            self.append_to_message(TIFRONT_ERR_TEST_CONNECTIVITY_FAILED)
            return self.set_status(phantom.APP_ERROR)
        return self.set_status_save_progress(phantom.APP_SUCCESS, TIFRONT_SUCC_TEST_CONNECTIVITY_PASSED)

    def _unblock_ip(self, param):
        self.action_result = self.add_action_result(ActionResult(dict(param)))
        config = self.get_config()
        status = self._start_connection(host=config[TIFRONT_JSON_SWITCH],
                                        port=config[TIFRONT_JSON_SSH_PORT],
                                        user=config[TIFRONT_JSON_USERNAME],
                                        password=config[TIFRONT_JSON_PASSWORD],
                                        hostname=config[TIFRONT_JSON_HOSTNAME])
        if (not status) or phantom.is_fail(status):
            return self.action_result.get_status()
        commands = self._build_commands(action=TIFRONT_JSON_ACTION_ID_UNBLOCK_IP,
                                        acl_no=param[TIFRONT_JSON_ACL_NO],
                                        sip=param[TIFRONT_JSON_SRC_IP],
                                        dip=param[TIFRONT_JSON_DST_IP])
        status = self._send_commands(commands, config[TIFRONT_JSON_HOSTNAME])
        return self.action_result.get_status()

    def _block_ip(self, param):
        self.action_result = self.add_action_result(ActionResult(dict(param)))
        config = self.get_config()
        status = self._start_connection(host=config[TIFRONT_JSON_SWITCH],
                                        port=config[TIFRONT_JSON_SSH_PORT],
                                        user=config[TIFRONT_JSON_USERNAME],
                                        password=config[TIFRONT_JSON_PASSWORD],
                                        hostname=config[TIFRONT_JSON_HOSTNAME])
        if (not status) or phantom.is_fail(status):
            return self.action_result.get_status()
        commands = self._build_commands(action=TIFRONT_JSON_ACTION_ID_BLOCK_IP,
                                        acl_no=param[TIFRONT_JSON_ACL_NO],
                                        sip=param[TIFRONT_JSON_SRC_IP],
                                        dip=param[TIFRONT_JSON_DST_IP],
                                        interface=param[TIFRONT_JSON_INTERFACE])
        status = self._send_commands(commands, config[TIFRONT_JSON_HOSTNAME])
        return self.action_result.get_status()

    def handle_action(self, param):
        result = None
        action = self.get_action_identifier()
        if action == TIFRONT_JSON_ACTION_ID_BLOCK_IP:
            result = self._block_ip(param)
        elif action == TIFRONT_JSON_ACTION_ID_UNBLOCK_IP:
            result = self._unblock_ip(param)
        elif action == TIFRONT_JSON_ACTION_ID_TEST_CONNECTIVITY:
            result = self._test_connectivity()
        return result


if __name__ == '__main__':
    try:
        import simplejson as json
    except:
        pass

    import pudb
    pudb.set_trace()
    if len(sys.argv) < 2:
        print 'No test json specified as input'
        exit(0)
    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print json.dumps(in_json, indent='    ')
        connector = TifrontConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print ret_val
    exit(0)
