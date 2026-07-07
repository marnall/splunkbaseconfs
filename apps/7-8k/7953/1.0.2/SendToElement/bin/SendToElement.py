from __future__ import annotations
import contextlib, json, logging, os, ssl, sys, uuid
import urllib.parse as _uparse, urllib.request as _u
from urllib.error import HTTPError
from pathlib import Path
from typing import Any, Dict
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Optional requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

# Logging
LOGFILE = Path(os.environ.get("SPLUNK_HOME", "/opt/splunk")) / "var/log/splunk/sendtoelement.log"
LOGFILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOGFILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("SendToElement")

# Hierarchical config
def _get(cfg: Dict[str, str], key: str) -> str | None:
    prefixes = ["action.SendToElement.", "action.SendToElement.param.", "param.", ""]
    for pref in prefixes:
        val = cfg.get(pref + key)
        if val:
            return val
    return None

# ✅ Обновлённая функция _send_message с логированием небезопасных вызовов
def _send_message(api_url: str, body: dict, token: str, verify_ssl: bool) -> None:
    if not verify_ssl:
        log.warning("⚠️ SSL verification is disabled! This is insecure and should only be used in trusted environments.")
    if not api_url.lower().startswith("https://"):
        log.warning("⚠️ API URL is not HTTPS! This may expose sensitive data.")

    r = requests.put(
        api_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=10,
        verify=verify_ssl
    )
    if r.status_code == 403 and r.json().get("errcode") == "M_FORBIDDEN":
        join_url = api_url.split("/send/")[0].replace("/rooms/", "/join/")
        log.warning("Not in room, joining… %s", join_url)
        requests.post(join_url, headers={"Authorization": f"Bearer {token}"}, timeout=10, verify=verify_ssl).raise_for_status()
        r = requests.put(api_url, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }, json=body, timeout=10, verify=verify_ssl)
    r.raise_for_status()
    log.info("Matrix response: %s", r.json())

# Main sender
def send_alert_to_matrix(payload: Dict[str, Any]) -> None:
    cfg: Dict[str, str] = payload.get("configuration", {})
    result: Dict[str, Any] = payload.get("result", {})

    verify_str = _get(cfg, "verify_ssl") or "false"
    verify_ssl = verify_str.lower() not in {"false", "0", "no"}
    log.info(f"🔍 SSL verification enabled? {verify_ssl}")

    homeserver_url = _get(cfg, "homeserver_url")
    room_id = _get(cfg, "room_id")
    access_token = _get(cfg, "access_token")
    if room_id:
        room_id = room_id.strip()

    if not all([homeserver_url, room_id, access_token]):
        raise ValueError("access_token, homeserver_url and room_id are required")

    title = _get(cfg, "title") or "Splunk Alert"
    message_tpl = _get(cfg, "message") or "Alert triggered."
    severity = _get(cfg, "severity") or "info"
    include_link = (_get(cfg, "result_link") or "0").lower() in {"1", "true", "yes"}
    results_link = payload.get("results_link", "")

    for k, v in result.items():
        if isinstance(v, (str, int, float)):
            title = title.replace(f"$result.{k}$", str(v))
            message_tpl = message_tpl.replace(f"$result.{k}$", str(v))

    body = "\n".join([
        f"[{title}]",
        f"Severity: {severity}",
        f"Message: {message_tpl}",
        f"Link: {results_link}" if include_link and results_link else ""
    ])

    txn_id = str(uuid.uuid4())
    api_url = f"{homeserver_url}/_matrix/client/v3/rooms/{_uparse.quote(room_id, safe='')}/send/m.room.message/{txn_id}"
    log.info("POST → %s", api_url)
    log.debug("Message body: %s", body.replace("\n", " | "))

    try:
        if _HAS_REQUESTS:
            _send_message(api_url, {"msgtype": "m.text", "body": body}, access_token, verify_ssl)
        else:
            data = json.dumps({"msgtype": "m.text", "body": body}).encode()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            req = _u.Request(api_url, data=data, headers=headers, method="PUT")
            ctx = ssl.create_default_context()
            if not verify_ssl:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            try:
                with contextlib.closing(_u.urlopen(req, context=ctx, timeout=10)) as resp:
                    log.info("Matrix response code: %s", resp.status)
            except HTTPError as e:
                if e.code == 403:
                    join_url = api_url.split("/send/")[0].replace("/rooms/", "/join/")
                    log.warning("Not in room, joining… %s", join_url)
                    _u.urlopen(_u.Request(join_url, headers={"Authorization": f"Bearer {access_token}"}, method="POST"), context=ctx, timeout=10).close()
                    with contextlib.closing(_u.urlopen(req, context=ctx, timeout=10)) as resp2:
                        log.info("Matrix response code: %s", resp2.status)
                else:
                    raise
        print("✅ Alert sent to Matrix")
    except Exception as e:
        log.exception("SendToElement ERROR")
        print(f"❌ Error sending to Matrix: {e}", file=sys.stderr)
        sys.exit(2)

def main() -> None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
        send_alert_to_matrix(payload)
    except Exception as ex:
        log.exception("SendToElement ERROR")
        print(f"❌ {ex}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
