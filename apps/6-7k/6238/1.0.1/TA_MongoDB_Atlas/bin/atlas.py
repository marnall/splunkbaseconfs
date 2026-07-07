import os
from requests.auth import HTTPDigestAuth
from requests import Request, Session
from urllib.parse import urlparse
import datetime
import zlib
import json
import gzip
import io

class AtlasClient:
    """Interacts with the MongoDB Atlas API"""

    base_url = "https://cloud.mongodb.com/api/atlas/v1.0"
    group_id = None
    cluster_id = None
    auth = None

    def __init__(self, group_id, cluster_id, pub_key, priv_key, base_url=None):

        self.auth = HTTPDigestAuth(pub_key, priv_key)
        self.group_id = group_id
        self.cluster_id = cluster_id

        if base_url:
            self.base_url = base_url

    def _make_request(self, req_prepared):
        """Executes a prepared request"""
        s = Session()
        req_prepared.auth = self.auth
        resp = s.send(req_prepared)
        resp.raise_for_status()

        return resp

    def fetch_cluster_hosts(self):
        """Identify which hosts are part of the cluster"""
        endpoint = f"{self.base_url}/groups/{self.group_id}/clusters/{self.cluster_id}"

        req = Request('GET', endpoint, auth=self.auth)
        req_prepared = req.prepare()
        res = self._make_request(req_prepared)

        raw_hosts = res.json()["mongoURI"].split(",")

        hosts = []
        for url in raw_hosts:
            if "//" in url:
                url = urlparse(url).netloc
            hosts.append(url.split(":")[0])

        return hosts

    def fetch_host_logs(self, host, file_name, start_dt, end_dt):
        """Fetch logs for an individual host"""
        endpoint = f"{self.base_url}/groups/{self.group_id}/clusters/{host}/logs/{file_name}"

        params = {
            "startDate": start_dt.strftime('%s'),
            "endDate": end_dt.strftime('%s')
        }
        headers = {
            "Accept": "application/gzip"
        }

        req = Request('GET', endpoint, auth=self.auth, params=params, headers=headers)
        req_prepared = req.prepare()

        res = self._make_request(req_prepared)
        logs = self.parse_host_logs_response(res)

        return logs

    def parse_host_logs_response(self, response):
        """Parse host logs response into JSON structure"""
        logs = []
        if not response.content:
            return []

        data = response.content

        with gzip.open(io.BytesIO(response.content), "r") as f_gzip:
            data = f_gzip.read()

        for c in data.splitlines():
            entry = c.decode()
            if entry:
                json_entry = json.loads(entry)
                logs.append(json_entry)
        return logs
