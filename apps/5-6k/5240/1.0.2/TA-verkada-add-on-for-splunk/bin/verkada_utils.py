import requests
import logging

logger = logging.getLogger(__name__)

def get_notifications(helper,
                      org_id: str,
                      api_key: str,
                      start_time: int,
                      end_time: int) -> list:
    """
    Gets all notifications for the past minute and returns them as a list
    Args:
        org_id: Organization ID
        api_key: API Key of the organization
        notification_types: Types of notifications to look for

    Returns:
        List of dictionaries where each entry is a notification
    """
    proxies = get_proxy(helper, "requests")
    resp = requests.get(
        f"https://api.verkada.com/orgs/{org_id}/notifications?include_image_url=false",
        headers={"x-api-key": api_key},
        params={
            "start_time": start_time,
            "end_time": end_time,
            "per_page": 200,
        },
        proxies = proxies,
    )
    resp.raise_for_status()
    notifications: list = resp.json()["notifications"]
    pager_cursor = resp.json()["page_cursor"]
    while pager_cursor:
        sub_resp = requests.get(
            f"https://api.verkada.com/orgs/{org_id}/notifications?include_image_url=false",
            headers={"x-api-key": api_key},
            params={
                "start_time": start_time,
                "end_time": end_time,
                "per_page": 200,
                "page_cursor": pager_cursor,
            },
            proxies=proxies,
        )
        sub_resp.raise_for_status()
        notifications.extend(sub_resp.json()["notifications"])
        pager_cursor = sub_resp.json()["page_cursor"]
    return notifications

def get_cameras(helper, org_id: str, api_key: str) -> dict:
    """
    Gets all cameras for an organization
    Args:
        org_id: Organization ID
        api_key: API Key of the organization
    Returns:
        Dictionary that contains every camera. Mapped with camera ID
    """
    proxies = get_proxy(helper, "requests")
    resp = requests.get(
        f"https://api.verkada.com/orgs/{org_id}/cameras",
        headers={"x-api-key": api_key},
        proxies=proxies
    )
    resp.raise_for_status()
    cameras = resp.json()["cameras"]
    return cameras

def get_object_counts(helper,
                      org_id: str,
                      api_key: str,
                      camera_id: str,
                      start_time: int,
                      end_time: int) -> list:
    """
    Gets all notifications for the past minute and returns them as a list
    Args:
        org_id: Organization ID
        api_key: API Key of the organization
        camera_id: Id of the camera
        start_time: Start of time range
        end_time: End of time range

    Returns:
        List of dictionaries where each entry is a object_count
    """
    proxies = get_proxy(helper, "requests")
    resp = requests.get(
        f"https://api.verkada.com/orgs/{org_id}/cameras/{camera_id}/objects/counts",
        headers={"x-api-key": api_key},
        params={
            "start_time": start_time,
            "end_time": end_time,
            "per_page": 200,
        },
        proxies = proxies,
    )
    resp.raise_for_status()
    object_counts: list = resp.json()["object_counts"]
    pager_cursor = resp.json()["page_cursor"]
    while pager_cursor:
        sub_resp = requests.get(
            f"https://api.verkada.com/orgs/{org_id}/cameras/{camera_id}/objects/counts",
            headers={"x-api-key": api_key},
            params={
                "start_time": start_time,
                "end_time": end_time,
                "per_page": 200,
                "page_cursor": pager_cursor,
            },
            proxies=proxies,
        )
        sub_resp.raise_for_status()
        object_counts.extend(sub_resp.json()["object_counts"])
        pager_cursor = sub_resp.json()["page_cursor"]
    return object_counts


def get_proxy(helper, proxy_type="requests"):
    proxies = None
    helper.log_debug("_Splunk_ Getting proxy server.")
    proxy = helper.get_proxy()

    if proxy:
        helper.log_debug("_Splunk_ Proxy is enabled: %s:%s" % (proxy["proxy_url"], proxy["proxy_port"]))
        if proxy_type.lower() == "requests":
            proxy_url = "%s:%s" % (proxy["proxy_url"], proxy["proxy_port"])
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
        elif proxy_type.lower() == "event hub":
            proxies = {
                'proxy_hostname': proxy["proxy_url"],
                'proxy_port': int(proxy["proxy_port"]),
                'username': proxy["proxy_username"],
                'password': proxy["proxy_password"]
            }

    return proxies