import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
lib_path = os.path.join(os.path.dirname(__file__), "..", "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
import splunk
from base_handler import BaseRestHandler
from urllib.parse import parse_qs
# TODO: don't import kubernetes_fields here, add a function to K8SUtils to get just the K8S specific fields
from kubernetes_utility import K8SUtils, kubernetes_fields
from passwords import encode_passwords, decode_passwords

import exceptions

class ConfigureHandler(BaseRestHandler):
    def handle_POST(self):
        try:
            params = parse_qs(self.request['payload'])
            docker_url = params["docker_url"][0] if "docker_url" in params else ''
            docker_url = docker_url.strip('/')
            endpoint_hostname = params["endpoint_hostname"][0] if "endpoint_hostname" in params else ''
            endpoint_hostname_external = params["endpoint_hostname_external"][0] if "endpoint_hostname_external" in params else ''
            docker_network = params["docker_network"][0] if "docker_network" in params else ''
            api_workers = params["api_workers"][0] if "api_workers" in params else '1'
            docker_logging_endpoint_hostname = params["docker_logging_endpoint_hostname"][0] if "docker_logging_endpoint_hostname" in params else ''
            docker_logging_splunk_token = params["docker_logging_splunk_token"][0] if "docker_logging_splunk_token" in params else ''
            endpoint_cert_check_hostname = params["endpoint_cert_check_hostname"][0] if "endpoint_cert_check_hostname" in params else ''
            endpoint_cert_filename_or_path = params["endpoint_cert_filename_or_path"][0] if "endpoint_cert_filename_or_path" in params else ' '
            olly_splunk_access_token = params["olly_splunk_access_token"][0] if "olly_splunk_access_token" in params else ''
            olly_otel_endpoint = params["olly_otel_endpoint"][0] if "olly_otel_endpoint" in params else ''
            olly_otel_service_name = params["olly_otel_service_name"][0] if "olly_otel_service_name" in params else ''
            olly_enabled = params["olly_enabled"][0] if "olly_enabled" in params else ''

            container_enable_https = params["container_enable_https"][0] if "container_enable_https" in params else ''
            container_enable_keepalive = params["container_enable_keepalive"][0] if "container_enable_keepalive" in params else ''
            splunk_access_token = params["splunk_access_token"][0] if "splunk_access_token" in params else ''
            splunk_access_host = params["splunk_access_host"][0] if "splunk_access_host" in params else ''
            splunk_access_port = params["splunk_access_port"][0] if "splunk_access_port" in params else ''
            splunk_access_enabled = params["splunk_access_enabled"][0] if "splunk_access_enabled" in params else ''
            splunk_hec_enabled = params["splunk_hec_enabled"][0] if "splunk_hec_enabled" in params else ''
            splunk_hec_token = params["splunk_hec_token"][0] if "splunk_hec_token" in params else ''
            splunk_hec_url = params["splunk_hec_url"][0] if "splunk_hec_url" in params else ''
            in_cluster_mode = params["in_cluster_mode"][0] if "in_cluster_mode" in params else '0'
            image_pull_secrets = params["image_pull_secrets"][0] if "image_pull_secrets" in params else 'None'
            jupyter_passwd = params["jupyter_passwd"][0] if "jupyter_passwd" in params else ''
            api_token = params["api_token"][0] if "api_token" in params else ''

            if len(api_token)==0:
                import random, string
                api_token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=64))                

            settings = {}

            settings["endpoint_cert_check_hostname"] = endpoint_cert_check_hostname
            settings["endpoint_cert_filename_or_path"] = endpoint_cert_filename_or_path
            settings["olly_otel_endpoint"] = olly_otel_endpoint
            settings["olly_splunk_access_token"] = olly_splunk_access_token
            settings["olly_otel_service_name"] = olly_otel_service_name
            settings["olly_enabled"] = olly_enabled
            settings["container_enable_https"] = container_enable_https
            settings["container_enable_keepalive"] = container_enable_keepalive            
            settings["splunk_access_token"] = splunk_access_token
            settings["splunk_access_host"] = splunk_access_host
            settings["splunk_access_port"] = splunk_access_port
            settings["splunk_access_enabled"] = splunk_access_enabled
            settings["splunk_hec_enabled"] = splunk_hec_enabled
            settings["splunk_hec_token"] = splunk_hec_token
            settings["splunk_hec_url"] = splunk_hec_url
            settings["in_cluster_mode"] = in_cluster_mode
            settings["image_pull_secrets"] = image_pull_secrets
            settings["jupyter_passwd"] = jupyter_passwd
            settings["api_token"] = api_token
            settings["is_configured_complete"] = "0"
            settings["api_workers"] = api_workers

            # unpack params into a dict
            # TODO: use for parameter above too
            params = {
                k: params[k][0] for k in params
            }

            if not docker_url and not K8SUtils.is_enabled(params):
                raise exceptions.ApplicationError("Please enter at least one connection, either Docker or Kubernetes")

            if K8SUtils.is_enabled(params):
                K8SUtils.validate_cluster(params)
                # copy validated kubernetes settings from params into settings
                for k in kubernetes_fields:
                    if k in params:
                        settings[k] = params[k]

                # create volume without magic number bug please:
                # TODO: document what the magic number bug is
                k8s = K8SUtils(params)
                # ensure that the volume that is shared between the containers exists
                k8s.ensure_volume('1Gi')
            else:
                # make sure that we don't set any kubernetes fields
                # TODO: check if this is really needed as settings is an empty dict
                for k in kubernetes_fields:
                    settings[k] = ''
                # setup UI bugfix to override mandatory fields TODO: refactor this
                settings["in_cluster_mode"] = in_cluster_mode
                settings["image_pull_secrets"] = image_pull_secrets
                settings["jupyter_passwd"] = jupyter_passwd
                settings["api_token"] = api_token

            if docker_url:
                if self.create_docker_client(docker_url).ping() == False:
                    raise splunk.RESTException(400, "Could not ping Docker")
                settings["docker_url"] = docker_url
                settings["endpoint_hostname"] = endpoint_hostname
                settings["endpoint_hostname_external"] = endpoint_hostname_external
                settings["docker_network"] = docker_network
                settings["docker_logging_endpoint_hostname"] = docker_logging_endpoint_hostname
                settings["docker_logging_splunk_token"] = docker_logging_splunk_token
            else:
                settings["docker_url"] = ''
                settings["endpoint_hostname"] = ''
                settings["endpoint_hostname_external"] = ''
                settings["docker_network"] = ''
                settings["docker_logging_endpoint_hostname"] = ''
                settings["docker_logging_splunk_token"] = ''

            encode_passwords(self.service, settings)
 
            settings["is_configured_complete"] = 1
            self.service.confs["docker"]["connection"].submit(settings)
            self.service.confs["app"]["install"].submit({
                "is_configured": 1,
            })
            self.service.apps["mltk-container"].reload()

            self.send_json_response({})
        except exceptions.ApplicationError:
            raise
        except:
            import traceback
            raise Exception(traceback.format_exc())

    def handle_GET(self):
        settings = self.connection
        # TODO catch case where after update jupyter_pw is not set and therefore pwd endpoint and configure handler fails with server error 500
        decode_passwords(self.service, settings)
        data = {
            "docker_url": settings["docker_url"],
            "endpoint_hostname": settings["endpoint_hostname"],
            "endpoint_hostname_external": settings["endpoint_hostname_external"],
            "docker_network": settings["docker_network"],
            "api_workers": settings["api_workers"],
            "docker_logging_endpoint_hostname": settings["docker_logging_endpoint_hostname"],
            "docker_logging_splunk_token": settings["docker_logging_splunk_token"],
            "olly_otel_endpoint": settings["olly_otel_endpoint"],
            "olly_splunk_access_token": settings["olly_splunk_access_token"],
            "olly_otel_service_name": settings["olly_otel_service_name"],
            "olly_enabled": settings["olly_enabled"],
            "endpoint_cert_filename_or_path": settings["endpoint_cert_filename_or_path"],
            "endpoint_cert_check_hostname": settings["endpoint_cert_check_hostname"],
            "container_enable_https": settings["container_enable_https"],
            "container_enable_keepalive": settings["container_enable_keepalive"],
            "splunk_access_token": settings["splunk_access_token"],
            "splunk_access_host": settings["splunk_access_host"],
            "splunk_access_port": settings["splunk_access_port"],
            "splunk_access_enabled": settings["splunk_access_enabled"],
            "splunk_hec_enabled": settings["splunk_hec_enabled"],
            "splunk_hec_token": settings["splunk_hec_token"],
            "splunk_hec_url": settings["splunk_hec_url"],
        }
        for k in kubernetes_fields:
            if k in settings:
                data[k] = settings[k]
        self.send_json_response(data)
