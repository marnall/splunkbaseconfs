import os
import json
import time
import requests
import gzip
from requests import Request, Session
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from crs_config import logger


class LogUploader:
    LOG_PREFIX = 'stats_logs_'
    LOG_SUFFIX = '.data'
    META_SUFFIX = '.meta'  # created & managed by internel

    RET_SUCCSS = 0
    RET_INVLIAD_TOKEN = 1
    RET_NETWORK_ISSUE = 2
    RET_UNKNOWN = 999

    DEFAULT_TIME_OUT = 20

    def __init__(self, fqdn, token, log_path, http_proxy=None, https_proxy=None, log_prefix=LOG_PREFIX,
                 log_suffix='.data', batch_size=1000, custom_data=None):
        self.fqdn = fqdn
        self.token = token
        self.log_path = log_path
        self.log_prefix = log_prefix
        self.log_suffix = log_suffix
        self.batch_size = batch_size
        if http_proxy != None or https_proxy != None:
            self.proxies = {"http": http_proxy, 'https': https_proxy}
        else:
            self.proxies = None
        # self.http_proxy = http_proxy
        # self.https_proxy = https_proxy
        self.custom_data = custom_data

    def _get_log_files(self):
        logs = set()
        metas = set()
        for file in os.listdir(self.log_path):
            if file.startswith(self.log_prefix):
                if file.endswith(self.log_suffix):
                    logs.add(file)
                elif file.endswith(LogUploader.META_SUFFIX):
                    metas.add(file)
        upload_logs = {}
        for log in logs:
            meta = LogUploader._get_meta_name(log)
            if meta in metas:
                upload_logs[log] = meta
            else:
                upload_logs[log] = ''
        return upload_logs

    @classmethod
    def _get_meta_name(cls, log_name):
        return log_name.rsplit(".", 1)[0] + LogUploader.META_SUFFIX

    def _get_meta(self, meta):
        if meta:
            meta_file = os.path.join(self.log_path, meta)
            if os.path.exists(meta_file):
                with open(meta_file) as f:
                    first_line = f.readline().strip()
                    if first_line:
                        try:
                            return json.loads(first_line)
                        except Exception:
                            pass

        return {'upload_lines': 0, 'upload_time': 0}

    def _update_meta(self, meta, value):
        meta_file = os.path.join(self.log_path, meta)
        with open(meta_file, 'w') as f:
            f.write(value)

    def _upload(self, data, trace_id):
        url = self.fqdn + '/api/v2/asset_log/tpc/splunk'
        headers = {
            "Authorization": "Bearer " + self.token,
            "Content-Encoding": "gzip"
        }

        payload = gzip.compress(json.dumps(data).encode('utf-8'))
        # files = {'file': (trace_id + '.gz', payload, 'gzip')}

        try:
            r = requests.post(url, data=payload, headers=headers, proxies=self.proxies,
                              timeout=LogUploader.DEFAULT_TIME_OUT)
            if r.status_code == 200:
                return LogUploader.RET_SUCCSS
            elif r.status_code == 401:
                return LogUploader.RET_INVLIAD_TOKEN
            else:
                logger.error("upload error: status_code:{}".format(r.status_code))
                return LogUploader.RET_UNKNOWN
        except Exception:
            return LogUploader.RET_NETWORK_ISSUE

    def check_token(self):
        url = self.fqdn + '/api/v2/validate_token/tpc'
        headers = {"Authorization": "Bearer " + self.token}
        data = {}
        # {"user_name":"","email_address":"", "vendor_name":""}
        if self.custom_data:
            data = self.custom_data
        try:
            r = requests.post(url, headers=headers, proxies=self.proxies, data=data,
                              timeout=LogUploader.DEFAULT_TIME_OUT)
            if r.status_code == 200:
                return LogUploader.RET_SUCCSS
            elif r.status_code == 401:
                return LogUploader.RET_INVLIAD_TOKEN
            else:
                logger.error("check v1 tk: status_code:{}".format(r.status_code))
                return LogUploader.RET_UNKNOWN
        except Exception:
            return LogUploader.RET_NETWORK_ISSUE

    def _remove_log_file(self, log, meta):
        log_file = os.path.join(self.log_path, log)
        if os.path.exists(log_file):
            os.remove(log_file)
        meta_file = os.path.join(self.log_path, meta)
        if os.path.exists(meta_file):
            os.remove(meta_file)

    def upload(self):
        upload_logs = self._get_log_files()
        for log, meta in upload_logs.items():
            meta_value = self._get_meta(meta)
            skip_lines = upload_lines = meta_value.get('upload_lines', 0)
            if not meta:
                meta = LogUploader._get_meta_name(log)

            num = 0
            data = []
            rc = LogUploader.RET_SUCCSS
            with open(os.path.join(self.log_path, log)) as f:
                try:
                    for _ in range(upload_lines):
                        next(f)
                except Exception:
                    logger.error("skip lines are larger than real lines, no need to upload.")

                for line in f:
                    data.append(json.loads(line))
                    num += 1
                    if num >= self.batch_size:
                        # upload
                        trace_id = '{}_{}'.format(log, meta_value['upload_lines'])
                        rc = self._upload(data, trace_id)
                        if rc != LogUploader.RET_SUCCSS:
                            # upload failed, stop
                            logger.error("upload failed.rc={}".format(rc))
                            break
                        skip_lines += self.batch_size
                        meta_value['upload_lines'] = skip_lines
                        meta_value['upload_time'] = int(time.time())
                        self._update_meta(meta, json.dumps(meta_value))
                        data = []
                        num = 0

            if rc == 0:
                if num > 0:
                    # upload
                    trace_id = '{}_{}'.format(log, meta_value['upload_lines'])
                    rc = self._upload(data, trace_id)
                    if rc != LogUploader.RET_SUCCSS:
                        logger.error("upload failed.rc={}".format(rc))
                        break

                # delete log and meta file
                self._remove_log_file(log, meta)


if __name__ == "__main__":
    pass
