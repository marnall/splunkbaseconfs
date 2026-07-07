import datetime
from typing import Any, Dict, List, Optional

from requests.cookies import RequestsCookieJar

from rest_client import RestClient
from utils import remove_empty_elements, validate_url


class CyberintClient(RestClient):
    ALERTS_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
    API_PREFIX = 'alert/api/v1'

    def __init__(self, base_url: str, access_token: str):
        validate_url(base_url)

        cookies = RequestsCookieJar()
        cookies['access_token'] = access_token
        super().__init__(f'{base_url}/{self.API_PREFIX}', cookies=cookies)

    def list_alerts(
        self,
        page: int,
        page_size: int,
        created_date: Optional[str] = None,
        modification_date: Optional[str] = None,
        environments: Optional[str] = None,
        statuses: Optional[List[str]] = None,
        severities: Optional[List[str]] = None,
        types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        created_date_to = self._current_date() if created_date else None
        modification_date_to = self._current_date() if modification_date else None

        body = {
            'page': page,
            'size': page_size,
            'filters': {
                'created_date': {
                    'from': created_date,
                    'to': created_date_to
                },
                'modification_date': {
                    'from': modification_date,
                    'to': modification_date_to
                },
                'environments': environments,
                'status': statuses,
                'severity': severities,
                'type': types,
            },
        }

        return self.post('alerts', json=body)['alerts']

    def get_alert_attachment_url(self, alert_id: int, attachment_id: int) -> str:
        return f'{self.base_url}/alerts/{alert_id}/attachments/{attachment_id}'

    def get_alert_report_url(self, alert_id: int) -> str:
        return f'{self.base_url}/alerts/{alert_id}/analysis_report'

    def _request(self, method: str, path: str, resp_type: str = 'json', **kwargs):
        return super()._request(method, path, resp_type, **remove_empty_elements(kwargs))

    def _current_date(self):
        return datetime.datetime.strftime(datetime.datetime.now(), self.ALERTS_DATE_FORMAT)
