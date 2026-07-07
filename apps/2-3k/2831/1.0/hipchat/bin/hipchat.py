# send splunk results to hipchat

import prettytable
import ConfigParser
import requests
import json
import os
import sys
import splunk.Intersplunk as sis
(a, kwargs) = sis.getKeywordsAndOptions()
TRUE_VALUES = ['true', '1', 't', 'y', 'yes']

def get_pretty_table(results, msg_fmt):
    if results:
        keys = results[0].keys()
    else:
        return ''
    x = prettytable.PrettyTable(keys, padding_width=4)
    for row in results:
        x.add_row([row[k] for k in keys])
    return x.get_string() if msg_fmt == 'text' else x.get_html_string()


def main():
    # get config from config file
    config = ConfigParser.ConfigParser()
    config.readfp(open(os.path.join('..', 'default', 'hipchat.conf')))

    # update args if user speicify them in search
    room    = kwargs.get('room', config.get('default', 'room'))
    color   = kwargs.get('color', config.get('default', 'color'))
    notify  = kwargs.get('notify', config.get('default', 'notify'))
    msg_fmt = kwargs.get('message_format', 
                         config.get('default', 'message_format'))

    if config.get('default', 'allow_users_set_base_url').lower() in TRUE_VALUES:
        base_url = kwargs.get('base_url', config.get('default', 'base_url'))
    else:
        base_url = config.get('default', 'base_url')

    # check if auth token is set properly
    try:
        auth_token = {"auth_token": config.get(room, 'auth_token')}
    except ConfigParser.NoSectionError as e:
        raise Exception("Room not set, please set the room stanza")
    except ConfigParser.NoOptionError as e:
        raise Exception("Auth token not set, please set auth token for room")

    # construct url
    url = base_url + "{s}{r}/notification".format(
        s='' if base_url.endswith('/') else '/', r=room)

    # read search results
    results = sis.readResults(None, None, True)

    # prepare data to be sent
    data = {
        'message': get_pretty_table(results, msg_fmt),
        'message_format': msg_fmt,
        'color': color,
        'notify': notify.lower() in TRUE_VALUES
    }

    # send data
    headers = {'Content-type': 'application/json'}
    r = requests.post(url, 
        data=json.dumps(data), 
        params=auth_token, 
        headers=headers)

    if r.status_code == 204:
        sis.outputResults(results)
    else:
        err_msg = ("Error sending results to slack, reason: {r}, {t}".format( 
                    r=r.reason, t=r.text))
        sis.generateErrorResults(err_msg)

try:
    main()
except Exception, e:
    import traceback
    stack =  traceback.format_exc()
    sis.generateErrorResults("Error '{e}'".format(e=e))
