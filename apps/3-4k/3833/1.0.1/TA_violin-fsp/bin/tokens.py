import requests
import logger_manager as log

from requests_toolbelt.adapters import host_header_ssl

# set up logging
logger = log.setup_logging('violin_fsp')


def get_lun_id(path, cookies, cert_host, verify):
    """
    To generate endpoints replacing get_lun_id token in original endpoints 
    
    :param path: original endpoint containing token
    :param cookies: cookie for current session for API call
    :param cert_host: issuer of certificate
    :param verify: value to decide way of certificate verification while executing api call
    :return: list of generated endpoints
    """
    try:
        snap_endpoint = []
        lun_url = path.split('/concerto')[0] + "/concerto/logicalresource/sanresource"
        request_session = requests.Session()
        request_session.mount('https://', host_header_ssl.HostHeaderSSLAdapter())
        headers = {"Host": cert_host}
        lun_data = request_session.get(lun_url, cookies=cookies, verify=verify, headers=headers)
        lun_data_json = lun_data.json()

        for virtual_device in lun_data_json.get("data", {}).get("virtual_devices", []):
            if 'object_id' in virtual_device:
                snap_url = path.split('/concerto')[0] + "/concerto/logicalresource/snapshotresource/" \
                           + virtual_device['object_id']
                snap_endpoint.append(snap_url)

        return snap_endpoint

    except Exception as e:
        logger.error(
            "Violin FSP Error: Looks like an error while getting snaphot information %s : %s" % (str(e), path))
        return None


def get_storagepool_id(path, cookies, cert_host, verify):
    """
    To generate endpoints replacing get_storagepool_id token in original endpoints 

    :param path: original endpoint containing token
    :param cookies: cookie for current session for API call
    :param cert_host: issuer of certificate
    :param verify: value to decide way of certificate verification while executing api call
    :return: list of generated endpoints
    """
    try:
        pool_endpoint = []
        storagepool_url = path.split('/concerto')[0] + "/concerto/physicalresource/storagepool"
        request_session = requests.Session()
        request_session.mount('https://', host_header_ssl.HostHeaderSSLAdapter())
        headers = {"Host": cert_host}
        storagepool_data = request_session.get(storagepool_url, cookies=cookies, verify=verify, headers=headers)
        storagepool_data_json = storagepool_data.json()

        if storagepool_data_json.get("data", {}).get("storage_pools"):
            for storage_pool in storagepool_data_json['data']['storage_pools']:
                if 'storage_pool_id' in storage_pool:
                    pool_url = storagepool_url + '/' + str(storage_pool['storage_pool_id'])
                    pool_endpoint.append(pool_url)
            pool_endpoint.append(storagepool_url)

        return pool_endpoint

    except Exception as e:
        logger.error("Violin FSP Error: Looks like an error while getting storagepool information %s : %s" % (
                str(e), path))
        return None


def get_client_id(path, cookies, cert_host, verify):
    """
    To generate endpoints replacing get_client_id token in original endpoints 

    :param path: original endpoint containing token
    :param cookies: cookie for current session for API call
    :param cert_host: issuer of certificate
    :param verify: value to decide way of certificate verification while executing api call
    :return: list of generated endpoints
    """
    try:
        sid = []
        client_endpoint = []
        san_client_url = path.split('/concerto')[0] + "/concerto/client/sanclient"
        request_session = requests.Session()
        request_session.mount('https://', host_header_ssl.HostHeaderSSLAdapter())
        headers = {"Host": cert_host}
        san_client_data = request_session.get(san_client_url, cookies=cookies, verify=verify, headers=headers)
        san_client_data_json = san_client_data.json()

        if san_client_data_json.get("data", {}).get("san_clients"):
            for san_client in san_client_data_json['data']['san_clients']:
                sid.append(san_client['sanclient_id'])
                client_url = san_client_url + '/' + str(san_client['sanclient_id'])
                client_endpoint.append(client_url)
            client_endpoint.append(san_client_url)

        return client_endpoint

    except Exception as e:
        logger.error(
            "Violin FSP Error: Looks like an error while getting client information %s : %s" % (str(e), path))
        return None


def get_timemark_lun_id(path, cookies, cert_host, verify):
    """
    To generate endpoints replacing get_timemark_lun_id token in original endpoints 

    :param path: original endpoint containing token
    :param cookies: cookie for current session for API call
    :param cert_host: issuer of certificate
    :param verify: value to decide way of certificate verification while executing api call
    :return: list of generated endpoints
    """
    try:
        snap_endpoint = []
        lun_url = path.split('/concerto')[0] + "/concerto/logicalresource/sanresource"
        request_session = requests.Session()
        request_session.mount('https://', host_header_ssl.HostHeaderSSLAdapter())
        headers = {"Host": cert_host}
        lun_data = request_session.get(lun_url, cookies=cookies, verify=verify, headers=headers)
        lun_data_json = lun_data.json()

        for virtual_device in lun_data_json.get('data', {}).get('virtual_devices', []):
            if virtual_device['timemarkEnabled']:
                snap_endpoint.append(path.split('/concerto')[0] + "/concerto/logicalresource/timemark/"
                                     + str(virtual_device['object_id']))

        group_url = path.split('/concerto')[0] + "/concerto/logicalresource/snapshotgroup"
        group_data = request_session.get(group_url, cookies=cookies, verify=verify, headers=headers)
        group_data_json = group_data.json()

        for snapshot_group in group_data_json.get('data', {}).get('snapshot_groups', []):
            if snapshot_group['timemarkEnabled']:
                snap_endpoint.append(path.split('/concerto')[0] + "/concerto/logicalresource/timemark/"
                                     + str(snapshot_group['object_id']))

        return snap_endpoint

    except Exception as e:
        logger.error(
            "Violin FSP Error: Looks like an error while getting TimeMark information %s : %s" % (str(e), path))
        return None

def get_physical_adapter_id(path, cookies, cert_host, verify):
    """
    To generate endpoints replacing get_physical_adapter_id token in original endpoints 

    :param path: original endpoint containing token
    :param cookies: cookie for current session for API call
    :param cert_host: issuer of certificate
    :param verify: value to decide way of certificate verification while executing api call
    :return: list of generated endpoints
    """
    try:
        physical_adapter_endpoint = []
        physical_adapter_url = path.split('/concerto')[0] + "/concerto/physicalresource/physicaladapter"
        request_session = requests.Session()
        request_session.mount('https://', host_header_ssl.HostHeaderSSLAdapter())
        headers = {"Host": cert_host}
        physical_adapter_data = request_session.get(physical_adapter_url, cookies=cookies, verify=verify, headers=headers)
        physical_adapter_data_json = physical_adapter_data.json()

        if physical_adapter_data_json.get("data", {}).get("physical_adapters", []):
            for physical_adapter in physical_adapter_data_json['data']['physical_adapters']:
                adapter_url = physical_adapter_url + '/' + str(physical_adapter['object_id'])
                physical_adapter_endpoint.append(adapter_url)

        return physical_adapter_endpoint

    except Exception as e:
        logger.error(
            "Violin FSP Error: Looks like an error while getting physical adapter information %s : %s" % (str(e), path))
        return None
