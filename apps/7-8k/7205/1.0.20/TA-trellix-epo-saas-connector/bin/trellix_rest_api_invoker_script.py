# Copyright 2020 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from splunk.persistconn.application import PersistentServerConnectionApplication


import logging
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


_APPNAME = 'TA-trellix-epo-saas-connector'

def setup_logger(level):
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('splunk.appserver.%s.controllers.trellix_saas_apply_tag_script' % _APPNAME)
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(
        make_splunkhome_path(['var', 'log', 'splunk', 'trellix_SaaS_api_invoker_script.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


logger = setup_logger(logging.DEBUG)



class TrellixRESTInvokerScript(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """
        payload = {
            "text": "Hello world!"
        }
        logger.debug("*** In string == " + str(in_string))
        return {'payload': payload, 'status': 200}

    def handleStream(self, handle, in_string):
        """
        For future use
        """
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass