
import logging

from datetime import datetime

from requests import Session


def urljoin(*args):
    """
    Joins given arguments into an url. Trailing but not leading slashes are
    stripped for each argument.
    """
    return "/".join(map(lambda x: str(x).rstrip('/'), args))


class APISession(Session):

    def __init__(self, *args, **kwargs):
        """
        Creates a new CoreAPISession instance.
        """
        super().__init__(*args, **kwargs)

    def get_auth_payload(self, username, password):
        return {
            "username": username,
            "password": password
        }

    def init_bearer_auth(self, token):
        self.headers.update({
            'Authorization': 'Bearer {}'.format(token)
        })


class BaseAPI:
    def __init__(
        self,
        host,
        username,
        password,
        version="V1",
    ):
        self.host = host
        self.version = version
        self.session = APISession()
        self._username = username
        self._password = password
        self._token = self._get_bearer_token()

    @property
    def url(self):
        return urljoin(self.host, "rest", self.version)

    def _get_bearer_token(self):
        endpoint = "integration/admin/token"
        auth_payload = self.session.get_auth_payload(self._username, self._password)
        response = self._request(endpoint, "POST", data=auth_payload)
        response.raise_for_status()
        bearer_token = response.json()
        self.session.init_bearer_auth(bearer_token)

        return bearer_token

    def _request(
        self,
        endpoint,
        method,
        headers=None,
        data=None,
        payload=None,
        params=None
    ):
        full_url = urljoin(self.url, endpoint)
        response = self.session.request(
            method,
            full_url,
            headers=headers,
            json=data,
            data=payload,
            params=params
        )
        response.raise_for_status()

        if response.status_code >= 400:
            # handle_error_response(resp)
            raise IndexError

        return response

    def _paginated_request(
        self,
        endpoint,
        method,
        headers=None,
        files=None,
        data=None,
        params=None,
        auth=None,
        cookies=None,
        hooks=None,
        json=None,
        position=0,
        count=200
    ):
        page = 1
        total = 0
        counter = 0
        full_url = urljoin(self.url, endpoint)

        while True:
            logging.info(
                f'Sending HTTP Request url={full_url} page_count={page} total_count={total} counter={counter} position={position}'
            )
            paginated_params = {
                "searchCriteria[page_size]": count,
                "searchCriteria[current_page]": page
            }
            params.update(paginated_params)
            try:
                response = self.session.request(
                    method,
                    full_url,
                    headers=headers,
                    files=files,
                    data=data,
                    params=params,
                    auth=auth,
                    cookies=cookies,
                    hooks=hooks,
                    json=json
                )
                response_data = response.json()
                total = response_data.get('total_count', -1)
                counter += len(response_data['items'])
                yield response_data["items"]

                if counter >= total:
                    logging.info(
                        f'Pagination done url={full_url} page_count={page} total_count={total} counter={counter} position={position}'
                    )
                    break

                page +=1
            except Exception as http_error_exc:
                raise http_error_exc


class MagentoLogsAPIClient(BaseAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def list_log_files(self):
        endpoint = "monitoring/logFiles"
        response = self._request(endpoint, "GET")
        server_id = response.headers.get("X-Platform-Server", "unknown")

        if server_id != "unknown":
            server_ids = server_id.split(",")
            server_id = server_ids[0] if server_ids else server_id

        return (
            server_id,
            response.json()
        )

    def get_log_file(self, file_path, bytes_ranges):
        endpoint = "monitoring/log"
        response = self._request(
            endpoint,
            "GET",
            params={
                'filePath': file_path,
                'range': bytes_ranges,
            }
        )
        server_id = response.headers.get("X-Platform-Server", "unknown")

        if server_id != "unknown":
            server_ids = server_id.split(",")
            server_id = server_ids[0] if server_ids else server_id

        file_content = response.text

        return {
            "server": server_id,
            "content": file_content
        }

    def filter_log_files_by_date(self, log_files, threshold_datetime):
        filtered_log_files = []

        for log_file in log_files:
            log_file_modified_time_str = log_file.get("modified_time")
            log_file_modified_time_datetime = datetime.strptime(log_file_modified_time_str, '%Y/%m/%d %H:%M:%S')

            if not log_file_modified_time_datetime > threshold_datetime:
                continue

            filtered_log_files.append(log_file)

        return filtered_log_files


class MagentoOrdersAPIClient(BaseAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_created_orders_within_period(self, start_time, end_time):
        filters = {
            "searchCriteria[filter_groups][1][filters][0][field]": "created_at",
            "searchCriteria[filter_groups][1][filters][0][condition_type]": "from",
            "searchCriteria[filter_groups][1][filters][0][value]": start_time,
            "searchCriteria[filter_groups][2][filters][0][field]": "created_at",
            "searchCriteria[filter_groups][2][filters][0][condition_type]": "to",
            "searchCriteria[filter_groups][2][filters][0][value]": end_time,
        }
        return self._paginated_request("orders", "GET", params=filters)


    def get_updated_orders_within_period(self, start_time, end_time):
        filters = {
            "searchCriteria[filter_groups][1][filters][0][field]": "updated_at",
            "searchCriteria[filter_groups][1][filters][0][condition_type]": "from",
            "searchCriteria[filter_groups][1][filters][0][value]": start_time,
            "searchCriteria[filter_groups][2][filters][0][field]": "updated_at",
            "searchCriteria[filter_groups][2][filters][0][condition_type]": "to",
            "searchCriteria[filter_groups][2][filters][0][value]": end_time,
        }
        return self._paginated_request("orders", "GET", params=filters)


class MagentoJobsAPIClient(BaseAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_finished_jobs_within_period(self, start_time, end_time):
        filters = {
            "searchCriteria[filter_groups][0][filters][0][field]": "finished_at",
            "searchCriteria[filter_groups][0][filters][0][value]": start_time,
            "searchCriteria[filter_groups][0][filters][0][condition_type]": "gteq",
            "searchCriteria[filter_groups][1][filters][0][field]": "finished_at",
            "searchCriteria[filter_groups][1][filters][0][value]": end_time,
            "searchCriteria[filter_groups][1][filters][0][condition_type]": "lteq",
        }
        return self._paginated_request("monitoring/cronjobStatuses", "GET", params=filters)

    def get_executed_jobs_within_period(self, start_time, end_time):
        filters = {
            "searchCriteria[filter_groups][0][filters][0][field]": "executed_at",
            "searchCriteria[filter_groups][0][filters][0][value]": start_time,
            "searchCriteria[filter_groups][0][filters][0][condition_type]": "from",
            "searchCriteria[filter_groups][1][filters][0][field]": "executed_at",
            "searchCriteria[filter_groups][1][filters][0][value]": end_time,
            "searchCriteria[filter_groups][1][filters][0][condition_type]": "to",
        }
        return self._paginated_request("monitoring/cronjobStatuses", "GET", params=filters)
