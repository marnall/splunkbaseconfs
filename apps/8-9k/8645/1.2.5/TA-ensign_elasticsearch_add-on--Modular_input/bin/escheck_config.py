# encoding = utf-8
# Copyright 2026 Ensign Infosecurity Indonesia. All Rights Reserved.

"""
Custom SPL Command: escheck_config
====================================
Displays the configuration and live health status of a configured
Elasticsearch cluster.

Usage:
    | escheck_config cluster_name="<stanza_name>"

This command is APP-RESTRICTED — it only runs within the
TA-ensign_elasticsearch_add-on--Modular_input app context.

Output Fields:
    cluster_name, es_host, es_port, es_user, es_pass (masked),
    verify_cert, cert_location, enable_sniffing, max_retries,
    retry_on_timeout, connection_timeout, disabled,
    es_cluster_health, es_cluster_name, es_node_count
"""

import ta_ensign_elasticsearch_add_on_modular_input_declare

import os
import sys
import json
import re
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

# ── Security: Input sanitization ─────────────────────────────────────────
_SAFE_STANZA_RE = re.compile(r'^[a-zA-Z0-9_\-\.]+$')


def _sanitize_stanza_name(name):
    """Validate stanza name — only safe characters allowed."""
    if not name or not _SAFE_STANZA_RE.match(name):
        raise ValueError(
            f"Invalid cluster_name: '{name}'. "
            f"Only alphanumeric, underscore, hyphen, and dot characters are allowed."
        )
    return name


def _read_cluster_config(session_key, cluster_name):
    """Read ES cluster configuration from Splunk REST API."""
    import splunklib.client as client

    safe_name = _sanitize_stanza_name(cluster_name)
    service = client.connect(token=session_key, app=_ALLOWED_APP, owner="nobody")

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


def _bool_display(val):
    """Convert various boolean representations to On/Off."""
    return "On" if str(val).lower() in ["1", "true", "yes"] else "Off"


@Configuration(type="reporting")
class ESCheckConfigCommand(GeneratingCommand):
    """Displays ES cluster configuration and live health status."""

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
        check_time = datetime.datetime.utcnow().isoformat() + "Z"

        try:
            config = _read_cluster_config(session_key, self.cluster_name)

            es_host = config.get("es_host", "")
            es_port = config.get("es_port", "9200")
            es_user = config.get("es_user", "")
            verify_cert = config.get("verify_cert", "0")
            cert_location = config.get("cert_location", "")
            enable_sniffing = config.get("enable_sniffing", "0")
            max_retries = config.get("max_retries", "3")
            retry_on_timeout = config.get("retry_on_timeout", "1")
            connection_timeout = config.get("connection_timeout", "30")
            disabled = config.get("disabled", "0")
            es_pass = config.get("es_pass", "")

            # ── Live health check ────────────────────────────────────
            live_health = "unknown"
            live_cluster_name = "unknown"
            live_node_count = "unknown"

            try:
                from elasticsearch import Elasticsearch

                hosts = []
                for h in str(es_host).split(","):
                    h = h.strip()
                    if h:
                        hosts.append({"host": h, "port": int(es_port), "scheme": "https"})

                es_kwargs = {
                    "hosts": hosts,
                    "basic_auth": (es_user, es_pass),
                    "request_timeout": 15,
                    "max_retries": 1,
                    "retry_on_timeout": False,
                }

                is_verify = str(verify_cert).lower() in ["1", "true", "yes"]
                if is_verify:
                    es_kwargs["verify_certs"] = True
                    # v1.3.0: hardened cert_location validation (see bin/cert_path.py)
                    try:
                        from cert_path import validate_cert_path
                        ca_path = validate_cert_path(cert_location)
                        if ca_path:
                            es_kwargs["ca_certs"] = ca_path
                    except ValueError:
                        # Fall back to system CA bundle. The detailed reason
                        # is intentionally NOT surfaced in the SPL output to
                        # avoid leaking internal-path hints to non-admins.
                        pass
                else:
                    es_kwargs["verify_certs"] = False

                client = Elasticsearch(**es_kwargs)
                health = client.cluster.health(timeout="10s")
                live_health = health.get("status", "unknown")
                live_cluster_name = health.get("cluster_name", "unknown")
                live_node_count = str(health.get("number_of_nodes", "unknown"))
            except Exception as health_err:
                live_health = f"error: {str(health_err)[:100]}"

            result = {
                "_raw": json.dumps({
                    "cluster_name": self.cluster_name,
                    "es_host": es_host,
                    "es_port": es_port,
                    "es_user": es_user,
                    "es_pass": "*****",
                    "verify_cert": _bool_display(verify_cert),
                    "cert_location": cert_location or "(system CA)",
                    "enable_sniffing": _bool_display(enable_sniffing),
                    "max_retries": max_retries,
                    "retry_on_timeout": _bool_display(retry_on_timeout),
                    "connection_timeout": f"{connection_timeout}s",
                    "disabled": _bool_display(disabled),
                    "es_cluster_health": live_health,
                    "es_cluster_name": live_cluster_name,
                    "es_node_count": live_node_count,
                    "timestamp": check_time,
                }),
                "cluster_name": self.cluster_name,
                "es_host": es_host,
                "es_port": es_port,
                "es_user": es_user,
                "es_pass": "*****",
                "verify_cert": _bool_display(verify_cert),
                "cert_location": cert_location or "(system CA)",
                "enable_sniffing": _bool_display(enable_sniffing),
                "max_retries": max_retries,
                "retry_on_timeout": _bool_display(retry_on_timeout),
                "connection_timeout": f"{connection_timeout}s",
                "disabled": _bool_display(disabled),
                "es_cluster_health": live_health,
                "es_cluster_name": live_cluster_name,
                "es_node_count": live_node_count,
                "timestamp": check_time,
            }
            yield result

        except Exception as e:
            err_msg = str(e)
            err_msg = re.sub(r'://[^@]+@', '://***:***@', err_msg)

            yield {
                "_raw": json.dumps({
                    "cluster_name": self.cluster_name,
                    "error": err_msg,
                    "timestamp": check_time,
                }),
                "cluster_name": self.cluster_name,
                "error": err_msg,
                "timestamp": check_time,
            }


if __name__ == "__main__":
    dispatch(ESCheckConfigCommand, sys.argv, sys.stdin, sys.stdout, __name__)
