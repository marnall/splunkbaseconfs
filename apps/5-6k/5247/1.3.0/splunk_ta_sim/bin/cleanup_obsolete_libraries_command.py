#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2011-2024 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License'): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import sys
import logging
import uuid
import shutil
import time
import json
import requests

current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, '..', 'libs'))
sys.path.append(os.path.join(current_path, '..', 'libs', 'external'))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration  # noqa: E402

CAPABILITY_ADMIN_ALL_OBJECTS = 'admin_all_objects'


@Configuration()
class CleanupObsoleteLibrariesCommand(GeneratingCommand):
    DIRECTORIES_TO_REMOVE = [
        'defusedxml', 'requests', 'simlib', 'solnlib', 'sortedcontainers', 'splunklib'
    ]

    class LoggerContextFilter(logging.Filter):
        """
        This is a filter which injects command invocation instance UUID in the logs.
        """
        request_id = uuid.uuid4().hex

        def filter(self, record):
            record.request_id = self.request_id
            return True

    def generate(self):
        self.logger.addFilter(self.LoggerContextFilter())
        data_to_return = {}
        try:
            self.validate_user_access_before_running_command()
            directory_list = os.listdir(os.path.join(current_path, '..', 'libs'))
            self.logger.debug(f"The list of present directories are: {directory_list}")
            directories_to_remove = list(
                set(self.DIRECTORIES_TO_REMOVE).intersection(directory_list)
            )
            if directories_to_remove:
                self.logger.info('Found obsolete directories, removing those directories.')
                self.remove_directories(directories_to_remove)
                self.logger.info('Completed cleaning up obsolete directories.')
                data_to_return['_raw'] = 'Completed cleaning up obsolete directories.'
                data_to_return['directories'] = directories_to_remove
            else:
                self.logger.info('No Action Needed.')
                data_to_return['_raw'] = 'No Action Needed.'
            data_to_return['_time'] = time.time()
            data_to_return['log_level'] = 'INFO'
        except Exception as e:
            data_to_return['_raw'] = str(e)
            data_to_return['log_level'] = 'ERROR'
            data_to_return['_time'] = time.time()
            self.logger.error(data_to_return)
            self.write_command_error(str(data_to_return['_raw']))
        finally:
            self.logger.info(data_to_return)
            yield data_to_return

    def remove_directories(self, directory_list):
        """This method loops through each directory to remove and remove it
        Args:
            directory_list (list): List of directories to be removed

        Raises:
            e: Raises Exception if any error occurs while removing directory
        """
        try:
            for directory_name in directory_list:
                dir_path = os.path.join(current_path, '..', 'libs', directory_name)
                if os.path.exists(dir_path):
                    self.logger.debug(f"Trying to remove {dir_path}")
                    shutil.rmtree(dir_path)
                    self.logger.debug(f"Sucessfully removed {dir_path}")
                else:
                    self.logger.error(f"Directory {dir_path} doesn't exists")
        except Exception as e:
            self.logger.error(f"Failed to remove directories, error: {e}")
            raise e

    def fetch_user_capabilities(self, username, session_key):
        """Fetches user capabilities for the username provided

        Args:
            username (str): Username for which to fetch capabilities
            session_key (str): Session Key

        Raises:
            e, Exception: Exception if any error occurs while fetching the user capability

        Returns:
            list: list of capabilities of given username
        """
        getargs = {'output_mode': 'json'}
        uri = (
            f'{self.service.scheme}://{self.service.host}:{self.service.port}'
            f'/services/authentication/users/{username}'
        )
        headers = {
            'Authorization': f'Splunk {session_key}',
            'Content-Type': 'application/json'
        }
        try:
            response = requests.get(
                uri,
                params=getargs,
                verify=False,
                headers=headers
            )
            content = response.content
        except Exception as e:
            self.logger.error(f'Error while polling splunkd: {e}')
            self.logger.exception(e)
            raise e

        if response.status_code != 200:
            message = f'Error while polling Splunkd. Response: "{response}". Content: "{content}"'
            self.logger.error(message)
            raise Exception(message)

        user_access_details = json.loads(content)
        capabilities = user_access_details['entry'][0]['content']['capabilities']
        self.logger.debug(f'Fetched user access details for user "{username}".')

        return capabilities

    def is_user_capable(self):
        """Checking if the current user has appropriate capability to run the command. We need
        admin_all_objects in order to make sure we only those users can remove the directories.

        Raises:
            Exception: Raises an exception if the user do not have the admin_all_object capability.

        Returns:
            bool: whether the current user is capable of running command
        """
        user_is_capable = False
        username = self.metadata.searchinfo.username
        try:
            user_capabilities = self.fetch_user_capabilities(username, self.service.token)
            assert type(user_capabilities) is list
            message = f'Capabilities for "{username}" are "{json.dumps(user_capabilities)}".'
            self.logger.debug(message)

            if CAPABILITY_ADMIN_ALL_OBJECTS not in user_capabilities:
                message = f'"{username}" is not capable of "{CAPABILITY_ADMIN_ALL_OBJECTS}".'
                self.logger.info(message)
            else:
                self.logger.info(f'"{username}" is capable of "{CAPABILITY_ADMIN_ALL_OBJECTS}".')
                user_is_capable = True

        except Exception as e:
            message = f'Failed to check for user capability {CAPABILITY_ADMIN_ALL_OBJECTS}, {e}'
            self.logger.error(message)
            raise Exception(message)

        return user_is_capable

    def validate_user_access_before_running_command(self):
        """Will check whether user meets following criteria:
        1. Has admin_all_objects capability

        Raises:
            Exception: Raises an exception if the user do not have valid access before running
            cleanup command
        """

        # validate user has required capability to proceed
        user_is_capable = self.is_user_capable()
        if not user_is_capable:
            error_msg = (
                f'Access denied. Current user is missing '
                f'"{CAPABILITY_ADMIN_ALL_OBJECTS}" capability.'
            )
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def write_command_error(self, message):
        """Outputs given message in case any error occurs while executing the command

        Args:
            message (str): Description of the error message
        """
        message = f'Error in "cleanup" command: {message}'
        self.write_error(message)


dispatch(CleanupObsoleteLibrariesCommand, sys.argv, sys.stdin, sys.stdout, __name__)
