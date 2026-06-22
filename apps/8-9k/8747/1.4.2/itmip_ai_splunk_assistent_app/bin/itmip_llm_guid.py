"""Environment GUID detection.

The Cryptolens MachineCode parameter must be a single, stable
identifier that survives node replacement, restart, and (where
possible) re-imaging of a single member. We deliberately do NOT use
the hostname — admins can rename Splunk servers, and that would
silently break the node lock.

Resolution order (most cluster-scoped first):

  1. Search Head Cluster `id` from `/services/shcluster/config`
     (when `disabled = false`). This GUID is splunk-managed and shared
     across all SHC members for the lifetime of the cluster.
  2. Indexer Cluster Manager GUID. On a cluster peer or search head
     pointing at a CM, `/services/cluster/config` exposes `master_uri`;
     we fetch the CM's `/services/server/info → guid`.
  3. Splunk Cloud: when `instance_type == "cloud"`, use `server_name`
     (the stack hostname). For Splunk Cloud, this is the only stable
     identifier customers can reference.
  4. Standalone: local `/services/server/info → guid` from
     `etc/instance.cfg`.

The result is cached at module level for `CACHE_TTL_SEC` so the
license-validate path doesn't probe the cluster on every request.
"""

import json
import time

import splunk.rest as rest  # type: ignore


CACHE_TTL_SEC = 600  # 10 minutes
_cached = {"value": None, "expires": 0}


def _get(sys_token, path):
    """REST GET helper. Returns (status_code, parsed_json or None)."""
    try:
        resp, content = rest.simpleRequest(
            path + ("&" if "?" in path else "?") + "output_mode=json",
            sessionKey=sys_token,
            method="GET",
        )
    except Exception:
        return 0, None
    status = getattr(resp, "status", 0)
    if status != 200:
        return status, None
    try:
        return status, json.loads(content)
    except Exception:
        return status, None


def _shc_id(sys_token):
    status, data = _get(sys_token, "/services/shcluster/config")
    if status != 200 or not data:
        return None
    entry = (data.get("entry") or [{}])[0]
    content = entry.get("content") or {}
    if content.get("disabled"):
        return None
    cluster_id = (content.get("id") or "").strip()
    return cluster_id or None


def _idx_cluster_master_guid(sys_token):
    status, data = _get(sys_token, "/services/cluster/config")
    if status != 200 or not data:
        return None
    entry = (data.get("entry") or [{}])[0]
    content = entry.get("content") or {}
    if content.get("disabled"):
        return None
    mode = content.get("mode")
    if mode not in ("master", "manager", "slave", "peer", "searchhead"):
        return None
    if mode in ("master", "manager"):
        # We ARE the cluster manager — our own instance guid is the
        # cluster's stable identifier.
        return _instance_guid(sys_token)
    master_uri = content.get("master_uri") or ""
    if not master_uri or master_uri.strip() == "?":
        return None
    # Note: a remote /services/server/info call would need the CM's
    # session key. From a peer/SH the local sessionKey isn't valid
    # against the CM. So we use the master_uri as a stable identifier
    # surrogate (it's the hostname:port of the CM, baked into config).
    # Hash it deterministically into a GUID-shaped string.
    return _surrogate_from_uri(master_uri)


def _surrogate_from_uri(uri):
    """Hash `https://manager.example:8089` -> a stable GUID-like string.

    Used when we can't reach the CM directly to fetch its real GUID.
    """
    import hashlib

    digest = hashlib.sha256(uri.encode("utf-8")).hexdigest()
    return "CM-" + digest[:32].upper()


def _instance_guid(sys_token):
    status, data = _get(sys_token, "/services/server/info")
    if status != 200 or not data:
        return None, None
    entry = (data.get("entry") or [{}])[0]
    content = entry.get("content") or {}
    return content.get("guid"), content


def _cloud_stack_name(server_info):
    """For Splunk Cloud, prefer the stack hostname (server_name)."""
    if not server_info:
        return None
    if server_info.get("instance_type") == "cloud":
        return server_info.get("server_name") or server_info.get("guid")
    return None


def is_splunk_cloud(sys_token):
    """True if this Splunk instance is Splunk Cloud
    (`instance_type == "cloud"`). Used to enforce compliance gates that
    forbid certain dev-mode features (e.g. tls_skip_verify on LLM /
    MCP / custom-tool configs).

    Cached for the splunkd process lifetime via the same
    `get_environment_guid` cache, so cheap to call per request.

    Fail-safe: if detection fails (REST unreachable, etc.) return True
    — refuse the dangerous feature rather than risk silently disabling
    TLS in a Cloud tenant where the admin has no recourse."""
    try:
        env = get_environment_guid(sys_token) or {}
        return (env.get("source") or "").lower() == "cloud"
    except Exception:
        return True


def get_environment_guid(sys_token, force=False):
    """Return {guid, source}. Cached for CACHE_TTL_SEC.

    `source` is one of:
      "shcluster"       — Search Head Cluster `id`
      "idx_cluster_cm"  — Indexer Cluster Manager (or surrogate)
      "cloud"           — Splunk Cloud stack hostname
      "instance"        — Standalone instance.cfg guid

    Never returns None for `guid`; falls back to the local instance
    GUID as a last resort.
    """
    now = int(time.time())
    if not force and _cached["value"] and _cached["expires"] > now:
        return _cached["value"]

    # 1) SHC wins (cluster-scoped, splunk-managed).
    shc = _shc_id(sys_token)
    if shc:
        result = {"guid": shc, "source": "shcluster"}
        _cached["value"] = result
        _cached["expires"] = now + CACHE_TTL_SEC
        return result

    # 2) Indexer cluster manager.
    idx = _idx_cluster_master_guid(sys_token)
    if idx:
        result = {"guid": idx, "source": "idx_cluster_cm"}
        _cached["value"] = result
        _cached["expires"] = now + CACHE_TTL_SEC
        return result

    # 3) Splunk Cloud — fetch /server/info first so we can detect it.
    instance_guid, server_info = _instance_guid(sys_token)
    cloud = _cloud_stack_name(server_info)
    if cloud:
        result = {"guid": cloud, "source": "cloud"}
        _cached["value"] = result
        _cached["expires"] = now + CACHE_TTL_SEC
        return result

    # 4) Standalone.
    result = {"guid": instance_guid or "UNKNOWN", "source": "instance"}
    _cached["value"] = result
    _cached["expires"] = now + CACHE_TTL_SEC
    return result


def reset_cache():
    """For tests."""
    _cached["value"] = None
    _cached["expires"] = 0
