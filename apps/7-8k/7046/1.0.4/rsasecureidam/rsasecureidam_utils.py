# File: rsasecureidam_utils.py
#
# Copyright (c) 2023-2025 Splunk Inc.
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

import time

import paramiko
import phantom.app as phantom
import phantom.utils as ph_utils
from bs4 import UnicodeDammit

import rsasecureidam_consts as consts


class RSASecureIdAMUtils:
    def __init__(self, connector):
        self._connector = connector

    def _start_connection(self):
        self.hostname = self._connector.config["hostname"]
        self._username = self._connector.config["username"]
        self._password = self._connector.config["password"]

        self._connector.save_progress(f"Connecting to {self.hostname}")

        self._ssh_client = paramiko.SSHClient()
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if not ph_utils.is_ip(self.hostname):
            return False, "Please enter valid IP hostname"

        try:
            self._ssh_client.connect(
                hostname=self.hostname, username=self._username, password=self._password, allow_agent=False, look_for_keys=True, timeout=30
            )
        except Exception as e:
            return False, f"SSH connection attempt failed. Please enter valid values for asset parameters. {e!s}"

        return True, "SSH connection successful"

    def _send_command(self, action_result, input_data, timeout=0):
        """
        Args:
            command: command to send
            timeout: how long to wait before terminating program
        """
        # attempt to establish connection first
        status, msg = self._start_connection()
        if not status:
            return action_result.set_status(phantom.APP_ERROR, msg), []

        try:
            super_admin_user = self._connector.config.get("super_admin_user")
            super_admin_user_password = self._connector.config.get("super_admin_user_password")

            sftp = self._ssh_client.open_sftp()

            output = ""
            data = ""
            filename = int(time.time())
            input_file = f"ph_rsa_{filename}.csv"
            output_results_file = f"ph_rsa_results_{filename}.csv"
            output_file = f"ph_rsa_{filename}.log"
            output_reject_file = f"ph_rsa_rej_{filename}.csv"
            path = "/opt/rsa/am/utils/"
            if not (super_admin_user and super_admin_user_password):
                return action_result.set_status(phantom.APP_ERROR, "Please enter valid Super Admin Username and Password."), []
            command = consts.RSA_RUN_COMMAND.format(
                username=super_admin_user,
                password=super_admin_user_password,
                input_file=input_file,
                output_results_file=output_results_file,
                output_log_file=output_file,
                output_reject_file=output_reject_file,
            )
            command = consts.RSA_COMMAND_PATH + command

            sftp.chdir(path)
            try:
                f = sftp.file(input_file, "w", -1)
                f.write(input_data)
                f.close()
            except Exception as e:
                return action_result.set_status(phantom.APP_ERROR, f"Error in creating input file. {e!s}"), []

            trans = self._ssh_client.get_transport()
            self._shell_channel = trans.open_session()
            self._shell_channel.set_combine_stderr(True)

            self._shell_channel.exec_command(command)

            success, data, exit_status = self._get_output(timeout)

            if exit_status:
                if data.find("Error 2004:") != -1:
                    data = str(data).split(":")
                    data = data[1]
                    self._connector.save_progress("Authentication Error.", data)
                    sftp.remove(input_file)
                    return (
                        action_result.set_status(
                            phantom.APP_ERROR, "Authentication failed. Please enter valid Super Admin Username and Password"
                        ),
                        [],
                    )
                else:
                    log_file = sftp.file(output_file, "r")
                    logs = str(log_file.read())
                    if logs.find("Failure") != -1:
                        rej_data_file = sftp.file(output_reject_file, "r")
                        data = rej_data_file.read()
                        self._connector.debug_print(f"Logs for the action: {data}")
                        data = str(data.splitlines()[1].split(":"))[1]
                        rej_data_file.close()
                    log_file.close()

            self._connector.debug_print("Deleting output files")
            sftp.remove(input_file)
            sftp.remove(output_file)
            sftp.remove(output_reject_file)
            output += data

            if exit_status or (not success):
                return action_result.set_status(phantom.APP_ERROR, f"Error occured.\r\nOutput: {output}\r\nExit Status: {exit_status}"), []

            if self._connector.get_action_identifier() == "list_tokens":
                results_file = sftp.file(output_results_file, "r")
                tokens_data = results_file.read()
                token_list = self.parse_token_list(tokens_data)
                self._connector.debug_print(f"tokens::{token_list}")
                results_file.close()
                sftp.remove(output_results_file)
                return action_result.set_status(phantom.APP_SUCCESS), token_list

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error occured.\r\nDetails:{e}"), []

        return action_result.set_status(phantom.APP_SUCCESS), []

    def parse_token_list(self, tokens):
        token_list = list()
        for token_data in tokens.splitlines():
            data = {}
            token = token_data.decode("utf-8").split(",")
            data["token_serial"] = token[0]
            data["status"] = "Enabled" if (token[8] == "true") else "Disabled"
            token_list.append(data)

        return token_list

    def _get_output(self, timeout):
        """
        returns:
            success, data, exit_status
        """
        sendpw = True
        self._shell_channel.settimeout(2)
        self._shell_channel.set_combine_stderr(True)
        output = ""
        stime = int(time.time())

        try:
            while True:
                ctime = int(time.time())
                # data is ready to be received on the channel
                if self._shell_channel.recv_ready():
                    recv_output = UnicodeDammit(self._shell_channel.recv(8000)).unicode_markup
                    if recv_output:
                        output += recv_output
                    else:
                        break
                    if sendpw and self._password:
                        try:
                            self._shell_channel.send(f"{self._password}\n")
                        except OSError:
                            pass
                        sendpw = False
                elif timeout and ctime - stime >= timeout:
                    return False, "Error: Timeout", None
                elif self._shell_channel.exit_status_ready() and not self._shell_channel.recv_ready():
                    break
                time.sleep(1)
        except Exception as e:
            return False, "Error", str(e)

        return True, output, self._shell_channel.recv_exit_status()
