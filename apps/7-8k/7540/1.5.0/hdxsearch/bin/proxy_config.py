from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional
from typing_extensions import TypedDict

from errors import HdxCommandFatalError

if TYPE_CHECKING:
    # `splunklib` is vendored under `lib/` and is only importable after the bin
    # entry points run their `sys.path.insert`. This module is loaded earlier in
    # the import chain and uses `SplunkService` only for type annotations, so
    # keep the import type-checking-only to avoid a runtime ModuleNotFoundError.
    from splunklib.client import Service as SplunkService


@dataclass(frozen=True)
class ProxyConfig:
    protocol: str
    host: str
    port: int
    user: str = ""
    password: str = ""

    class Repr(TypedDict, total=False):
        """JSON representation of a proxy config (i.e., a dict from the
        `proxies` JSON array in hdxsearch.conf)

        Written manually by users who need proxy configs
        """

        cluster: str
        protocol: str
        host: str
        port: int
        user: str
        password: str

    def to_url(self) -> str:
        auth = f"{self.user}:{self.password}@" if self.user and self.password else ""
        return f"{self.protocol}://{auth}{self.host}:{str(self.port)}"

    @classmethod
    def from_dict(cls, conf: Repr) -> "ProxyConfig":
        required_keys = ["protocol", "host", "port"]
        if any(missing_keys := {key for key in required_keys if not conf.get(key)}):
            raise HdxCommandFatalError(
                f"Found proxy configuration for this cluster missing required keys: {missing_keys}"
            )
        return cls(
            conf["protocol"],
            conf["host"],
            conf["port"],
            conf.get("user", ""),
            conf.get("password", ""),
        )

    @classmethod
    def _load_proxies(cls, service: SplunkService) -> List["ProxyConfig.Repr"]:
        """Load the proxies JSON array from hdxsearch.conf. Returns [] if absent, raises if parsing fails."""
        proxies_stanza = service.confs["hdxsearch"]["proxies"]
        if "proxies" not in proxies_stanza:
            return []
        try:
            return json.loads(proxies_stanza["proxies"])
        except json.JSONDecodeError:
            raise HdxCommandFatalError(
                "Unable to decode config key `proxies` in hdxsearch.conf `proxies` stanza as JSON"
            )

    @classmethod
    def from_service(cls, service: SplunkService, cluster_name: str) -> Optional["ProxyConfig"]:
        """Look up proxy configuration for the given cluster."""
        for p in cls._load_proxies(service):
            if p.get("cluster") == cluster_name:
                return ProxyConfig.from_dict(p)
        return None

    @classmethod
    def infer_proxy_for(
        cls,
        service: SplunkService,
        cluster_name: Optional[str] = None,
        cluster_endpoint: Optional[str] = None,
    ) -> Optional["ProxyConfig"]:
        """
        Resolve a proxy for validation, trying name match then falling back to
        the cluster configured with the specified endpoint (assuming exactly
        1 such cluster exists). The latter case is meant to handle verifying connections
        when the cluster name is being changed (i.e., the name being tested differs from the
        name of the same cluster in the persisted config).
        """
        if not cluster_name and not cluster_endpoint:
            return None

        proxies = cls._load_proxies(service)
        if not proxies:
            return None

        # Step 1: direct name match (skip when no cluster_name provided)
        if cluster_name:
            for p in proxies:
                if p.get("cluster") == cluster_name:
                    return ProxyConfig.from_dict(p)

        # Step 2: endpoint fallback (skip when no endpoint provided)
        if not cluster_endpoint:
            return None

        try:
            clusters_json = service.confs["hdxsearch"]["clusters"]["clusters"]
            cluster_endpoints: dict = {c.get("cluster"): c.get("endpoint") for c in json.loads(clusters_json)}
        except KeyError:
            # The "clusters" config couldn't be found -- so no cluster could possibly match
            return None
        except json.JSONDecodeError:
            # The "clusters" config failed to parse -- so no cluster could be used
            return None

        matches = [p for p in proxies if cluster_endpoints.get(p.get("cluster")) == cluster_endpoint]
        if len(matches) == 1:
            # If using host+port based matching, the matched cluster must be unambiguous
            return ProxyConfig.from_dict(matches[0])
        return None
