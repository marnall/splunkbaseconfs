import logging

from time import sleep
from base64 import b64encode
from zlib import decompressobj, MAX_WBITS
from dataclasses import dataclass
from tempfile import NamedTemporaryFile
from json.decoder import JSONDecodeError

from utils import urljoin

from requests import Session
from requests.exceptions import (
    HTTPError,
    RetryError,
    ReadTimeout,
)


@dataclass
class APIOAuthClientOrServerError(Exception):
    """
    API Auth client or server error occurred.

    HTTP Client errors status codes: 4xx
    HTTP Server errors status codes: 5xx
    """

    http_status_code: int
    exc_msg: str

    def __post_init__(self):
        super().__init__(self.exc_msg)


class APIOAuthError(Exception):
    """API Auth error occurred."""


@dataclass
class APIClientOrServerError(Exception):
    """
    API client or server error occurred.

    HTTP Client errors status codes: 4xx
    HTTP Server errors status codes: 5xx
    """

    http_status_code: int
    http_response_body: str
    exc_msg: str

    def __post_init__(self):
        super().__init__(self.exc_msg)


@dataclass
class APIResponseBodyDecodeError(Exception):
    """Couldn't decode the text into JSON"""

    http_status_code: int
    http_response_body: str
    exc_msg: str

    def __post_init__(self):
        super().__init__(self.exc_msg)


@dataclass
class APIRetryError(Exception):
    """Custom retries logic failed"""

    http_status_code: int
    http_response_body: str
    exc_msg: str

    def __post_init__(self):
        super().__init__(self.exc_msg)


@dataclass
class APIReadTimeoutError(Exception):
    """Server is taking longer to respond and send information"""

    http_status_code: int
    http_response_body: str
    exc_msg: str

    def __post_init__(self):
        super().__init__(self.exc_msg)


@dataclass
class APIError(Exception):
    """API error occurred."""

    child_exc: Exception

    def __post_init__(self):
        super().__init__(self.child_exc.exc_msg)


class APISession(Session):
    def __init__(self, *args, **kwargs):
        """
        Creates a new CoreAPISession instance.
        """
        super().__init__(*args, **kwargs)

    def init_bearer_auth(self, token):
        self.headers.update({"Authorization": "Bearer {}".format(token)})

    def update_http_headers(self, http_headers):
        self.headers.update(http_headers)

    def remove_http_headers(self, http_headers_keys):
        for http_header in http_headers_keys:
            self.headers.pop(http_header, None)


class SalesforceAPI:
    auth_url = "https://account.demandware.com/dw/oauth2/access_token"

    def __init__(self, host, endpoint, client_id, client_secret):
        self.host = host
        self.endpoint = endpoint
        self.session = APISession()
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = self._get_access_token()

    @property
    def url(self):
        return urljoin(self.host, self.endpoint)

    def _get_access_token(self):
        credentials = self._client_id + ":" + self._client_secret
        basic_auth = b64encode(credentials.encode("utf-8")).decode("utf-8")
        response = self._request(
            self.auth_url,
            "POST",
            params={"grant_type": "client_credentials"},
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Basic " + basic_auth,
                "Accept": "*/*",
            },
        )
        access_token = response.json()
        bearer_token = access_token["access_token"]
        self.session.init_bearer_auth(bearer_token)

        return access_token

    def _update_session_http_headers(self, http_headers):
        self.session.update_http_headers(http_headers)

    def _remove_session_http_headers(self, http_headers_keys):
        self.session.remove_http_headers(http_headers_keys)

    def _request(self, url, method, headers=None, data=None, params=None, stream=False):
        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                json=data,
                params=params,
                stream=stream,
                timeout=120,  # 2 minutes for bulk operations and larger file downloads
            )
            response.raise_for_status()

            return response
        except HTTPError as http_error_exc:
            raise APIClientOrServerError(
                http_status_code=response.status_code,
                http_response_body=response.text,
                exc_msg=str(http_error_exc),
            )
        except JSONDecodeError as json_decode_exc:
            raise APIResponseBodyDecodeError(
                http_status_code=response.status_code,
                http_response_body=response.text,
                exc_msg=str(json_decode_exc),
            )
        except ReadTimeout as read_timeout_exc:
            raise APIReadTimeoutError(
                http_status_code=408,
                http_response_body="408 Request Timeout. Failed to process request in time.",
                exc_msg=str(read_timeout_exc),
            )
        except RetryError as retry_error_exc:
            raise APIRetryError(
                http_status_code=response.status_code,
                http_response_body=response.text,
                exc_msg=str(retry_error_exc),
            )


class SalesforceOrderAPIClient(SalesforceAPI):
    auth_uri = "https://account.demandware.com/dw/oauth2/access_token"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __build_created_orders_query(self, date_from, date_to, fields):
        return {
            "query": {
                "filtered_query": {
                    "filter": {
                        "range_filter": {
                            "field": "creation_date",
                            "from_inclusive": False,
                            "from": date_from,
                            "to": date_to,
                            "to_inclusive": True,
                        }
                    },
                    "query": {"match_all_query": {}},
                }
            },
            "sorts": [{"field": "creation_date", "sort_order": "asc"}],
            "select": fields,
        }

    def __build_updated_orders_query(self, date_from, date_to, fields):
        return {
            "query": {
                "filtered_query": {
                    "filter": {
                        "range_filter": {
                            "field": "last_modified",
                            "from_inclusive": False,
                            "from": date_from,
                            "to": date_to,
                            "to_inclusive": True,
                        }
                    },
                    "query": {"match_all_query": {}},
                }
            },
            "sorts": [{"field": "last_modified", "sort_order": "asc"}],
            "select": fields,
        }

    def set_permanent_http_headers(self, http_headers):
        self._update_session_http_headers(http_headers)

    def get_created_orders_total_count_within_period(
        self, date_from, date_to, fields="(*)"
    ):
        body = self.__build_created_orders_query(date_from, date_to, fields)
        response = self._request(self.url, "POST", data=body)
        response_data = response.json()
        total = response_data.get("total", 0)

        return total

    def get_created_orders_within_period(
        self, date_from, date_to, fields="(*)", start=0, count=200
    ):
        body = self.__build_created_orders_query(date_from, date_to, fields)
        body["start"] = start
        body["count"] = count
        logging.info(
            f"Sending HTTP Request url={self.url} method=POST data_type=created_orders position={start} limit={count}"
        )

        return self._request(self.url, "POST", data=body)

    def get_updated_orders_total_count_within_period(
        self, date_from, date_to, fields="(*)"
    ):
        body = self.__build_updated_orders_query(date_from, date_to, fields)
        response = self._request(self.url, "POST", data=body)
        response_data = response.json()
        total = response_data.get("total", 0)

        return total

    def get_updated_orders_within_period(
        self, date_from, date_to, fields="(*)", start=0, count=200
    ):
        body = self.__build_updated_orders_query(date_from, date_to, fields)
        body["start"] = start
        body["count"] = count
        logging.info(
            f"Sending HTTP Request url={self.url} method=POST data_type=updated_orders position={start} limit={count}"
        )

        return self._request(self.url, "POST", data=body)


class SalesforceLogAPIClient(SalesforceAPI):
    auth_uri = "https://account.demandware.com/dw/oauth2/access_token"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def set_permanent_http_headers(self, http_headers):
        self._update_session_http_headers(http_headers)

    def list_webdav_files(self):
        response = self._request(self.url, "PROPFIND")

        return response

    def get_file_content(self, file_name, file_byte_start_range, file_byte_end_range):
        bytes_range = f"{file_byte_start_range}-{file_byte_end_range}"
        headers = {"Range": f"bytes={bytes_range}"}
        full_url_including_file_name = f"{self.url}/{file_name}"
        logging.info(
            f"Sending HTTP Request url={full_url_including_file_name} method=GET bytes_range={bytes_range}"
        )
        response = self._request(full_url_including_file_name, "GET", headers=headers)

        return response


class SalesforceECDNAPIClient(SalesforceAPI):
    auth_uri = "https://account.demandware.com/dw/oauth2/access_token"

    def __init__(self, *args, download_dir_path="."):
        self.dowload_dir_path = download_dir_path

        super().__init__(*args)

    def __build_log_file_fetching_query(self, date_from, date_to, zone_name):
        return {"start_time": date_from, "end_time": date_to, "zone_name": zone_name}

    def set_permanent_http_headers(self, http_headers):
        self._update_session_http_headers(http_headers)

    def drop_auth_http_header(self):
        self._remove_session_http_headers(["Authorization"])

    def request_log_file_for_download(self, zone_name, date_from, date_to):
        try:
            body = self.__build_log_file_fetching_query(date_from, date_to, zone_name)
            logging.info(
                f"Sending HTTP Request url={zone_name} method=POST date_from={date_from} date_to={date_to}"
            )
            response = self._request(self.url, "POST", data=body)
            response_data = response.json()

            return response_data["id"]
        except JSONDecodeError as json_decode_exc:
            raise APIResponseBodyDecodeError(
                http_status_code=response.status_code,
                http_response_body=response.text,
                exc_msg=f"{str(json_decode_exc)} url={self.url}",
            )

    def get_log_file_download_link(
        self, log_file_id, base_delay=4, backoff=2, max_retries=6
    ):
        try:
            response_data = None
            url = urljoin(self.url, log_file_id)

            for retry in range(1, max_retries + 1):
                delay = base_delay * (backoff**retry)
                logging.info(f"Sending HTTP Request url={url} attempt={retry}")
                response = self._request(url, "GET")
                response_data = response.json()

                if "link" in response_data and response_data["status"] == "finished":
                    break

                sleep(delay)

            link = response_data["link"]

            return link
        except (JSONDecodeError, KeyError) as body_data_exc:
            raise APIResponseBodyDecodeError(
                http_status_code=response.status_code,
                http_response_body=response.text,
                exc_msg=f"{str(body_data_exc)} url={url}",
            )

    def download_log_file(self, link):
        self.drop_auth_http_header()
        response = self._request(link, "GET", stream=True)
        gzip_decompressor = decompressobj(16 + MAX_WBITS)

        with NamedTemporaryFile(
            mode="r+", dir=self.dowload_dir_path, prefix="file", suffix=".log"
        ) as tmp_file:
            for chunk in response.iter_content(chunk_size=10 * 1024):
                chunk_decompressed = gzip_decompressor.decompress(chunk)
                chunk_str = chunk_decompressed.decode("utf-8")
                tmp_file.write(chunk_str)

            tmp_file.flush()
            tmp_file.seek(0)

            while True:
                line = tmp_file.readline()

                if not line:
                    break

                yield line

        return None
