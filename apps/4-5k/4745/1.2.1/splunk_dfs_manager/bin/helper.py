from future.standard_library import install_aliases
install_aliases()  # noqa: E402
from builtins import str
from builtins import object
import configparser
import json
import locale
import os
import requests
import six
import socket
from .pbs_global_configs import PbsGlobalConfigs as pbsConf
from .messaging import Messaging as msging


class RestComm(object):
    connectTimeout = 2
    readTimeout = 4
    restTimeout = (connectTimeout, readTimeout)

    @staticmethod
    def splunk_rest(endpoint, header, host='127.0.0.1', mgmt_port="8089", master=False, data=None, params=None,
                    verify=False):
        response = None
        try:
            # TODO: How should we check for dynamic management port?
            if not master:
                if params is not None:
                    response = requests.get(
                        "https://" + host + ":" + mgmt_port + "/" + endpoint + "?output_mode=json",
                        params=params,
                        headers=header,
                        verify=verify,
                        timeout=RestComm.restTimeout
                    )
                elif data is not None:
                    response = requests.post(
                        "https://" + host + ":" + mgmt_port + "/" + endpoint + "?output_mode=json",
                        data=data,
                        headers=header,
                        verify=verify,
                        timeout=RestComm.restTimeout
                    )
                else:
                    response = requests.get(
                        "https://" + host + ":" + mgmt_port + "/" + endpoint + "?output_mode=json",
                        headers=header,
                        verify=verify,
                        timeout=RestComm.restTimeout
                    )
            else:
                response = requests.get(
                    "http://" + host + ":" + mgmt_port + "/" + endpoint,
                    verify=verify,
                    timeout=RestComm.restTimeout
                )

            if response.status_code in (requests.codes.ok, requests.codes.created):
                # TODO: Make this cleaner I think?
                try:
                    response = response.json()

                except ValueError:
                    response = response.content
            else:
                # This will raise a exception when we get a bad/invalid response
                response.raise_for_status()
                return response.text

        except requests.HTTPError:
            # print("HTTP requests returned error: " + str(response.status_code))
            return None
        except requests.Timeout:
            # print("HTTP request time out")
            return None
        except requests.ConnectionError:
            # print("Connection issues encountered when executing: " + response.url)
            return None

        if six.PY3 and isinstance(response, six.binary_type):
            return response.decode(locale.getpreferredencoding())
        else:
            return response

    @staticmethod
    def get_config_using_rest(conf_file, stanza, key, header, mgmt_port, hostname='127.0.0.1'):
        key_suffix = ("/" + key) if key else ""
        endpoint = "services/properties/" + conf_file + "/" + stanza + key_suffix
        return RestComm.splunk_rest(endpoint, header, hostname, mgmt_port)

    @staticmethod
    def modify_config_using_rest(conf_file, stanza, key, value, header, mgmt_port, app=pbsConf.app_name):
        data = {key: value}

        endpoint = "servicesNS/nobody/" + app + "/" + "configs/" + 'conf-' + conf_file + "/" + stanza
        response = RestComm.splunk_rest(endpoint, header, mgmt_port=mgmt_port, data=data)
        return response

    @staticmethod
    def start_search_using_rest(searchQuery, header, mgmt_port):
        endpoint = "services/search/jobs"
        return RestComm.splunk_rest(endpoint, header, mgmt_port=mgmt_port, data={'search': searchQuery})

    @staticmethod
    def check_search_status_using_rest(sid, header, mgmt_port):
        endpoint = "services/search/jobs/%s/" % sid
        return RestComm.splunk_rest(endpoint, header, mgmt_port=mgmt_port)

    @staticmethod
    def get_search_result_using_rest(sid, header, mgmt_port):
        endpoint = "services/search/jobs/%s/results" % sid
        return RestComm.splunk_rest(endpoint, header, mgmt_port=mgmt_port)

    @staticmethod
    def run_splunk_search(query, header, mgmt_port):
        results = []
        try:
            response = RestComm.start_search_using_rest(query, header, mgmt_port)
            sid = response["sid"]

            # Wait for search to be finished
            is_query_finished = False
            while not is_query_finished:
                response = RestComm.check_search_status_using_rest(sid, header, mgmt_port)
                is_query_finished = response["entry"][0]["content"]["isDone"]
            results = RestComm.get_search_result_using_rest(sid, header, mgmt_port)["results"]
        except Exception, e:
            results = [{"Error": "Failed: " + e.message}]

        return results

    @staticmethod
    def get_app_config(mgmt_port, header):
        app_config = {}
        try:
            config_resp = RestComm.get_config_using_rest(pbsConf.conf_name, pbsConf.conf_stanza, '',
                                                         header, mgmt_port)
            config_list = config_resp['entry']
            for conf_map in config_list:
                app_config[conf_map['name']] = conf_map['content']
        except Exception as e:
            raise e

        return app_config

    @staticmethod
    def get_spark_info(spark_master_ip, spark_master_ui):
        try:
            spark_master = SparkMaster(spark_master_ip, spark_master_ui)
            spark_data = spark_master.spark_rest()
        except Exception as e:
            raise e

        return spark_data

    @staticmethod
    def get_sh_site_info(mgmt_port, header, global_warnings, multisite_warnings):
        resp = RestComm.splunk_rest('services/cluster/searchhead/searchheadconfig', header, '127.0.0.1', mgmt_port)

        if resp is None:
            multisite_warnings.append(msging.warn_obj_map["mul_site_connect_warn"].to_json())
            return '-'

        cluster_peer_data = resp['entry']
        cluster_peer_content = cluster_peer_data[0]['content']
        multi_site = False
        if 'multiSite' in cluster_peer_content:
            multi_site = True if cluster_peer_content['multiSite'].lower() == "true" else False

        if multi_site is False:
            multisite_warnings.append(msging.warn_obj_map["mul_site_clustering_warn"].to_json())
            return '-'

        site = '-'

        if 'site' not in cluster_peer_content or (
                'site' in cluster_peer_content and cluster_peer_content['site'] == 'default'):
            multisite_warnings.append(msging.warn_obj_map["mul_site_no_site_warn"].to_json())
            global_warnings.append(msging.warn_obj_map["mul_site_no_site_warn"].to_json())
            return site

        return cluster_peer_content['site']

    @staticmethod
    def get_search_peers_keys_app(mgmt_port, header):
        params = {"count": "0"}
        resp = RestComm.splunk_rest('services/search/distributed/peers', header, '127.0.0.1', mgmt_port,
                                    params=params)
        peer_data = resp['entry']
        hosts_list = []
        guid_list = []
        peer_map = {}
        for peer in peer_data:
            peer_content = peer['content']
            peer_guid = peer_content['guid']
            host, port = peer['name'].split(':')
            # Revert to using host field instead?
            try:
                ip = socket.gethostbyname(host)
            except Exception:
                ip = host
            peer_content['peer_uri'] = '{}:{}'.format(ip, port)

            guid_list.append(peer_guid)
            hosts_list.append(ip)
            peer_map[peer_guid] = peer_content

        return guid_list, hosts_list, peer_map


class Helper(object):
    @staticmethod
    def write_json_response(resp, obj):
        resp.setHeader('content-type', 'text/json')
        resp.write(json.dumps(obj, indent=4))

    @staticmethod
    def is_valid_history_resp(history_resp):
        if history_resp is not None:
            valid_type = isinstance(history_resp, dict)
            if valid_type:
                return pbsConf.spark_version in history_resp['spark']
        return False

    @staticmethod
    def check_for_conf(path, stanza, key):
        port = None
        config = configparser.ConfigParser(strict=False)

        if os.path.exists(path):
            config.read(path)
            if config.has_option(stanza, key) is True:
                host_port = config.get(stanza, key)
                _, port = host_port.split(':')

        return port

    @staticmethod
    def get_splunkd_mgmt_port():
        try:
            local_conf_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'system', 'local', 'web.conf')
            default_conf_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'system', 'default', 'web.conf')

            stanza = "settings"
            key = "mgmtHostPort"

            port = Helper.check_for_conf(local_conf_path, stanza, key)
            if port is None:
                port = Helper.check_for_conf(default_conf_path, stanza, key)

            return port

        except Exception:
            return None

    @staticmethod
    def get_node_site_info(host, site_map):
        if host not in site_map:
            return '-'

        return '-' if site_map[host] == 'default' else site_map[host]


class Node(object):
    def __init__(self, host_name):
        self.host_name = host_name
        self.node_name = "Base Node"


class SparkMaster(Node):
    def __init__(self, host_name, web_ui_port):
        Node.__init__(self, host_name)
        self.host_name = host_name
        self.node_name = "Spark Master"
        self.web_ui_port = web_ui_port
        self.end_point = "json/"

    def spark_rest(self):
        response = RestComm.splunk_rest(self.end_point, None, self.host_name, str(self.web_ui_port), True)
        return response
