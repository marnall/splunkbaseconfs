# Target-list helpers: parse comma-separated host:port lists (port validated via solnlib.net_utils) or bare hostname lists, and fan probes across a thread pool.
try:
    import import_declare_test
except ImportError:
    pass

import concurrent.futures
import re

from solnlib import net_utils

_MAX_WORKERS = 20

_LABEL = r"[A-Za-z0-9_](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9_])?"
_HOSTNAME_RE = re.compile(r"^%s(?:\.%s)*\.?$" % (_LABEL, _LABEL))


def parse_targets(raw, default_port=None):
    if not raw or not raw.strip():
        raise ValueError("targets is empty")
    targets = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            if default_port is None:
                raise ValueError("target missing port: " + chunk)
            host, port = chunk, default_port
        else:
            host, _, port_str = chunk.rpartition(":")
            host = host.strip()
            port_str = port_str.strip()
            if not net_utils.is_valid_port(port_str):
                raise ValueError("target port invalid: " + chunk)
            port = int(port_str)
        if not host:
            raise ValueError("target missing host: " + chunk)
        targets.append((host, port))
    if not targets:
        raise ValueError("no valid targets parsed")
    return targets


def is_plausible_hostname(name):
    return bool(name) and len(name) <= 253 and bool(_HOSTNAME_RE.match(name))


def parse_names(raw):
    if not raw or not raw.strip():
        raise ValueError("no hostnames provided")
    names = []
    seen = set()
    for chunk in raw.replace("\r", "\n").replace("\n", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not is_plausible_hostname(chunk):
            raise ValueError("invalid hostname: " + chunk)
        if chunk not in seen:
            seen.add(chunk)
            names.append(chunk)
    if not names:
        raise ValueError("no valid hostnames parsed")
    return names


def run_parallel(targets, fn):
    workers = max(1, min(len(targets), _MAX_WORKERS))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(fn, targets))


def run_targets(targets_raw, timeout_ms, fn, default_port=None):
    timeout_s = timeout_ms / 1000.0
    targets = parse_targets(targets_raw, default_port=default_port)
    return run_parallel(targets, lambda target: fn(target[0], target[1], timeout_s))
