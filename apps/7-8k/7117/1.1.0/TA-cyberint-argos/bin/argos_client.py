import http
import logging
import re
from typing import Any, Dict, List, Optional

import utils
from requests.cookies import RequestsCookieJar
from rest_client import InvalidResponse, RestClient


class CyberintClient(RestClient):
    """
    A client for interacting with the Cyberint API.

    Args:
        RestClient (class): The base class for REST API clients.

    Attributes:
        API_PREFIX (str): The API prefix endpoint for Cyberint alerts.
    """

    API_PREFIX = "alert/api/v1"

    @staticmethod
    def _normalize_instance_domain(raw_value: str, logger: logging.Logger) -> str:
        """Normalize the user-provided instance_domain value.

        Backward compatible behavior:
        - If value starts with http(s):// treat as full URL.
        - Else if value contains 'cyberint.io' (any case), prepend https:// if missing.
        - Else treat as legacy short tenant key and expand to https://{tenant}.cyberint.io
        - Lower-case legacy short tenant to avoid DNS case issues.
        - Avoid duplicating region later if user already provided it in URL.
        """
        raw = raw_value.strip()
        is_url = re.match(r"^(https?://)", raw, re.IGNORECASE) is not None
        contains_platform_domain = "cyberint.io" in raw.lower()

        if is_url:
            domain_clean = raw
            logger.debug(f"Instance domain recognized as full URL: {domain_clean}")
        elif contains_platform_domain:
            # Provided a domain like tenant.cyberint.io (without protocol)
            domain_clean = raw
            domain_clean = domain_clean.rstrip('/')
            domain_clean = f"https://{domain_clean}" if not domain_clean.lower().startswith(
                ("http://", "https://")) else domain_clean
            logger.info(f"Instance domain recognized as domain, protocol added if needed: {domain_clean}")
        else:
            # Legacy short tenant key
            tenant_key = raw.lower().strip('.')
            domain_clean = f"https://{tenant_key}.cyberint.io"
            logger.info(f"Legacy instance_domain '{raw}' expanded to full URL: {domain_clean}")

        return domain_clean

    def __init__(self, version: str, client_name: str, instance_domain: str, access_token: str, input_name: str, proxies: dict):
        """
        Initialize a new Cyberint client.

        Args:
            version (str): The application version.
            client_name (str): The client (company/customer) name.
            instance_domain (str): The domain of the Cyberint instance.
            access_token (str): The access token for authentication.
            input_name (str): The name of the application input.
        """
        logger = utils.logger_for_input(input_name)
        normalized_domain = self._normalize_instance_domain(instance_domain, logger)

        # Ensure single trailing slash
        base_url_root = normalized_domain.rstrip('/') + '/'

        cookies = RequestsCookieJar()
        cookies["access_token"] = access_token
        headers = {
            "X-Integration-Type": "Splunk",
            "X-Integration-Instance-Name": input_name,
            "X-Integration-Instance-Id": base_url_root,
            "X-Integration-Customer-Name": client_name,
            "X-Integration-Version": version,
        }
        utils.logger_for_input(input_name).info(f"HTTP Headers: {headers}")
        super().__init__(f"{base_url_root}{self.API_PREFIX}", cookies=cookies, headers=headers, proxies=proxies, timeout=10)

    def list_alerts(
        self,
        page: int,
        page_size: int,
        include_csv: Optional[bool] = False,
        created_date: Optional[str] = None,
        update_date: Optional[str] = None,
        environments: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        severities: Optional[List[str]] = None,
        types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List Argos alerts based on specified criteria.

        Args:
            page (int): The page number for pagination.
            page_size (int): The number of items per page.
            include_csv_attachments_as_json_content (Optional[bool], optional):
                Flag to include CSV attachments as JSON content. Defaults to False.
            created_date (Optional[str], optional):
                The start date for filtering alerts based on their creation date. Defaults to None.
            modification_date (Optional[str], optional):
                The start date for filtering alerts based on their modification date. Defaults to None.
            environments (Optional[List[str]], optional):
                A string or list of environments to filter alerts by. Defaults to None.
            statuses (Optional[List[str]], optional):
                A list of statuses to filter alerts by. Defaults to None.
            severities (Optional[List[str]], optional):
                A list of severities to filter alerts by. Defaults to None.
            types (Optional[List[str]], optional):
                A list of alert types to filter alerts by. Defaults to None.

            Returns:
                List[Dict[str, Any]]: API response from Argos API.
        """
        created_date_to = utils.get_current_date() if created_date else None
        update_date_to = utils.get_current_date() if update_date else None

        body = utils.remove_empty_elements(
            {
                "page": page,
                "size": page_size,
                "include_csv_attachments_as_json_content": include_csv,
                "filters": {
                    "created_date": {"from": created_date, "to": created_date_to},
                    "update_date": {"from": update_date, "to": update_date_to},
                    "environments": environments,
                    "status": statuses,
                    "severity": severities,
                    "type": types,
                },
            }
        )

        return self.post("alerts", json=body)

    def update_alerts_status(
        self,
        alert_ref_ids: List[str],
        status: str,
        closure_reason: Optional[str] = None,
        closure_reason_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update the status of one or more Cyberint Argos alerts.

        Args:
            alert_ref_ids: List of alert reference IDs to update.
            status: New status ('open', 'acknowledged', or 'closed').
            closure_reason: Required when status is 'closed'.
            closure_reason_description: Optional free-text description.

        Returns:
            Dict[str, Any]: API response.
        """
        body = {
            "alert_ref_ids": alert_ref_ids,
            "data": utils.remove_empty_elements(
                {
                    "status": status,
                    "closure_reason": closure_reason,
                    "closure_reason_description": closure_reason_description,
                }
            ),
        }
        return self.put("alerts/status", json=body)


def get_data_from_api(
    logger: logging.Logger, version: str, api_key: str, input_data: dict, input_name: str, last_run: str, proxies: dict
):
    logger.info("Initiating data retrieval from API...")

    try:
        client = CyberintClient(
            version,
            client_name=input_data["client_name"],
            instance_domain=input_data["instance_domain"],
            access_token=api_key,
            input_name=input_name,
            proxies=proxies
        )
        logger.info("API client successfully created.")
        logger.debug(f"Input data provided: {input_data}")
        alerts = []
        page = 1
        total = None
        while total is None or len(alerts) < total:
            logger.info("Fetching alerts from API...")
            data = client.list_alerts(
                page=page,
                page_size=input_data["max_fetch"],
                include_csv=utils.string_to_bool(input_data.get("include_csv")),
                environments=utils.string_to_list(input_data.get("environment")),
                update_date=last_run,
                statuses=utils.string_to_list(input_data.get("statuses")),
                severities=utils.string_to_list(input_data.get("severities")),
                types=utils.string_to_list(input_data.get("types")),
            )
            total = data["total"]
            alerts += data["alerts"]
            page += 1

        logger.info(f"Total alerts to fetch: {total}. Successfully fetched: {len(alerts)} alerts.")
        return alerts

    except InvalidResponse as err:
        # Log the full error for debugging purposes
        decoded_error = str(err)
        logger.warning(f"API Client Error: {err}")
        # Handle specific HTTP status codes
        if err.response.status_code == http.HTTPStatus.UNAUTHORIZED:
            raise ValueError("Unauthorized: Please check your API key and permissions.")
        elif err.response.status_code == http.HTTPStatus.FORBIDDEN:
            raise ValueError("Forbidden: You do not have permission to perform this action.")
        elif err.response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY:
            raise ValueError("Unprocessable Entity: Please check your input values.")
        elif err.response.status_code == http.HTTPStatus.CONFLICT:
            raise ValueError("Conflict: The requested resource already exists.")
        elif err.response.status_code == http.HTTPStatus.BAD_REQUEST:
            if "environment" in decoded_error:
                env = utils.extract_environment_value(decoded_error)
                raise ValueError(
                    f"Bad Request: The environment {env} is unrecognized. "
                    "Please verify your input or consult the documentation."
                )
            else:
                raise ValueError(f"Invalid response: {err}")
        else:
            # Handle unexpected errors.
            logger.error(f"Unexpected error: {str(err)}")
            raise ValueError(
                f"An unexpected error occurred during validation of input parameters for Cyberint data input, \
                    Detailed error: {str(err)}"
            )
    except Exception as err:
        # Handle unexpected errors.
        logger.error(f"Unexpected error: {str(err)}")
        raise ValueError(
            f"An unexpected error occurred during validation of input parameters for Cyberint data input, \
                Detailed error: {str(err)}"
        )
