import copy
import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
lib_path = os.path.join(os.path.dirname(__file__), "..", "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
import json
from kubernetes import client as kubernetes_client
from kubernetes import config as kubernetes_config
from passwords import decode_passwords

import base64
import tempfile
import re

kubernetes_fields = set([
    "auth_mode",
    "cluster_url",
    "cluster_ca",
    "client_cert",
    "user_token",
    "user_name",
    "aws_cluster_name",
    "aws_access_key_id",
    "aws_region_name",
    "storage_class",
    "namespace",
    "service_type",
    "ingress_host_pattern",
    "ingress_annotations",
    "node_port_hostname_internal",
    "node_port_hostname_external",
    "client_key",
    "user_password",
    "aws_secret_access_key",
    "image_pull_secrets",
    "in_cluster_mode",
    "jupyter_passwd",
    "api_token"
])


# TODO: add handler if no connection to K8S is available, e.g. time out or retry
class K8SUtils():
    def __init__(self, settings):
        self.connected = False
        self.settings = settings
        # TODO: move to create_ingress after fixing splunk bug
        if self.settings.get('service_type') == "ingress":
            # TODO: for now try...catch to prevent parsing error on reading an empty or not yet existing ingress_annotation
            # FIXME: Can't use splunk's service conf
            # TODO: sdk ticket for config parser 
            # ingress_annotations = self.service.confs["docker"]["connection"].ingress_annotations
            # As Splunk is giving me this:
            # {"kubernetes.io/ingress.class": "alb", "alb.ingress.kubernetes.io/ssl-redirect": "443", "alb.ingress.kubernetes.io/listen-ports": "[{\"HTTP\": 80}, {\"HTTPS\":443}]", "alb.ingress.kubernetes.io/scheme": "internet-facing", "alb.ingress.kubernetes.io/target-type": "ip", "alb.ingress.kubernetes.io/target-group-attributes": "stickiness.enabled=true,stickiness.lb_cookie.duration_seconds=28800", "alb.ingress.kubernetes.io/success-codes": "200,301,303"}
            # which leads to an json.decoder.JSONDecodeError: Expecting ',' delimiter: line 1 column 137 (char 136)
            # Therefore I use Python's configparser here which depends on docker.conf being stored in local
            try:
                import configparser
                confs = configparser.ConfigParser()
                confs.read(os.path.join(os.path.dirname(__file__), "..", "local", "docker.conf"))
                ingress_annotations = confs['connection']['ingress_annotations']
            except:
                ingress_annotations = "{}"
                pass          
            self.ingress_annotations = json.loads(ingress_annotations)

        if self.is_enabled(self.settings):
            self._connect()

    def __bool__(self):
        return self.connected

    @classmethod
    def from_service(cls, service):
        settings = service.confs["docker"]["connection"]
        decode_passwords(service, settings)
        # get settings as dict from splunk entity
        return cls(settings.content)

    def _connect(self):
        config = self._create_client_configuration(self.settings)
        self.k8s = kubernetes_client.ApiClient(config)
        self.connected = True

    @staticmethod
    def _create_client_configuration(kubernetes_settings):
        config = kubernetes_client.Configuration()

        if kubernetes_settings.get("auth_mode") == "aws-iam":
            # https://github.com/kubernetes-sigs/aws-iam-authenticator
            # https://aws.amazon.com/de/about-aws/whats-new/2019/05/amazon-eks-simplifies-kubernetes-cluster-authentication/
            # https://github.com/aws/aws-cli/blob/develop/awscli/customizations/eks/get_token.py

            # get cluster info
            import boto3
            eks_client = boto3.client('eks',
                                      region_name=kubernetes_settings.get("aws_region_name"),
                                      aws_access_key_id=kubernetes_settings.get("aws_access_key_id"),
                                      aws_secret_access_key=kubernetes_settings.get("aws_secret_access_key"))
            cluster_info = eks_client.describe_cluster(
                name=kubernetes_settings.get("aws_cluster_name"))
            aws_cluster_ca = cluster_info['cluster']['certificateAuthority']['data']
            aws_cluster_url = cluster_info['cluster']['endpoint']

            # get authentication token
            from botocore.signers import RequestSigner  # pylint: disable=import-error
            STS_TOKEN_EXPIRES_IN = 60
            session = boto3.Session(
                region_name=kubernetes_settings.get("aws_region_name"),
                aws_access_key_id=kubernetes_settings.get("aws_access_key_id"),
                aws_secret_access_key=kubernetes_settings.get("aws_secret_access_key")
            )
            sts_client = session.client('sts')
            service_id = sts_client.meta.service_model.service_id
            token_signer = RequestSigner(
                service_id,
                kubernetes_settings.get("aws_region_name"),
                'sts',
                'v4',
                session.get_credentials(),
                session.events
            )
            signed_url = token_signer.generate_presigned_url(
                {
                    'method': 'GET',
                    'url': 'https://sts.{}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15'.format(kubernetes_settings.get("aws_region_name")),
                    'body': {},
                    'headers': {
                        'x-k8s-aws-id': kubernetes_settings.get("aws_cluster_name")
                    },
                    'context': {}
                },
                region_name=kubernetes_settings.get("aws_region_name"),
                expires_in=STS_TOKEN_EXPIRES_IN,
                operation_name=''
            )
            base64_url = base64.urlsafe_b64encode(
                signed_url.encode('utf-8')).decode('utf-8')
            auth_token = 'k8s-aws-v1.' + re.sub(r'=*', '', base64_url)

            config.host = aws_cluster_url
            ca_data = base64.standard_b64decode(aws_cluster_ca)
            fp = tempfile.NamedTemporaryFile(delete=False)   # TODO when to delete?
            fp.write(ca_data)
            fp.close()
            config.ssl_ca_cert = fp.name
            config.api_key["authorization"] = auth_token
            config.api_key_prefix["authorization"] = "Bearer"

        elif kubernetes_settings.get("auth_mode") == "cert-key":
            config.host = kubernetes_settings.get("cluster_url")
            if kubernetes_settings.get("client_cert"):
                try:
                    cert_data = base64.standard_b64decode(
                        kubernetes_settings.get("client_cert"))
                    fp = tempfile.NamedTemporaryFile(
                        delete=False)   # TODO when to delete?
                    fp.write(cert_data)
                    fp.close()
                    config.cert_file = fp.name
                except Exception as e:
                    raise Exception("Error applying cluster cert: %s" % (e))

            if kubernetes_settings.get("client_key"):
                try:
                    key_data = base64.standard_b64decode(
                        kubernetes_settings.get("client_key"))
                    fp = tempfile.NamedTemporaryFile(
                        delete=False)   # TODO when to delete?
                    fp.write(key_data)
                    fp.close()
                    config.key_file = fp.name
                except Exception as e:
                    raise Exception(
                        "Error applying cluster key: %s" % (e))

            if kubernetes_settings.get("cluster_ca"):
                try:
                    cluster_ca_data = base64.standard_b64decode(
                        kubernetes_settings.get("cluster_ca"))
                    fp = tempfile.NamedTemporaryFile(
                        delete=False)   # TODO when to delete?
                    fp.write(cluster_ca_data)
                    fp.close()
                    config.ssl_ca_cert = fp.name
                except Exception as e:
                    raise Exception(
                        "Error applying cluster ca: %s" % (e))

            config.verify_ssl = False

        elif kubernetes_settings.get("auth_mode") == "user-token":
            config.host = kubernetes_settings.get("cluster_url")
            config.api_key["authorization"] = kubernetes_settings.get("user_token")
            config.api_key_prefix["authorization"] = "Bearer"
            config.verify_ssl = False

        elif kubernetes_settings.get("auth_mode") == "user-login":
            if kubernetes_settings.get("cluster_ca"):
                try:
                    cluster_ca_data = base64.standard_b64decode(
                        kubernetes_settings.get("cluster_ca"))
                    fp = tempfile.NamedTemporaryFile(
                        delete=False)   # TODO when to delete?
                    fp.write(cluster_ca_data)
                    fp.close()
                    config.ssl_ca_cert = fp.name
                except Exception as e:
                    raise Exception(
                        "Error applying cluster ca: %s" % (e))
            config.host = kubernetes_settings.get("cluster_url")

            import urllib3
            config.api_key["authorization"] = urllib3.util.make_headers(
                basic_auth=kubernetes_settings.get("user_name") + ':' + kubernetes_settings.get("user_password")
            ).get('authorization')

            config.verify_ssl = False

        elif kubernetes_settings.get("auth_mode") == "service-account":
            kubernetes_config.load_incluster_config()
            config = kubernetes_client.Configuration()

        else:
            raise Exception("invalid auth mode '%s'" % kubernetes_settings.get("auth_mode"))

        return config

    @staticmethod
    def get_clean_model(model_name):
        valids = []
        for c in model_name:
            if c.isalpha() or c.isdigit():
                valids.append(c.lower())
            else:
                valids.append('-')
        s = ''.join(valids)
        return s.strip('-')

    @staticmethod
    def validate_cluster(kubernetes_settings):
        """ raises an exception if the cluster configuration is not valid"""
        try:
            config = K8SUtils._create_client_configuration(kubernetes_settings)
            api_client = kubernetes_client.ApiClient(config)
            version_api = kubernetes_client.VersionApi(api_client)
            version_api.get_code()
        except Exception as e:
            raise Exception("Could not connect to Kubernetes.\n\n%s" % e)

    @staticmethod
    def is_enabled(settings):
        if "auth_mode" in settings:
            if settings.get("auth_mode") == "aws-iam" and settings.get("aws_cluster_name"):
                return True
            if settings.get("auth_mode") == "cert-key" and settings.get("cluster_url"):
                return True
            if settings.get("auth_mode") == "user-token" and settings.get("cluster_url"):
                return True
            if settings.get("auth_mode") == "user-login" and settings.get("cluster_url"):
                return True
            if settings.get("auth_mode") == "service-account":
                return True
        return False

    def create_deployment(self, runtime, model, image, environment_vars):
        # Disable HTTPS for in cluster traffic
        if self.settings.get("in_cluster_mode") == "1":
            environment_vars = copy.deepcopy(environment_vars)
            environment_vars["ENABLE_HTTPS"] = "false"
        model_name = self.get_clean_model(model)
        apps_api = kubernetes_client.AppsV1Api(self.k8s)
        resource_limits = None
        if runtime == "nvidia":
            resource_limits = kubernetes_client.V1ResourceRequirements(
                requests={
                    "nvidia.com/gpu": "1"
                },
                limits={
                    "nvidia.com/gpu": "1"
                }
            )
        return apps_api.create_namespaced_deployment(
            namespace=self.settings.get("namespace"),
            body=kubernetes_client.V1Deployment(
                metadata=kubernetes_client.V1ObjectMeta(
                    name=model_name,
                    namespace=self.settings.get("namespace"),
                    labels={
                        "mltk-container": "",
                        "mltk-model": model_name,
                    },
                ),
                spec=kubernetes_client.V1DeploymentSpec(
                    replicas=1,
                    selector=kubernetes_client.V1LabelSelector(
                        match_labels={
                            "mltk-model": model_name,
                        }
                    ),
                    template=kubernetes_client.V1PodTemplateSpec(
                        metadata=kubernetes_client.V1ObjectMeta(
                            labels={
                                "mltk-model": model_name,
                            },
                        ),
                        spec=kubernetes_client.V1PodSpec(
                            containers=[
                                kubernetes_client.V1Container(
                                    name="mltk-model",
                                    image=image,
                                    resources=resource_limits,
                                    volume_mounts=[
                                        kubernetes_client.V1VolumeMount(
                                            name="data",
                                            mount_path="/srv",
                                        ),
                                    ],
                                    env=[
                                        kubernetes_client.V1EnvVar(name=name, value=environment_vars[name]) for name in environment_vars
                                    ]
                                ),
                            ],
                            volumes=[
                                kubernetes_client.V1Volume(
                                    name="data",
                                    persistent_volume_claim=kubernetes_client.V1PersistentVolumeClaimVolumeSource(
                                        claim_name="dltk",
                                    ),
                                )
                            ],
                            image_pull_secrets=[kubernetes_client.V1LocalObjectReference(name=self.settings.get("image_pull_secrets"))]
                        ),
                    ),
                ),
            ),
        )

    def create_service(self, deployment, model, mode):
        if self.settings.get("service_type") == "load_balancer":
            service_type = "LoadBalancer"
        elif self.settings.get("service_type") == "route" or self.settings.get("service_type") == "ingress":
            service_type = None
        else:
            service_type = "NodePort"
        model_name = self.get_clean_model(model)
        core_api = kubernetes_client.CoreV1Api(self.k8s)
        active_ports = [kubernetes_client.V1ServicePort(
            name="api",
            port=5000,
            protocol="TCP",
            target_port=5000,
        )]
        if mode == "DEV":
            active_ports = [
                kubernetes_client.V1ServicePort(
                    name="jupyter",
                    port=8888,
                    protocol="TCP",
                    target_port=8888,
                ),
                kubernetes_client.V1ServicePort(
                    name="tensorboard",
                    port=6006,
                    protocol="TCP",
                    target_port=6006,
                ),
                kubernetes_client.V1ServicePort(
                    name="api",
                    port=5000,
                    protocol="TCP",
                    target_port=5000,
                ),
                kubernetes_client.V1ServicePort(
                    name="spark",
                    port=4040,
                    protocol="TCP",
                    target_port=4040,
                ),
                kubernetes_client.V1ServicePort(
                    name="mlflow",
                    port=6060,
                    protocol="TCP",
                    target_port=6000,
                ),
            ]

        core_api.create_namespaced_service(
            namespace=self.settings.get("namespace"),
            body=kubernetes_client.V1Service(
                api_version="v1",
                kind="Service",
                metadata=kubernetes_client.V1ObjectMeta(
                    name=model_name,
                    namespace=self.settings.get("namespace"),
                    owner_references=[
                        kubernetes_client.V1OwnerReference(
                            api_version="apps/v1",
                            controller=True,
                            kind="Deployment",
                            name=model_name,
                            uid=deployment.metadata.uid,
                        ),
                    ],
                ),
                spec=kubernetes_client.V1ServiceSpec(
                    type=service_type,
                    selector={
                        "mltk-model": model_name,
                    },
                    ports=active_ports,
                ),
            ),
        )

    def create_route(self, deployment, model, port_name):
        # TODO: check if this is still working as openshift was updated
        from openshift.dynamic import DynamicClient
        dyn_client = DynamicClient(self.k8s)
        model_name = self.get_clean_model(model)
        v1_routes = dyn_client.resources.get(api_version='route.openshift.io/v1', kind='Route')
        v1_routes.create(
            body={
                "apiVersion": "route.openshift.io/v1",
                "kind": "Route",
                "metadata": {
                    # TODO: Consider using host pattern (similar to settings.ingress_host_pattern) for routes too
                    "name": "dltk-" + model_name + "-" + port_name,
                    "ownerReferences": [{
                        "apiVersion": "apps/v1",
                        "controller": True,
                        "kind": "Deployment",
                        "name": model_name,
                        "uid": deployment.metadata.uid,
                    }],
                },
                "spec": {
                    "port": {
                        "targetPort": port_name
                    },
                    "tls": {
                        "termination": "edge"
                    },
                    "to": {
                        "kind": "Service",
                        "name": model_name,
                    }
                }
            },
            namespace=self.settings.get("namespace")
        )

    def create_ingress(self, deployment, model, port_name):
        networking_v1_api = kubernetes_client.NetworkingV1Api(self.k8s)
        host_pattern = self.settings.get("ingress_host_pattern")
        model_name = self.get_clean_model(model)
        ingress_name = model_name + "-" + port_name
        body = kubernetes_client.V1Ingress(
            api_version="networking.k8s.io/v1",
            kind="Ingress",
            metadata=kubernetes_client.V1ObjectMeta(
                name=ingress_name,
                namespace=self.settings.get("namespace"),
                annotations=self.ingress_annotations,
                owner_references=[
                    kubernetes_client.V1OwnerReference(
                        api_version="apps/v1",
                        controller=True,
                        kind="Deployment",
                        name=model_name,
                        uid=deployment.metadata.uid,
                    ),
                ],
            ),
            spec=kubernetes_client.V1IngressSpec(
                rules=[kubernetes_client.V1IngressRule(
                    host=host_pattern.format(name=model_name, port=port_name),
                    http=kubernetes_client.V1HTTPIngressRuleValue(
                        paths=[kubernetes_client.V1HTTPIngressPath(
                            path="/",
                            path_type="Prefix",
                            backend=kubernetes_client.V1IngressBackend(
                                service=kubernetes_client.V1IngressServiceBackend(
                                    port=kubernetes_client.V1ServiceBackendPort(
                                        name=port_name
                                    ),
                                    name=model_name)
                            )
                        )]
                    )
                )
                ]
            )
        )
        networking_v1_api.create_namespaced_ingress(
            namespace=self.settings.get("namespace"),
            body=body
        )

    def ensure_volume(self, storage_size):
        core_api = kubernetes_client.CoreV1Api(self.k8s)

        try:
            volume_claim = core_api.read_namespaced_persistent_volume_claim(
                namespace=self.settings.get("namespace"),
                name="dltk",
            )
        except kubernetes_client.rest.ApiException as e:
            if e.status != 404:
                raise
            volume_claim = None
        if not volume_claim:
            volume_claim = core_api.create_namespaced_persistent_volume_claim(
                namespace=self.settings.get("namespace"),
                body=kubernetes_client.V1PersistentVolumeClaim(
                    api_version='v1',
                    kind="PersistentVolumeClaim",
                    metadata=kubernetes_client.V1ObjectMeta(
                        name="dltk",
                        namespace=self.settings.get("namespace"),
                        labels={
                            "app": "dltk",
                        }
                    ),
                    spec=kubernetes_client.V1PersistentVolumeClaimSpec(
                        access_modes=["ReadWriteMany"],
                        resources=kubernetes_client.V1ResourceRequirements(
                            requests={
                                "storage": storage_size,
                            },
                        ),
                        storage_class_name=self.settings.get("storage_class"),
                    ),
                ),
            )

    def get_logs(self, model_name):
        entries = []
        core_api = kubernetes_client.CoreV1Api(self.k8s)
        pods = core_api.list_namespaced_pod(
            namespace=self.settings.get("namespace"),
            label_selector="mltk-model=%s" % (model_name),
        ).items
        for pod in pods:
            logs = core_api.read_namespaced_pod_log(
                name=pod.metadata.name,
                namespace=self.settings.get("namespace"),
                tail_lines=1000,
                timestamps=True,
            )
            for line in logs.split("\n"):
                entries.append({
                    "_time": str(line[:30]),
                    "log": str(line[31:]),
                })
        return entries

    def delete_deployment(self, model_name):
        apps_api = kubernetes_client.AppsV1Api(self.k8s)
        apps_api.delete_namespaced_deployment(
            name=model_name,
            namespace=self.settings.get("namespace"),
        )

    def get_deployments_by_name(self):
        apps_api = kubernetes_client.AppsV1Api(self.k8s)
        deployments = apps_api.list_namespaced_deployment(
            namespace=self.settings.get("namespace"),
            label_selector="mltk-container",
        ).items
        deployments_by_name = {}
        for d in deployments:
            deployments_by_name[d.metadata.name] = d
        return deployments_by_name

    def _get_external_url(self, name, port_name):
        core_api = kubernetes_client.CoreV1Api(self.k8s)
        service = core_api.read_namespaced_service(name, self.settings.get("namespace"))
        ingress_hostnames = []
        if service.status and service.status.load_balancer and service.status.load_balancer.ingress:
            for ingress in service.status.load_balancer.ingress:
                if ingress.hostname:
                    ingress_hostnames.append(ingress.hostname)
                if ingress.ip:
                    ingress_hostnames.append(ingress.ip)
        for p in service.spec.ports:
            if p.name == port_name:
                if service.spec.type == "NodePort":
                    if port_name == "api":
                        hostname = self.settings.get("node_port_hostname_internal")
                    else:
                        hostname = self.settings.get("node_port_hostname_external")
                    if not hostname and len(ingress_hostnames):
                        hostname = ingress_hostnames[0]
                    if hostname:
                        # enforce HTTPS for data transmission related api
                        # additionally enfore HTTPS for jupyter too
                        if port_name == "api" or port_name == "jupyter":
                            return "https://%s:%s" % (hostname, p.node_port)
                        else:
                            return "http://%s:%s" % (hostname, p.node_port)
                elif service.spec.type == "LoadBalancer":
                    if len(ingress_hostnames):
                        hostname = ingress_hostnames[0]
                        # enforce HTTPS for data transmission related api
                        # additionally enfore HTTPS for jupyter too
                        if port_name == "api" or port_name == "jupyter":
                            return "https://%s:%s" % (hostname, p.port)
                        else:
                            return "http://%s:%s" % (hostname, p.port)
        return None

    def _get_internal_url(self, name, port_name):
        core_api = kubernetes_client.CoreV1Api(self.k8s)
        service = core_api.read_namespaced_service(name, self.settings.get("namespace"))
        for p in service.spec.ports:
            if p.name == port_name:
                return "http://%s:%s" % (service.spec.cluster_ip, p.port)
        return None

    # TODO: make this code independent of port_name specific logic (e.g. port_name="api") and move this logic instead to the caller
    def get_url(self, k8s_name, port_name):
        if port_name == "api" and self.settings.get("in_cluster_mode") == "1":
            return self._get_internal_url(k8s_name, port_name)
        if self.settings.get("service_type") == "load_balancer" or self.settings.get("service_type") == "node_port":
            return self._get_external_url(k8s_name, port_name)
        if self.settings.get("service_type") == "route":
            from openshift.dynamic import DynamicClient
            dyn_client = DynamicClient(self.k8s)
            v1_routes = dyn_client.resources.get(api_version='route.openshift.io/v1', kind='Route')
            route = v1_routes.get(
                name="dltk-" + k8s_name + "-" + port_name,
                namespace=self.settings.get("namespace")
            )
            # TODO: get hostname from route and build URL
            return "https://%s" % route.spec["host"]
        if self.settings.get("service_type") == "ingress":
            name = self.settings.get("ingress_host_pattern").format(name=k8s_name, port=port_name)
            return "https://%s" % name
        return None
