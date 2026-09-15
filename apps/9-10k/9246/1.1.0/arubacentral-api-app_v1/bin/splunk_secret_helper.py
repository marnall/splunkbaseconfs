import os
import urllib.parse
import xml.etree.ElementTree as ET
import requests

APP = "arubacentral-api-app_v1"
REALM = "arubacentral"

def splunkd_uri():
    return os.environ.get("SPLUNKD_URI", "https://127.0.0.1:8089")

def auth_headers(session_key):
    return {"Authorization": f"Splunk {session_key}"}

def list_storage_passwords(session_key):
    url = f"{splunkd_uri()}/servicesNS/nobody/{APP}/storage/passwords"
    r = requests.get(url, headers=auth_headers(session_key), verify=False, timeout=30)
    r.raise_for_status()
    return r.text

def get_secret(session_key, username, realm=REALM):
    xml_text = list_storage_passwords(session_key)
    root = ET.fromstring(xml_text)
    ns = {"a": "http://www.w3.org/2005/Atom", "s": "http://dev.splunk.com/ns/rest"}

    for entry in root.findall("a:entry", ns):
        title = entry.find("a:title", ns)
        if title is None or title.text != f"{realm}:{username}:":
            continue
        content = entry.find("a:content", ns)
        if content is None:
            continue
        dict_node = content.find("s:dict", ns)
        if dict_node is None:
            continue
        for key in dict_node.findall("s:key", ns):
            if key.attrib.get("name") == "clear_password":
                return key.text
    return None

def set_secret(session_key, username, password, realm=REALM):
    list_url = f"{splunkd_uri()}/servicesNS/nobody/{APP}/storage/passwords"
    existing = get_secret(session_key, username, realm)

    if existing is None:
        r = requests.post(
            list_url,
            headers=auth_headers(session_key),
            data={"name": username, "password": password, "realm": realm},
            verify=False,
            timeout=30
        )
        r.raise_for_status()
        return

    encoded = urllib.parse.quote(f"{realm}:{username}:", safe="")
    item_url = f"{list_url}/{encoded}"
    r = requests.post(
        item_url,
        headers=auth_headers(session_key),
        data={"password": password},
        verify=False,
        timeout=30
    )
    r.raise_for_status()