from core.app_api_client import AppApiClient


class InputsCopierTool:
    """
    Tool for copying inputs from one connection to another.
    """

    def __init__(self, app_api_client: AppApiClient):
        self.app_api_client = app_api_client

    def copy_by_connection(self, from_connection_name: str,
        to_connection_name: str):
        success = []
        failures = []
        inputs = self.app_api_client.get_inputs(from_connection_name)

        if inputs == []:
            print("No inputs found.")
            return success, failures

        action = self._review(inputs)

        if action != "yes":
            print("Copy operation cancelled.")
            return success, failures

        for _input in inputs:
            copied = self._copy(_input, to_connection_name)
            if copied:
                success.append(_input["name"])
            else:
                failures.append(_input["name"])

        return success, failures

    @staticmethod
    def _review(inputs: list):
        print("\nReview the list of inputs that will be copied:")
        count = 1
        for _input in inputs:
            print(f"{count}. {_input['name']}")
            count += 1

        action = input(
            "\nDo you want to continue with the copying process? (yes/no): ")

        return action.strip().lower()

    def _copy(self, _input: dict, to_connection_name: str):
        print(f"\nCopying input {_input['name']}...")
        if _input["mode"] == "rising":
            self._set_checkpoint(_input)

        _input["name"] = f"{_input['name']}-{to_connection_name}"
        _input["connection"] = to_connection_name

        response = self.app_api_client.create_input(_input)

        if response is not None:
            print(f"Input {_input['name']} created successfully.")
            return True
        else:
            print(f"Input {_input['name']} failed to be created.")
            return False

    def _set_checkpoint(self, _input: dict):
        checkpoint = self.app_api_client.get_checkpoint(_input["name"])

        if checkpoint is None:
            print(f"Checkpoint not found for {_input['name']}")
        else:
            _input["checkpoint"] = {"value": checkpoint["value"],
                                    "columnType": checkpoint["columnType"]}
