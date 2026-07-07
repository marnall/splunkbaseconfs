import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
docker_path = os.path.join(os.path.dirname(__file__),"dockerlib")
if docker_path not in sys.path:
    sys.path.insert(0, docker_path)
import splunk.rest
import json
import logging_utility
import splunklib.client as client
import docker

logger = logging_utility.getLogger()


class BaseRestHandler(splunk.rest.BaseRestHandler):
    # splunk client service object
    _service = None
    # docker connection object
    _connection = None
    # containers.conf stanzas object 
    _containers = None
    # images.conf stanzas object 
    _images = None
    # docker client object
    _docker_client = None
    _docker_api_client = None

    # splunk client service object create
    def create_service(self):
        s = client.Service(
            token=self.sessionKey,
            sharing="app",
            app="mltk-container-ja",
        )
        return s
    # splunk client service get or create
    @property
    def service(self):
        if self._service != None:
            return self._service
        self._service = self.create_service()
        return self._service
    # get docker connection object from docker.conf containing docker_url and endpoint_hostname
    @property
    def connection(self):
        if self._connection:
            return self._connection
        self._connection = self.service.confs["docker"]["connection"]
        return self._connection

    # get container stanza objects from containers.conf
    @property
    def container_stanzas(self):
        if self._containers != None:
            return self._containers
        confs = self.service.confs
        self._containers = confs.create("containers")
        return self._containers

    # get image stanza objects from images.conf
    @property
    def image_stanzas(self):
        if self._images != None:
            return self._images
        confs = self.service.confs
        self._images = confs.create("images")
        return self._images

    def create_docker_client(self, docker_url):
        return docker.DockerClient(base_url=docker_url)

    @property
    def docker_client(self):
        if self._docker_client != None:
            return self._docker_client
        docker_url = self.connection["docker_url"]
        self._docker_client = self.create_docker_client(docker_url)
        return self._docker_client

    @property
    def docker_api_client(self):
        if self._docker_api_client != None:
            return self._docker_api_client
        docker_url = self.connection["docker_url"]
        self._docker_api_client = docker.APIClient(base_url=docker_url)
        return self._docker_api_client

    # send result list as json response
    def send_entries(self, entries):
        self.send_json_response({
            "entry": [{
                "content": e
            } for e in entries]
        })

    # send json response
    def send_json_response(self, object):
        self.response.setStatus(200)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps(object))
    
    # get logger from splunk BaseRestHandler
    def get_logger(self):
        return logger
