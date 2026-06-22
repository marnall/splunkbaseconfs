# File: infoblox_nios_connector.py
#
# Copyright 2025 Infoblox Inc.
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
# Standard library imports
import importlib
import json
import sys

# Phantom imports
import phantom.app as phantom
import requests
from phantom.base_connector import BaseConnector

# Local imports
import infoblox_nios_consts as consts
from infoblox_nios_utils import InfobloxNIOSUtils, Validator


class InfobloxNIOSConnector(BaseConnector):
    """Infoblox NIOS connector class that inherits the BaseConnector.

    This connector supports the test connectivity action for Infoblox NIOS.
    """

    def __init__(self):
        """Initialize the connector with required parameters."""
        # Calling the BaseConnector's init function
        super().__init__()

        self._url = None
        self._username = None
        self._password = None
        self.validator = None
        self._verify = False
        self._session_id = None
        self.utils = None
        self.validator = None
        return

    def initialize(self):
        """Initialize connector with configuration parameters.

        This function MUST return a value of either phantom.APP_SUCCESS or phantom.APP_ERROR.
        """
        # Load configuration
        config = self.get_config()

        # Access configuration parameters
        self._url = config[consts.CONFIG_URL]
        self._username = config[consts.CONFIG_USERNAME]
        self._password = config[consts.CONFIG_PASSWORD]
        self._verify = config.get(consts.CONFIG_VERIFY_SERVER_CERT, False)

        # Initialize utility and validator objects
        self.utils = InfobloxNIOSUtils(self)
        self.validator = Validator()

        # Initialize validator object
        self.validator = Validator()

        return phantom.APP_SUCCESS

    def handle_action(self, param):
        """Handle the flow of execution, calls the appropriate method for the action.

        This method retrieves the action identifier for the current App Run and imports
        the corresponding action module. It then searches for the appropriate action class
        within the imported module and creates an instance of it. Finally, it executes
        the action by calling the `execute` method of the action instance.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """
        action_id = self.get_action_identifier()
        self.debug_print("Action id", action_id)

        try:
            # Import the action module
            module_name = f"actions.infoblox_nios_{action_id}"
            importlib.import_module(module_name)

            # Find all subclasses of BaseAction
            from actions import BaseAction

            base_action_sub_classes = BaseAction.__subclasses__()
            self.debug_print(f"Finding action module: {module_name}")

            # Find the matching action class and execute it
            for action_class in base_action_sub_classes:
                if action_class.__module__ == module_name:
                    action = action_class(self, param)
                    return action.execute()

            self.debug_print("Action class not found")
            return self.set_status(phantom.APP_ERROR, f"Action {action_id} is not implemented")

        except ImportError as e:
            self.debug_print(f"Failed to import action module {module_name}: {e}")
            return self.set_status(phantom.APP_ERROR, f"Action {action_id} is not implemented")
        except Exception as e:
            error_message = self.utils.get_error_message_from_exception(e)
            self.debug_print(f"Exception occurred: {error_message}")
            return self.set_status(phantom.APP_ERROR, f"Error occurred: {error_message}")

    def finalize(self):
        """This function gets called once all the param dictionary elements are looped over.

        It gives the AppConnector a chance to do final cleanup before exiting.
        """
        return phantom.APP_SUCCESS


def main():
    """Main function that creates the InfobloxNIOSConnector object."""
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument("input_json", help="Input JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

    args = argparser.parse_args()
    session_id = None

    if args.username and args.password:
        try:
            login_url = f"{args.input_json}/_session"
            r = requests.post(login_url, auth=(args.username, args.password), verify=args.verify)
            session_id = r.text
        except Exception as e:
            print(f"Error creating session: {e!s}")
            sys.exit(1)

    with open(args.input_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        if session_id:
            in_json["config"]["session_id"] = session_id

        connector = InfobloxNIOSConnector()
        connector.print_progress_message = True

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
