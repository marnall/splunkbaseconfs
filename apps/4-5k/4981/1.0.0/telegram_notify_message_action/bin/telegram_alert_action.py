#!/bin/python

import requests
import sys
import json


def send_alert(message, bot_id, chat_id):
    url = 'https://api.telegram.org/bot' + bot_id + '/sendMessage'

    response = requests.post(url=url, data={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}).json()
    print(url)
    return response


def main():
    payload = json.loads(sys.stdin.read())
    config = payload.get('configuration', dict())
    bot_id = config.get('bot_id')
    title = config.get('title')
    message = config.get('message')
    severity = config.get('severity')
    chat_id = config.get('chat_id')
    warning = '\xE2\x9A\xA0'
    message = '{0} <b>{1}</b> {2}\n<b>SEVERITY:</b> {3}\n<b>MESSAGE:</b> {4}'.format(warning, title, warning, severity, message)
 
    send_alert(message, bot_id, chat_id)

if __name__ == "__main__":
    main()
