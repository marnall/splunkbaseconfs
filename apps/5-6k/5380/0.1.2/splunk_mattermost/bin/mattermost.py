import sys
import json
import requests


def send_notification(payload):
    settings = payload.get('configuration')

    # Check if channel exists
    if "channel" in settings:
        payload = "{\n \"channel\":\"" + settings.get(
            'channel') + "\", \n \"text\":\"" + settings.get('message') + "\"\n}"
    else:
        payload = "{\n \"text\":\"" + settings.get('message') + "\"\n}"
    headers = {'Content-Type': 'application/json'}

    response = requests.request("POST", settings.get(
        'url'), data=payload, headers=headers, verify=False)

    if response.status_code >= 300:
        print("ERROR return code was " +
              str(response.status_code), file=sys.stderr)
        return False

    print("Alert was successfully send response code " +
          str(response.status_code), file=sys.stderr)
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload_stdin = json.loads(sys.stdin.read())
        success = send_notification(payload_stdin)
        if not success:
            print("FATAL Failed trying to send Mattermost notification",
                  file=sys.stderr)
            sys.exit(2)
        else:
            print("INFO Mattermost notification successfully sent", file=sys.stderr)
    else:
        print("FATAL Unsupported execution mode (expected --execute flag)",
              file=sys.stderr)
        sys.exit(1)
