#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import json
import ssl
import time
import re
import base64
import random
import datetime
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any

from splunklib.modularinput import Script, Scheme, Argument, Event, EventWriter

APP_NAME = "resecurity"
CRED_REALM = f"{APP_NAME}_global"


def _log(ew: Optional[EventWriter], level: str, msg: str):
    try:
        if ew:
            ew.log(getattr(EventWriter, level.upper(), EventWriter.INFO), msg)
        else:
            sys.stderr.write(f"{level} {msg}\n")
            sys.stderr.flush()
    except Exception:
        sys.stderr.write(f"{level} {msg}\n")
        sys.stderr.flush()


def _now_utc() -> datetime.datetime:
    # second precision without microseconds
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc, microsecond=0)


def _now_iso() -> str:
    dt = _now_utc()
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + ".0Z"


def _dt_to_iso(dt: datetime.datetime) -> str:
    dt = dt.astimezone(datetime.timezone.utc).replace(microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + ".0Z"


def _iso_to_dt(s: str) -> Optional[datetime.datetime]:
    """
    Robust conversion of ISO8601 to datetime (UTC).
    Supports:
      - 2025-09-17T11:19:05Z
      - 2025-09-17T11:19:05.0Z
      - 2025-09-17T11:19:05.000Z
      - 2025-09-17T11:19:05+00:00
      - 2025-09-17T11:19:05.0+00:00
    """
    if not s:
        return None
    try:
        ss = s.strip()
        # Fast Z variants
        if ss.endswith("Z"):
            # With/without second parts
            try:
                return datetime.datetime.strptime(ss, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
            except Exception:
                pass
            try:
                # Support for .fZ (any fractional part length)
                m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d+)Z$", ss)
                if m:
                    base = m.group(1)
                    frac = (m.group(2) + "000000")[:6]  # normalize to microseconds
                    dt = datetime.datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
                    dt = dt.replace(microsecond=int(frac), tzinfo=datetime.timezone.utc)
                    return dt
            except Exception:
                pass
            # Universal fallback: replace Z with +00:00
            ss = ss[:-1] + "+00:00"

        # fromisoformat with timizone
        try:
            dt = datetime.datetime.fromisoformat(ss)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc).replace(microsecond=0)
        except Exception:
            pass

        try:
            dt = datetime.datetime.strptime(ss, "%Y-%m-%dT%H:%M:%S")
            return dt.replace(tzinfo=datetime.timezone.utc)
        except Exception:
            return None
    except Exception:
        return None


def _join_url(base: str, part: str) -> str:
    if not base:
        return part.lstrip("/")
    if base.endswith("/") and part.startswith("/"):
        return base[:-1] + part
    if not base.endswith("/") and not part.startswith("/"):
        return base + "/" + part
    return base + part


def _build_ssl_context(verify_ssl: bool) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _http_request_with_retries(req, ctx, max_retries=5, base_sleep=1.0, ew: Optional[EventWriter] = None, log_ctx: str = ""):
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
                return resp.getcode(), resp.headers, resp.read()
        except urllib.error.HTTPError as e:
            status = e.code
            headers = e.headers or {}

            # Backoff на 429/5xx
            if status == 429 or 500 <= status < 600:
                attempt += 1
                if attempt > max_retries:
                    raise
                ra = headers.get("Retry-After")
                try:
                    delay = float(ra) if ra else None
                except Exception:
                    delay = None
                if delay is None:
                    delay = base_sleep * (2 ** (attempt - 1)) + random.uniform(0.0, 0.5)
                delay = min(max(delay, 1.0), 60.0)
                if ew:
                    _log(ew, "WARN", f"{log_ctx} HTTP {status}, retry in {delay:.1f}s")
                time.sleep(delay)
                continue
            raise
        except urllib.error.URLError as e:
            attempt += 1
            if attempt > max_retries:
                if ew:
                    _log(ew, "ERROR", f"{log_ctx} URLError {e} for {getattr(req, 'full_url', '')}")
                raise
            delay = base_sleep * (2 ** (attempt - 1)) + random.uniform(0.0, 0.5)
            delay = min(max(delay, 1.0), 60.0)
            if ew:
                _log(ew, "WARN", f"{log_ctx} URL error, retry in {delay:.1f}s")
            time.sleep(delay)
            continue


def _http_get_json(url: str, headers: Dict[str, str], ctx: ssl.SSLContext, ew: Optional[EventWriter] = None, log_ctx: str = "") -> Dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    status, _, data = _http_request_with_retries(req, ctx, ew=ew, log_ctx=log_ctx)
    if status < 200 or status >= 300:
        raise Exception(f"HTTP {status} from {url}")
    return json.loads(data.decode("utf-8"))


def _build_objects_url(base_url: Optional[str], api_root: str, collection: str) -> str:
    """
    Builds URL:
      <base_url>/<api_root>/collections/<collection>/objects/
    If api_root is full URL (http/https), base_url is ignored.
    """
    base = (api_root or "").strip()
    if base.lower().startswith("http://") or base.lower().startswith("https://"):
        root = base
    else:
        root = _join_url((base_url or "").strip(), base)
    return _join_url(_join_url(_join_url(root, "collections"), collection.strip()), "objects/")


def _iter_objects(objects_url: str, headers: Dict[str, str], ctx: ssl.SSLContext,
                  added_after_iso: Optional[str], limit: Optional[int],
                  ew: Optional[EventWriter] = None, log_ctx: str = ""):
    def with_params(base, params):
        parsed = list(urllib.parse.urlparse(base))
        q = dict(urllib.parse.parse_qsl(parsed[4], keep_blank_values=True))
        for k, v in params.items():
            if v is not None:
                q[k] = v
        parsed[4] = urllib.parse.urlencode(q)
        return urllib.parse.urlunparse(parsed)

    # Normalize added_after to ".0Z"
    if added_after_iso:
        if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", added_after_iso):
            added_after_iso = added_after_iso[:-1] + ".0Z"
        elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$", added_after_iso):
            added_after_iso = re.sub(r"\.\d+Z$", ".0Z", added_after_iso)

    url = objects_url
    if added_after_iso:
        url = with_params(url, {"added_after": added_after_iso})
    if limit:
        url = with_params(url, {"limit": str(limit)})

    _log(ew, "INFO", f"url={url}")

    while True:
        payload = _http_get_json(url, headers, ctx, ew=ew, log_ctx=log_ctx)
        for obj in payload.get("objects", []):
            yield obj
        # Pagination: next/more support
        next_token = payload.get("next")
        more = payload.get("more")
        if isinstance(next_token, str) and next_token:
            if next_token.startswith("http"):
                url = next_token
            else:
                url = with_params(objects_url, {"next": next_token, "added_after": added_after_iso, "limit": limit})
            continue
        if isinstance(more, str) and more:
            url = more if more.startswith("http") else _join_url(objects_url, more)
            continue
        break


def _parse_lookback(s: str) -> Optional[datetime.timedelta]:
    if not s:
        return None
    m = re.match(r"^\s*(\d+)\s*([smhd])\s*$", s, re.I)
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2).lower()
    return {
        "s": datetime.timedelta(seconds=val),
        "m": datetime.timedelta(minutes=val),
        "h": datetime.timedelta(hours=val),
        "d": datetime.timedelta(days=val),
    }.get(unit)


def _normalize_to_cim(obj: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    stix_type = obj.get("type")
    out["stix_type"] = stix_type
    out["stix_id"] = obj.get("id")
    out["labels"] = obj.get("labels")
    out["description"] = obj.get("description") or obj.get("name")
    out["confidence"] = obj.get("confidence")
    out["valid_from"] = obj.get("valid_from")
    out["valid_until"] = obj.get("valid_until")

    indicator = None
    indicator_type = None
    pattern = (obj.get("pattern") or "").strip()

    # Simple attempt to extract indicator from STIX pattern
    if stix_type == "indicator" and pattern:
        try:
            p = pattern.strip().strip("[]")
            left, right = p.split("=", 1)
            val = right.strip().strip("'").strip('"')
            l = left.lower()
            if l.startswith("ipv4-addr:value"):
                indicator_type = "ipv4"
            elif l.startswith("ipv6-addr:value"):
                indicator_type = "ipv6"
            elif l.startswith("domain-name:value"):
                indicator_type = "domain"
            elif l.startswith("url:value"):
                indicator_type = "url"
            elif "file:hashes.'sha-256'" in l or "file:hashes.'sha256'" in l:
                indicator_type = "sha256"
            elif "file:hashes.'md5'" in l:
                indicator_type = "md5"
            elif "file:hashes.'sha-1'" in l or "file:hashes.'sha1'" in l:
                indicator_type = "sha1"
            elif l.startswith("file:name"):
                indicator_type = "filename"
            indicator = val
        except Exception:
            pass

    if not indicator and obj.get("value"):
        indicator = obj.get("value")
    if not indicator_type and obj.get("pattern_type"):
        indicator_type = obj.get("pattern_type")

    if indicator:
        out["indicator"] = indicator
    if indicator_type:
        out["indicator_type"] = indicator_type

    out["vendor_product"] = "TAXII2"
    out["threat_collection"] = obj.get("created_by_ref")
    return out


def _basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    return f"Basic {token}"


def _safe_name(x: str) -> str:
    """normalize a string to a safe lowercase token for filenames"""
    if x is None:
        return "none"
    x = x.strip().lower()
    return re.sub(r"[^a-z0-9_.-]+", "_", x)


def _ckpt_path(checkpoint_dir: str, stanza_name: str, collection: str) -> str:
    """stable checkpoint path based on stanza + collection (normalized)"""
    fname = f"taxii2_ioc__{_safe_name(stanza_name)}__{_safe_name(collection)}.ckpt"
    return os.path.join(checkpoint_dir, fname)


class Taxii2Input(Script):
    def get_scheme(self):
        scheme = Scheme("Resecurity TAXII 2 IOC Input")
        scheme.description = "Fetch IOCs from a TAXII 2.x server"
        scheme.use_external_validation = False
        scheme.use_single_instance = False

        # Minimum set of user instance parameters
        for name, dtype, desc, req in [
            ("collection", Argument.data_type_string, "Collection ID or name", True),
            ("limit", Argument.data_type_number, "Page size per request", False),
            ("initial_lookback", Argument.data_type_string, "e.g., 24h, 7d", False),
        ]:
            arg = Argument(name)
            arg.data_type = dtype
            arg.description = desc
            arg.required_on_create = req
            arg.required_on_edit = False
            scheme.add_argument(arg)
        return scheme

    def stream_events(self, inputs, ew: EventWriter):
        service = self.service
        try:
            if hasattr(service, "namespace") and isinstance(service.namespace, dict):
                service.namespace["owner"] = "nobody"
                service.namespace["app"] = APP_NAME
                service.namespace["sharing"] = "app"
            else:
                service.namespace = {"owner": "nobody", "app": APP_NAME, "sharing": "app"}
        except Exception:
            pass

        username, password, verify_ssl_global, conf = self._get_global_settings(service)
        if not username or not password:
            _log(ew, "ERROR", "Global username/token not configured. Open the app setup page and save credentials.")
            return

        for stanza_name, params in list(inputs.inputs.items()):
            # api_root take only from global settings resecurity.conf [settings]
            api_root = (conf.get("api_root") or "").strip()
            collection = (params.get("collection") or "").strip() or None

            verify_ssl = bool(verify_ssl_global)

            # page size limit
            limit = None
            if params.get("limit"):
                try:
                    limit = int(params["limit"])
                except Exception:
                    _log(ew, "WARN", f"{stanza_name}: invalid limit, ignored")

            # initial lookback (for all launches it is used as a rolling floor)
            lb_raw = (params.get("initial_lookback") or "").strip()
            lookback_td = _parse_lookback(lb_raw) or datetime.timedelta(hours=24)

            if not api_root:
                _log(ew, "ERROR", f"{stanza_name}: global api_root not configured in resecurity.conf [settings]")
                continue
            if not collection:
                _log(ew, "ERROR", f"{stanza_name}: collection is required")
                continue

            ctx = _build_ssl_context(verify_ssl)
            headers = {
                "Accept": "application/taxii+json; version=2.1",
                "Authorization": _basic_auth_header(username, password),
                "User-Agent": f"{APP_NAME}/1.0",
            }

            ck_dir = inputs.metadata.get("checkpoint_dir") or os.environ.get("SPLUNK_CHECKPOINT_DIR") or "."
            ck_path = _ckpt_path(ck_dir, stanza_name, collection)

            last_iso = None
            last_raw = None
            try:
                if os.path.exists(ck_path):
                    with open(ck_path, "r", encoding="utf-8") as f:
                        data = json.load(f) or {}
                        last_raw = data.get("added_after")
                        last_dt = _iso_to_dt(last_raw)
                        if last_dt:
                            last_iso = _dt_to_iso(last_dt)
            except Exception as e:
                _log(ew, "WARN", f"{stanza_name} failed to read checkpoint {ck_path}: {e}")

            floor_dt = _now_utc() - lookback_td
            floor_iso = _dt_to_iso(floor_dt)

            if not last_iso:
                since_dt = floor_dt
                since_iso = floor_iso
                _log(ew, "INFO", f"{stanza_name} checkpoint: none/invalid (raw={last_raw}) at {ck_path}, using floor={floor_iso}")
            else:
                last_dt = _iso_to_dt(last_iso) or floor_dt
                since_dt = last_dt if last_dt > floor_dt else floor_dt
                since_iso = _dt_to_iso(since_dt)

            _log(ew, "INFO", f"{stanza_name} resolve since: last_iso={last_iso or '(none)'} floor={floor_iso} → since={since_iso}")

            request_start_dt = _now_utc()
            newest_dt = since_dt

            try:
                base_url = (conf.get("url") or "").strip() or None
                objects_url = _build_objects_url(base_url, api_root, collection)

                masked_user = f"{username[:2]}***" if username else "?"
                _log(ew, "INFO", f"{stanza_name} request: url={objects_url} added_after={since_iso} limit={limit} "
                                 f"verify_ssl={verify_ssl} auth=basic user={masked_user}")

                count = 0
                for obj in _iter_objects(objects_url, headers, ctx, since_iso, limit, ew=ew, log_ctx=f"{stanza_name}"):
                    event = Event()
                    event.stanza = stanza_name
                    event.data = json.dumps({**obj, **_normalize_to_cim(obj)}, ensure_ascii=False)

                    iso_ts = obj.get("created") or obj.get("modified")
                    dt_ts = _iso_to_dt(iso_ts) if iso_ts else None
                    if dt_ts:
                        now_utc = datetime.datetime.now(datetime.timezone.utc)
                        if dt_ts > now_utc + datetime.timedelta(minutes=5):
                            dt_ts = now_utc
                        event.time = dt_ts.timestamp()
                    else:
                        event.time = None

                    event.source = stanza_name
                    ew.write_event(event)

                    created = obj.get("created") or obj.get("modified")
                    cdt = _iso_to_dt(created) if created else None
                    if cdt and cdt > newest_dt:
                        newest_dt = cdt

                    count += 1

                if request_start_dt > newest_dt:
                    newest_dt = request_start_dt

                save_dt = newest_dt if newest_dt > floor_dt else floor_dt
                new_iso = _dt_to_iso(save_dt)

                _log(ew, "INFO", f"{stanza_name} checkpoint update: old={last_iso or '(none)'} → new={new_iso} (floor={floor_iso}) path={ck_path}")

                try:
                    os.makedirs(ck_dir, exist_ok=True)
                    with open(ck_path + ".tmp", "w", encoding="utf-8") as f:
                        json.dump({"added_after": new_iso}, f)
                    os.replace(ck_path + ".tmp", ck_path)
                except Exception as e:
                    _log(ew, "ERROR", f"{stanza_name} cannot write checkpoint {ck_path}: {e}")

                _log(ew, "INFO", f"{stanza_name} done, events={count}")

            except Exception as e:
                _log(ew, "ERROR", f"{stanza_name} {collection}: {e}")

    def _get_global_settings(self, service):
        username = self._get_secret(service, "username")
        password = self._get_secret(service, "token")

        conf = {}
        try:
            if hasattr(service, "namespace") and isinstance(service.namespace, dict):
                service.namespace["owner"] = "nobody"
                service.namespace["app"] = APP_NAME
                service.namespace["sharing"] = "app"
            if "resecurity" in service.confs:
                rs = service.confs["resecurity"]
                if "settings" in rs:
                    content = rs["settings"].content
                    conf = dict(content)
        except Exception:
            pass

        verify_ssl = str(conf.get("verify_ssl", "true")).lower() != "false"
        return username, password, verify_ssl, conf

    def _get_secret(self, service, username):
        key = f"{CRED_REALM}:{username}:"
        try:
            item = service.storage_passwords[key]
            item.refresh()
            cp = item.content.get("clear_password")
            if cp:
                return cp
        except Exception:
            pass

        try:
            for cred in service.storage_passwords:
                c = cred.content or {}
                if c.get("realm") == CRED_REALM and c.get("username") == username:
                    try:
                        name = getattr(cred, "name", None)
                        if name:
                            item2 = service.storage_passwords[name]
                            item2.refresh()
                            cp = item2.content.get("clear_password")
                            if cp:
                                return cp
                    except Exception:
                        continue
        except Exception:
            pass
        return None


if __name__ == "__main__":
    sys.exit(Taxii2Input().run(sys.argv))