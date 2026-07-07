import sys
import re
import common
from consts import *

def log_and_exit(helper, message, module_name):
    common.make_error_message(helper, message, module_name)
    sys.exit(0)

def _is_ip_allowlist_message(text):
    t = (text or "").lower()
    keys = ("whitelist", "allowlist", "ip not allowed", "ip address not authorized", "not whitelisted")
    return any(k in t for k in keys)

def _extract_ipv4(text):
    m = re.search(r"(?:\d{1,3}\.){3}\d{1,3}", text or "")
    return m.group(0) if m else None

def proxy_error_to_message(err):
    msg = str(err)
    if "407" in msg or "Proxy Authentication Required" in msg:
        return MSG_PROXY_407
    return MSG_PROXY_GENERIC

def http_error_to_message(http_err):
    resp = getattr(http_err, "response", None)
    status = getattr(resp, "status_code", None)

    try:
        body = (resp.text or "").strip()
    except Exception:
        body = ""

    if status == 429:
        retry_after = resp.headers.get("Retry-After") if resp else None
        hint = f" Retry-After={retry_after}s." if retry_after else ""
        return f"{MSG_RATE_LIMIT}{hint}"

    if status == 403:
        if _is_ip_allowlist_message(body):
            ip = _extract_ipv4(body)
            if ip:
                return f"IP Address Not Allowed: Your source IP address {ip} is not on your SpyCloud allowlist. Please contact your SpyCloud administrator to add this IP address to the allowlist, or check if your network configuration has changed."
            return MSG_FORBIDDEN_IP
        return MSG_FORBIDDEN_KEY

    if status == 407:
        return MSG_PROXY_407

    snippet = (body or "")[:200].replace("\n", " ")
    return f"{MSG_API_PREFIX} HTTP {status}. {snippet}"
