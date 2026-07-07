#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_configuration.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Built-in libraries
import json
import os
import sys
import re
from collections import OrderedDict

# Third-party libraries
import requests

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.configuration", "trackme_rest_api_configuration.log"
)


# import test handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    TrackMeRemoteConnectionError,
    run_splunk_search,
    trackme_get_emails_account,
    trackme_get_report,
    trackme_get_remote_account,
    trackme_get_server_time_info,
    trackme_get_version,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_reqinfo,
    trackme_test_remote_account,
    trackme_test_remote_connectivity,
)

# import trackme libs schema
from trackme_libs_schema import trackme_schema_format_version

# canonical access-control gate (role check + username allowlist)
from trackme_libs_load import has_user_access as _lib_has_user_access

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerConfigurationRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerConfigurationRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_configuration(self, request_info, **kwargs):
        response = {
            "resource_group_name": "configuration",
            "resource_group_desc": "These endpoints provide various application-level configuration capabilities. They are used internally by the user interface and can be customized according to your needs.",
        }

        return {"payload": response, "status": 200}

    # Return current Splunk server time. Simple by design — it just wraps
    # trackme_get_server_time_info() (which is datetime.now().astimezone()).
    # The *correctness* of the returned TZ comes from **how** this endpoint
    # is invoked: get_request_info() below calls back into here over the
    # splunkd REST API authenticated with the system authtoken, so the
    # helper runs in a system-user context where the TZ env var is not
    # polluted by the HTTP caller's user-prefs.conf preference. See the
    # doc comment in get_request_info() for the full rationale.
    def get_server_time(self, request_info, **kwargs):
        """
        | trackme mode=get url=\"/services/trackme/v2/configuration/server_time\"
        """

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "This endpoint returns the current Splunk server local time "
                    "from the perspective of the authenticated user's Python "
                    "context. It is intended to be called internally by "
                    "/configuration/request_info using a system authtoken so the "
                    "returned timezone reflects splunkd's system frame (matching "
                    "the decision maker) rather than the HTTP caller's user-prefs "
                    "TZ. Calling it directly with a personal token is valid but "
                    "will return the caller's own TZ."
                ),
                "resource_desc": "Return current Splunk server local time",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/configuration/server_time"',
            }
            return {"payload": response, "status": 200}

        try:
            server_time = trackme_get_server_time_info(source_tag="system_authed_call")
        except Exception as e:
            logger.warning(
                f"get_server_time: failed to resolve server_time info, err={e}"
            )
            return {"payload": {"error": str(e)}, "status": 500}

        return {"payload": server_time, "status": 200}

    # Return request info
    def get_request_info(self, request_info, **kwargs):
        """
        | trackme mode=get url=\"/services/trackme/v2/configuration/request_info\"
        """

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)


        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": (
                    "This endpoint returns request information such as splunkd_uri and "
                    "other useful technical details. It also exposes a `python_info` "
                    "object describing the interpreter's Python version (version, "
                    "version_major/minor/micro, min_version_for_ai, meets_ai_requirement) "
                    "which the UI uses to gate the AI Advisor tabs (the Agent SDK "
                    "requires Python 3.13+). It requires a GET call with no options."
                ),
                "resource_desc": "Return request information",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/configuration/request_info"',
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # conf
        conf_file = "trackme_settings"
        confs = service.confs[str(conf_file)]

        # Initialize the trackme_conf dictionary
        trackme_conf = {}

        # TrackMe version
        trackme_version = trackme_get_version(service)

        # Get schema_version_required
        schema_version_required = trackme_schema_format_version(trackme_version)

        # Get conf
        for stanza in confs:
            logger.debug(f'get_trackme_conf, Processing stanza.name="{stanza.name}"')

            # Create a sub-dictionary for the current stanza name if it doesn't exist
            if stanza.name not in trackme_conf:
                trackme_conf[stanza.name] = {}

            # Store key-value pairs from the stanza content in the corresponding sub-dictionary
            for stanzakey, stanzavalue in stanza.content.items():
                logger.debug(
                    f'get_trackme_conf, Processing stanzakey="{stanzakey}", stanzavalue="{stanzavalue}"'
                )
                if stanzavalue:
                    trackme_conf[stanza.name][stanzakey] = stanzavalue
                else:
                    trackme_conf[stanza.name][stanzakey] = ""


        # set logger.level
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Splunk server current local time — this is the reference frame the
        # TrackMe decision maker uses when evaluating variable delay / variable
        # threshold slots. Calling trackme_get_server_time_info() directly
        # from *this* handler is wrong: Splunk has propagated the HTTP caller's
        # user-prefs.conf `tz` into the REST handler's Python process as the
        # TZ env var, so datetime.now().astimezone() returns the caller's
        # preferred TZ (e.g. BST for a GB user) instead of splunkd's system
        # TZ (e.g. UTC).
        #
        # To get the system frame, we make an internal REST call back into
        # our own /configuration/server_time endpoint, using the `service`
        # that was connected with owner="nobody" and token=system_authtoken.
        # splunkd routes that request in a system-user context, so the
        # helper runs against an unpolluted TZ. We tag the result with
        # source="system_authed_call" so the frontend / support can confirm
        # which path was taken.
        #
        # Fallback: if the internal REST call fails (splunkd overloaded,
        # local network flake, route not registered), we call the helper
        # directly and tag source="direct_fallback" so the UI can surface
        # the degradation. The banner still renders, just with the caller's
        # possibly-wrong TZ.
        server_time = None
        try:
            raw = service.get(
                "/services/trackme/v2/configuration/server_time",
                output_mode="json",
            )
            body = raw.body.read()
            if isinstance(body, bytes):
                body = body.decode("utf-8", errors="replace")
            parsed = json.loads(body) if body else None
            if isinstance(parsed, dict):
                # The persistent handler wraps responses as { payload, status }.
                # splunklib may also surface the payload at the top level for
                # some response shapes — tolerate both.
                candidate = parsed.get("payload") if isinstance(parsed.get("payload"), dict) else None
                if candidate is None and "epoch" in parsed:
                    candidate = parsed
                if candidate and isinstance(candidate.get("epoch"), (int, float)):
                    server_time = candidate
            if server_time is None:
                logger.warning(
                    "get_request_info: system-authed /configuration/server_time "
                    "returned an unexpected payload shape; falling back to direct helper"
                )
        except Exception as e:
            logger.warning(
                f"get_request_info: system-authed /configuration/server_time call failed "
                f"({e}); falling back to direct helper (server_time.source will reflect this)"
            )

        if server_time is None:
            try:
                server_time = trackme_get_server_time_info(source_tag="direct_fallback")
            except Exception as e:
                logger.warning(
                    f"get_request_info: failed to resolve server_time info even via "
                    f"direct fallback, UI will hide the banner. err={e}"
                )
                server_time = None

        # Python version info — the AI Advisor features require Python 3.13+
        # (hard dependency of splunklib.ai / the Splunk Agent SDK).  Expose
        # the runtime interpreter version + a precomputed boolean so the UI
        # can gate the AI Advisor tabs without re-implementing the check.
        # All fields are grouped under `python_info` for a clean, namespaced
        # payload — consumers read `python_info.meets_ai_requirement` rather
        # than sprinkling `python_*` keys at the record root.
        _AI_MIN_PYTHON_VERSION = (3, 13)
        _py = sys.version_info
        python_info = {
            "version": f"{_py.major}.{_py.minor}.{_py.micro}",
            "version_major": _py.major,
            "version_minor": _py.minor,
            "version_micro": _py.micro,
            "min_version_for_ai": f"{_AI_MIN_PYTHON_VERSION[0]}.{_AI_MIN_PYTHON_VERSION[1]}",
            "meets_ai_requirement": (_py.major, _py.minor) >= _AI_MIN_PYTHON_VERSION,
        }

        # gen record
        record = {
            "user": request_info.user,
            "server_rest_uri": request_info.server_rest_uri,
            "server_rest_host": request_info.server_rest_host,
            "server_rest_port": request_info.server_rest_port,
            "server_hostname": request_info.server_hostname,
            "server_servername": request_info.server_servername,
            "connection_src_ip": request_info.connection_src_ip,
            "connection_listening_port": request_info.connection_listening_port,
            "logging_level": trackme_conf["logging"]["loglevel"],
            "trackme_version": trackme_version,
            "schema_version_required": schema_version_required,
            "trackme_conf": trackme_conf,
            "server_time": server_time,
            "python_info": python_info,
        }

        return {"payload": record, "status": 200}

    # Return the full TrackMe REST API catalog as JSON. Same data the
    # ``trackmeapiautodocs`` custom search command emits as SPL rows,
    # but exposed as a single REST round-trip so the Concierge Advisor's
    # ``discover_endpoints`` MCP tool (and any other programmatic
    # consumer, e.g. the REST API Reference UI's drill-in flow) can
    # fetch the catalog without spawning a search.
    #
    # Both this endpoint and the search command call into the same
    # ``trackme_libs_autodocs_catalog_builder.build_catalog`` library
    # function, so the output is guaranteed to match.
    def get_api_catalog(self, request_info, **kwargs):
        """
        | trackme mode=get url=\"/services/trackme/v2/configuration/api_catalog\"
        """

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "Return the full TrackMe REST API catalog as JSON — every "
                    "registered handler and its endpoints, with each endpoint's "
                    "self-documentation block (``describe=true`` output) inlined. "
                    "Same data the ``| trackmeapiautodocs`` search command emits "
                    "as SPL rows, but in a single JSON response. Used by the "
                    "Concierge Advisor's ``discover_endpoints`` tool to navigate "
                    "the API by user intent. ``target=groups`` returns the "
                    "resource-group description rows; ``target=endpoints`` "
                    "(default) returns the full per-endpoint detail. The "
                    "catalog is cached on the filesystem keyed by app version "
                    "— first call after an app deploy rebuilds (~19s); "
                    "subsequent calls serve from cache (sub-second). Pass "
                    "``force_rebuild=true`` to bypass the cache."
                ),
                "resource_desc": "Return the full TrackMe REST API catalog as JSON",
                "resource_spl_example": (
                    '| trackme mode=get '
                    'url="/services/trackme/v2/configuration/api_catalog" '
                    'body="{\'target\': \'endpoints\'}"'
                ),
                "options": [
                    {
                        "target": (
                            "Optional. ``\"endpoints\"`` (default) for full "
                            "per-endpoint documentation; ``\"groups\"`` for "
                            "resource-group description rows only."
                        ),
                        "force_rebuild": (
                            "Optional. ``true`` to bypass the filesystem "
                            "cache and rebuild from live handlers. Default "
                            "``false`` (serve cached when available)."
                        ),
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Parse optional ``target`` from EITHER the JSON body OR a URL
        # query parameter. Two transports for two consumers:
        #
        #   - ``| trackme mode=get url="..." body="{...}"`` (SPL helper)
        #     and the Concierge describe payload's loopback caller pass
        #     params as a JSON body — splunkd surfaces that under
        #     ``request_info.raw_args["payload"]``.
        #
        #   - The browser-side REST API Reference UI (PR #1465 + #1470)
        #     uses ``fetch('?target=groups')`` — a regular GET with
        #     URL-encoded query parameters. GETs typically have no body,
        #     so the JSON parse below short-circuits to ``{}`` and
        #     ``target`` would silently default to ``"endpoints"``,
        #     making the second concurrent UI call return endpoints
        #     data instead of groups data — exactly the regression
        #     PR #1470 was meant to fix end-to-end (bugbot caught this
        #     on PR #1472, the version_2322 port — same gap exists on
        #     beta_ai_agent and is fixed here too).
        #
        # Splunk's persistent-handler framework dispatches handler
        # methods as ``method(request_info, **query)`` where ``query``
        # is a dict of URL query parameters. Our signature already
        # accepts ``**kwargs`` to receive that. Read body first
        # (richer; native JSON types) and fall back to ``kwargs`` for
        # the query-param path. Both consumers therefore work without
        # changing either caller.
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = {}
        if not isinstance(resp_dict, dict):
            resp_dict = {}

        # ``target``: prefer body, fall back to query param, default to
        # ``"endpoints"``. Query params arrive as strings, which is
        # fine here since ``target`` is naturally a string enum.
        target = resp_dict.get("target")
        if target is None:
            target = kwargs.get("target", "endpoints")
        if target not in ("endpoints", "groups"):
            return {
                "payload": {
                    "error": (
                        f"invalid target='{target}', valid values are: "
                        "'endpoints' (default) or 'groups'"
                    ),
                },
                "status": 400,
            }

        # Defer the heavy import — ``build_catalog`` pulls in every
        # REST handler at module-load time, which is fine when this
        # method runs but unnecessary work for endpoints that don't
        # need the catalog. Splunk loads each REST handler module
        # eagerly anyway, so this defer is a small constant-time win,
        # not a structural concern.
        try:
            from trackme_libs_autodocs_catalog_builder import (
                build_catalog_as_list_cached,
            )
        except Exception as exc:
            logger.error(
                f"get_api_catalog: failed to import catalog builder, err={exc}"
            )
            return {
                "payload": {
                    "error": f"catalog builder unavailable: {exc}",
                },
                "status": 500,
            }

        # Optional ``force_rebuild`` — bypass cache and rebuild even if
        # a hit exists. Lets operators / tests refresh the cache without
        # an app redeploy. Same dual-source parsing as ``target``: prefer
        # body, fall back to query param. Query params arrive as strings,
        # so ``"true"`` / ``"false"`` need explicit normalisation —
        # ``bool("false")`` is ``True`` (any non-empty string is truthy)
        # and that would silently force a rebuild on every UI request
        # carrying ``?force_rebuild=false``.
        force_rebuild_raw = resp_dict.get("force_rebuild")
        if force_rebuild_raw is None:
            force_rebuild_raw = kwargs.get("force_rebuild", False)
        if isinstance(force_rebuild_raw, bool):
            force_rebuild = force_rebuild_raw
        elif isinstance(force_rebuild_raw, str):
            force_rebuild = force_rebuild_raw.strip().lower() in ("true", "1", "yes")
        else:
            force_rebuild = bool(force_rebuild_raw)

        # Filesystem cache keyed by app version. Cache hit = sub-second;
        # cache miss = ~19s build (+ write). The cache invalidates
        # automatically on the next app deploy because ``version.json``
        # is the cache key. See ``trackme_libs_autodocs_catalog_builder``
        # for the cache implementation rationale (RBAC trade-off, atomic
        # writes, fail-open on infrastructure failure).
        try:
            catalog = build_catalog_as_list_cached(
                splunkd_uri=request_info.server_rest_uri,
                session_key=request_info.session_key,
                target=target,
                force_rebuild=force_rebuild,
            )
        except Exception as exc:
            logger.error(
                f"get_api_catalog: build_catalog failed, target={target!r}, err={exc}"
            )
            return {
                "payload": {
                    "error": f"failed to build catalog: {exc}",
                },
                "status": 500,
            }

        # Surface basic counters alongside the entries — useful for
        # operator debugging ("did the build succeed at all?") and for
        # the agent's tool wrapper (and any other programmatic caller)
        # to validate the response shape.
        ok_count = sum(1 for entry in catalog if "error" not in entry)
        err_count = len(catalog) - ok_count

        return {
            "payload": {
                "target": target,
                "entries_count": len(catalog),
                "ok_count": ok_count,
                "error_count": err_count,
                "entries": catalog,
            },
            "status": 200,
        }

    # This endpoint verifies the level of privileges of the user currently connected
    def get_trackme_check_privileges_level(self, request_info, **kwargs):
        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)


        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint verifies the privilege level of the currently connected user. It requires a GET call with no options.",
                "resource_desc": "Check current user's privilege level",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/configuration/trackme_check_privileges_level"',
            }

            return {"payload": response, "status": 200}

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % request_info.session_key,
            "Content-Type": "application/json",
        }

        # final_response
        final_response = {}

        # TrackMe reqinfo
        reqinfo_trackme = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        trackmeconf = reqinfo_trackme["trackme_conf"]
        logger.debug(f'trackmeconf="{json.dumps(trackmeconf, indent=2)}"')

        # init
        is_admin = False
        is_power = False

        # check allow_admin_ops

        # check admin
        record_url = "%s/services/trackme/v2/vtenants/admin/add_tenant" % (
            request_info.server_rest_uri
        )

        try:
            response = requests.post(
                record_url,
                headers=header,
                data=json.dumps({"describe": "True"}),
                verify=False,
                timeout=600,
            )
            if response.status_code == 200:
                is_admin = True
            else:
                is_admin = False
        except Exception as e:
            return {
                "payload": {
                    "response": "An exception was encountered",
                    "exception": str(e),
                },
                "status": 500,
            }

        # check power
        record_url = "%s/services/trackme/v2/ack/write/ack_manage" % (
            request_info.server_rest_uri
        )

        try:
            response = requests.post(
                record_url,
                headers=header,
                data=json.dumps({"describe": "True"}),
                verify=False,
                timeout=600,
            )
            if response.status_code == 200:
                is_power = True
            else:
                is_power = False
        except Exception as e:
            return {
                "payload": {
                    "response": "An exception was encountered",
                    "exception": str(e),
                },
                "status": 500,
            }

        # prepare the response
        final_response = {
            "username": request_info.user,
            "user_level": "admin",
        }

        if is_admin:
            final_response["user_level"] = "admin"
        elif is_power:
            final_response["user_level"] = "power"
        else:
            final_response["user_level"] = "user"

        # add trackme_conf
        final_response["trackme_conf"] = trackmeconf

        # UI defaults configuration
        ui_defaults_conf = trackmeconf.get("trackme_ui_defaults", {})
        ui_default_theme = ui_defaults_conf.get("default_theme", "dark")
        ui_auto_refresh = ui_defaults_conf.get("auto_refresh", "1")
        ui_auto_refresh_interval_seconds = ui_defaults_conf.get("auto_refresh_interval_seconds", "15")
        ui_vtenants_card_detail_level = ui_defaults_conf.get("vtenants_card_detail_level", "0")
        ui_shadow_page_size = ui_defaults_conf.get("shadow_page_size", "25000")

        # AI assistant configuration
        general_conf = trackmeconf.get("trackme_general", {})
        enable_ai_assistant = general_conf.get("enable_ai_assistant", "1")

        # Add ui_default_theme to response (system-level setting)
        user_prefs_dict = {
            "ui_default_theme": ui_default_theme,
            "ui_auto_refresh": ui_auto_refresh,
            "ui_auto_refresh_interval_seconds": ui_auto_refresh_interval_seconds,
            "ui_vtenants_card_detail_level": ui_vtenants_card_detail_level,
            "ui_shadow_page_size": ui_shadow_page_size,
            "enable_ai_assistant": enable_ai_assistant,
        }

        # add user_prefs_dict to response
        final_response["user_prefs"] = user_prefs_dict

        # return
        return {"payload": final_response, "status": 200}

    # This endpoint verifies that the local instance meets TrackMe requirements
    def get_trackme_check_dependencies(self, request_info, **kwargs):
        """
        | trackme mode=get url=\"/services/trackme/v2/configuration/trackme_check_dependencies\"
        """

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)


        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint verifies that the local instance meets TrackMe dependencies requirements. It requires a GET call with no options.",
                "resource_desc": "Check TrackMe dependencies requirements",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/configuration/trackme_check_dependencies"',
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # TrackMe reqinfo
        trackmeconf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )

        # proceed
        try:
            apps = []
            for app in service.apps:
                apps.append(app.name)

            missing_apps = []
            checked_apps = []

            app_check = "Splunk_ML_Toolkit"
            if not app_check in apps:
                missing_apps.append(
                    {
                        "application_name": app_check,
                        "splunkbase_link": "https://splunkbase.splunk.com/app/2890",
                    }
                )
            else:
                checked_apps.append(app_check)

            # Then, within your try block where you check for apps, add the following:
            app_prefix = "Splunk_SA_Scientific_Python_"
            # This will create a pattern that matches any app name starting with the app_prefix
            pattern = re.compile(re.escape(app_prefix) + r".*")
            scientific_python_app_found = any(
                pattern.match(app.name) for app in service.apps
            )

            if not scientific_python_app_found:
                missing_apps.append(
                    {
                        "application_name": "Splunk_SA_Scientific_Python_<architecture>",
                        "splunkbase_link": "https://splunkbase.splunk.com/app/2882",
                    }
                )
            else:
                checked_apps.append("Splunk_SA_Scientific_Python_<architecture>")

            if len(missing_apps) > 0:
                response = {
                    "action": "failure",
                    "response": "Applications dependencies requirements are not met",
                    "missing_apps": missing_apps,
                }
                logger.error(json.dumps(response, indent=2))
                return {"payload": response, "status": 200}

            else:
                response = {
                    "action": "success",
                    "response": "All applications dependencies are met",
                    "checked_apps": checked_apps,
                    "trackme_conf": trackmeconf,
                }
                logger.debug(json.dumps(response, indent=2))
                return {"payload": response, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": "An exception was encountered",
                "exception": str(e),
            }
            logger.error(json.dumps(response, indent=2))
            return {"payload": response, "status": 500}

    # Retrieve tenants according to RBAC
    def get_vtenants_all(self, request_info, **kwargs):
        """
        | trackme mode=get url=\"/services/trackme/v2/configuration/vtenants_all\"
        """

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)


        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves all the tenants the user profiles allows access to, it requires a GET call with no options",
                "resource_desc": "Get the list of TrackMe tenants according to RBAC policies for the user currently connected",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/configuration/vtenants_all"',
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # get current user
        username = request_info.user

        # get user info
        users = service.users

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Get roles for the current user
        username_roles = []
        for user in users:
            if user.name == username:
                username_roles = user.roles
        logger.info(f'username="{username}", roles="{username_roles}"')

        # Compute effective roles (direct + inherited via Splunk role
        # imports).  Without this, a user whose tenant access comes from
        # an INHERITED role would see the tenant via trackmeload /
        # trackmetenantstatus / describe_vtenants but be denied here —
        # all four call sites of ``_lib_has_user_access`` must reason
        # over the same role set or the access decisions diverge.
        # Bugbot caught the inconsistency on PR #1528 cycle 1 (Medium):
        # ``post_vtenants_all`` was passing ``set(username_roles)`` (direct
        # roles only) while every other caller passes ``effective_roles``
        # from ``get_effective_roles()``.  The same bug is on
        # ``version_2322`` (where PR #1524 introduced the refactor) — a
        # follow-up PR will port this fix back so future syncs stay
        # clean.  Implementation mirrors ``trackmetenantstatus.py``'s
        # ``get_effective_roles`` exactly (depth-first walk over
        # ``imported_roles``, idempotent) so the two paths stay in
        # lockstep semantically.
        roles_dict = {}
        try:
            for role in service.roles:
                imported = role.content.get("imported_roles", [])
                if imported:
                    roles_dict[role.name] = imported
        except Exception as e:
            logger.warning(
                f'unable to load role inheritance map for effective-roles '
                f'computation, exception="{str(e)}" — falling back to '
                f'direct roles only (inherited-role users may be denied '
                f'access until the role lookup recovers)'
            )
        effective_roles = set(username_roles)
        to_check = list(username_roles)
        while to_check:
            current_role = to_check.pop()
            for inherited_role in roles_dict.get(current_role, []):
                if inherited_role not in effective_roles:
                    effective_roles.add(inherited_role)
                    to_check.append(inherited_role)
        logger.info(
            f'username="{username}", direct_roles="{username_roles}", '
            f'effective_roles="{sorted(effective_roles)}"'
        )

        try:
            # Data collection
            collection_name = "kv_trackme_virtual_tenants"
            collection = service.kvstore[collection_name]

            records = collection.data.query()
            filtered_records = []

            # Pre-load per-tenant `tenant_allowed_users` from the trackme_vtenants
            # conf so the username allowlist can be enforced alongside the role
            # check. Failure here is non-fatal (fall back to "no allowlist").
            vtenant_allowed_users_map = {}
            try:
                vtenants_conf = service.confs["trackme_vtenants"]
                for stanza in vtenants_conf:
                    vtenant_allowed_users_map[stanza.name] = stanza.content.get(
                        "tenant_allowed_users", ""
                    )
            except Exception as e:
                logger.warning(
                    f'unable to load trackme_vtenants conf for username allowlist, exception="{str(e)}"'
                )

            for record in records:
                logger.info(
                    f'tenant_id="{record["tenant_id"]}", tenant_roles_admin="{record["tenant_roles_admin"]}", tenant_roles_power="{record["tenant_roles_power"]}", tenant_roles_user="{record["tenant_roles_user"]}"'
                )

                # log
                logger.info(
                    f'checking permissions of user="{username}" with effective_roles="{sorted(effective_roles)}" for tenant_id="{record["tenant_id"]}"'
                )

                # Carry the per-tenant username allowlist onto the record so
                # the canonical lib gate sees it (trackmeload uses the same
                # convention via vtenants_account, this handler reads it
                # directly from the conf into vtenant_allowed_users_map).
                record["tenant_allowed_users"] = vtenant_allowed_users_map.get(
                    record["tenant_id"], ""
                )

                # Single source of truth for the access decision: role check +
                # optional username allowlist. splunk-system-user always
                # bypasses (matches trackmeload — internal callers must keep
                # working on restricted tenants). ``effective_roles``
                # includes inherited roles so the decision is consistent
                # with the other three call sites of ``_lib_has_user_access``.
                if username == "splunk-system-user" or _lib_has_user_access(
                    effective_roles, record, username
                ):
                    filtered_records.append(record)

            return {"payload": filtered_records, "status": 200}

        except Exception as e:
            logger.error(f'Warn: exception encountered="{str(e)}"')
            return {"payload": f'Warn: exception encountered="{str(e)}"'}

    # Retrieve tenants RBAC configuration
    def post_show_vtenants_rbac(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/configuration/show_vtenants_rbac\" body=\"{'tenant_id': 'mytenant'}\"
        """

        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint shows the Virtual Tenants and their RBAC current configuration, it requires a POST call with the following options",
                "resource_desc": "Shows Virtual Tenants RBAC current configuration",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/configuration/show_vtenants_rbac\" body=\"{'tenant_id': 'mytenant'}\"",
                "options": [
                    {
                        "tenant_id": "tenant identifier, use a wildcard to get RBAC configuration for all existing tenants",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            # Data collection
            collection_name = "kv_trackme_virtual_tenants"
            collection = service.kvstore[collection_name]

            # Define the KV query
            if tenant_id != "*":
                query_string = {
                    "tenant_id": tenant_id,
                }
            else:
                query_string = {}

            records = collection.data.query(query=json.dumps(query_string))
            filtered_records = []

            for record in records:
                logger.info(
                    f'tenant_id="{record["tenant_id"]}", tenant_owner="{record["tenant_owner"]}", tenant_roles_admin="{record["tenant_roles_admin"]}", tenant_roles_user="{record["tenant_roles_user"]}"'
                )

                # get, turn into a list and sort
                tenant_roles_admin_orig = record["tenant_roles_admin"].split(",")
                tenant_roles_admin = sorted(tenant_roles_admin_orig)

                # get, turn into a list and sort
                tenant_roles_power_orig = record["tenant_roles_power"].split(",")
                tenant_roles_power = sorted(tenant_roles_power_orig)

                # get, turn into a list and sort
                tenant_roles_user_orig = record["tenant_roles_user"].split(",")
                tenant_roles_user = sorted(tenant_roles_user_orig)

                filtered_records.append(
                    {
                        "tenant_id": record["tenant_id"],
                        "tenant_owner": record["tenant_owner"],
                        "tenant_roles_admin": tenant_roles_admin,
                        "tenant_roles_power": tenant_roles_power,
                        "tenant_roles_user": tenant_roles_user,
                    }
                )

            return {"payload": filtered_records, "status": 200}

        except Exception as e:
            logger.error(f'Warn: exception encountered="{str(e)}"')
            return {"payload": f'Warn: exception encountered="{str(e)}"'}

    # List all accounts
    def get_list_accounts(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/configuration/list_accounts\"
        """

        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint lists all available accounts. It requires a GET call with no options.",
                "resource_desc": "Lists all configured accounts",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/configuration/list_accounts"',
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # get all accounts
        accounts = ["local"]
        try:
            conf_file = "trackme_account"
            confs = service.confs[str(conf_file)]
            for stanza in confs:
                # get all accounts
                for name in stanza.name:
                    accounts.append(stanza.name)
                    break
        except Exception as e:
            accounts = ["local"]

        return {"payload": {"accounts": accounts}, "status": 200}

    # List local users with a least privileges approach
    def get_list_local_users(self, request_info, **kwargs):
        """
        | trackme mode=get url=\"/services/trackme/v2/configuration/list_local_users\"
        """

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)


        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves local Splunk users with a least privileges approach, it requires a GET call with no options",
                "resource_desc": "List local Splunk users",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/configuration/list_local_users"',
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # get user info
        users = service.users

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # TrackMe reqinfo
        trackmeconf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        trackme_owner_default = trackmeconf["trackme_conf"]["trackme_general"][
            "trackme_owner_default"
        ]

        # users_lister
        users_list = []
        users_list.append(trackme_owner_default)
        for user in users:
            if user.name not in users_list:
                users_list.append(user.name)

        return {"payload": {"users": users_list}, "status": 200}

    # Test remote account connectivity
    def post_test_remote_account(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/configuration/test_remote_account\" body=\"{'account': 'lab'}\"
        """

        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                account = resp_dict["account"]
        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint performs a connectivity check for a Splunk remote account. It requires a POST call with the following options:",
                "resource_desc": "Run connectivity checks for a Splunk remote account. This validates the configuration, network connectivity and authentication.",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/configuration/test_remote_account\" body=\"{'account': 'lab'}\"",
                "options": [
                    {
                        "account": "The account configuration identifier",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # get all accounts
        try:
            accounts = []
            conf_file = "trackme_account"
            confs = service.confs[str(conf_file)]
            for stanza in confs:
                # get all accounts
                for name in stanza.name:
                    accounts.append(stanza.name)
                    break

        except Exception as e:
            error_msg = "There are no remote Splunk account configured yet"
            return {
                "payload": {
                    "status": "failure",
                    "message": error_msg,
                    "account": account,
                },
                "status": 500,
            }

        else:
            try:
                response = trackme_test_remote_account(request_info, account)
                return {"payload": response, "status": 200}

            except TrackMeRemoteConnectionError as e:
                return {"payload": e.error_info, "status": 500}
            except Exception as e:
                return {"payload": str(e), "status": 500}

    # Test remote connectivity prior to the creation of a remote account
    def post_test_remote_connectivity(self, request_info, **kwargs):
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        # Check if describe is requested (this doesn't require the full body)
        if resp_dict is not None:
            try:
                describe_value = resp_dict.get("describe")
                if describe_value in ("true", "True"):
                    describe = True
                else:
                    describe = False
            except Exception as e:
                describe = False
        else:
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint performs a connectivity check for Splunk remote search capabilities prior to the formal creation of a remote account. It requires a POST call with the following options:",
                "resource_desc": "Run connectivity checks for remote search capabilities prior to the creation of an account. This validates the configuration, network connectivity and authentication.",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/configuration/test_remote_connectivity\" body=\"{'target_endpoints': 'https://myendpoint1:8089,https://myendpoint2:8089,https://myendpoint3:8089', 'bearer_token': 'xxx', 'app_namespace': 'search'}\"",
                "options": [
                    {
                        "target_endpoints": "One or more splunkd API endpoints in the form: https://<url>:<port>",
                        "app_namespace": "The remote application namespace. If not provided, defaults to search",
                        "bearer_token": "The Splunk bearer token to be used",
                        "timeout_connect_check": "Optional: The timeout in seconds for the connect health check. Defaults to 15 seconds (integer)",
                        "timeout_search_check": "Optional: The timeout in seconds for the search connection. Defaults to 300 seconds (integer)",
                        "retry_enabled": "Optional: Enable retry with backoff (1 or 0). Defaults to 1 (enabled)",
                        "retry_max_total_time": "Optional: Maximum total time in seconds to spend retrying. Defaults to 30 seconds (integer)",
                        "retry_initial_delay": "Optional: Initial delay in seconds before first retry. Defaults to 2 seconds (integer)",
                        "retry_backoff_multiplier": "Optional: Multiplier for exponential backoff. Defaults to 2.0 (float)",
                        "retry_max_attempts": "Optional: Maximum number of retry attempts. Defaults to 10 (integer)",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Validate that required parameters are provided (only needed if not describing)
        if resp_dict is None:
            return {
                "payload": {
                    "action": "failure",
                    "response": "Request body is required. Must include 'target_endpoints' and 'bearer_token' at minimum.",
                },
                "status": 400,
            }

        # Verify required fields exist before extracting variables
        if "target_endpoints" not in resp_dict or "bearer_token" not in resp_dict:
            return {
                "payload": {
                    "action": "failure",
                    "response": "Missing required fields: 'target_endpoints' and 'bearer_token' are required.",
                },
                "status": 400,
            }

        # Extract variables now that we've validated they exist
        target_endpoints = resp_dict["target_endpoints"]
        bearer_token = resp_dict["bearer_token"]
        app_namespace = resp_dict.get("app_namespace", "search")
        try:
            timeout_connect_check = int(
                resp_dict.get("timeout_connect_check", 15)
            )
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": "timeout_connect_check should be an integer",
                },
                "status": 500,
            }

        try:
            timeout_search_check = int(
                resp_dict.get("timeout_search_check", 300)
            )
        except Exception as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": "timeout_search_check should be an integer",
                },
                "status": 500,
            }

        # retry configuration (all optional)
        retry_enabled = resp_dict.get("retry_enabled", "1")
        retry_max_total_time = resp_dict.get("retry_max_total_time", "30")
        retry_initial_delay = resp_dict.get("retry_initial_delay", "2")
        retry_backoff_multiplier = resp_dict.get("retry_backoff_multiplier", "2.0")
        retry_max_attempts = resp_dict.get("retry_max_attempts", "10")

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            connection_info = {
                "target_endpoints": target_endpoints,
                "app_namespace": app_namespace,
                "bearer_token": bearer_token,
                "timeout_connect_check": timeout_connect_check,
                "timeout_search_check": timeout_search_check,
            }
            
            # Add retry configuration if provided
            if 'retry_enabled' in locals():
                connection_info["retry_enabled"] = retry_enabled
            if 'retry_max_total_time' in locals():
                connection_info["retry_max_total_time"] = retry_max_total_time
            if 'retry_initial_delay' in locals():
                connection_info["retry_initial_delay"] = retry_initial_delay
            if 'retry_backoff_multiplier' in locals():
                connection_info["retry_backoff_multiplier"] = retry_backoff_multiplier
            if 'retry_max_attempts' in locals():
                connection_info["retry_max_attempts"] = retry_max_attempts
            
            response = trackme_test_remote_connectivity(connection_info)
            return {"payload": response, "status": 200}

        # note: the exception is returned as a JSON object
        except Exception as e:
            return {"payload": str(e), "status": 500}

    # Get remote account credentials with a least privileges approach
    def post_get_remote_account(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/configuration/get_remote_account\" body=\"{'account': 'lab'}\"
        """

        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                account = resp_dict["account"]
        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint provides connection details for a Splunk remote account to be used in a programmatic manner with a least privileges approach, it requires a POST call with the following options:",
                "resource_desc": "Return a remote account credential details for programmatic access with a least privileges approach",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/configuration/get_remote_account\" body=\"{'account': 'lab'}\"",
                "options": [
                    {
                        "account": "The account configuration identifier",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # get all accounts
        try:
            accounts = []
            conf_file = "trackme_account"
            confs = service.confs[str(conf_file)]
            for stanza in confs:
                # get all accounts
                for name in stanza.name:
                    accounts.append(stanza.name)
                    break

        except Exception as e:
            error_msg = "There are no remote Splunk account configured yet"
            return {
                "payload": {
                    "status": "failure",
                    "message": error_msg,
                    "account": account,
                },
                "status": 500,
            }

        else:
            try:
                response = trackme_get_remote_account(request_info, account)
                return {"payload": response, "status": 200}

            # note: the exception is returned as a JSON object
            except Exception as e:
                return {"payload": str(e), "status": 500}

    # Get components
    def post_components(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/configuration/components\" body=\"{'tenant_id': 'mytenant'}\"
        """

        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves the components status for a specific tenant id, it requires a POST call with the following options:",
                "resource_desc": "Get the status of the TrackMe components for a given tenant",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/configuration/components\" body=\"{'tenant_id': 'mytenant'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # TrackMe reqinfo
        reqinfo_trackme = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        trackmeconf = reqinfo_trackme["trackme_conf"]

        # conf
        conf_file = "trackme_settings"
        confs = service.confs[str(conf_file)]

        # get vtenant account
        conf_file = "trackme_vtenants"

        # if there are no account, raise an exception, otherwise what we would do here?
        try:
            confs = service.confs[str(conf_file)]
        except Exception as e:
            error_msg = "there are no tenants configured yet"
            raise Exception(error_msg)

        # init
        trackme_vtenant_conf = {}
        trackme_vtenant_conf[tenant_id] = {}

        # get account
        for stanza in confs:
            if stanza.name == str(tenant_id):
                # Store key-value pairs from the stanza content in the corresponding sub-dictionary
                for stanzakey, stanzavalue in stanza.content.items():
                    logger.debug(
                        f'get virtual tenant account, Processing stanzakey="{stanzakey}", stanzavalue="{stanzavalue}"'
                    )
                    trackme_vtenant_conf[stanza.name][stanzakey] = stanzavalue

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # TrackMe version
        trackme_version = trackme_get_version(service)

        # Data collection
        collection_name = "kv_trackme_virtual_tenants"
        collection = service.kvstore[collection_name]

        # Define the KV query search string
        query_string = {
            "tenant_id": tenant_id,
        }

        # Get the record
        try:
            kvrecord = collection.data.query(query=json.dumps(query_string))[0]
            key = kvrecord.get("_key")

        except Exception as e:
            key = None

        # proceed
        if key:
            # debug
            logger.debug(
                f"tenant_id={tenant_id} record={json.dumps(kvrecord, indent=1)}"
            )

            # schema version: detect the current schema_version and if the upgrade is in progress
            schema_version_raw = kvrecord.get("schema_version")
            schema_version_required = trackme_schema_format_version(trackme_version)
            
            # If schema_version_required is 0 (version retrieval failed), treat as graceful degradation
            # and don't block operations - consistent with other handlers
            if schema_version_required == 0:
                schema_version = int(schema_version_raw) if schema_version_raw is not None else None
                schema_version_upgrade_in_progress = False
            elif schema_version_raw is None:
                # If schema_version is missing (e.g., tenant was created when version retrieval failed),
                # treat it as needing an upgrade
                schema_version = None
                schema_version_upgrade_in_progress = True
            else:
                schema_version = int(schema_version_raw)
                schema_version_upgrade_in_progress = False
                if not schema_version or schema_version < schema_version_required:
                    schema_version_upgrade_in_progress = True

            # retrieve the components configuration
            try:
                component_splk_dhm = int(kvrecord.get("tenant_dhm_enabled"))
            except Exception as e:
                component_splk_dhm = 0

            try:
                component_splk_dsm = int(kvrecord.get("tenant_dsm_enabled"))
            except Exception as e:
                component_splk_dsm = 0

            try:
                component_splk_mhm = int(kvrecord.get("tenant_mhm_enabled"))
            except Exception as e:
                component_splk_mhm = 0

            try:
                component_splk_flx = int(kvrecord.get("tenant_flx_enabled"))
            except Exception as e:
                component_splk_flx = 0

            try:
                component_splk_fqm = int(kvrecord.get("tenant_fqm_enabled"))
            except Exception as e:
                component_splk_fqm = 0

            try:
                component_splk_wlk = int(kvrecord.get("tenant_wlk_enabled"))
            except Exception as e:
                component_splk_wlk = 0

            try:
                ui_default_timerange = str(
                    trackme_vtenant_conf[tenant_id]["ui_default_timerange"]
                )
            except Exception as e:
                ui_default_timerange = "24h"

            try:
                ui_min_object_width = int(
                    trackme_vtenant_conf[tenant_id]["ui_min_object_width"]
                )
            except Exception as e:
                ui_min_object_width = 300

            try:
                ui_expand_metrics = int(
                    trackme_vtenant_conf[tenant_id]["ui_expand_metrics"]
                )
            except Exception as e:
                ui_expand_metrics = 0

            try:
                ui_home_tabs_order = str(
                    trackme_vtenant_conf[tenant_id]["ui_home_tabs_order"]
                )
            except Exception as e:
                ui_home_tabs_order = "dsm,flx,dhm,mhm,wlk,fqm,flip,audit,alerts"

            try:
                sampling = int(trackme_vtenant_conf[tenant_id]["sampling"])
            except Exception as e:
                sampling = 1

            try:
                mloutliers = int(trackme_vtenant_conf[tenant_id]["mloutliers"])
            except Exception as e:
                mloutliers = 1

            try:
                mloutliers_allowlist = str(
                    trackme_vtenant_conf[tenant_id]["mloutliers_allowlist"]
                )
            except Exception as e:
                mloutliers_allowlist = "dsm,dhm,flx,wlk,fqm"

            try:
                adaptive_delay = int(trackme_vtenant_conf[tenant_id]["adaptive_delay"])
            except Exception as e:
                adaptive_delay = 1

            try:
                indexed_constraint = str(
                    trackme_vtenant_conf[tenant_id]["indexed_constraint"]
                )
            except Exception as e:
                indexed_constraint = ""

            try:
                splk_feeds_delayed_inspector_24hours_range_min_sec = int(
                    trackme_vtenant_conf[tenant_id][
                        "splk_feeds_delayed_inspector_24hours_range_min_sec"
                    ]
                )
            except Exception as e:
                splk_feeds_delayed_inspector_24hours_range_min_sec = int(
                    trackmeconf["splk_general"][
                        "splk_general_feeds_delayed_inspector_24hours_range_min_sec"
                    ]
                )

            try:
                splk_feeds_delayed_inspector_7days_range_min_sec = int(
                    trackme_vtenant_conf[tenant_id][
                        "splk_feeds_delayed_inspector_7days_range_min_sec"
                    ]
                )
            except Exception as e:
                splk_feeds_delayed_inspector_7days_range_min_sec = int(
                    trackmeconf["splk_general"][
                        "splk_general_feeds_delayed_inspector_7days_range_min_sec"
                    ]
                )

            try:
                splk_feeds_delayed_inspector_until_disabled_range_min_sec = int(
                    trackme_vtenant_conf[tenant_id][
                        "splk_feeds_delayed_inspector_until_disabled_range_min_sec"
                    ]
                )
            except Exception as e:
                splk_feeds_delayed_inspector_until_disabled_range_min_sec = int(
                    trackmeconf["splk_general"][
                        "splk_general_feeds_delayed_inspector_until_disabled_range_min_sec"
                    ]
                )

            try:
                splk_feeds_delayed_inspector_max_backoff_multiplier = int(
                    trackme_vtenant_conf[tenant_id][
                        "splk_feeds_delayed_inspector_max_backoff_multiplier"
                    ]
                )
            except Exception as e:
                splk_feeds_delayed_inspector_max_backoff_multiplier = int(
                    trackmeconf["splk_general"][
                        "splk_general_feeds_delayed_inspector_max_backoff_multiplier"
                    ]
                )

            try:
                splk_feeds_auto_disablement_period = str(
                    trackme_vtenant_conf[tenant_id][
                        "splk_feeds_auto_disablement_period"
                    ]
                )
            except Exception as e:
                splk_feeds_auto_disablement_period = trackmeconf["splk_general"][
                    "splk_general_feeds_auto_disablement_period"
                ]

            try:
                cmdb_lookup = int(trackme_vtenant_conf[tenant_id]["cmdb_lookup"])
            except Exception as e:
                cmdb_lookup = 1

            try:
                data_sampling_obfuscation = int(
                    trackme_vtenant_conf[tenant_id]["data_sampling_obfuscation"]
                )
            except Exception as e:
                data_sampling_obfuscation = 0

            try:
                pagination_mode = str(
                    trackme_vtenant_conf[tenant_id]["pagination_mode"]
                )
            except Exception as e:
                pagination_mode = trackmeconf["trackme_general"]["pagination_mode"]

            try:
                pagination_size = int(
                    trackme_vtenant_conf[tenant_id]["pagination_size"]
                )
            except Exception as e:
                pagination_size = int(trackmeconf["trackme_general"]["pagination_size"])

            try:
                splk_dsm_tabulator_groupby = trackme_vtenant_conf[tenant_id][
                    "splk_dsm_tabulator_groupby"
                ]
            except Exception as e:
                splk_dsm_tabulator_groupby = "data_index"

            try:
                splk_dhm_tabulator_groupby = trackme_vtenant_conf[tenant_id][
                    "splk_dhm_tabulator_groupby"
                ]
            except Exception as e:
                splk_dhm_tabulator_groupby = "tenant_id"

            try:
                splk_mhm_tabulator_groupby = trackme_vtenant_conf[tenant_id][
                    "splk_mhm_tabulator_groupby"
                ]
            except Exception as e:
                splk_mhm_tabulator_groupby = "tenant_id"

            try:
                splk_flx_tabulator_groupby = trackme_vtenant_conf[tenant_id][
                    "splk_flx_tabulator_groupby"
                ]
            except Exception as e:
                splk_flx_tabulator_groupby = "group"

            try:
                splk_fqm_tabulator_groupby = trackme_vtenant_conf[tenant_id][
                    "splk_fqm_tabulator_groupby"
                ]
            except Exception as e:
                splk_fqm_tabulator_groupby = "group"

            try:
                splk_wlk_tabulator_groupby = trackme_vtenant_conf[tenant_id][
                    "splk_wlk_tabulator_groupby"
                ]
            except Exception as e:
                splk_wlk_tabulator_groupby = "overgroup"

            try:
                default_disruption_min_time_sec = int(
                    trackme_vtenant_conf[tenant_id]["default_disruption_min_time_sec"]
                )
            except Exception as e:
                default_disruption_min_time_sec = 0

            component_owner = str(kvrecord.get("tenant_owner"))

            #
            # mloutliers:
            # - loop troough each component in mloutliers_allowlist,
            # for each define a new key as mloutliers_<component> which gets 0 if mloutliers is disabled, 0 if enabled and not in the list, 1 if enabled and in the list

            # Define the components
            outliers_components = ["dsm", "dhm", "flx", "wlk", "fqm"]

            # Convert the allowlist to a set for faster lookups
            mloutliers_set = set(mloutliers_allowlist.split(","))

            # Create a dictionary dynamically
            mloutliers_dict = {
                f"mloutliers_{comp}": (
                    1 if comp in mloutliers_set and mloutliers == 1 else 0
                )
                for comp in outliers_components
            }

            # If you need separate variables, you can unpack the dictionary
            mloutliers_dsm = mloutliers_dict["mloutliers_dsm"]
            mloutliers_dhm = mloutliers_dict["mloutliers_dhm"]
            mloutliers_flx = mloutliers_dict["mloutliers_flx"]
            mloutliers_fqm = mloutliers_dict["mloutliers_fqm"]
            mloutliers_wlk = mloutliers_dict["mloutliers_wlk"]

            response = {
                "schema_version": str(schema_version),
                "schema_version_upgrade_in_progress": int(
                    schema_version_upgrade_in_progress
                ),
                "component_splk_dsm": int(component_splk_dsm),
                "component_splk_dhm": int(component_splk_dhm),
                "component_splk_mhm": int(component_splk_mhm),
                "component_splk_flx": int(component_splk_flx),
                "component_splk_fqm": int(component_splk_fqm),
                "component_splk_wlk": int(component_splk_wlk),
                "component_owner": str(component_owner),
                "ui_default_timerange": str(ui_default_timerange),
                "ui_min_object_width": int(ui_min_object_width),
                "ui_expand_metrics": int(ui_expand_metrics),
                "ui_home_tabs_order": str(ui_home_tabs_order),
                "sampling": int(sampling),
                "mloutliers": int(mloutliers),
                "mloutliers_allowlist": str(mloutliers_allowlist),
                "mloutliers_dsm": int(mloutliers_dsm),
                "mloutliers_dhm": int(mloutliers_dhm),
                "mloutliers_flx": int(mloutliers_flx),
                "mloutliers_fqm": int(mloutliers_fqm),
                "mloutliers_wlk": int(mloutliers_wlk),
                "adaptive_delay": int(adaptive_delay),
                "cmdb_lookup": int(cmdb_lookup),
                "data_sampling_obfuscation": int(data_sampling_obfuscation),
                "indexed_constraint": str(indexed_constraint),
                "splk_feeds_delayed_inspector_24hours_range_min_sec": int(
                    splk_feeds_delayed_inspector_24hours_range_min_sec
                ),
                "splk_feeds_delayed_inspector_7days_range_min_sec": int(
                    splk_feeds_delayed_inspector_7days_range_min_sec
                ),
                "splk_feeds_delayed_inspector_until_disabled_range_min_sec": int(
                    splk_feeds_delayed_inspector_until_disabled_range_min_sec
                ),
                "splk_feeds_delayed_inspector_max_backoff_multiplier": int(
                    splk_feeds_delayed_inspector_max_backoff_multiplier
                ),
                "splk_feeds_auto_disablement_period": str(
                    splk_feeds_auto_disablement_period
                ),
                "pagination_mode": str(pagination_mode),
                "pagination_size": int(pagination_size),
                "splk_dsm_tabulator_groupby": str(splk_dsm_tabulator_groupby),
                "splk_dhm_tabulator_groupby": str(splk_dhm_tabulator_groupby),
                "splk_mhm_tabulator_groupby": str(splk_mhm_tabulator_groupby),
                "splk_flx_tabulator_groupby": str(splk_flx_tabulator_groupby),
                "splk_fqm_tabulator_groupby": str(splk_fqm_tabulator_groupby),
                "splk_wlk_tabulator_groupby": str(splk_wlk_tabulator_groupby),
                "default_disruption_min_time_sec": int(default_disruption_min_time_sec),
            }

            logger.debug(
                f"tenant_id={tenant_id} components={json.dumps(response, indent=1)}"
            )

            # add trackme_conf
            response["trackme_conf"] = trackmeconf

            return {"payload": response, "status": 200}

        else:
            logger.debug(f"could not find a record for tenant={tenant_id}")
            return {"payload": f"Tenant was not found, tenant_id={tenant_id}", "status": 404}

    # Shows knowledge objects per tenant
    def post_get_tenant_knowledge_objects(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/configuration/get_tenant_knowledge_objects\" body=\"{'tenant_id':'mytenant'}\"
        """

        describe = False
        tenant_id = None

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves the tenant knowledge objects, it requires a POST call with the following options:",
                "resource_desc": "Get all knowledge objects for a given TrackMe tenant",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/configuration/get_tenant_knowledge_objects\" body=\"{'tenant_id':'mytenant'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # header
        header = {
            "Authorization": "Splunk %s" % request_info.session_key,
            "Content-Type": "application/json",
        }

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Define the SPL query
        kwargs_search = {
            "app": "trackme",
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }
        searchquery = f"| `get_tenants_reports({tenant_id})`"

        # specific to alerts
        alerts_static_fields = [
            "alert_type",
            "alert.severity",
            "alert.suppress",
            "alert.suppress.fields",
            "alert.suppress.period",
            "alert.track",
            "alert_comparator",
            "alert_threshold",
            "alert.digest_mode",
        ]

        query_results = []
        try:
            # spawn the search and get the results
            reader = run_splunk_search(
                service,
                searchquery,
                kwargs_search,
                24,
                5,
            )

            with requests.Session() as session:
                session.headers.update(header)

                for item in reader:
                    if isinstance(item, dict):

                        # extract the values
                        tenant_id_value = item.get("tenant_id")
                        component_value = item.get("component")
                        title_value = item.get("title")
                        type_value = item.get("type")
                        properties_value = {}

                        # init object_dict
                        object_dict = {
                            "tenant_id": tenant_id_value,
                            "component": component_value,
                            "type": type_value,
                            "title": title_value,
                            "properties": properties_value,
                        }

                        if type_value in ("savedsearches", "alerts"):

                            # get the object
                            savedsearch_object = service.saved_searches[
                                item.get("title")
                            ]

                            acl_link = savedsearch_object.links["alternate"]
                            acl_url = f"{request_info.server_rest_uri}/{acl_link}/acl/list?output_mode=json"

                            try:
                                acl_response = session.get(acl_url, verify=False)
                                acl_properties = json.loads(acl_response.text).get(
                                    "entry"
                                )[0]["acl"]

                                # get perms['read'] as perms_read and turn from list to csv
                                perms_read = ",".join(acl_properties["perms"]["read"])
                                # get perms['write'] as perms_write and turn from list to csv
                                perms_write = ",".join(acl_properties["perms"]["write"])

                                object_dict["properties"] = {
                                    "eai:acl.owner": acl_properties.get("owner"),
                                    "eai:acl.perms.read": perms_read,
                                    "eai:acl.perms.write": perms_write,
                                    "eai:acl.sharing": acl_properties.get("sharing"),
                                }

                                # check if we have a value for dispatch.sample_ratio and if it differs from 1, if so add it to the properties
                                try:
                                    if savedsearch_object.content.get("dispatch.sample_ratio") != "1":
                                        object_dict["properties"]["dispatch.sample_ratio"] = savedsearch_object.content.get("dispatch.sample_ratio")
                                except Exception as e:
                                    pass

                            except Exception as e:
                                object_dict["properties"] = {
                                    "eai:acl.owner": "nobody",
                                    "eai:acl.perms.read": "trackme_user,trackmer_power",
                                    "eai:acl.perms.write": "trackme_user,trackme_power,trackmer_admin",
                                    "eai:acl.sharing": "app",
                                }
                                logger.error(
                                    f'failed to retrieve the ACL properties for object="{title_value}" with exception="{str(e)}"'
                                )

                            # get the search definition
                            definition = savedsearch_object.content["search"]
                            object_dict["definition"] = definition

                            # get description as description
                            description = savedsearch_object.content.get("description")
                            object_dict["properties"]["description"] = description

                            # get schedule_window as schedule_window
                            schedule_window = savedsearch_object.content.get(
                                "schedule_window"
                            )
                            object_dict["properties"][
                                "schedule_window"
                            ] = schedule_window

                            # get is_scheduled as is_scheduled
                            is_scheduled = savedsearch_object.content.get(
                                "is_scheduled"
                            )
                            object_dict["properties"]["is_scheduled"] = int(
                                is_scheduled
                            )

                            # get cron_schedule as cron_schedule, only if it's not None
                            cron_schedule = savedsearch_object.content.get(
                                "cron_schedule"
                            )
                            if cron_schedule and cron_schedule not in (None, "None", "null"):
                                object_dict["properties"]["cron_schedule"] = cron_schedule

                            # get dispatch.earliest_time as earliest_time
                            earliest_time = savedsearch_object.content.get(
                                "dispatch.earliest_time"
                            )
                            object_dict["properties"]["earliest_time"] = earliest_time

                            # get dispatch.latest_time as latest_time
                            latest_time = savedsearch_object.content.get(
                                "dispatch.latest_time"
                            )
                            object_dict["properties"]["latest_time"] = latest_time

                            # only for alerts
                            if type_value == "alerts":

                                # store in alert_properties
                                alert_properties = {}

                                # Process the predefined fields
                                for field in alerts_static_fields:
                                    alert_properties[field] = (
                                        savedsearch_object.content.get(field)
                                    )

                                # other use cases
                                for (
                                    key,
                                    value,
                                ) in savedsearch_object.content.items():

                                    # support trackme actions
                                    if (
                                        (key.startswith("action.trackme_"))
                                        and value is not None
                                        and ".param." in key
                                    ):
                                        alert_properties[key] = value

                                    # support trackme actions enablement
                                    elif key in (
                                        "action.trackme_auto_ack",
                                        "action.trackme_notable",
                                        "action.trackme_stateful_alert",
                                    ):
                                        alert_properties[key] = value

                                    # support email actions
                                    if (
                                        key.startswith("action.email")
                                        and value is not None
                                    ):
                                        alert_properties[key] = value

                                # add to object_dict
                                object_dict["alert_properties"] = alert_properties

                        elif type_value == "macros":

                            # get the object
                            macro_object = service.confs["macros"][item.get("title")]

                            acl_link = macro_object.links["alternate"]
                            acl_url = f"{request_info.server_rest_uri}/{acl_link}/acl/list?output_mode=json"

                            try:
                                acl_response = session.get(acl_url, verify=False)
                                acl_properties = json.loads(acl_response.text).get(
                                    "entry"
                                )[0]["acl"]

                                # get perms['read'] as perms_read and turn from list to csv
                                perms_read = ",".join(acl_properties["perms"]["read"])
                                # get perms['write'] as perms_write and turn from list to csv
                                perms_write = ",".join(acl_properties["perms"]["write"])

                                object_dict["properties"] = {
                                    "eai:acl.owner": acl_properties.get("owner"),
                                    "eai:acl.perms.read": perms_read,
                                    "eai:acl.perms.write": perms_write,
                                    "eai:acl.sharing": acl_properties.get("sharing"),
                                }

                            except Exception as e:
                                object_dict["properties"] = {
                                    "eai:acl.owner": "nobody",
                                    "eai:acl.perms.read": "trackme_user,trackmer_power",
                                    "eai:acl.perms.write": "trackme_user,trackme_power,trackmer_admin",
                                    "eai:acl.sharing": "app",
                                }
                                logger.error(
                                    f'failed to retrieve the ACL properties for object="{title_value}" with exception="{str(e)}"'
                                )

                            definition = macro_object.content["definition"]
                            object_dict["definition"] = definition

                        elif type_value == "lookup_definitions":

                            # get the object
                            lookup_object = service.confs["transforms"][
                                item.get("title")
                            ]

                            acl_link = lookup_object.links["alternate"]
                            acl_url = f"{request_info.server_rest_uri}/{acl_link}/acl/list?output_mode=json"

                            try:
                                acl_response = session.get(acl_url, verify=False)
                                acl_properties = json.loads(acl_response.text).get(
                                    "entry"
                                )[0]["acl"]

                                # get perms['read'] as perms_read and turn from list to csv
                                perms_read = ",".join(acl_properties["perms"]["read"])
                                # get perms['write'] as perms_write and turn from list to csv
                                perms_write = ",".join(acl_properties["perms"]["write"])

                                object_dict["properties"] = {
                                    "eai:acl.owner": acl_properties.get("owner"),
                                    "eai:acl.perms.read": perms_read,
                                    "eai:acl.perms.write": perms_write,
                                    "eai:acl.sharing": acl_properties.get("sharing"),
                                }

                            except Exception as e:
                                object_dict["properties"] = {
                                    "eai:acl.owner": "nobody",
                                    "eai:acl.perms.read": "trackme_user,trackmer_power",
                                    "eai:acl.perms.write": "trackme_user,trackme_power,trackmer_admin",
                                    "eai:acl.sharing": "app",
                                }
                                logger.error(
                                    f'failed to retrieve the ACL properties for object="{title_value}" with exception="{str(e)}"'
                                )

                            collection_value = lookup_object.content["collection"]
                            field_list_value = lookup_object.content["fields_list"]
                            object_dict["collection"] = collection_value
                            object_dict["fields_list"] = field_list_value

                        elif type_value == "kvstore_collections":

                            acl_link = f"/servicesNS/nobody/trackme/storage/collections/config/{title_value}"
                            acl_url = f"{request_info.server_rest_uri}/{acl_link}/acl/list?output_mode=json"

                            try:
                                acl_response = session.get(acl_url, verify=False)
                                acl_properties = json.loads(acl_response.text).get(
                                    "entry"
                                )[0]["acl"]

                                # get perms['read'] as perms_read and turn from list to csv
                                perms_read = ",".join(acl_properties["perms"]["read"])
                                # get perms['write'] as perms_write and turn from list to csv
                                perms_write = ",".join(acl_properties["perms"]["write"])

                                object_dict["properties"] = {
                                    "eai:acl.owner": acl_properties.get("owner"),
                                    "eai:acl.perms.read": perms_read,
                                    "eai:acl.perms.write": perms_write,
                                    "eai:acl.sharing": acl_properties.get("sharing"),
                                }

                            except Exception as e:
                                object_dict["properties"] = {
                                    "eai:acl.owner": "nobody",
                                    "eai:acl.perms.read": "trackme_user,trackmer_power",
                                    "eai:acl.perms.write": "trackme_user,trackme_power,trackmer_admin",
                                    "eai:acl.sharing": "app",
                                }
                                logger.error(
                                    f'failed to retrieve the ACL properties for object="{title_value}" with exception="{str(e)}"'
                                )

                        # create the result
                        query_results.append(object_dict)

            return {"payload": query_results, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Shows tenants operational status
    def post_get_tenant_ops_status(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/configuration/get_tenant_ops_status\" body=\"{'tenant_id':'mytenant'}\"
        """

        describe = False
        mode = "pretty"
        tenant_id = "*"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    tenant_id = "*"

                try:
                    mode = resp_dict["mode"]
                    if mode in ("pretty", "raw"):
                        mode = mode
                    else:
                        mode = "pretty"
                except Exception as e:
                    mode = "pretty"

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves the tenant operational status, it requires a POST call with optional data:",
                "resource_desc": "Get operational status for a TrackMe tenant",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/configuration/get_tenant_ops_status\" body=\"{'tenant_id':'mytenant'}\"",
                "options": [
                    {
                        "tenant_id": "Tenant identifier, optional and defaults to all tenants if not specified",
                        "mode": "rendering mode, valid options are: pretty | raw (defaults to pretty if not specified)",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service - Attention this must run as the user!
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Define the SPL query
        kwargs_search = {
            "app": "trackme",
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }
        if mode == "pretty":
            searchquery = "| `per_tenant_ops_statusv2(" + str(tenant_id) + ")`"
        elif mode == "raw":
            searchquery = "| `per_tenant_ops_status_raw(" + str(tenant_id) + ")`"
        logger.debug(f'searchquery="{searchquery}"')

        query_results = []
        try:
            # spawn the search and get the results
            reader = run_splunk_search(
                service,
                searchquery,
                kwargs_search,
                24,
                5,
            )

            for item in reader:
                if isinstance(item, dict):
                    query_results.append(item)
            return {"payload": query_results, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Shows tenants scheduler status
    def get_get_tenant_scheduler_status(self, request_info, **kwargs):

        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves the tenant scheduler status, it requires a GET call:",
                "resource_desc": "Get scheduler status for a TrackMe tenant",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/configuration/get_tenant_scheduler_status"',
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service - Attention this must run as the user!
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Define the SPL query
        kwargs_search = {
            "app": "trackme",
            "earliest_time": "-24h",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }
        searchquery = remove_leading_spaces(
            rf"""
            search (index=_internal sourcetype=scheduler app="trackme")
            | rex field=savedsearch_name "_tenant_(?<tenant_id>.*)$"
            | rex field=savedsearch_name "tenant_id:(?<tenant_id>[^\s]*)"
            | lookup trackme_virtual_tenants tenant_id OUTPUT tenant_id as found | where isnotnull(found) | fields - found
            | eval alert_actions=if((isnull(alert_actions) OR (alert_actions == "")),"none",alert_actions)
            | eval is_alert=if(alert_actions!="none", 1, 0)
            | eval status=case(((status == "success") OR (status == "completed")),"completed",(status == "skipped"),"skipped",(status == "continued"),"deferred")
            | search (status="completed" OR status="deferred" OR status="skipped")
            | stats count(eval(status=="completed")) as count_completed, count(eval(status=="skipped")) as count_skipped, count, max(is_alert) as is_alert by tenant_id, savedsearch_name
            | eval "pct_completed"=round(((count_completed / count) * 100),2)
            | eval status=if('pct_completed'==100, "completed", "skipped")
            | eval "pct_completed_icon"=if('pct_completed'==100, "✅", "❌")
            | rename savedsearch_name as report
            | sort 0 tenant_id, report
        """
        )

        logger.debug(f'searchquery="{searchquery}"')

        query_results = []
        try:
            # spawn the search and get the results
            reader = run_splunk_search(
                service,
                searchquery,
                kwargs_search,
                24,
                5,
            )

            for item in reader:
                if isinstance(item, dict):
                    query_results.append(item)
            return {"payload": query_results, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Retrieve a report definition
    def post_get_report(self, request_info, **kwargs):
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
                report_name = resp_dict["report_name"]
        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint returns the full Splunk saved-search (report/alert) definition for the given report_name in the given tenant — the same shape Splunk's savedsearches REST endpoint returns, with the conf-stanza key/value pairs surfaced in the response payload.",
                "resource_desc": "Return the full Splunk saved-search definition for a given tenant + report_name",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/configuration/get_report" body="{\'tenant_id\': \'mytenant\', \'report_name\': \'my_saved_search\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "report_name": "REQUIRED. Name of the saved-search (report) to retrieve",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # create the transform
        try:
            report_definition = trackme_get_report(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                report_name,
            )
            return {"payload": report_definition, "status": 200}

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to retrieve the report definition, report="{report_name}", exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # List emails delivery accounts with a least privileges approach
    def get_get_emails_delivery_accounts(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/configuration/get_emails_delivery_accounts\"
        """

        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint provides the list of configured emails delivery accounts, it requires a GET call:",
                "resource_desc": "Return the list of emails delivery accounts, if none are configured it will return localhost for the local MTA",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/configuration/get_emails_delivery_accounts"',
                "options": [],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # get all accounts
        try:
            accounts = []
            conf_file = "trackme_emails"
            confs = service.confs[str(conf_file)]
            for stanza in confs:
                # get all accounts
                for name in stanza.name:
                    accounts.append(stanza.name)
                    break

            # If no accounts found, return localhost as default
            if not accounts:
                accounts = ["localhost"]

            return {"payload": {"accounts": accounts}, "status": 200}

        except Exception as e:
            return {"payload": {"accounts": ["localhost"]}, "status": 200}

    # Get emails delivery accounts with a least privileges approach
    def post_get_emails_delivery_account(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/configuration/get_emails_delivery_account\" body=\"{'account': 'lab'}\"
        """

        describe = False
        account = None

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                account = resp_dict.get("account")
        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint provides connection details for a Splunk remote account to be used in a programmatic manner with a least privileges approach, it requires a POST call with the following options:",
                "resource_desc": "Return a emails delivery account details for programmatic access with a least privileges approach",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/configuration/get_emails_delivery_account\" body=\"{'account': 'lab'}\"",
                "options": [
                    {
                        "account": "The account configuration identifier",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # TrackMe reqinfo
        trackmeconf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )

        # get all accounts
        try:
            accounts = []
            conf_file = "trackme_emails"
            confs = service.confs[str(conf_file)]
            for stanza in confs:
                # get all accounts
                for name in stanza.name:
                    accounts.append(stanza.name)
                    break

        except Exception as e:
            accounts = []

        if not accounts or account == "localhost":
            return {
                "payload": {
                    "account": "localhost",
                    "allowed_email_domains": None,
                    "email_footer": trackmeconf["trackme_conf"]["trackme_general"][
                        "email_footer"
                    ],
                    "email_format": trackmeconf["trackme_conf"]["trackme_general"][
                        "email_format"
                    ],
                    "email_password": None,
                    "email_security": None,
                    "email_server": "localhost:25",
                    "email_username": None,
                    "sender_email": trackmeconf["trackme_conf"]["trackme_general"][
                        "sender_email"
                    ],
                },
                "status": 200,
            }

        else:
            try:
                response = trackme_get_emails_account(request_info, account)
                return {"payload": response, "status": 200}

            except Exception as e:
                return {"payload": str(e), "status": 500}
