import ta_swimlane_declare
import traceback
import sys
import splunk.Intersplunk as view
from cmd_push_to_swimlane import CMDPushToSwimlane
import sw_constants


def main():
    stdin_data = sys.stdin.read()
    args = sys.argv
    try:
        cmd = CMDPushToSwimlane(stdin_data, args, sw_constants.SWIMLANE_APP_SPLUNK_NAME)
        cmd.run()
        return 0
    except Exception as e:
        view.parseError(traceback.format_exc())
        return 5


if __name__ == "__main__":
    exitcode = main()
    sys.exit(exitcode)
