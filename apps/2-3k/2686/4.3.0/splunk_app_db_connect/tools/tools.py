import getpass

from core.app_api_client import AppApiClient
from core.splunk_api_client import SplunkApiClient
from inputs_copier_tool import InputsCopierTool
from config import Config


def choose_tool():
    while True:
        print("\nTools:")
        print("1. Copying inputs from one connection to another")
        print("2. Exit")

        choice = input("Choose a tool (1-2): ")

        if choice == "1":
            start_input_copier_tool()
        elif choice == "2":
            break
        else:
            print("Invalid choice. Please try again.")


def start_input_copier_tool():
    from_connection_name = input(
        "Enter the name of the connection to copy from: ")
    to_connection_name = input("Enter the name of the connection to copy to: ")

    if from_connection_name == "" or to_connection_name == "":
        print("\n✗ No connection names provided.")
        return

    app_api_client = AppApiClient(Config.HOST, Config.APP_PORT, Config.SESSION_KEY)
    inputs_copier_tool = InputsCopierTool(app_api_client)

    success, failures = inputs_copier_tool.copy_by_connection(
        from_connection_name, to_connection_name)

    print("\nSummary:")
    print("✓ Successfully:", success)
    print("✗ Failures:", failures)


if __name__ == "__main__":
    print("=" * 40)
    print("=== Splunk DB Connect - Tools v1.0.0 ===")
    print("=" * 40)

    Config.HOST = input("Enter host [localhost]: ") or Config.HOST
    Config.SPLUNK_PORT = input("Enter Splunk management port [8089]: ") or Config.SPLUNK_PORT
    username = input("Enter Splunk username: ")
    password = getpass.getpass("Enter Splunk password: ")
    Config.APP_PORT = input("Enter Splunk DB Connect port [9998]: ") or Config.APP_PORT

    splunk_api_client = SplunkApiClient(Config.HOST, Config.SPLUNK_PORT, username, password)
    Config.SESSION_KEY = splunk_api_client.get_session_key()

    if Config.SESSION_KEY is None:
        print("\n✗ Failed to obtain the session key.")
    else:
        choose_tool()
