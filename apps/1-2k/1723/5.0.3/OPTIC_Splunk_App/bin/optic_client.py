import os, os.path, sys
import urllib
import urllib2
import json
import hashlib
from settings import get_app_home
sys.path.append(os.path.join(get_app_home(), 'lib', 'python2.7', 'site-packages'))
import requests

class OpticClient(object):
    SNAPSHOT_FORMAT="splunk_csv_gz_tar"
    TIMEOUT=2*60
    def __init__(self, username, apikey, **kwargs):
        self.username = username
        self.apikey = apikey
        self.url = "https://api.threatstream.com/api/v1/snapshot/latest/"
        self.proxy_host = kwargs.get('proxy_host')
        self.proxy_port = kwargs.get('proxy_port')
        self.proxy_user = kwargs.get('proxy_user')
        self.proxy_password = kwargs.get('proxy_password')
        self.https_proxy = 'https://%s:%s@%s:%s' % (self.proxy_user, self.proxy_password, self.proxy_host, self.proxy_port)
        self.proxy_dict = None
        if self.proxy_host and self.proxy_port:
            self.proxy_dict = {'https':self.https_proxy}

    def get_url(self):
        data = {"username":self.username, "api_key":self.apikey, "snapshot_format":OpticClient.SNAPSHOT_FORMAT}
        data = urllib.urlencode(data)
        headers = {'Content-Type':'application/json'}
        optic_url = self.url + "?" + data
        response = requests.get(optic_url, headers=headers, proxies=self.proxy_dict)
        if response.status_code >= 400:
            raise Exception("Failed to retrieve url error_code=%s reason=%s" % (response.status_code, response.content))
        result = response.content
        content_json = json.loads(result)
        objects = content_json['objects']
        if len(objects) > 0:
            return objects[0]['download_url'], objects[0]['sha256sum']
        else:
            return None, None

    def get_checksum(self, filename, hasher):
        blocksize = 16 * 1024
        with open(filename, "rb") as file_handler:
            for block in iter(lambda: file_handler.read(blocksize), ""):
                hasher.update(block)
        return hasher.hexdigest()

    def download(self, dest, logger=None):
        (download_url, sha256sum) = self.get_url()
        if logger:
            logger.debug("download_url:%s, checksum:%s" % (download_url, sha256sum))
        else:
            print("download_url:%s, checksum:%s" % (download_url, sha256sum))

        if download_url:
            response = requests.get(download_url, stream=True, proxies=self.proxy_dict, timeout=OpticClient.TIMEOUT)
            if response.status_code >= 400:
                raise Exception ("Failed to download file %s error_code=%s reason=%s" % (download_url, response.status_code, response.content))

            with open(dest, "wb") as file_handler:
                for chunk in response.iter_content(chunk_size=16*1024):
                    if chunk:
                        file_handler.write(chunk)
                        file_handler.flush()

            #verify checksum
            new_sha256sum = self.get_checksum(dest, hashlib.sha256())
            if new_sha256sum != sha256sum:
                raise Exception("checksum mismatch, original checksum=%s, new checksum=%s", (sha256sum, new_sha256sum))
            if logger:
                logger.info("Successfully download the file %s" % (dest))
            else:
                print("Successfully download the file %s" % (dest))
