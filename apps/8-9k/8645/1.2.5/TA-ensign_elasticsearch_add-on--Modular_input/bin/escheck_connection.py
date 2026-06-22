# encoding = utf-8
# Copyright 2026 Ensign Infosecurity Indonesia. All Rights Reserved.

"""
Custom SPL Command: escheck_connection
=======================================
Tests connectivity to a configured Elasticsearch cluster.

Usage:
    | escheck_connection cluster_name="<stanza_name>"

This command is APP-RESTRICTED — it only runs within the
TA-ensign_elasticsearch_add-on--Modular_input app context.

Output Fields:
    cluster_name, es_host, es_port, status, response_time_ms,
    es_version, error, timestamp
"""

import ta_ensign_elasticsearch_add_on_modular_input_declare

import os
import sys
import json
import time
import re
import logging
import datetime
import urllib.parse

from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# ── App Restriction ──────────────────────────────────────────────────────
_ALLOWED_APP = "TA-ensign_elasticsearch_add-on--Modular_input"
_LOGGER = logging.getLogger(_ALLOWED_APP)

# ── Security: Input sanitization ─────────────────────────────────────────
_SAFE_STANZA_RE = re.compile(r'^[a-zA-Z0-9_\-\.]+$')


def _sanitize_stanza_name(name):
    """
    Validate and sanitize stanza name to prevent injection attacks.
    Only alphanumeric, underscore, hyphen, and dot are allowed.
    """
    if not name or not _SAFE_STANZA_RE.match(name):
        raise ValueError(
            f"Invalid cluster_name: '{name}'. "
            f"Only alphanumeric, underscore, hyphen, and dot characters are allowed."
        )
    return name


def _read_cluster_config(session_key, server_uri, cluster_name):
    """
    Read ES cluster configuration from Splunk REST API.
    Returns dict of cluster settings or raises Exception.
    """
    import splunklib.client as client

    # SECURITY: Sanitize input before use in REST path
    safe_name = _sanitize_stanza_name(cluster_name)

    service = client.connect(token=session_key, app=_ALLOWED_APP, owner="nobody")
    import splunklib.binding as binding

    endpoint = (
        f"/servicesNS/nobody/{_ALLOWED_APP}/"
        f"TA_ensign_elasticsearch_add_on__Modular_input_es_clusters/"
        f"{urllib.parse.quote(safe_name)}?output_mode=json&--cred--=1"
    )

    response = service.get(endpoint)
    body = response.body.read()
    data = json.loads(body)

    if not data.get("entry"):
        raise ValueError(f"ES Cluster profile '{safe_name}' not found.")

    return data["entry"][0]["content"]


@Configuration(type="reporting")
class ESCheckConnectionCommand(GeneratingCommand):
    """Tests connectivity to a configured Elasticsearch cluster."""

    cluster_name = Option(
        name="cluster_name",
        require=True,
        validate=validators.Fieldname(),
    )

    def generate(self):
        # ── App restriction check ────────────────────────────────────
        app = self._metadata.searchinfo.app
        if app != _ALLOWED_APP:
            yield {
                "_raw": json.dumps({"error": f"App-restricted command. Must run from '{_ALLOWED_APP}', current: '{app}'"}),
                "error": f"This command can only be run from '{_ALLOWED_APP}'. Current app: '{app}'",
                "status": "blocked",
            }
            return

        session_key = self._metadata.searchinfo.session_key
        server_uri  = self._metadata.searchinfo.splunkd_uri
        check_time  = datetime.datetime.utcnow().isoformat() + "Z"

        # ── 5W1H Audit: WHO / WHERE ──────────────────────────────────
        username = self._metadata.searchinfo.username
        sid      = self._metadata.searchinfo.sid

        _LOGGER.info(
            f"[AUDIT] command=escheck_connection action=INITIATED "
            f"who={username} when={check_time} "
            f"where=app={app},sid={sid} "
            f"what=es_connectivity_check "
            f"which=cluster={self.cluster_name} how=pending"
        )

        status = "failed"
        es_host = ""
        elapsed_ms = 0

        try:
            # ── Read cluster config ──────────────────────────────────
            config = _read_cluster_config(session_key, server_uri, self.cluster_name)

            es_host = config.get("es_host", "")
            es_port = int(config.get("es_port", 9200))
            es_user = config.get("es_user", "")
            es_pass = config.get("es_pass", "")

            # SSL/TLS
            verify_cert  = str(config.get("verify_cert", "0")).lower() in ["1", "true", "yes"]
            cert_location = config.get("cert_location", "").strip()

            # ── Build hosts list ─────────────────────────────────────
            hosts = []
            for h in str(es_host).split(","):
                h = h.strip()
                if h:
                    hosts.append({"host": h, "port": es_port, "scheme": "https"})

            # ── Connect and test ─────────────────────────────────────
            from elasticsearch import Elasticsearch

            es_kwargs = {
                "hosts": hosts,
                "basic_auth": (es_user, es_pass),
                "request_timeout": 15,
                "max_retries": 1,
                "retry_on_timeout": False,
            }

            if verify_cert:
                es_kwargs["verify_certs"] = True
                if cert_location and os.path.isabs(cert_location) and os.path.isfile(cert_location):
                    es_kwargs["ca_certs"] = cert_location
            else:
                es_kwargs["verify_certs"] = False

            start_time = time.time()
            client = Elasticsearch(**es_kwargs)
            info = client.info()
            elapsed_ms = round((time.time() - start_time) * 1000, 2)

            es_version = info.get("version", {}).get("number", "unknown")
            cluster_resp_name = info.get("cluster_name", "unknown")
            status = "connected"

            # ── 5W1H Audit: HOW = result ─────────────────────────────
            _LOGGER.info(
                f"[AUDIT] command=escheck_connection action=SUCCESS "
                f"who={username} sid={sid} "
                f"which=cluster={self.cluster_name},host={es_host} "
                f"how=result=connected,response_ms={elapsed_ms},es_version={es_version}"
            )

            result = {
                "_raw": json.dumps({
                    "cluster_name": self.cluster_name,
                    "es_host": es_host,
                    "es_port": es_port,
                    "status": "connected",
                    "response_time_ms": elapsed_ms,
                    "es_version": es_version,
                    "es_cluster_name": cluster_resp_name,
                    "error": "",
                    "timestamp": check_time,
                }),
                "cluster_name": self.cluster_name,
                "es_host": es_host,
                "es_port": str(es_port),
                "status": "connected",
                "response_time_ms": str(elapsed_ms),
                "es_version": es_version,
                "es_cluster_name": cluster_resp_name,
                "error": "",
                "timestamp": check_time,
            }
            yield result

        except Exception as e:
            # SECURITY: Sanitize error message — strip credentials
            err_msg = str(e)
            err_msg = re.sub(r'://[^@]+@', '://***:***@', err_msg)

            # ── 5W1H Audit: HOW = FAILED ─────────────────────────────
            _LOGGER.warning(
                f"[AUDIT] command=escheck_connection action=FAILED "
                f"who={username} sid={sid} "
                f"which=cluster={self.cluster_name} "
                f"how=result=FAILED,error={err_msg[:150]}"
            )

            yield {
                "_raw": json.dumps({
                    "cluster_name": self.cluster_name,
                    "status": "failed",
                    "error": err_msg,
                    "timestamp": check_time,
                }),
                "cluster_name": self.cluster_name,
                "es_host": "",
                "es_port": "",
                "status": "failed",
                "response_time_ms": "",
                "es_version": "",
                "es_cluster_name": "",
                "error": err_msg,
                "timestamp": check_time,
            }


if __name__ == "__main__":
    dispatch(ESCheckConnectionCommand, sys.argv, sys.stdin, sys.stdout, __name__)
