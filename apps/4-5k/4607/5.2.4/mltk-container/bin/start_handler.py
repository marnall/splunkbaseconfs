import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
lib_path = os.path.join(os.path.dirname(__file__), "..", "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
from base_handler import BaseRestHandler
from urllib.parse import parse_qs
from kubernetes_utility import K8SUtils
import time
import json
from passwords import decode_llm_passwords
from llm_config_helper import set_llm_config

class StartHandler(BaseRestHandler):
    def handle_POST(self):
        params = parse_qs(self.request['payload'])
        image = params["image"][0]
        model = params["model"][0] if "model" in params else ''
        runtime = params["runtime"][0] if "runtime" in params else None
        cluster = params["cluster"][0]
        mode = params["mode"][0] if "mode" in params else 'DEV'
        # platform specific and default hardcoded settings
        devFlag = model == "__dev__"
        repo = "splunk/"
        image_name = "mltk-container-golden-cpu"
        image_stanzas = dict()
        for stanza in self.image_stanzas:
            image_stanzas[stanza.image] = stanza
        if image in image_stanzas:
            image_stanza = image_stanzas[image]
            repo = image_stanza.repo
            image_name = image_stanza.image

        #self.get_logger().info("MLTKContainer START model name: %s - image name: %s", model, image_name)

        stanza_name = "%s" % (model)
        if not stanza_name in self.container_stanzas:
            container_stanza = self.container_stanzas.create(stanza_name)
        else:
            container_stanza = self.container_stanzas[stanza_name]
        
        # setup environment variables
        environment_vars = {
            "olly_enabled": "false",
            "splunk_access_enabled": "false",
            "splunk_hec_enabled": "false",
            "ENABLE_HTTPS": "true",
            "JUPYTER_PASSWD": "sha1:f7432152c71d:e8520c26b9d960e838d562768c1d24ef5b9b76c7",
            "MODE_DEV_PROD": "DEV" if mode=="DEV" else "PROD",
            "api_token": "",
            "api_workers": "1",
            "MAX_MSGS": "20",
            "TTL_EVICT_SECONDS": "3600",
            "MAX_LOG_TOKEN_SIZE": "3000",
            "DEFAULT_LLM": "ollama",
            "SYSTEM_PROMPT": "You are a friendly chatbot that is well-verse in Splunk and logs. You are here to help people",
            "llm_config": ""
        }
        #NOTE If you wish to directly read a llm_config.json JSON configuration file from local/ folder
        #NOTE Uncomment Line 59 ~ 65 and comment out Line 66 ~ 72
        # llm_config_path = os.path.join(os.path.dirname(__file__), "..", "local/llm_config.json")
        # try:
        #     with open(llm_config_path, 'r') as file:
        #         llm_config = json.load(file)
        #     llm_config_str = json.dumps(llm_config)
        # except:
        #     llm_config_str = ""
        try:
            llm_chat_params = self.service.confs["llm_chat"]["llm_chat"]
            environment_vars["MAX_MSGS"] = str(llm_chat_params["MAX_MSGS"])
            environment_vars["TTL_EVICT_SECONDS"] = str(llm_chat_params["TTL_EVICT_SECONDS"])
            environment_vars["MAX_LOG_TOKEN_SIZE"] = str(llm_chat_params["MAX_LOG_TOKEN_SIZE"])
            environment_vars["DEFAULT_LLM"] = llm_chat_params["DEFAULT_LLM"]
            environment_vars["SYSTEM_PROMPT"] = llm_chat_params["SYSTEM_PROMPT"]
        except:
            pass
        
        try:
            llm_params = self.service.confs["llm"]["llm_config"]
            decode_llm_passwords(self.service, llm_params)
            llm_config_str = set_llm_config(llm_params)
        except Exception as e:
            self.get_logger().info("MLTKContainer llm_params error : %s", str(e))
            llm_config_str = ""
        environment_vars["llm_config"] = llm_config_str        
        try:
            api_workers = int(self.connection["api_workers"])
            api_workers = str(api_workers)
        except:
            api_workers = "1"
        if not api_workers == None:
            environment_vars["api_workers"] = api_workers

        try:
            jupyter_passwd = self.connection["jupyter_passwd"]
            if not jupyter_passwd == None:
                environment_vars["JUPYTER_PASSWD"] = jupyter_passwd
        except:
            pass
        try:
            api_token = self.connection["api_token"]
            if not api_token == None:
                environment_vars["api_token"] = api_token
        except:
            pass

        container_enable_https = self.connection["container_enable_https"]
        if not container_enable_https == None:
            if 'false' in container_enable_https or container_enable_https == "0":
                environment_vars["ENABLE_HTTPS"] = "false"

        olly_enabled = self.connection["olly_enabled"]
        if not olly_enabled == None:
            if 'true' in olly_enabled or olly_enabled == "1":
                environment_vars["SPLUNK_ACCESS_TOKEN"] = self.connection["olly_splunk_access_token"]
                environment_vars["OTEL_TRACES_EXPORTER"] = "jaeger-thrift-splunk"
                environment_vars["OTEL_SERVICE_NAME"] = self.connection["olly_otel_service_name"]
                environment_vars["OTEL_EXPORTER_JAEGER_ENDPOINT"] = self.connection["olly_otel_endpoint"]
                environment_vars["olly_enabled"] = self.connection["olly_enabled"]

        splunk_access_enabled = self.connection["splunk_access_enabled"]
        if not splunk_access_enabled == None:
            if 'true' in splunk_access_enabled or splunk_access_enabled == "1":
                environment_vars["splunk_access_token"] = self.connection["splunk_access_token"]
                environment_vars["splunk_access_host"] = self.connection["splunk_access_host"]
                environment_vars["splunk_access_port"] = self.connection["splunk_access_port"]
                environment_vars["splunk_access_enabled"] = self.connection["splunk_access_enabled"]
        
        splunk_hec_enabled = self.connection["splunk_hec_enabled"]
        if not splunk_hec_enabled == None:
            if 'true' in splunk_hec_enabled or splunk_hec_enabled == "1":
                environment_vars["splunk_hec_token"] = self.connection["splunk_hec_token"]
                environment_vars["splunk_hec_url"] = self.connection["splunk_hec_url"]
                environment_vars["splunk_hec_enabled"] = self.connection["splunk_hec_enabled"]

        if cluster == "docker":
            docker_log_config = None
            docker_network = self.connection["docker_network"]
            docker_logging_endpoint_hostname = self.connection["docker_logging_endpoint_hostname"]
            if not docker_logging_endpoint_hostname == None:
                docker_logging_splunk_token = self.connection["docker_logging_splunk_token"]
                if not docker_logging_splunk_token == None:
                    from docker.types import LogConfig
                    docker_log_config = LogConfig(type='splunk', config={
                        'splunk-token': docker_logging_splunk_token, 
                        'splunk-url': docker_logging_endpoint_hostname # e.g. 'http://host.docker.internal:8088'
                    })
            docker_ports = {
                '5000/tcp': None
            }
            if mode=="DEV":
                docker_ports = {
                    '8888/tcp': '8888' if devFlag else None,
                    '6006/tcp': '6006' if devFlag else None,
                    '6000/tcp': '6060' if devFlag else None,
                    '4040/tcp': '4040' if devFlag else None,
                    '5000/tcp': '5000' if devFlag else None,
                }
                
            c = self.docker_client.containers.run(repo + image_name, labels={
                "mltk_container": "",
                "mltk_model": model,
            }, runtime=runtime, detach=True, ports=docker_ports, volumes={
                'mltk-container-data': {'bind': '/srv', 'mode': 'rw'},
                'mltk-container-app': {'bind': '/srv/backup/app', 'mode': 'ro'},
                'mltk-container-notebooks': {'bind': '/srv/backup/notebooks', 'mode': 'ro'}
            }, remove=True, log_config=docker_log_config, environment=environment_vars, network=docker_network)

            endpoint_hostname = self.connection["endpoint_hostname"]
            endpoint_hostname_external = self.connection["endpoint_hostname_external"]
            if endpoint_hostname_external == None:
                endpoint_hostname_external = endpoint_hostname

            # quick fix for UI bug: sleep 1 second to avoid the IndexError: list index out of range
            # it was reported to occasionally show after click on start button
            timeout = 60
            retries = 0
            while retries < timeout:
                inspect = self.docker_api_client.inspect_container(c.id)
                try:
                    api_port = inspect["NetworkSettings"]["Ports"]['5000/tcp'][0]["HostPort"]
                    if mode=="DEV":
                        jupyter_port = inspect["NetworkSettings"]["Ports"]['8888/tcp'][0]["HostPort"]
                        tensorboard_port = inspect["NetworkSettings"]["Ports"]['6006/tcp'][0]["HostPort"]
                        spark_port = inspect["NetworkSettings"]["Ports"]['4040/tcp'][0]["HostPort"]
                        mlflow_port = inspect["NetworkSettings"]["Ports"]['6000/tcp'][0]["HostPort"]
                    break
                except:
                    self.get_logger().info("MLTKContainer inspect_container index out of range after %s retries for container_id=%s", retries, c.id)
                    pass
                time.sleep(1)
                retries += 1
            else:
                self.get_logger().info("MLTKContainer inspect_container did not respond after %s retries for container_id=%s", retries, c.id)

            # data transmission from Splunk search head to container is handled over api_url
            # since DLTK version 3.5 by default provided via HTTPS 
            api_url = "https://%s:%s" % (endpoint_hostname, api_port)
            api_url_external = "https://%s:%s" % (endpoint_hostname_external, api_port)
            # non data transmission related but also enforced to HTTPS for Juypter for additional security
            jupyter_url = "https://%s:%s" % (endpoint_hostname_external, jupyter_port) if mode=="DEV" else ''
            # non data transmission related external shortcut links are provided via http
            tensorboard_url = "http://%s:%s" % (endpoint_hostname_external, tensorboard_port) if mode=="DEV" else ''
            spark_url = "http://%s:%s" % (endpoint_hostname_external, spark_port) if mode=="DEV" else ''
            mlflow_url = "http://%s:%s" % (endpoint_hostname_external, mlflow_port) if mode=="DEV" else ''

            container_stanza.submit({
                "id": c.id,
                "mode": mode,
                "cluster": cluster,
                "image": image_name,
                "runtime": runtime,
                "api_url": api_url,
                "api_url_external": api_url_external,
                "jupyter_url": jupyter_url,
                "tensorboard_url": tensorboard_url,
                "spark_url": spark_url,
                "mlflow_url": mlflow_url,
            })

            self.get_logger().info("MLTKContainer START on cluster=%s model_name=%s image_name=%s container_id=%s", cluster, model, image_name, c.id)

        # TODO api_url_external in k8s
        elif cluster == "kubernetes":
            k8s = K8SUtils.from_service(self.service)
            deployment = k8s.create_deployment(runtime, model, repo + image_name, environment_vars)
            k8s.create_service(deployment, model, mode)

            port_names = ["api"]
            if mode=="DEV":
                port_names = ["jupyter", "tensorboard", "api", "spark", "mlflow"]
                
            for port_name in port_names: 
                if port_name == "api" and self.connection["in_cluster_mode"] == "1":
                    # skip creating ingress for api service for in cluster mode
                    continue 
                if self.connection["service_type"] == "route":
                    k8s.create_route(deployment, model, port_name)
                elif self.connection["service_type"] == "ingress":
                    k8s.create_ingress(deployment, model, port_name)

            container_stanza.submit({
                "id": k8s.get_clean_model(model),
                "cluster": cluster,
                "image": image_name,
                "runtime": runtime,
                "mode": mode
            })
            self.get_logger().info("MLTKContainer START on cluster=%s model_name=%s image_name=%s container_id=%s", cluster, model, image_name, k8s.get_clean_model(model))

        container_stanza.refresh()
        self.send_json_response({
            "container_id": container_stanza.id,
        })
    
