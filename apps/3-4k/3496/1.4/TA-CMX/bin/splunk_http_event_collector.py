import json
import time
import socket
import threading
import Queue

import requests

from CMXUtil import get_logger


http_event_collector_debug = False
http_event_collector_SSL_verify = False

__author__ = "george@georgestarcher.com (George Starcher)"


# Default batch max size to match splunk's default limits for max byte
# See http_input stanza in limits.conf; note in testing I had to
# limit to 100,000 to avoid http event collector breaking connection
# Auto flush will occur if next event payload will exceed limit
_max_content_bytes = 10000
_number_of_threads = 10

logger = get_logger('HTTPEC')


class HttpEventCollector:
    def __init__(self, token, http_event_server, host = "", http_event_port = '8088', http_event_server_ssl = True,
                 max_bytes = _max_content_bytes):
        self.token = token
        self.batchEvents = []
        self.maxByteLength = max_bytes
        self.currentByteLength = 0
        self.flushQueue = Queue.Queue(0)
        for x in range(_number_of_threads):
            t = threading.Thread(target = self.batch_thread)
            t.daemon = True
            t.start()

        # Set host to specified value or default to localhostname if no value provided
        if host:
            self.host = host
        else:
            self.host = socket.gethostname()

        # Build and set server_uri for http event collector
        # Defaults to SSL if flag not passed
        # Defaults to port 8088 if port not passed
        logger.debug("http_event_server_ssl:::" + str(http_event_server_ssl))
        if http_event_server_ssl:
            protocol = 'https'
        else:
            protocol = 'http'

        self.server_uri = '%s://%s:%s/services/collector/event' % (protocol, http_event_server, http_event_port)

        if http_event_collector_debug:
            logger.debug(self.token)
            logger.debug(self.server_uri)

    def send_event(self, payload, eventtime = ""):
        # Method to immediately send an event to the http event collector

        # If eventtime in epoch not passed as optional argument and not in payload, use current system time in epoch
        if not eventtime and 'time' not in payload:
            eventtime = str(int(time.time()))
            payload.update({'time': eventtime})

        # Fill in local hostname if not manually populated
        if 'host' not in payload:
            payload.update({"host": self.host})

        # send event to http event collector
        event = []

        self.flushQueue.put(event)
        if http_event_collector_debug:
            logger.debug("Single Submit: Sticking the event on the queue.")
        self.wait_until_done()

    def batch_event(self, payload, eventtime = ""):
        # Method to store the event in a batch to flush later

        # Fill in local hostname if not manually populated
        if 'host' not in payload:
            payload.update({"host": self.host})

        # If eventtime in epoch not passed as optional argument and not in payload, use current system time in epoch
        if not eventtime and 'time' not in payload:
            eventtime = str(int(time.time()))
            payload.update({"time": eventtime})

        pay_load_string = json.dumps(payload)
        pay_load_length = len(pay_load_string)
        logger.debug("Content Length:" + str(self.currentByteLength + pay_load_length))

        if (self.currentByteLength + pay_load_length) > self.maxByteLength:
            if http_event_collector_debug:
                logger.debug("Auto Flush: Sticking the batch on the queue.")
            self.flushQueue.put(self.batchEvents)
            self.batchEvents = []
            self.currentByteLength = 0

        self.batchEvents.append(pay_load_string)
        self.currentByteLength += pay_load_length

    def batch_thread(self):
        # Threads to send batches of events.

        while True:
            if http_event_collector_debug:
                logger.debug("Events received on thread. Sending to Splunk.")

            payload = " ".join(self.flushQueue.get())
            if http_event_collector_debug:
                logger.debug("Pay load " + payload)
            headers = {'Authorization': 'Splunk ' + self.token}
            logger.debug(self.server_uri)
            r = requests.post(self.server_uri, data = payload, headers = headers,
                              verify = http_event_collector_SSL_verify, allow_redirects = True)
            logger.debug(r.status_code)
            self.flushQueue.task_done()

    def wait_until_done(self):
        # Block until all flushQueue is empty.
        self.flushQueue.join()
        return

    def flush_batch(self):
        if http_event_collector_debug:
            logger.debug("Manual Flush: Sticking the batch on the queue.")
        self.flushQueue.put(self.batchEvents)
        self.batchEvents = []
        self.currentByteLength = 0
        self.wait_until_done()



