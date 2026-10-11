import json
import os
import sys
from urllib.parse import parse_qs

sys.path.insert(0, os.path.dirname(__file__))

import import_declare_test  # noqa: F401
from alerts.params import AlertValidationError, UnsupportedFilterError
from alerts.search_client import SearchJobClient
from alerts.service import AlertsQueryService, SearchUnavailable
from alerts.snapshots import SnapshotExpired
from config.models import DataSource, DataSourceValidationError
from config.orchestrator import DataSourceNotFoundError
from config.service import UNSET, DataSourceService
from config.transaction import TransactionRollbackError
from config.validation import list_index_names
from graph.edge_service import EdgeListService
from graph.query import GraphItemNotFoundError
from graph.topology_service import L2TopologyService
from graph.vertex_service import VertexListService
from health.binding_service import (
    BindingConflictError,
    BindingMutationService,
    BindingNotFoundError,
)
from health.capability_binding_compiler import CompilerError
from health.capability_service import CapabilityCatalogService
from health.conf_writer import BindingPersistenceError
from health.metrics_service import (
    HealthMetricsReadError,
    HealthMetricsService,
)
from health.models import CapabilityValidationError
from health.state_service import HealthStateReadError, HealthStateService
from model.kvstore import KvStoreClient, KvStoreError
from model.repository import TopologyKvRepository
from ni_app_logging import configure_component_logger
from rbac.access import check_capability
from rbac.identity import SystemTokenUnavailable, get_system_token, resolve_identity
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication

logger = configure_component_logger("rest_handler")

# Splunk appends output_mode to every REST call (including from webapp/utils/api.ts).
# report_as is a transport hint used by the `rest` search command. Neither value
# is part of an endpoint contract, so keep both out of parser allowlists.
_FRAMEWORK_QUERY_KEYS = frozenset({"output_mode", "report_as"})
HEALTH_CAPABILITIES_ROUTE = "health/capabilities"


class NetworkIntelligenceRestHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super().__init__()
        app_dir = make_splunkhome_path(["etc", "apps", "network_intelligence"])
        self.binding_service = BindingMutationService(app_dir)
        self.data_source_service = DataSourceService(app_dir)
        self.health_metrics_service = HealthMetricsService()
        self.health_state_service = HealthStateService(logger=logger)
        self.capability_service = CapabilityCatalogService()
        self.alerts_service = AlertsQueryService(SearchJobClient())
        graph_repository = TopologyKvRepository(KvStoreClient(logger=logger), logger=logger)
        self.vertex_service = VertexListService(
            graph_repository,
            health_service=self.health_state_service,
            alerts_service=self.alerts_service,
            logger=logger,
        )
        self.edge_service = EdgeListService(graph_repository)
        self.l2_topology_service = L2TopologyService(
            graph_repository,
            health_service=self.health_state_service,
        )

    def handle(self, request):
        try:
            payload = json.loads(request)
            user_session_key = payload.get("session", {}).get("authtoken")
            if not user_session_key:
                return self._json_response(401, {"error": "Missing session token."})

            method = payload.get("method", "GET").upper()
            route = self._route(payload)

            if route == "hello":
                if method == "GET":
                    return self._json_response(200, {"message": "hello"})
                return self._json_response(405, {"error": "Only GET is supported for this route."})

            if route == "alerts/summary":
                check_capability(user_session_key, "ni_alerts_read", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                caller_user = self._caller_user(payload)
                result = self.alerts_service.summarize_alerts(
                    user_session_key, get_system_token(payload), caller_user, self._params(payload)
                )
                return self._json_response(200, result)

            # Every route that contains a data operation: KV/search/conf run on
            # the system token. The caller's token is only for identity/role checks
            # -- is_admin() ahead of mutations, check_scoped_visibility ahead of reads.

            if route == "alerts":
                check_capability(user_session_key, "ni_alerts_read", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                system_session_key = get_system_token(payload)
                caller_user = self._caller_user(payload)
                result = self.alerts_service.list_alerts(
                    user_session_key, system_session_key, caller_user, self._params(payload)
                )
                return self._json_response(200, result)

            if route == "graph/vertices":
                check_capability(user_session_key, "ni_topology_read", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                result = self.vertex_service.list_vertices(
                    user_session_key, get_system_token(payload), self._params(payload)
                )
                return self._json_response(200, result)

            vertex_id = self._vertex_route_id(route)
            if vertex_id is not None:
                check_capability(user_session_key, "ni_topology_read", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                result = self.vertex_service.get_vertex(user_session_key, get_system_token(payload), vertex_id)
                return self._json_response(200, result)

            if route == "graph/edges":
                check_capability(user_session_key, "ni_topology_read", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                result = self.edge_service.list_edges(
                    user_session_key, get_system_token(payload), self._params(payload)
                )
                return self._json_response(200, result)

            edge_id = self._edge_route_id(route)
            if edge_id is not None:
                check_capability(user_session_key, "ni_topology_read", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                result = self.edge_service.get_edge(user_session_key, get_system_token(payload), edge_id)
                return self._json_response(200, result)

            if route == "graph/topology/l2":
                check_capability(user_session_key, "ni_topology_read", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                result = self.l2_topology_service.get_topology(
                    user_session_key, get_system_token(payload), self._params(payload)
                )
                return self._json_response(200, result)

            if route == "health/bindings":
                check_capability(user_session_key, "ni_config_manage", route)
                if method != "POST":
                    return self._json_response(405, {"error": "Only POST is supported for this route."})
                self._require_admin(user_session_key)
                result = self.binding_service.create(self._binding_body(payload), get_system_token(payload))
                return self._mutation_response(201, result)

            if route == "health/state":
                check_capability(user_session_key, "ni_health_read", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                vertex_ids = self._list_param(self._params(payload), "vertex_id")
                if len(vertex_ids) != 1:
                    raise ValueError("Exactly one vertex_id query parameter is required.")
                system_session_key = get_system_token(payload)
                result = self.health_state_service.get_state(
                    user_session_key, system_session_key, vertex_ids[0]
                )
                return self._json_response(200, result)

            if route == HEALTH_CAPABILITIES_ROUTE:
                check_capability(user_session_key, "ni_health_read", HEALTH_CAPABILITIES_ROUTE)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                params = self._params(payload)
                subject_values = self._list_param(params, "subject")
                if len(subject_values) > 1:
                    raise ValueError("subject must be specified once.")
                result = self.capability_service.list_capabilities(
                    get_system_token(payload), subject_values[0] if subject_values else None
                )
                return self._json_response(200, {"items": result})

            if route == "health/state/bulk":
                # POST here is a bulk read (vertex_ids goes in the body, not
                # query params) -- still ni_health_read, not a manage capability.
                check_capability(user_session_key, "ni_health_read", route)
                if method != "POST":
                    return self._json_response(405, {"error": "Only POST is supported for this route."})
                body = self._json_body(payload)
                system_session_key = get_system_token(payload)
                result = self.health_state_service.get_states(
                    user_session_key, system_session_key, body.get("vertex_ids")
                )
                return self._json_response(200, {"items": result})

            if route == "health/metrics_summary":
                check_capability(user_session_key, "ni_health_read", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                request_params = self._params(payload, include_framework=True)
                report_as = self._list_param(request_params, "report_as")
                result = self.health_metrics_service.get_summary(
                    user_session_key,
                    get_system_token(payload),
                    self._params(payload),
                )
                content_type = "text/plain" if report_as == ["text"] else "application/json"
                return self._json_response(200, result, content_type=content_type)

            if route == "health/metrics_subjects":
                check_capability(user_session_key, "ni_health_read", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                result = self.health_metrics_service.get_subjects(
                    user_session_key,
                    get_system_token(payload),
                    self._params(payload),
                )
                return self._json_response(200, result)

            if route == "health/metrics_history":
                check_capability(user_session_key, "ni_health_read", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                result = self.health_metrics_service.get_history(
                    user_session_key,
                    get_system_token(payload),
                    self._params(payload),
                )
                return self._json_response(200, result)

            if route == "settings/data_sources":
                check_capability(user_session_key, "ni_config_manage", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                self._require_admin(user_session_key)
                listing = self.data_source_service.list_sources(get_system_token(payload))
                return self._json_response(200, self._data_sources_response(listing))

            if route == "settings/indexes":
                check_capability(user_session_key, "ni_config_manage", route)
                if method != "GET":
                    return self._json_response(405, {"error": "Only GET is supported for this route."})
                self._require_admin(user_session_key)
                indexes = sorted(list_index_names(get_system_token(payload)))
                return self._json_response(200, {"indexes": indexes})

            if route == "settings/collection":
                check_capability(user_session_key, "ni_config_manage", route)
                if method != "PUT":
                    return self._json_response(405, {"error": "Only PUT is supported for this route."})
                self._require_admin(user_session_key)
                body = self._json_body(payload)
                result = self.data_source_service.update_default_interval(
                    body.get("default_collection_interval_s"),
                    get_system_token(payload),
                )
                return self._json_response(
                    200,
                    {
                        "status": "updated" if result.changed else "unchanged",
                        "default_collection_interval_s": result.default_collection_interval_s,
                    },
                )

            data_source_id = self._data_source_route_id(route)
            if data_source_id is not None:
                check_capability(user_session_key, "ni_config_manage", route)
                if method != "PUT":
                    return self._json_response(405, {"error": "Only PUT is supported for this route."})
                self._require_admin(user_session_key)
                body = self._json_body(payload)
                result = self.data_source_service.update_source(
                    data_source_id,
                    get_system_token(payload),
                    indexes=body.get("indexes", UNSET),
                    collection_interval_s=body.get("collection_interval_s", UNSET),
                    enabled=body.get("enabled", UNSET),
                )
                return self._json_response(200, self._data_source_mutation_response(result))

            binding_id = self._binding_route_id(route)
            if binding_id is not None:
                check_capability(user_session_key, "ni_config_manage", route)
                if method == "PUT":
                    self._require_admin(user_session_key)
                    result = self.binding_service.update(
                        binding_id,
                        self._binding_body(payload),
                        get_system_token(payload),
                    )
                    return self._mutation_response(200, result)
                return self._json_response(405, {"error": "Only PUT is supported for this route."})

            return self._json_response(404, {"error": f"Unknown route: {route or '/'}"})
        except SystemTokenUnavailable as error:
            return self._json_response(
                503, {"error": {"code": "system_auth_unavailable", "message": str(error)}}
            )
        except PermissionError as error:
            return self._json_response(403, {"error": str(error)})
        except UnsupportedFilterError as error:
            return self._alert_error_response(400, "unsupported_filter", error)
        except AlertValidationError as error:
            return self._alert_error_response(400, "validation_error", error)
        except SnapshotExpired as error:
            return self._alert_error_response(410, "snapshot_expired", error)
        except SearchUnavailable as error:
            return self._alert_error_response(503, "search_unavailable", error)
        except GraphItemNotFoundError as error:
            return self._json_response(404, {"error": str(error)})
        except DataSourceNotFoundError as error:
            return self._json_response(404, {"error": str(error)})
        except DataSourceValidationError as error:
            return self._json_response(400, {"error": str(error)})
        except TransactionRollbackError as error:
            logger.exception("Data source transaction rollback failed: %s", error)
            return self._json_response(
                500,
                {
                    "error": {
                        "code": "data_source_transaction_failed",
                        "message": str(error),
                    }
                },
            )
        except BindingConflictError as error:
            return self._json_response(409, {"error": str(error)})
        except BindingNotFoundError as error:
            return self._json_response(404, {"error": str(error)})
        except CompilerError as error:
            return self._json_response(400, {"error": str(error), "diagnostics": [error.to_diagnostic()]})
        except CapabilityValidationError as error:
            return self._json_response(
                400,
                {
                    "error": str(error),
                    "diagnostics": [
                        {
                            "stage": "validation",
                            "error_code": "invalid_binding",
                            "message": str(error),
                        }
                    ],
                },
            )
        except BindingPersistenceError as error:
            logger.exception("Binding persistence failed: %s", error)
            return self._json_response(
                500,
                {
                    "error": str(error),
                    "diagnostics": [
                        {
                            "stage": "persistence",
                            "error_code": "binding_persistence_failed",
                            "message": str(error),
                        }
                    ],
                },
            )
        except HealthMetricsReadError:
            logger.exception("Health metrics read failed")
            return self._json_response(500, {"error": "Unable to read health metrics."})
        except (HealthStateReadError, KvStoreError):
            logger.exception("Health state read failed")
            return self._json_response(500, {"error": "Unable to read health state."})
        except ValueError as error:
            return self._json_response(400, {"error": str(error)})
        except Exception as error:
            logger.exception("Unhandled error in REST handler: %s", error)
            return self._json_response(500, {"error": "Internal server error."})

    @classmethod
    def _mutation_response(cls, status: int, result) -> dict:
        binding = result.binding
        artifact = result.artifact
        return cls._json_response(
            status,
            {
                "status": result.operation if result.changed else "unchanged",
                "binding_id": binding.binding_id,
                "capability_id": binding.capability_id,
                "validation_state": "valid",
                "lifecycle": "active" if binding.is_active else "disabled",
                "compiled_search_name": artifact.name,
                "updated_ts": result.updated_ts,
                "diagnostics": [],
            },
        )

    @staticmethod
    def _json_response(
        status: int, payload: dict, content_type: str = "application/json"
    ) -> dict:
        return {
            "status": int(status),
            "headers": {"Content-Type": content_type},
            "payload": json.dumps(payload),
        }

    @classmethod
    def _alert_error_response(cls, status: int, code: str, error: Exception) -> dict:
        details = {}
        field = getattr(error, "field", None)
        if field:
            details["field"] = field
        return cls._json_response(
            status, {"error": {"code": code, "message": str(error), "details": details}}
        )

    @staticmethod
    def _require_admin(user_session_key: str) -> None:
        identity = resolve_identity(user_session_key)
        if identity is None or not identity.is_admin():
            raise PermissionError("Admin role required.")

    @staticmethod
    def _caller_user(payload: dict) -> str:
        session = payload.get("session", {})
        user = session.get("user")
        if user:
            return str(user)
        identity = resolve_identity(session.get("authtoken"))
        if identity is None:
            raise ValueError("Missing caller identity on session.")
        return identity.username

    @staticmethod
    def _route(payload: dict) -> str:
        path_info = payload.get("path_info")
        if isinstance(path_info, bytes):
            path_info = path_info.decode("utf-8")
        if path_info:
            return str(path_info).strip().strip("/")

        path = payload.get("path")
        if isinstance(path, bytes):
            path = path.decode("utf-8")
        if path:
            marker = "/api/v1"
            path = str(path)
            if marker in path:
                return path.split(marker, 1)[1].strip().strip("/")
            return path.strip().strip("/")

        return ""

    @staticmethod
    def _binding_route_id(route: str) -> str | None:
        parts = route.split("/")
        if len(parts) == 3 and parts[:2] == ["health", "bindings"]:
            return parts[2] or None
        return None

    @staticmethod
    def _data_source_route_id(route: str) -> str | None:
        parts = route.split("/")
        if len(parts) == 3 and parts[:2] == ["settings", "data_sources"]:
            return parts[2] or None
        return None

    @staticmethod
    def _serialize_data_source(source: DataSource) -> dict:
        return {
            "source_system": source.source_system,
            "indexes": list(source.indexes),
            "collection_interval_s": source.collection_interval_s,
            "enabled": source.enabled,
        }

    @classmethod
    def _data_sources_response(cls, listing) -> dict:
        return {
            "default_collection_interval_s": listing.default_collection_interval_s,
            "data_sources": {
                source_system: cls._serialize_data_source(source)
                for source_system, source in listing.data_sources.items()
            },
        }

    @classmethod
    def _data_source_mutation_response(cls, result) -> dict:
        return {
            "status": "updated" if result.changed else "unchanged",
            "data_source": cls._serialize_data_source(result.source),
        }

    @staticmethod
    def _vertex_route_id(route: str) -> str | None:
        parts = route.split("/")
        if len(parts) == 3 and parts[:2] == ["graph", "vertices"]:
            return parts[2] or None
        return None

    @staticmethod
    def _edge_route_id(route: str) -> str | None:
        parts = route.split("/")
        if len(parts) == 3 and parts[:2] == ["graph", "edges"]:
            return parts[2] or None
        return None

    @staticmethod
    def _json_body(payload: dict) -> dict:
        body = payload.get("payload", payload.get("body", {}))
        if body in (None, ""):
            raise ValueError("Request body is required.")
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        if isinstance(body, str):
            body = json.loads(body)
        if not isinstance(body, dict):
            raise ValueError("Request body must be a JSON object.")
        return body

    @classmethod
    def _binding_body(cls, payload: dict) -> dict:
        body = cls._json_body(payload)
        binding = body.get("binding", body)
        if not isinstance(binding, dict):
            raise ValueError("Request body must contain a binding object.")
        return binding

    @staticmethod
    def _params(payload: dict, *, include_framework: bool = False) -> dict:
        params = {}

        query = payload.get("query", {})
        if isinstance(query, dict):
            for key, value in query.items():
                NetworkIntelligenceRestHandler._append_param_value(params, key, value)
        elif isinstance(query, (list, tuple)):
            for item in query:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    key, value = item
                    NetworkIntelligenceRestHandler._append_param_value(params, key, value)
                elif isinstance(item, dict):
                    key = item.get("name") or item.get("key")
                    value = item.get("value")
                    if key is not None:
                        NetworkIntelligenceRestHandler._append_param_value(params, key, value)
        elif isinstance(query, str) and query:
            params.update(parse_qs(query, keep_blank_values=True))

        form = payload.get("form", {})
        if isinstance(form, dict):
            params.update(form)

        if include_framework:
            return params
        return {key: value for key, value in params.items() if key not in _FRAMEWORK_QUERY_KEYS}

    @staticmethod
    def _append_param_value(params: dict, key, value) -> None:
        key = str(key)
        is_list_input = isinstance(value, list)
        if is_list_input:
            values = [str(item) for item in value]
        elif value is None:
            values = [""]
        else:
            values = [str(value)]

        existing = params.get(key)
        if existing is None:
            params[key] = values if (is_list_input or len(values) > 1) else values[0]
            return

        if not isinstance(existing, list):
            existing = [existing]
        existing.extend(values)
        params[key] = existing

    @staticmethod
    def _list_param(params: dict, key: str) -> list[str]:
        value = params.get(key, [])
        if isinstance(value, list):
            return [str(item) for item in value if str(item)]
        if value in (None, ""):
            return []
        return [str(value)]

    @classmethod
    def _bool_param(cls, params: dict, key: str) -> bool:
        values = cls._list_param(params, key)
        if not values:
            return False
        return values[0].strip().lower() in {"1", "true", "yes", "y", "on"}
