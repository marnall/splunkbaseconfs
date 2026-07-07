import os
import json
import splunk.rest as rest

APP_NAME = __file__.split(os.sep)[-3]


class ConfigReader(object):

    @staticmethod
    def read_conf(session_key, conf_file_name, stanza_name):
        """
        Read from Rest Endpoint
        :param session_key: session key of splunk
        :param conf_file_name: configuration file name
        :param stanza_name: Name of stanza from which we need to read
        :return: dictionary of all field present in config file
        """
        access_url = '/servicesNS/nobody/{}/configs/conf-{}/{}'.format(APP_NAME, conf_file_name, stanza_name)
        _, content = rest.simpleRequest(
            access_url, sessionKey=session_key, getargs={"output_mode": "json"}, raiseAllErrors=True)
        content = json.loads(content)
        response_dict = {}

        for item in content['entry']:
            response_dict = item['content']

        return response_dict
