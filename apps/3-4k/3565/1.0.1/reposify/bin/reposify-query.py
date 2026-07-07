#!/usr/bin/env python

# Standard library imports
import sys
import re
import datetime
import json
import time
import inspect

# Splunk imports
import splunk.Intersplunk
import splunk.entity

# Reposify imports
import reposify.reposify
import reposify.exceptions

MSG_USAGE = (
    "Usage: reposify filters=KEY1:VALUE1[+KEY2:VALUE2+...] banner=BANNER_STRING [page=<int> token=TOKEN]"
    "[page=<int> token=TOKEN]"
)
# Error messages
MSG_REQUIRED_PARAMETER = (
    'The "reposify" command requires at least '
    'one parameter.'
)
MSG_UNSUPPORTED_ARGUMENT = 'Argument %s is not supported'
MSG_UNSUPPORTED_PARAMETER = 'The parameter %s (%s) is not supported'
MSG_CREDENTIALS_ERROR = 'Could not get "%s" credentials from splunk. Error: %s'
MSG_MISSING_CREDENTIALS = (
        'No credentials have been found. Please setup reposify, '
        'or provide a valid "token=TOKEN_VALUE" argument to the command.'
)
MSG_API_HTTP_EXCEPTION = (
    'The reposify sever returned an HTTP exception:\n%s.\n'
    'Please see https://docs.reposify.com/#response-codes for '
    'more details.'
)

# Used for catching all exceptions raised by the reposify api
EXCEPTION_LIST = []
for name, obj in inspect.getmembers(reposify.exceptions):
    if inspect.isclass(obj) and issubclass(obj, Exception):
        EXCEPTION_LIST.append(obj)
# A tuple is needed for catching exceptions
EXCEPTION_LIST = tuple(EXCEPTION_LIST)


class ReposifyQueryException(Exception):
    pass


def format_exception(e):
    return str(e)


def get_credentials(session_key):
    app_name = 'reposify'
    try:
        # list all credentials
        entities = splunk.entity.getEntities(
            ['admin', 'passwords'],
            namespace=app_name,
            owner='nobody',
            sessionKey=session_key
        )
    except Exception as e:
        raise ReposifyQueryException(
            MSG_CREDENTIALS_ERROR % (
                app_name, format_exception(e)
            )
        )

    # return first set of credentials
    last = None
    for i, c in entities.items():
        if c['eai:acl']['app'] == app_name:
            last = c['username'], c['clear_password']
    if last:
        return last

    raise ReposifyQueryException(MSG_MISSING_CREDENTIALS)


def main():
    try:
        token = None

        try:
            argv = sys.argv[1:]
        except IndexError:
            raise ReposifyQueryException(MSG_REQUIRED_PARAMETER)

        # A dictionary containing valid endpoints and their respective
        # actions, and actions' parameters. Designed so that more endpoints
        # can be added in the future
        valid_endpoints = {
            'insights': {
                'search': ['banner', 'filters', 'page'],
                'count': ['banner', 'filters'],
            },
        }

        endpoint = 'insights'

        valid_actions = valid_endpoints[endpoint]
        # Check whether a valid action is supplied as the first argument
        if argv != [] and argv[0] in valid_actions:
            action = argv.pop(0)
        else:
            action = 'search'
            
        if not argv:
            raise ReposifyQueryException(MSG_REQUIRED_PARAMETER)

        valid_parameters = valid_endpoints[endpoint][action]

        params = {}
        query = ''
        # Parse the remaining args and try to extract valid parameters
        for arg in argv:
            try:
                (key, value) = arg.split('=', 1)
            except ValueError:
                raise ReposifyQueryException(MSG_UNSUPPORTED_ARGUMENT % repr(arg))

            key = key.lower()
            if key == 'token':
                token = value
            elif key in valid_parameters:
                params[key] = value
                if query == '':
                    query = arg
                else:
                    query += ' ' + arg
            else:
                raise ReposifyQueryException(
                    MSG_UNSUPPORTED_PARAMETER % (
                        repr(key), repr(arg)
                    )
                )

        if token is None:
            stdin = sys.stdin.read()
            session_key = re.search(r'sessionKey:(.*)', stdin).groups(1)[0]
            token = get_credentials(session_key)[1]

        # Get an instance of the endpoint class from the reposify Python api.
        # The getattr part allows adding support for more endpoints
        # in the future
        endpoint_object = getattr(
            reposify.reposify,
            endpoint.capitalize()
        )(token)

        # Call the appropriate method of the endpoint_object
        try:
            devices = getattr(endpoint_object, action)(**params)['devices']
        except EXCEPTION_LIST as e:
            # reposify-python puts request code numbers in the exceptions'
            # docstrings
            if e.__doc__:
                code = e.__doc__.strip()
            else:
                code = format_exception(e)
            raise ReposifyQueryException(MSG_API_HTTP_EXCEPTION % code)

        # Create appropriate splunk events from the devices list
        events = list()
        for device in devices:
            event = device
            event['_raw'] = json.dumps(device)
            event['source'] = 'reposify'
            event['sourcetype'] = 'reposify'
            event['query'] = query

            if 'timestamp' in event:
                try:
                    dt = datetime.datetime.strptime(event['timestamp'],
                                                    '%Y-%m-%dT%H:%M:%S.%f')
                except ValueError:
                    dt = datetime.datetime.strptime(event['timestamp'],
                                                    '%Y-%m-%dT%H:%M:%S')
                event['_time'] = time.mktime(dt.timetuple())
            else:
                event['_time'] = time.time()

            if 'ip_address' in event:
                event['host'] = event['ip_address']
            else:
                event['host'] = 'reposify'

            if 'location' in event:
                location = event.pop('location')
                for k in location:
                    new_k = 'location_{}'.format(k)
                    event[new_k] = location[k]
            if 'services' in event:
                services = event.pop('services')
                event['services'] = json.dumps(services)
            events.append(event)

    except Exception as e:
        events = splunk.Intersplunk.generateErrorResults(
            format_exception(e) + '\n' + MSG_USAGE
        )
    splunk.Intersplunk.outputResults(events)


if __name__ == "__main__":
    main()
