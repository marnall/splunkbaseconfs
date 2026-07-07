import configparser
import datetime
import enum
import io
import json
import os
import pathlib
import shutil
import time
import zipfile
from pathlib import Path
import requests
import typing as t

from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class ApiClient:
    class RequestType(str, enum.Enum):
        deployment = 'deployment'
        job = 'job'

    class JobStatus(str, enum.Enum):
        NotStarted = 'NotStarted'
        Pending = 'Pending'
        Started = 'Started'
        Failed = 'Failed'
        CompletedWithErrors = 'CompletedWithErrors'
        Success = 'Success'
        Canceled = 'Canceled'

    @property
    def endpoints(self):
        return {
            'deployment': '/api/signatures/deployments/',
            'hits': '/api/detection/events/client/analytic_hits/',
            'job': '/api/integrations/jobs/',
            'import': '/api/harbor/signatures/import/integrations/csv/',
            'import_status': '/api/harbor/signatures/import/integrations/{task_id}/',
        }

    def __init__(self, api_key: str, config_file='snapattack_api.conf'):
        self.config = configparser.RawConfigParser()
        self._read_default_local_override(config_file)
        self._read_default_local_override('app.conf')
        self._read_default_local_override('macros.conf')
        self.app_version = self.config.get('id', 'version')
        self.results_index = self.config.get('sa_results_summary_index', 'definition', fallback='snapattack_results')
        self.api_url = self.config.get('SETTINGS', 'URL').rstrip('/')
        if not self.api_url.lower().startswith('https'):
            raise ValueError('API access requires an HTTPS URL.')
        http_proxy = self.config.get('PROXY', 'HTTP_URL', fallback=None)
        https_proxy = self.config.get('PROXY', 'HTTPS_URL', fallback=None)
        self.proxy_settings = dict(http=http_proxy, https=https_proxy) if http_proxy or https_proxy else None
        self.api_key = api_key
        self.send_stats = self.config.getboolean('SETTINGS', 'SEND_STATS')
        self.send_log = self.config.getboolean('SETTINGS', 'SEND_LOG')

    def acknowledge_job(self, job_id: str):
        self.set_job_status(job_id, self.JobStatus.Started)

    def set_job_status(self, job_id: str, status: JobStatus, detail: str = None, item_status: t.List[dict] = None):
        url = f'{self.endpoints.get(self.RequestType.job)}status/{job_id}/'
        self._query_endpoint(
            'POST',
            url,
            json=dict(status=status, status_detail=detail, **(dict(item_status=item_status) if item_status else {})),
        )

    def set_deployment_status(self, deployment_id, error_message=None, **kwargs):
        url = f'{self.endpoints.get(self.RequestType.deployment)}{deployment_id}/'
        self._query_endpoint('POST', url, json=dict(success=not error_message, error_message=error_message, **kwargs))

    def fetch_requested_items(self, request_type: RequestType) -> t.Dict[str, t.Any]:
        results = self._query_endpoint('GET', self.endpoints.get(request_type)).json()
        # For deployments we key based on the guid+compilation, for jobs based on the job guid
        identity_func = lambda x: (
            f'{x.get("guid")}_{x.get("analytic_compilation_target_id", 0)}'
            if request_type == self.RequestType.deployment
            else x['guid']
        )
        return {identity_func(result): result for result in results}

    def submit_job_result(self, guid, payload, temp_file_path: pathlib.Path):
        payload = dict(payload=json.dumps(payload).encode('utf-8'))
        files = [self._package_directory(temp_file_path)] if temp_file_path else None
        result_url = f'{self.endpoints.get(self.RequestType.job)}{guid}/result/'
        self._query_endpoint('POST', result_url, data=payload, files=files if files else None)

    def upload_analytic_hits(self, results: t.Dict[str, t.List]):
        """Export results to json, compress and send to SnapAttack API"""
        if results:
            upload_file = self._package_results_file(results)
            response = self._query_endpoint('POST', self.endpoints.get('hits'), files=[upload_file]).json()
            status_url = f'{self.endpoints.get("hits")}status/{response.get("task_id")}/'
            status = self._query_endpoint('GET', status_url).json()
            while status['status'] not in ['SUCCESS', 'FAILED']:
                time.sleep(1)
                status = self._query_endpoint('GET', status_url).json()
            if status['status'] == 'FAILED':
                raise RuntimeError('Failed to upload analytic hits: ' + str(status['output']))

    def fetch_checkpoint(self):
        """Fetch the timestamp of the last analytic hit submitted to SnapAttack"""
        response = self._query_endpoint('GET', f"{self.endpoints.get('hits')}checkpoint/").json()
        return response['checkpoint']

    def import_native_detections(self, csv_file: io.BytesIO):
        csv_file.seek(0)
        f = ('file', csv_file)
        resp = self._query_endpoint('POST', self.endpoints.get('import'), files=[f]).json()
        task_id = resp.get('task_id')
        count = 0
        while count < 600:  # 10m is way longer than any import should take
            resp = self._query_endpoint('GET', self.endpoints.get('import_status').format(task_id=task_id)).json()
            if resp.get('status') in ('SUCCESS', 'FAILED'):
                return resp.get('output')
            time.sleep(1)
            count += 1
        raise TimeoutError(f'Unable to get success response from endpoint. Last status: {str(resp)}')

    def _query_endpoint(
        self, method: str, endpoint: str, data=None, json=None, timeout=10, **request_args
    ) -> requests.Response:
        headers = {'X-API-KEY': self.api_key, 'X-APP-VERSION': self.app_version}
        resp = requests.request(
            method,
            self.api_url + endpoint,  # HTTPS URL validated on line 46
            json=json,
            data=data,
            timeout=timeout,
            headers=headers,
            proxies=self.proxy_settings,
            **request_args,
        )
        resp.raise_for_status()
        return resp

    def _read_path(self, path_part: str, filename: str):
        full_path = Path(__file__).parent.parent / path_part / filename
        if os.path.exists(full_path.absolute()):
            self.config.read(full_path)

    def _read_default_local_override(self, config_file: str):
        self._read_path('default', config_file)
        self._read_path('local', config_file)

    def _package_results_file(self, results):
        export = json.dumps(dict(results=results))
        filename = f'{int(datetime.datetime.utcnow().timestamp())}_analytic.export'
        z_file = io.BytesIO()
        with zipfile.ZipFile(z_file, mode='w', compression=zipfile.ZIP_DEFLATED) as zip:
            zip.writestr(filename, export)
        z_file.seek(0)
        return ('file', z_file)

    def _package_directory(self, path: pathlib.Path):
        try:
            z_file = io.BytesIO()
            with zipfile.ZipFile(z_file, mode='w', compression=zipfile.ZIP_DEFLATED) as zip:
                for f in path.glob('*.export'):
                    zip.write(f, f.name)
            z_file.seek(0)
            return ('file', z_file)
        finally:
            shutil.rmtree(path)
