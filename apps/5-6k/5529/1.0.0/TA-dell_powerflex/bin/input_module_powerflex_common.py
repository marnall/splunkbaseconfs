# encoding = utf-8

import time
import powerflex_utilities
from powerflex_account import PowerFlexAccount


def timer(func):
    """
    Timer keeps track of execution time for any function
    It is hardly related to PowerFlexCommonDataCollector as it is using some of class variables
    """
    def wrapper(self, *args, **kwargs):
        self.logger.info("Data collection started.")
        start = time.time()
        ret = func(self, *args, **kwargs)
        end = time.time()
        self.logger.info("Data collection completed in {} seconds.".format((end-start)))
        return ret
    return wrapper


class PowerFlexCommonDataCollector(object):
    """
    Statistics collector
    """
    def __init__(self, helper, event_writer, logger_name):
        self.helper = helper
        self.event_writer = event_writer

        self.session_key = self.helper.context_meta['session_key']

        # input name
        self.input_name = self.helper.get_input_stanza_names()

        # system
        self.input_stanza = self.helper.get_input_stanza()
        endpoint = self.input_stanza[self.input_name]['system']['endpoint']
        system_name = self.input_stanza[self.input_name]['system']['name']
        username = self.input_stanza[self.input_name]['system']['username']
        password = self.input_stanza[self.input_name]['system']['password']

        # other metadata fields
        self.index = self.helper.get_arg('index')
        self.sourcetype = self.helper.get_arg('sourcetype')
        self.source = None
        self.host = str(endpoint).strip(" ").strip("/")

        self.logger = powerflex_utilities.get_logger(self.session_key, logger_name, system_name, input_name=self.input_name)
        
        # initialize session obj for all the requests
        self.powerflex_account_obj = PowerFlexAccount(system_name, endpoint, username, password)
        self.session_obj = self.powerflex_account_obj.get_request_session(self.session_key, self.helper, self.logger)

        self.system_id = None
    
    def get_system_id(self):
        """
        Get system id for which the instance data will be collected. Only required in case of Delta type of endpoint.
        """
        checkpoint_name = "{}_system".format(self.powerflex_account_obj.name)
        # Try to Get from Checkpoint
        if self.system_id:
            return self.system_id

        # Read system_id from checkpoint file
        try:
            self.logger.debug("Getting system_id through checkpoint file ckpt_name={}".format(checkpoint_name))
            self.system_id = self.helper.get_check_point(checkpoint_name)
        except Exception as e:
            self.logger.info("Checkpoint for system_id not found. msg={}".format(str(e)))

        if not self.system_id:
            # Request to get the system_id
            self.logger.debug("Getting system_id using system_endpoint={}.".format(powerflex_utilities.SYSTEM_ENDPOINT))
            sys_response = self.session_obj.request(url=powerflex_utilities.SYSTEM_ENDPOINT)
            if not sys_response or not len(sys_response):
                self.logger.error("Could not get system id")
            self.system_id = sys_response[0].get("id")

            # Store in checkpoint
            self.helper.save_check_point(checkpoint_name, self.system_id)
        self.logger.debug("Got system id. system_id={}.".format(self.system_id))
        return self.system_id
