import json
import os
import sys
import time
import threading

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "BaseClient"))
from baseclient import BaseClient
import endpoints


class DeployIoc(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        self.index = IndexIoc()
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        deploy_process = threading.Thread(target=self.index.deploy, args=(in_string,))
        deploy_process.start()
        return {'payload': {'status': "IOC deployed successfully"},
                'status': 200
                }


class IndexIoc(BaseClient):
    def __init__(self):
        super().__init__()
        self.user = None
        self.passw = None
        self.session = ()
        self.url = None
        self.outputmode = {
            'output_mode': 'json'
        }

    def deploy(self, data):
        """
        This function recieves iocs and add them in a collection named IOC
        """
        args = json.loads(data)
        content = json.loads(args['payload'])
        self.user = content['username']
        self.passw = content['password']
        self.url = content['url']
        self.session = (self.user, self.passw)
        ioc = content['ioc']
        url = self.url + endpoints.const_conf
        endpoints.verify_ssl = content.get('verify_ssl')
        ssl = {
            'value': endpoints.verify_ssl
        }
        self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=ssl, method='POST', auth=self.session)

        self.create_collections()
        self.create_pass_conf()
        job_tag = {
            'job_tag': "Deploy IOC"
        }
        self.check_available()
        self.logger.info("Received {} IOCs for deployment.".format(len(ioc)))
        for x in ioc:
            x.update(job_tag)
            data = {
                'ioc': x,
            }
            url = self.url + endpoints.ioc_collection
            response = self.http_method(url=url, verify_ssl=endpoints.verify_ssl, req_json=data, method='POST',
                                        auth=self.session)
            if response is None:
                self.logger.error("Error occurred while deploying IOC {}".format(x))

        self.logger.info("invoking {} endpoint".format(endpoints.database_restart))
        data = {
            'script': '//$SPLUNK_HOME/etc/apps/strikereadyapp/bin/database.py'
        }
        url = self.url + endpoints.database_restart
        response = self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=data, method='POST', auth=self.session)
        if response is None:
            self.logger.error("Error occurred while invoking {} endpoint".format(endpoints.database_restart))

    def check_available(self):
        """
        This function checks the availability of the collection
        """
        url = self.url + endpoints.ioc_collection
        response = self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=self.outputmode, method='GET',
                                    auth=self.session)
        if response:
            size = response.json()
            while size:
                time.sleep(20)
                response = self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=self.outputmode,
                                            method='GET', auth=self.session)
                if response:
                    size = response.json()
                    self.logger.debug(size)
                else:
                    self.logger.error("Unable to check collection availability")
        else:
            self.logger.error("Unable to check collection availability")

    def create_collections(self):
        """
        This function creates the collection
        """
        url = self.url + endpoints.create_collection
        data = {
            'name': 'IOC',
        }
        result = self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=data, method='POST', auth=self.session)
        if result is None:
            self.logger.error("Unable to create collection {}".format(data))

    def create_pass_conf(self):
        sec = {
            'name': self.user,
            'password': self.passw,
            'realm': self.url,
            'output_mode': 'json'
        }
        url = self.url + endpoints.password_conf
        result = self.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=sec, method='POST', auth=self.session)
        if result is None:
            self.logger.error("Unable to create password configurations")
