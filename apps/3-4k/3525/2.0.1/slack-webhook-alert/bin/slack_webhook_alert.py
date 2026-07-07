import requests
import sys
import json


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        event = json.load(sys.stdin)

        slack_webhook = event['configuration']['slack_webhook']
        slack_message = event['configuration']['slack_message']

        requests.post(slack_webhook, data=json.dumps({'text': slack_message}))
