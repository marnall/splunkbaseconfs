import base64
import json
from typing import Dict, List, Optional, Union

from enums import KvStoreRecordsPagination, KvStorePaginatedRecords

MASK_LENGTH = 12


def mask_credentials(data: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Masks sensitive credentials in the provided data.

    Args:
        data (List[Dict[str, str]]): List of dictionaries containing settings data.

    Returns:
        List[Dict[str, str]]: The modified list with sensitive credentials masked.
    """
    for obj in data:
        for key in ("token", "apiKey", "apiSecret"):
            if key in obj:
                obj[key] = "*" * MASK_LENGTH
    return data


def decode_jwt_payload(token: str) -> Dict[str, str]:
    """
    This function decodes the JWT token and returns the payload as a dictionary.

    Args:
        token (str): JWT token string.

    Returns:
        Dict[str, str]: Decoded payload of the JWT token.

    Raises:
        ValueError: If the token is empty.
    """
    if not (token or isinstance(token, str)):
        raise ValueError("Token must not be empty and must be a string.")
    payload = token.split(".")[1]
    payload = f"{payload}{'=' * ((4 - len(payload) % 4) % 4)}"
    decoded_payload = base64.b64decode(payload).decode()
    decoded_payload = json.loads(decoded_payload)
    return decoded_payload


def get_org_id_from_token(token: str) -> str:
    """
    Extracts the organization ID from the JWT token.

    Args:
        token (str): JWT token string.

    Returns:
        str: Extracted organization ID.
    """
    sub: str = decode_jwt_payload(token).get("sub", "")
    if (sub_list := sub.split("/")) and len(sub_list) > 1:
        return sub_list[1]
    return ""


def get_kvstore_pagination_params(params: Dict[str, str]) -> KvStoreRecordsPagination:
    """
    Extracts pagination parameters from the provided dictionary.

    Args:
        params (Dict[str, str]): Dictionary containing pagination parameters.

    Returns:
        KvStorePagination: An object containing pagination parameters.
    """
    page_size = params.get("page_size", 10)
    page_number = params.get("page_number", 1)
    sort_field = params.get("sort_field", "_key")
    sort_direction = params.get("sort_direction", -1)

    pagination = KvStoreRecordsPagination(
        limit=int(page_size),
        skip=(int(page_number) - 1) * int(page_size),
        sort_by=sort_field,
        sort_direction=int(sort_direction),
    )
    return pagination


def paginate_kvstore_records(
    records: List[Dict[str, str]], skip: int, limit: int
) -> KvStorePaginatedRecords:
    """
    Paginate the records based on skip and limit.

    Args:
        records (List[Dict[str, str]]): The list of records to paginate.
        skip (int): The number of records to skip.
        limit (int): The maximum number of records to return.

    Returns:
        KvStorePaginatedRecords: The paginated list of records.
    """
    if not records:
        return KvStorePaginatedRecords(total_records=0, records=[])

    total_records = len(records)

    if skip < 0:
        skip = 0

    if limit <= 0:
        limit = total_records

    if skip >= total_records:
        return KvStorePaginatedRecords(total_records=total_records, records=[])

    paginated_data = records[skip : skip + limit]

    return KvStorePaginatedRecords(total_records=total_records, records=paginated_data)

def format_response_for_data_table(
    paginated_records: KvStorePaginatedRecords,
    draw: Optional[int] = 1,
) -> Dict[str, object]:
    """
    Formats the paginated records into a response structure suitable for data tables.

    Args:
        paginated_records (KvStorePaginatedRecords): The paginated records.
        draw (Optional[int]): The draw counter for data tables. Defaults to 1.
    
    Returns:
        Dict[str, object]: Formatted response containing total records and the records list.
    """
    response = {
        "data": paginated_records.records,
        "recordsTotal": paginated_records.total_records,
        "recordsFiltered": paginated_records.total_records,
        "draw": draw,
    }
    return response


def send_splunk_notification(
    session_token: str, name: str, message: str, severity: str = "warn"
) -> None:
    """Send a notification message to Splunk UI.
    
    Args:
        session_token: Splunk session authentication token.
        name: Unique identifier for the notification message.
        message: The notification message content.
        severity: Notification severity - 'error', 'warn', or 'info'.
    """
    import splunk.rest

    endpoint = "/services/messages"
    post_args = {
        "name": name,
        "severity": severity,
        "value": message,
    }

    splunk.rest.simpleRequest(
        endpoint,
        method="POST",
        sessionKey=session_token,
        raiseAllErrors=False,
        postargs=post_args,
    )


def str_to_boolean(value: Union[str, bool, int, None]) -> bool:
    """
    Converts Splunk string boolean representations to Python boolean values.

    Args:
        value: The value to convert. Can be boolean, string, or numeric.

    Returns:
        bool: True if value is considered true, False otherwise.
    """
    if value is None:
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        # Normalize the string value to uppercase for comparison
        value = value.upper()
        if value in ("TRUE", "T", "Y", "YES", "1"):
            return True
        elif value in ("FALSE", "F", "N", "NO", "NONE", "0", ""):
            return False
