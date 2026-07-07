# encoding = utf-8

import re
import asyncio
import json
import sys

from aiosfstream import Client
from aiosfstream.auth import PasswordAuthenticator
from aiosfstream.replay import ReplayOption

SUBSCRIPTION_TOPIC_PATTERN = '/\w+/\w+'


def validate_input(helper, definition):
    topic = definition.parameters.get('topic', None)
    pattern = re.compile(SUBSCRIPTION_TOPIC_PATTERN)
    if pattern.match(topic) is None:
        raise Exception("Subscription topic name is invalid (EG:/event/ReportEventStream)")


def collect_events(helper, ew):
    # https://stackoverflow.com/questions/30361824/asynchronous-exception-handling-in-python
    loop = asyncio.get_event_loop()
    task = asyncio.gather(connect_sfdc(helper, ew))
    loop.run_until_complete(task)


def validate_connection(helper, connection: dict):
    if not connection['domain'].startswith("https"):
        helper.log_error("Only HTTPS connections are allowed; Change connection settings in Configurations: [{}]"
                         "".format(connection['name']))
        sys.exit()
    helper.log_info("Using connection: {} for data input: {}".format(connection['name'], helper.get_arg('name')))
    if not connection['domain'] and connection['client_id'] and connection['client_secret'] and connection['username'] \
            and connection['password']:
        raise Exception("Connection {} is invalid".format(connection['name']))


async def connect_sfdc(helper, event_writer):
    connection = helper.get_arg('global_account')
    validate_connection(helper, connection)
    if int(connection['sandbox']):
        helper.log_info("{} SFDC instance is marked as a sandbox instance".format(connection['domain']))

    password_authenticator = PasswordAuthenticator(url=connection['domain'],
                                                   consumer_key=connection['client_id'],
                                                   consumer_secret=connection['client_secret'],
                                                   username=connection['username'],
                                                   password=connection['password'],
                                                   sandbox=bool(int(connection['sandbox'])))

    if helper.get_arg('position'):
        replay_position = ReplayOption.NEW_EVENTS
    else:
        replay_position = ReplayOption.ALL_EVENTS

    sf_streaming_client = Client(password_authenticator,
                                 replay=replay_position)

    async with sf_streaming_client as client:
        try:
            await client.subscribe(helper.get_arg('topic'))
        except Exception as e:
            helper.log_error("Subscription Failure: {}".format(e))
            await client.close()
            sys.exit()

        helper.log_info("SFDC streaming client is subscribed to {} and replaying events from LATEST={}".format(
                        helper.get_arg('topic'),
                        helper.get_arg('position')))

        async for message in client:
            event = dict(message["data"]["payload"])
            write_event = event.copy()
            if event.get('Records'):
                '''
                Convert string to json
                This is a workaround for ReportEventStream where the "Records" field is encoded as a string instead 
                of a json.
                '''
                write_event['Records'] = json.loads(event.get('Records'))

            event_writer.write_event(helper.new_event(data=json.dumps(write_event)))
