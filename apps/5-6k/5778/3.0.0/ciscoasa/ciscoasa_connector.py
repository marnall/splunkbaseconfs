# File: ciscoasa_connector.py
#
# Copyright (c) 2014-2022 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
#
# Phantom imports
import socket
import sys
from socket import inet_ntoa
from struct import pack

import paramiko
import phantom.app as phantom
from parse import parse
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# THIS Connector imports
from ciscoasa_consts import *


class CiscoasaConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(CiscoasaConnector, self).__init__()

        self._ssh_client = None
        self._shell_channel = None

    def _validate_access_list(self, access_list, direction, intf, acc_groups, action_result):

        # Access list entries are of the form
        # access-group <acc_list_name> <direction> interface <interface_name>

        for curr_acc_list in acc_groups:
            if len(curr_acc_list) == 0:
                continue

            # Check if the direction and interface name match
            acc_list_broken = curr_acc_list.split(' ')
            if len(acc_list_broken) < 5:
                continue

            if (direction == acc_list_broken[2]) and (intf == acc_list_broken[4]):
                # match, check the name
                if access_list == acc_list_broken[1]:
                    return action_result.set_status(phantom.APP_SUCCESS, CISCOASA_SUCC_ASA_FOUND_ACCESS_LIST)
                else:
                    # There is some other access-list for this interface and
                    # direction, we can't overwrite with this one
                    # error, return
                    return action_result.set_status(phantom.APP_ERROR, CISCOASA_ERR_ASA_DUPLICATE_ACCESS_LIST,
                            present_acl_name=acc_list_broken[1], intf=intf, direction=direction, acl_name=access_list)

        return action_result.set_status(phantom.APP_SUCCESS, CISCOASA_SUCC_ASA_ACCESS_LIST_NOT_FOUND)

    def _list_sessions(self):
        """ List users currently connected over webvpn
        """
        if phantom.is_fail(self._connect()):
            return self.get_status()

        action_result = self.add_action_result(ActionResult())

        cmd = "show vpn-sessiondb webvpn"
        status_code, cmd_output = self._send_command(cmd, action_result)
        if phantom.is_fail(status_code):
            return action_result.set_status(phantom.APP_ERROR, CISCOASA_ERR_CMD_EXEC)

        data = self._reformat_cmd_output(cmd_output)
        if data is None:
            return action_result.set_status(phantom.APP_ERROR, CISCOASA_ERR_ASA_INVALID_DATA_ACCESS_GROUP)

        self._parse_to_dict(data, action_result)
        if action_result.get_data()[0]['users']:
            return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrived user sessions")
        else:
            return action_result.set_status(phantom.APP_SUCCESS, "There are no active sessions")

    def _parse_to_dict(self, data, action_result):

        d = {}
        user_dict = {}
        d['users'] = []
        for line in data[3:]:           # Skip the first three lines
            if not line and user_dict:  # blank line, new user entry
                d['users'].append(user_dict)
                user_dict = {}
            self._add_line_to_dict(line.split(' : '), user_dict)
        action_result.update_summary({'total_users': len(d['users'])})
        action_result.add_data(d)
        return

    def _add_line_to_dict(self, line, d):

        if len(line) <= 1:
            return
        if len(line) == 2:
            d[line[0].replace(' ', '')] = line[1].strip()
            return
        else:
            mid = line[1].split()
            d[line[0].replace(' ', '')] = mid[0]
            line = line[2:]
            line[:0] = [' '.join(mid[1:])]
            return self._add_line_to_dict(line, d)

    def _terminate_session(self, param):

        if phantom.is_fail(self._connect()):
            return self.get_status()

        action_result = self.add_action_result(ActionResult(param))

        target = param[CISCOASA_JSON_IP_USERNAME]

        cmd = "vpn-sessiondb logoff name {}\n".format(target)
        status_code, cmd_output = self._send_command(cmd, action_result)
        if phantom.is_fail(status_code):
            return action_result.set_status(phantom.APP_ERROR, CISCOASA_ERR_CMD_EXEC)

        data = self._reformat_cmd_output(cmd_output)
        try:
            num = int(data[1].split(':')[-1])
            if num == 0:
                return action_result.set_status(phantom.APP_SUCCESS, "No such user is logged in")
        except:
            output = data[1].split(':')
            if output[0] == "ERROR":
                return action_result.set_status(phantom.APP_ERROR, "Invalid input")

        action_result.update_summary({"sessions_terminated": num})
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully terminated session")

    def _is_online(self, target, action_result):
        cmd = "show vpn-sessiondb webvpn filter name {}".format(target)
        status_code, cmd_output = self._send_command(cmd, action_result)
        if phantom.is_fail(status_code):
            return action_result.set_status(phantom.APP_ERROR, CISCOASA_ERR_CMD_EXEC)

        data = self._reformat_cmd_output(cmd_output)
        try:
            if data[0].split(':')[0] == "INFO":
                return action_result.set_status(phantom.APP_SUCCESS, "User is not logged in")
        except:
            if data[1].split(':')[0] == "ERROR":
                return action_result.set_status(phantom.APP_ERROR, "Invalid input")

    def _block_ip(self, param, delete, action_result):

        """Function that implements the block_ip action for an ASA box

            Args:
                The param for the action
                The boolean stating wheather to delete a block ip rule or not
                The action_result that will hold all the status

            Return:
                Status code
                Data returned by the command
        """

        cmd_output = None
        # both the src and dest can't be any
        src = phantom.get_str_val(param, CISCOASA_JSON_SRC, 'any')
        dest = phantom.get_str_val(param, CISCOASA_JSON_DEST, 'any')

        if ((param[CISCOASA_JSON_SRC] == CISCOIOS_CONST_ANY) and (param[CISCOASA_JSON_DEST] == CISCOIOS_CONST_ANY)):
            return (action_result.set_status(phantom.APP_ERROR, CISCOASA_ERR_ASA_SRC_DEST_ANY), None)

        # get the config into vars
        access_list = param[CISCOASA_JSON_ACCESS_LIST]
        direction = param[CISCOASA_JSON_DIRECTION]
        intf = param[CISCOASA_JSON_INTERFACE]

        # First get the access-list for the given direction+interface combination
        cmd_to_run = "show running-config access-group"
        status_code, cmd_output = self._send_command(cmd_to_run, action_result)
        if phantom.is_fail(status_code):
            return (action_result.set_status(phantom.APP_ERROR, CISCOASA_ERR_CMD_EXEC), cmd_output)

        # create a python list of acc lists
        data_to_parse = self._reformat_cmd_output(cmd_output)
        if data_to_parse is None:
            return (action_result.set_status(phantom.APP_ERROR, CISCOASA_ERR_ASA_INVALID_DATA_ACCESS_GROUP), cmd_output)

        # Now we need to validate the access-list name
        ret_code = self._validate_access_list(access_list, direction, intf, data_to_parse, action_result)

        if phantom.is_fail(ret_code):
            self.debug_print("acl validation failed")
            return (action_result.get_status(), None)

        # Set the boolean which specifies if we need to create the access group or not
        create_access_group = False
        if ret_code == CISCOASA_SUCC_ASA_ACCESS_LIST_NOT_FOUND:
            create_access_group = True

        # Things get a bit different when the access-list is to be deleted
        if delete is True:
            # Should not create the access group
            create_access_group = False

        self.save_progress(CISCOASA_PROG_ACCESS_LIST_VALIDATED)

        # First we will require to go into the configure terminal
        cmd_to_run = "configure terminal"
        status_code, cmd_output = self._send_command(cmd_to_run, action_result)
        if phantom.is_fail(status_code):
            return (action_result.set_status(phantom.APP_ERROR, CISCOASA_ERR_CMD_EXEC), cmd_output)

        self.save_progress(CISCOIOS_PROG_EXECUTED_CMD, cmd_to_run)

        # now set the terminal width to 511 anything more than that and things fail
        cmd_to_run = "terminal width 511"
        status_code, cmd_output = self._send_command(cmd_to_run, action_result)

        # We don't mind if this command fails
        self.save_progress(CISCOIOS_PROG_EXECUTED_CMD, cmd_to_run)

        # The actual command on the ASA box is of the form:
        # [no] access-list <acl_name> line <line#> extended deny ip
        # <src_ip> <src_mask>
        # <dest_ip> <dest_mask>
        # default line to 1
        line = phantom.get_str_val(param, CISCOASA_JSON_LINE, 1)
        action_result.update_param({CISCOASA_JSON_LINE: line})

        # acc_list = "access-list {} line {} extended deny ip {} ".format( access_list, line, src)
        acc_list = "access-list %s " % access_list

        if delete is False:
            acc_list += "line %s " % line

        acc_list += "extended deny ip %s " % self._get_network_string(src)

        if delete is True:
            acc_list = "no " + acc_list

        # Add the dest ip
        acc_list += ' ' + self._get_network_string(dest)

        self.save_progress(CISCOIOS_PROG_EXECUTING_CMD, acc_list)

        status_code, cmd_output = self._send_command(acc_list, action_result)

        if phantom.is_fail(status_code):
            return (action_result.set_status(phantom.APP_ERROR, CISCOASA_ERR_CMD_EXEC), cmd_output)

        if len(cmd_output) > 0:
            self.save_progress(CISCOASA_PROG_GOT_TEXT, cmd_output)

        if create_access_group is True:
            # Have to create the access-group
            # The format is:
            # access-group <acl_name> <direction> interface <interface_name>
            acc_group = "access-group {} {} interface {} ".format(access_list, direction, intf)

            self.save_progress(CISCOIOS_PROG_EXECUTING_CMD, acc_group)

            status_code, cmd_output = self._send_command(acc_group, action_result)

            if phantom.is_fail(status_code):
                return (action_result.set_status(phantom.APP_ERROR, CISCOASA_ERR_CMD_EXEC), cmd_output)

            self.save_progress(CISCOIOS_PROG_EXECUTED_CMD, acc_group)

            if len(cmd_output) > 0:
                self.save_progress(CISCOASA_PROG_GOT_TEXT, cmd_output)

        return (action_result.get_status(), cmd_output)

    def _handle_block_ip(self, param, delete=False):

        if phantom.is_fail(self._connect()):
            return self.get_status()

        action_result = self.add_action_result(ActionResult(dict(param)))

        ip_to_block = param[CISCOASA_JSON_DEST]
        action_result.update_param({CISCOASA_JSON_DEST: ip_to_block})
        status_code, cmd_output = self._block_ip(param, delete, action_result)

        self.debug_print("status_code", status_code)
        self.debug_print("cmd_output", cmd_output)

        if phantom.is_fail(self._get_cmd_output_status(cmd_output)):
            action_result.set_status(phantom.APP_ERROR)
            if cmd_output:
                action_result.append_to_message(CISCOASA_MSG_FROM_DEVICE)
                action_result.append_to_message(self._reformat_cmd_output(cmd_output, rem_command=False,
                            to_list=False))

        return action_result.get_status()

    def validate_ip(self, param):
        if param == 'any':
            return True

        if phantom.is_ip(param):
            return True
        elif '/' in param:
            cidr = param.split('/')
            if phantom.is_ip(cidr[0]) and int(cidr[1]) in range(0, 33):
                return True

        return False

    def initialize(self):
        """Don't use BaseConnector's validations, for ip use our own
        """
        self.set_validator("ip", self.validate_ip)
        return phantom.APP_SUCCESS

    def _wait_for_data(self, size):
        """Waits till we have some data
        """
        # The first timeout is one value, most probably large

        self._shell_channel.settimeout(FIRST_RECV_TIMEOUT)
        output = ""

        while (1):
            try:

                data = self._shell_channel.recv(size)

                data = data.decode()
                output += data

                # The next timeout is a smaller value
                self._shell_channel.settimeout(SECOND_ONWARDS_RECV_TIMEOUT)
            except socket.timeout:
                break
            except:
                return (phantom.APP_ERROR, None, sys.exc_info()[0])

        return (phantom.APP_SUCCESS, output, None)

    def _connect(self):

        if self._shell_channel is not None:
            return phantom.APP_SUCCESS

        enable_password = self.get_config()[CISCOIOS_JSON_ENABLE_PASSWORD]

        # start the connection
        status_code = self._start_connection()

        if phantom.is_fail(status_code):
            return status_code

        cmd_to_run = 'enable'
        self.save_progress(CISCOIOS_PROG_EXECUTING_CMD, cmd_to_run)
        status_code, cmd_output = self._send_command(cmd_to_run, self)
        if phantom.is_fail(status_code):
            return status_code

        self.save_progress(CISCOIOS_PROG_SENDING_ENABLE_CREDENTIALS)
        status_code, cmd_output = self._send_command(enable_password, self)
        if phantom.is_fail(status_code):
            return status_code

        # Need to validate the text output for this command
        self.debug_print('status_code: ', status_code)
        self.debug_print('cmd_output: ', cmd_output)

        if cmd_output.lower().find('invalid password') != -1:
            self.set_status(phantom.APP_ERROR, CISCOIOS_ERR_ENABLE_COMMAND_LOGIN_FAILED)
            self.append_to_message(CISCOIOS_MSG_CHECK_YOUR_CREDENTIALS)
            return

        # "Set terminal pager"
        cmd_to_run = 'terminal pager 0'
        self.save_progress(CISCOIOS_PROG_EXECUTING_CMD, cmd_to_run)
        status_code, cmd_output = self._send_command(cmd_to_run, self)
        if phantom.is_fail(status_code):
            return status_code

        # Re-init the self status to Error, required for further processing
        self.set_status(phantom.APP_ERROR)
        return phantom.APP_SUCCESS

    def _start_connection(self):
        """Starts the shell
        """

        config = self.get_config()
        server = config[phantom.APP_JSON_DEVICE]
        user = config[phantom.APP_JSON_USERNAME]
        password = config[phantom.APP_JSON_PASSWORD]

        self._ssh_client = paramiko.SSHClient()
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the asa box
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, server)

        try:
            self._ssh_client.connect(hostname=server, username=user, password=password,
                    allow_agent=False, look_for_keys=False)
        except Exception as e:
            return self.set_status(phantom.APP_ERROR, CISCOIOS_ERR_SSH_CONNECTION_FAILED, e)

        try:
            self._shell_channel = self._ssh_client.invoke_shell()
        except Exception as e:
            self._ssh_client.close()
            return self.set_status(phantom.APP_ERROR, CISCOIOS_ERR_SSH_CONNECTION_FAILED, e)

        ret_code, output, exc = self._wait_for_data(MAX_RECV_BYTES_TO_READ)

        if phantom.is_fail(ret_code):
            self.set_status(phantom.APP_ERROR, CISCOIOS_ERR_READ_FROM_SERVER_FAILED, exc)
            if output:
                self.append_to_message(output)

            return self.get_status()

        return phantom.APP_SUCCESS

    def _send_command(self, command, result):
        """Send a command to the server on the provided channel

            Args:
                The command to send
                The MAX size of data to recv
                The object to use to store the status

            Return:
                The status code
                The recieved data
        """

        size = MAX_RECV_BYTES_TO_READ

        # Set the required timeout for the send
        self._shell_channel.settimeout(SECOND_ONWARDS_RECV_TIMEOUT)
        try:
            self._shell_channel.send(command + "\n")
        except Exception as e:
            # "Command send failed"
            return (result.set_status(phantom.APP_ERROR, CISCOIOS_ERR_SHELL_SEND_COMMAND, e, command), None)

        # Get the data
        ret_code, output, exc = self._wait_for_data(size)

        if phantom.is_fail(ret_code):
            result.set_status(phantom.APP_ERROR, CISCOIOS_ERR_READ_FROM_SERVER_FAILED, exc)

        return (result.set_status(phantom.APP_SUCCESS, CISCOIOS_SUCC_CMD_EXEC), output)

    def _reformat_cmd_output(self, cmd_output, rem_command=True, to_list=True):

        if cmd_output is None:
            return None

        try:
            data_lines = cmd_output.splitlines()

            # Remove the last line, it's going to be the prompt
            data_lines.pop()

            # Remove the first line that is the command
            if rem_command:
                del data_lines[0]

            if to_list:
                return data_lines
        except:
            return None

        return ('\r\n'.join(data_lines))

    def _get_cmd_output_status(self, cmd_output):

        if not cmd_output:
            return phantom.APP_SUCCESS

        if cmd_output.find('ERROR:') != -1:
            return phantom.APP_ERROR

        if cmd_output.find('Invalid input detected at ') != -1:
            return phantom.APP_ERROR

        return phantom.APP_SUCCESS

    def _get_network_string(self, ip_str):

        ip_str = ip_str.strip()

        if ip_str == CISCOIOS_CONST_ANY:
            return ip_str

        if ip_str.find('/') == -1:
            # it's not in cidr format, so just add the mask for the ip
            return ip_str + ' 255.255.255.255'

        # need to convert to the proper netmask
        ip_str_parsed = parse("{ip}/{mask}", ip_str)

        mask = int(ip_str_parsed['mask'])

        bits = 0xffffffff ^ (1 << 32 - mask) - 1
        net_str = inet_ntoa(pack('>I', bits))

        return '{0} {1}'.format(ip_str_parsed['ip'], net_str)

    def _get_version(self):
        """Function that executes the show version command on the asa box

        Args:

        Return:
            Status code
        """

        if phantom.is_fail(self._connect()):
            return self.get_status()

        # Create the action_result to store status
        action_result = self.add_action_result(ActionResult())

        cmd_to_run = "show version"
        status_code, cmd_output = self._send_command(cmd_to_run, action_result)
        if phantom.is_fail(status_code):
            return action_result.get_status()

        curr_data = action_result.add_data({})
        curr_data[CISCOIOS_JSON_CMD] = cmd_to_run
        cmd_output = self._reformat_cmd_output(cmd_output, rem_command=True, to_list=False)
        curr_data[CISCOIOS_JSON_OUTPUT] = cmd_output

        self.save_progress(CISCOIOS_PROG_EXECUTED_CMD, cmd_to_run)

        return action_result.set_status(phantom.APP_SUCCESS, CISCOIOS_SUCC_CMD_EXEC)

    def _test_asset_connectivity(self, param):

        if phantom.is_fail(self._connect()):
            self.debug_print("connect failed")
            self.save_progress(CISCOIOS_ERR_CONNECTIVITY_TEST)
            return self.append_to_message(CISCOIOS_ERR_CONNECTIVITY_TEST)

        self.debug_print("connect passed")
        return self.set_status_save_progress(phantom.APP_SUCCESS, CISCOIOS_SUCC_CONNECTIVITY_TEST)

    def _get_config(self):
        """Function that executes the show run command on the asa box

            Args:

            Return:
                Status code
        """

        if phantom.is_fail(self._connect()):
            return self.get_status()

        # Create the action_result to store status
        action_result = self.add_action_result(ActionResult())

        cmd_to_run = "show run"
        status_code, cmd_output = self._send_command(cmd_to_run, action_result)
        if phantom.is_fail(status_code):
            return action_result.get_status()

        curr_data = action_result.add_data({})
        curr_data[CISCOIOS_JSON_CMD] = cmd_to_run
        cmd_output = self._reformat_cmd_output(cmd_output, rem_command=True, to_list=False)
        curr_data[CISCOIOS_JSON_OUTPUT] = cmd_output

        self.save_progress(CISCOIOS_PROG_EXECUTED_CMD, cmd_to_run)

        cmd_to_run = "show switch vlan"
        status_code, cmd_output = self._send_command(cmd_to_run, action_result)
        if phantom.is_fail(status_code):
            return action_result.get_status()

        curr_data = action_result.add_data({})
        curr_data[CISCOIOS_JSON_CMD] = cmd_to_run
        cmd_output = self._reformat_cmd_output(cmd_output, rem_command=True, to_list=False)
        curr_data[CISCOIOS_JSON_OUTPUT] = cmd_output

        self.save_progress(CISCOIOS_PROG_EXECUTED_CMD, cmd_to_run)

        return action_result.set_status(phantom.APP_SUCCESS, CISCOIOS_SUCC_CMD_EXEC)

    def _cleanup(self):

        if self._ssh_client:
            # Close the ssh connection
            self._ssh_client.close()
            self._ssh_client = None

        self._shell_channel = None

    def finalize(self):
        self._cleanup()

    def handle_exception(self, e):
        self._cleanup()

    def handle_action(self, param):
        """Function that handles all the actions

            Args:

            Return:
                A status code
        """

        action = self.get_action_identifier()

        # Now each individual actions
        if action == ACTION_ID_GET_CONFIG:
            self._get_config()
        elif action == ACTION_ID_GET_VERSION:
            self._get_version()
        elif action == ACTION_ID_LIST_SESSIONS:
            self._list_sessions()
        elif action == ACTION_ID_TERMINATE_SESSION:
            self._terminate_session(param)
        elif action == ACTION_ID_BLOCK_IP:
            self._handle_block_ip(param)
        elif action == ACTION_ID_UNBLOCK_IP:
            self._handle_block_ip(param, True)
        elif action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            self._test_asset_connectivity(param)
        return self.get_status()


if __name__ == '__main__':

    try:
        import simplejson as json
    except:
        pass
    import pudb
    pudb.set_trace()

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=' ' * 4))

        connector = CiscoasaConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(ret_val)

    sys.exit(0)
