import sys
import os
import json
import logging
import uuid
from splunk.persistconn.application import PersistentServerConnectionApplication
import datetime
from dateutil.relativedelta import relativedelta

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import splunklib.client
from splunklib.binding import HTTPError
from splunk.clilib import cli_common as cli

class acti_retention(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        PersistentServerConnectionApplication.__init__(self)

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """

        # Cleanup, set a config class that sets up logging
        log_file_name = os.path.splitext(os.path.basename(__file__))[0]
        in_dict = json.loads(in_string)
        log_level = cli.getConfStanza('idefense', 'default')['log_level']
        logger = logging.getLogger('iDefense')
        FORMAT = "[%(levelname)-8s|%(asctime)s|%(filename)s|%(lineno)s|ID:{}] Method %(funcName)s %(message)s".\
                 format(uuid.uuid4())
        logging_file = f'{os.getenv("SPLUNK_HOME", "/opt/splunk")}/var/log/splunk/{log_file_name}.log'
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(logging_file)
        formatter = logging.Formatter(FORMAT)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        logger.setLevel(log_level)
        console_handler.setLevel(log_level)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        session_key = in_dict['session']['authtoken']
        # The URI in the dict below is in the form, https://hostname:port,
        # using split will create list  [https, //hostname, port]
        # //hostname[2:] = hostname
        host = in_dict['server']['rest_uri'].split(':')[1][2:]
        port = in_dict['server']['rest_uri'].split(':')[2]
        months_to_keep = 60
        for element in in_dict['query']:
            if "delete_older_than_months" in element:
                logger.info("threshold speficied during the call: " + element[1])
                months_to_keep = int(element[1])

        splunk_service = splunklib.client.connect(token=session_key, host=host, port=port)
        splunk_service.namespace.update({'owner': 'nobody'})
        threshold = (datetime.datetime.now() - relativedelta(months=months_to_keep)).timestamp()

        payload = {
            'entry': [
            ]
        }

        for kvstore in ['acti_threatindicator_file',
                        'acti_threatindicator_ip', 'acti_threatindicator_domain', 'acti_threatindicator_url']:

            entry = {"name": "Delete older records for " + kvstore, "content": ""}
            try:
                response = splunk_service.kvstore[kvstore].data.delete(
                    json.dumps({'last_published': {'$lt': threshold}}))
                logger.info("Made Request to delete delete old TI for " + kvstore)

            except (HTTPError) as e:
                entry["content"] = "Splunk Error Occured: " + str(e)
                payload['entry'].append(entry)
                break

            if response['status'] == 200:
                entry["content"] = "Request Completed"

            else:
                entry["content"] = "Request Was Incomplete, Unexpected response"
            payload['entry'].append(entry)

        return {'payload': payload, 'status': 200}

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass
