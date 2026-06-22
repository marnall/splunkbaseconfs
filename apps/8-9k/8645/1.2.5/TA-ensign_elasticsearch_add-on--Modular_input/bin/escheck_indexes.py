# encoding = utf-8
# Copyright 2026 Ensign Infosecurity Indonesia. All Rights Reserved.

"""
Custom SPL Command: escheck_indexes
Lists all Elasticsearch indices with health, status, doc count, and storage size.
Usage: | escheck_indexes cluster_name="<stanza_name>"
APP-RESTRICTED — only runs within TA-ensign_elasticsearch_add-on--Modular_input.
"""

import ta_ensign_elasticsearch_add_on_modular_input_declare

import os
import sys
import json
import re
import logging
import datetime
import urllib.parse

from splunklib.searchcommands import (
    dispatch, GeneratingCommand, Configuration, Option, validators,
)

_ALLOWED_APP = "TA-ensign_elasticsearch_add-on--Modular_input"
_LOGGER = logging.getLogger(_ALLOWED_APP)
_SAFE_STANZA_RE = re.compile(r'^[a-zA-Z0-9_\-\.]+$')


def _sanitize_stanza_name(name):
    if not name or not _SAFE_STANZA_RE.match(name):
        raise ValueError(f"Invalid cluster_name: '{name}'. Only alphanumeric, underscore, hyphen, and dot are allowed.")
    return name


def _read_cluster_config(session_key, cluster_name):
    import splunklib.client as client
    safe_name = _sanitize_stanza_name(cluster_name)
    service = client.connect(token=session_key, app=_ALLOWED_APP, owner="nobody")
    endpoint = (
        f"/servicesNS/nobody/{_ALLOWED_APP}/"
        f"TA_ensign_elasticsearch_add_on__Modular_input_es_clusters/"
        f"{urllib.parse.quote(safe_name)}?output_mode=json&--cred--=1"
    )
    response = service.get(endpoint)
    data = json.loads(response.body.read())
    if not data.get("entry"):
        raise ValueError(f"ES Cluster profile '{safe_name}' not found.")
    return data["entry"][0]["content"]


@Configuration(type="reporting")
class ESCheckIndexesCommand(GeneratingCommand):
    """Lists all Elasticsearch indices with health and statistics."""

    cluster_name = Option(name="cluster_name", require=True, validate=validators.Fieldname())

    def generate(self):
        app = self._metadata.searchinfo.app
        if app != _ALLOWED_APP:
            yield {
                "_raw": json.dumps({"error": f"App-restricted. Must run from '{_ALLOWED_APP}'."}),
                "error": f"This command can only be run from '{_ALLOWED_APP}'.",
                "status": "blocked",
            }
            return

        session_key = self._metadata.searchinfo.session_key
        check_time  = datetime.datetime.utcnow().isoformat() + "Z"
        username    = self._metadata.searchinfo.username
        sid         = self._metadata.searchinfo.sid

        # ── 5W1H Audit: INITIATED ────────────────────────────────────
        _LOGGER.info(
            f"[AUDIT] command=escheck_indexes action=INITIATED "
            f"who={username} when={check_time} "
            f"where=app={app},sid={sid} "
            f"what=es_index_enumeration "
            f"which=cluster={self.cluster_name} how=pending"
        )

        try:
            config = _read_cluster_config(session_key, self.cluster_name)

            es_host       = config.get("es_host", "")
            es_port       = int(config.get("es_port", 9200))
            es_user       = config.get("es_user", "")
            es_pass       = config.get("es_pass", "")
            verify_cert   = config.get("verify_cert", "0")
            cert_location = config.get("cert_location", "").strip()

            from elasticsearch import Elasticsearch

            hosts = [{"host": h.strip(), "port": es_port, "scheme": "https"}
                     for h in str(es_host).split(",") if h.strip()]

            es_kwargs = {
                "hosts": hosts,
                "basic_auth": (es_user, es_pass),
                "request_timeout": 30,
                "max_retries": 1,
                "retry_on_timeout": False,
            }

            is_verify = str(verify_cert).lower() in ["1", "true", "yes"]
            if is_verify:
                es_kwargs["verify_certs"] = True
                if cert_location and os.path.isabs(cert_location) and os.path.isfile(cert_location):
                    es_kwargs["ca_certs"] = cert_location
            else:
                es_kwargs["verify_certs"] = False

            client = Elasticsearch(**es_kwargs)
            indices = client.cat.indices(format="json", bytes="b")

            if not indices:
                _LOGGER.info(
                    f"[AUDIT] command=escheck_indexes action=SUCCESS "
                    f"who={username} sid={sid} which=cluster={self.cluster_name} "
                    f"how=result=0_indices_returned"
                )
                yield {
                    "_raw": json.dumps({"cluster_name": self.cluster_name, "message": "No indices found.", "timestamp": check_time}),
                    "cluster_name": self.cluster_name, "index_name": "(none)",
                    "message": "No indices found.", "timestamp": check_time,
                }
                return

            indices_sorted = sorted(indices, key=lambda x: x.get("index", ""))
            visible_count = 0

            for idx in indices_sorted:
                index_name = idx.get("index", "unknown")
                # SECURITY: Skip internal/system ES indices to prevent information disclosure
                if index_name.startswith("."):
                    continue
                visible_count += 1
                yield {
                    "_raw": json.dumps({
                        "cluster_name": self.cluster_name,
                        "index_name": index_name,
                        "health": idx.get("health", "unknown"),
                        "status": idx.get("status", "unknown"),
                        "doc_count": idx.get("docs.count", "0"),
                        "store_size": idx.get("store.size", "0"),
                        "pri_shards": idx.get("pri", "0"),
                        "rep_shards": idx.get("rep", "0"),
                        "timestamp": check_time,
                    }),
                    "cluster_name": self.cluster_name,
                    "index_name": index_name,
                    "health": idx.get("health", "unknown"),
                    "status": idx.get("status", "unknown"),
                    "doc_count": str(idx.get("docs.count", "0")),
                    "store_size": str(idx.get("store.size", "0")),
                    "pri_shards": str(idx.get("pri", "0")),
                    "rep_shards": str(idx.get("rep", "0")),
                    "timestamp": check_time,
                }

            # ── 5W1H Audit: SUCCESS ──────────────────────────────────
            _LOGGER.info(
                f"[AUDIT] command=escheck_indexes action=SUCCESS "
                f"who={username} sid={sid} which=cluster={self.cluster_name} "
                f"how=result={visible_count}_indices_returned,"
                f"hidden_skipped={len(indices_sorted)-visible_count}"
            )

        except Exception as e:
            err_msg = re.sub(r'://[^@]+@', '://***:***@', str(e))
            _LOGGER.warning(
                f"[AUDIT] command=escheck_indexes action=FAILED "
                f"who={username} sid={sid} which=cluster={self.cluster_name} "
                f"how=result=FAILED,error={err_msg[:150]}"
            )
            yield {
                "_raw": json.dumps({"cluster_name": self.cluster_name, "error": err_msg, "timestamp": check_time}),
                "cluster_name": self.cluster_name, "index_name": "", "error": err_msg, "timestamp": check_time,
            }


if __name__ == "__main__":
    dispatch(ESCheckIndexesCommand, sys.argv, sys.stdin, sys.stdout, __name__)
