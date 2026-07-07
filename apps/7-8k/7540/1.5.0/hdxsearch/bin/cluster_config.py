from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional
from typing_extensions import TypedDict

from hdxclient import HdxClient
from errors import HdxCommandFatalError
from proxy_config import ProxyConfig

if TYPE_CHECKING:
    # `splunklib` is vendored under `lib/` and is only importable after the bin
    # entry points run their `sys.path.insert`. This module is loaded earlier in
    # the import chain and uses `SplunkService` only for type annotations, so
    # keep the import type-checking-only to avoid a runtime ModuleNotFoundError.
    from splunklib.client import Service as SplunkService


@dataclass(frozen=True)
class ClusterConfig:
    """A single cluster's resolved configuration.

    Immutable data object produced by `ClusterConfig.from_service()`.
    Contains everything needed to construct an HdxClient.
    """

    cluster: str
    endpoint: str
    auth_type: str = "basic"
    username: Optional[str] = None
    password: Optional[str] = None
    api_token: Optional[str] = None
    # not ideal to have to specify a default value here as well as in the setup page,
    # but when users upgrade hdxsearch from a version without default limit setting
    # to a version with default limit, we don't want to force them to go through setup again.
    default_limit: int = 5000
    is_default: bool = False
    proxy: Optional[ProxyConfig] = None

    class Repr(TypedDict, total=False):
        """JSON representation of a cluster config (i.e., a dict from the
        `clusters` JSON array in hdxsearch.conf)

        Written by the setup page from form inputs. All keys are always
        present after a normal save, but older config versions may omit
        `authType` or `defaultLimit`.
        """

        cluster: str
        endpoint: str
        default: bool
        defaultLimit: int
        authType: str

    class SecretRepr(TypedDict, total=False):
        """JSON representation of a cluster secret (i.e., a dict from the
        `hdxsearch_realm:password` encrypted JSON array in storage_passwords)

        Each entry is keyed to a cluster by its `cluster` field.
        Depending on the cluster's `authType`, either `username`/`password` or
        `apiToken` will be populated.
        """

        cluster: str
        username: str
        password: str
        apiToken: str

    @classmethod
    def from_service(cls, service: SplunkService, cluster_name: Optional[str]) -> "ClusterConfig":
        """
        Resolve a cluster's full configuration from Splunk service objects.

        Raises HdxCommandFatalError if the cluster cannot be found.
        """
        clusters_json_list: str = cls._read_clusters_stanza(service)["clusters"]
        secrets_json_list: str = service.storage_passwords["hdxsearch_realm:password"].clear_password
        try:
            cluster_infos = json.loads(clusters_json_list)
        except json.JSONDecodeError:
            raise HdxCommandFatalError(
                "Unable to decode config key `clusters` in hdxsearch.conf `clusters` stanza as JSON"
            )

        try:
            cluster_secrets = {s.get("cluster"): s for s in json.loads(secrets_json_list)}
        except json.JSONDecodeError:
            raise HdxCommandFatalError("Unable to decode encrypted Hydrolix cluster connection secrets")

        resolved_name = cls._resolve_cluster_name(cluster_name, cluster_infos)

        if resolved_name is None:
            raise HdxCommandFatalError("No default cluster found")

        for conf in cluster_infos:
            if conf.get("cluster") == resolved_name:
                secret = cluster_secrets.get(resolved_name, {})
                proxy = ProxyConfig.from_service(service, resolved_name)
                return cls.from_dicts(conf, secret, proxy)

        raise HdxCommandFatalError(f"Cluster '{resolved_name}' not found")

    def make_client(self, logger: logging.Logger) -> HdxClient:
        """Construct an HdxClient from this resolved configuration."""
        return HdxClient(
            f"https://{self.endpoint}/",
            self.auth_type,
            self.username,
            self.password,
            self.api_token,
            self.proxy,
            logger,
        )

    @classmethod
    def from_dicts(
        cls,
        cluster_info: Repr,
        cluster_secret: SecretRepr,
        proxy: Optional[ProxyConfig] = None,
    ) -> "ClusterConfig":
        """Build a ClusterConfig from a cluster conf dict and a secret dict.

        INV: cluster_info.get("cluster") == cluster_secret.get("cluster")

        These dicts correspond to entries in the JSON arrays stored in
        Splunk's hdxsearch.conf (`clusters`) and storage_passwords
        (`hdxsearch_realm:password`) respectively.  See `ClusterConf`
        and `ClusterSecret` for the expected shapes.
        """
        required_keys = ["cluster", "endpoint"]
        if any(missing_keys := {key for key in required_keys if not cluster_info.get(key)}):
            raise HdxCommandFatalError(
                f"Found configuration for this cluster missing required settings: {missing_keys}"
            )
        oneof_auth_keys = ["username", "apiToken"]
        if not any(cluster_secret.get(key) for key in oneof_auth_keys):
            raise HdxCommandFatalError(
                f"Found configuration for cluster {cluster_info['cluster']} with no authentication information"
            )

        return cls(
            cluster=cluster_info["cluster"],
            endpoint=cluster_info["endpoint"],
            default_limit=int(cluster_info.get("defaultLimit", 5000)),
            is_default=cluster_info.get("default", False),
            auth_type=cluster_info.get("authType", "basic"),
            username=cluster_secret.get("username"),
            password=cluster_secret.get("password"),
            api_token=cluster_secret.get("apiToken"),
            proxy=proxy,
        )

    @staticmethod
    def _read_clusters_stanza(service: SplunkService) -> Dict[str, str]:
        """Read clusters config, falling back from hdxsearch.conf to app.conf.

        hdxsearch configurations were saved in app.conf in versions <1.0.3,
        so we check both files. hdxsearch.conf is preferred when its
        `clusters` property is present.

        NB calls stanza.submit() as a side-effect to migrate legacy config
        from app.conf to hdxsearch.conf
        """
        app_conf_install_stanza = service.confs["app"]["install"]
        hdxsearch_clusters_stanza = service.confs["hdxsearch"]["clusters"]
        if "clusters" in hdxsearch_clusters_stanza:
            return hdxsearch_clusters_stanza
        return hdxsearch_clusters_stanza.submit({"clusters": app_conf_install_stanza["clusters"]})

    @staticmethod
    def _resolve_cluster_name(cluster_name: Optional[str], confs: List[Repr]) -> Optional[str]:
        """Resolve the effective cluster name from configuration.

        When no cluster name is provided, looks for a cluster marked with
        'default: true', then falls back to a cluster literally named 'default'.
        Returns None if no default cluster is found.
        """
        name = cluster_name.strip() if cluster_name else None
        if name:
            return name
        for conf in confs:
            if conf.get("default", False):
                return conf.get("cluster")
        for conf in confs:
            if conf.get("cluster") == "default":
                return "default"
        return None
