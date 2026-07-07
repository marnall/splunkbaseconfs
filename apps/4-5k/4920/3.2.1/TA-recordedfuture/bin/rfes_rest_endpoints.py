# -*- coding: utf-8 -*-
"""Provide a set REST endpoints for the app."""

import json
import os
import sys
import time
import traceback
from os.path import dirname
from pathlib import Path

from requests.exceptions import HTTPError

# Because python...
# pylint: disable=wrong-import-position

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, str(Path(os.path.dirname(__file__)) / "vendor"))
import rfes_configuration  # noqa
import rfes_global_banner  # noqa
import rfes_search  # noqa
import rfes_ui_sync  # noqa
import rfes_validate  # noqa

from recordedfuture.enrichment import links  # noqa
from recordedfuture.enrichment import enrich  # noqa
from recordedfuture.correlation import usecases  # noqa
from recordedfuture.correlation import risklists  # noqa
from recordedfuture.correlation import correlate  # noqa
from recordedfuture.correlation import ato  # noqa
from recordedfuture.migration import migrations  # noqa
from recordedfuture.core.exceptions import (  # noqa
    ValidationError,
    NotFoundError,
)
from recordedfuture.settings import default_sigma_rules  # noqa
from recordedfuture.core.logging import setup_logging  # noqa
from recordedfuture.api.splunk_api import SplunkClient  # noqa

from recordedfuture.core.utils import LazyProperty  # noqa

from recordedfuture.core.app_env import RfesAppEnv  # noqa
from recordedfuture.core import retention  # noqa
from recordedfuture.core import troubleshooting  # noqa
from recordedfuture.alertcenter import sigma  # noqa
from recordedfuture.alerts import classical  # noqa
from recordedfuture.alerts import ingestion  # noqa
from recordedfuture.alerts import playbook  # noqa
from recordedfuture.alertcenter import alert_center  # noqa
from recordedfuture.es import estimates  # noqa
from recordedfuture.es import ti_framework  # noqa
from recordedfuture.es import rba  # noqa
from recordedfuture import asyncjob, asi  # noqa

from recordedfuture.metrics import (  # noqa
    wau,
    daily_metrics,
    timeit,
    timing_logs,
)
from recordedfuture.threathunt import (  # noqa
    threatmap,
    threathunt,
)
from recordedfuture.core.utils import LazyProperty  # noqa


if sys.platform == "win32":
    import msvcrt  # pylint: disable=import-error

    # Binary mode is required for persistent mode on Windows.
    # Looked what os.O_BINARY actually was and found on Windows 10,
    # Server 2016 and Server 2019 that the value is 32768.
    # noqa pylint: disable=no-member
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    # noqa pylint: disable=no-member
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    # noqa pylint: disable=no-member
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
# pylint: disable=import-error, wrong-import-position
# noinspection PyUnresolvedReferences
try:
    from splunk.persistconn.application import (
        PersistentServerConnectionApplication,
    )  # noqa
except ImportError:
    # So that the module can be imported in tests
    class PersistentServerConnectionApplication:
        """Some useless doc string"""

        pass


def rest_help(in_dict, app_env):
    """Loads the contents of a helpfile and wires that to the client."""
    query_params = {entry[0]: entry[1] for entry in in_dict["query"]}
    requested_page = "{}.html".format(query_params["page"])

    recorded_future_path = dirname(dirname(os.path.realpath(__file__)))
    page = os.path.join(recorded_future_path, "appserver", "static", requested_page)

    with open(page) as f:
        contents = f.read()

    return 200, {"links": {}, "entry": {"content": contents}}


class RfesHandler(PersistentServerConnectionApplication):
    """A set of REST endpoints for the app."""

    # pylint: disable=unused-argument
    def __init__(self, command_line, command_arg):
        """Initialize."""
        self.command_line = command_line
        self.command_arg = command_arg
        self.logger = self.setup_logging()
        PersistentServerConnectionApplication.__init__(self)
        # Register callback methods on the fly
        self.register_async_callbacks()

        # These functions all take in_dict, app_env as args and return status, payload
        # It's grouped based on the file it comes from.
        self.endpoints = dict()
        self.endpoints.update(
            dict(
                migrate_cached_correlations=migrations.migrate_cached_correlations,
                migrate_remove_threat_intel_entries=migrations.remove_threat_intel_entries,
                run_migrations=migrations.run_migrations_endpoint,
            )
        )
        self.endpoints.update(
            dict(
                check_async_jobs=asyncjob.check_async_jobs,
                process_async_job=asyncjob.process_async_job,
                get_jobs_progress=asyncjob.get_jobs_progress,
            )
        )
        self.endpoints.update(
            dict(
                alerts_metadata=classical.alerts_metadata,
                download_alerts=classical.fetch_alerts,
                get_alert_count=classical.get_alert_count,
                lookup_alert=classical.lookup_alert,
                update_alerts=classical.update_alert,
                write_alerts=classical.write_alerts,
                ingest_alerts=ingestion.ingest_alerts,
                download_alerts_v3=classical.fetch_alerts_v3,
                update_alerts_v3=classical.update_alert_v3,
                download_single_alert_v3=classical.fetch_single_alert_v3,
                get_configured_classic_alert_rules=classical.get_configured_rules,
                lookup_alert_v3=classical.lookup_alert_v3,
            )
        )
        self.endpoints.update(
            dict(
                get_incidents=alert_center.get_incidents,
                save_single_state=alert_center.save_single_state,
            )
        )
        self.endpoints.update(
            dict(
                sync_ato_feeds=ato.sync_ato_feeds,
                correlation_delete=correlate.correlation_delete,
                correlation_edit_metadata=correlate.correlation_edit_metadata,
                correlation_settings=correlate.correlation_settings,
                correlation_disable=correlate.correlation_disable,
                upsert_correlation_setting=correlate.upsert_correlation_setting,
                enrich_detect_correlations=ato.enrich_detect_correlations,
            )
        )
        self.endpoints.update(
            dict(
                asi_configuration=rfes_configuration.handle_asi_configuration,
                configuration=rfes_configuration.handle_configuration,
                delete_api_token=rfes_configuration.delete_api_token,
                delete_asi_api_token=rfes_configuration.delete_asi_api_token,
                disable_force_es=rfes_configuration.disable_force_es,
                enable_force_es=rfes_configuration.enable_force_es,
                get_intelligence=rfes_configuration.get_intelligence,
                import_settings=troubleshooting.import_settings,
                post_intelligence=rfes_configuration.post_intelligence,
                request_stanza=rfes_configuration.request_stanza,
                store_config=rfes_configuration.store_config,
                save_default_indicator_settings=rfes_configuration.save_default_indicator_settings,
                read_default_indicator_settings=rfes_configuration.read_default_indicator_settings,
                troubleshooting_package=troubleshooting.troubleshooting_package,
                troubleshooting_mailto=troubleshooting.mailto,
                update_purge_settings=rfes_configuration.update_purge_settings,
                update_alert_index_settings=rfes_configuration.update_index_settings,
                user_permission=rfes_configuration.user_permission,
                verify_asi_connection_after_migration_from_old_app=rfes_configuration.verify_asi_connection_after_migration_from_old_app,
                read_configuration=rfes_configuration.read_configuration,
                reset_indicators=rfes_configuration.reset_indicators,
                write_conf_file=rfes_configuration.write_conf_file,
                toggle_sigma_rules_notables_creation=rfes_configuration.toggle_sigma_rules_notables_creation,
                toggle_threat_hunts_notables_creation=rfes_configuration.toggle_threat_hunts_notables_creation,
                toggle_auto_threat_hunt_enabled=rfes_configuration.toggle_auto_threat_hunt_enabled,
                update_ato_dm_correlation_delay=rfes_configuration.update_ato_dm_correlation_delay,
                update_sigma_hunt_timeout=rfes_configuration.update_sigma_hunt_timeout,
                get_auto_threat_hunt_settings=rfes_configuration.get_auto_threat_hunt_settings,
                default_sigma_rules=default_sigma_rules.default_sigma_rules,
                save_default_indicators_for_sigma_rules=default_sigma_rules.save_default_indicators_for_sigma_rules,
                delete_default_indicators_for_sigma_rules=default_sigma_rules.delete_default_indicators_for_sigma_rules,
                sigma_rules_mapping=default_sigma_rules.sigma_rules_mapping,
                enable_ato_capabilities=rfes_configuration.enable_ato_capabilities,
            )
        )
        self.endpoints.update(
            dict(
                correlate_on_links=links.correlate_on_links,
            )
        )
        self.endpoints.update(
            dict(
                get_detection_counts=sigma.get_detection_counts,
                get_spl_sigma_rules=sigma.get_spl_sigma_rules,
                get_sigma_rules=sigma.get_sigma_rules,
                get_sigma_detections=sigma.get_sigma_detections,
                save_sigma_rule=sigma.save_sigma_rule,
                save_single_sigma_detection=sigma.save_single_sigma_detection,
                sigma_search=sigma.sigma_search,
                update_sigma_rule=sigma.update_sigma_rule,
                remove_sigma_rule=sigma.remove_sigma_rule,
            )
        )
        self.endpoints.update(
            dict(
                store_rba_usecase=ti_framework.store_rba_usecase,
                store_ar_usecase=ti_framework.store_ar_usecase,
                delete_tifeed=ti_framework.delete_tifeed_usecase,
                share_third_party_correlations=ti_framework.share_third_party_correlations,
                purge_entries_in_ti_store=ti_framework.purge_entries_in_ti_store,
                rba_estimate=estimates.rba_estimate,
            )
        )
        self.endpoints.update(
            dict(
                download_correlation_feed=risklists.download_correlation_feed,
                sync_correlation_feeds=risklists.sync_correlation_feeds,
                update_correlation_cache=risklists.update_correlation_cache,
                purge_risklists=risklists.purge_risklists,
            )
        )
        self.endpoints.update(
            dict(
                correlation_search=usecases.correlation_search,
                initial_correlation_search=usecases.initial_search_wrapper,
                store_correlation_usecase_reg=usecases.store_correlation_usecase_reg,  # noqa
                preview_search_correlation_reg=usecases.preview_search_correlation_reg,  # noqa
                store_correlation_usecase_model=usecases.store_correlation_usecase_model,  # noqa
                preview_search_correlation_model=usecases.preview_search_correlation_model,  # noqa
                sync_usecases=usecases.sync_usecases,
                get_correlations_by_category=usecases.get_correlations_by_category,
                toggle_correlations_feature=usecases.toggle_correlations_feature,
            )
        )
        self.endpoints.update(
            dict(
                fetch_playbook_alerts=playbook.fetch_alerts,
                update_single_playbook_alert=playbook.update_single_alert,
                save_playbook_alert_local_note=playbook.save_alert_local_note,
                update_cached_playbook_alerts=playbook.update_cached_alerts,
                fetch_single_alert=playbook.fetch_single_alert,
                get_playbook_alert_count=playbook.get_count,
                fetch_playbook_alert_image=playbook.fetch_image,
                update_ingested_playbook_alerts_purge_settings=playbook.update_ingested_playbook_alerts_purge_settings,
            )
        )
        self.endpoints.update(
            dict(
                fetch_threat_maps=threatmap.fetch_threat_maps,
                execute_threat_hunt=threathunt.execute_threat_hunt,
                check_pending_jobs=threathunt.check_pending_jobs,
                run_threat_hunt=threathunt.run_threat_hunt,
                populate_portal_profiles=threathunt.populate_portal_profiles,
                delete_threat_hunt_config=threathunt.delete_threat_hunt_config,
                create_threat_hunt_config=threathunt.create_threat_hunt_config,
                create_threat_actor_hunt_from_spl=threathunt.create_threat_actor_hunt_from_spl,
                update_threat_hunt_config=threathunt.update_threat_hunt_config,
                stop_threat_hunt=threathunt.stop_threat_hunt,
                update_threat_hunt_run_note=threathunt.update_threat_hunt_run_note,
                get_threat_hunt_saved_search_owner_info=threathunt.get_saved_search_owner_info,
            )
        )
        self.endpoints.update(
            dict(
                debug=self.handle_debug,
                enrich=enrich.enrich,
                cidr_to_ip_range=enrich.cidr_range,
                rba=rba.risk_based_alerting,
                rest_help=rest_help,
                search=rfes_search.search,
                sync_ui_elements=rfes_ui_sync.sync_ui_elements,
                sync_ui_element=rfes_ui_sync.sync_single_ui_element,
                sync_landing_page=rfes_ui_sync.sync_landing_page_endpoint,
                validate=rfes_validate.validate,
                get_global_banner=rfes_global_banner.get_global_banner,
                hide_global_banner=rfes_global_banner.hide_global_banner,
                send_timing_logs_to_bfi=timing_logs.send_timing_logs_to_bfi,
                push_wau_stats=wau.push_wau_stats,
                send_metrics=daily_metrics.send_metrics,
                collection_retention=retention.collection_retention,
            )
        )

        self.endpoints.update(
            dict(
                fetch_asi_activity=asi.fetch_activity,
                fetch_asi_surface=asi.fetch_surface,
                fetch_asi_inventory=asi.fetch_inventory,
                asi_investigate_hostname=asi.investigate_hostname,
                asi_investigate_domain=asi.investigate_domain,
                get_modules_info=rfes_configuration.get_modules_info,
                migrate_asi_config=asi.migrate_config,
                skip_asi_migration=asi.skip_migration,
                fetch_asi_projects=asi.fetch_projects,
            )
        )

        # Setting Timeit decorator for all handlers to measure the duration of calls
        for endpoint_name, endpoint_handler in self.endpoints.items():
            self.endpoints[endpoint_name] = timeit.Timeit()(endpoint_handler)

    def register_async_callbacks(self):
        """When called, registers a number of callback methods to hook
        them up with ´callback´, argument of SplunkClient.searches.async_search()

        """
        asyncjob.register_callback(
            "process_threathunt_results", threathunt.process_threathunt_results
        )
        asyncjob.register_callback("create_detect_feed", ato.create_detect_feed)
        asyncjob.register_callback(
            "update_detect_feed_savedsearch", ato.update_detect_feed_savedsearch
        )

    def handle_lookup(self, in_dict, app_env):
        """Handle lookup calls. These are legacy endpoints. Only supported
        for custom scripts, to be removed in an undefined futur
        """
        self.logger.info("handle_lookup entered.")
        try:
            category, ent = in_dict["path_info"][7:].split("/", 1)
            self.logger.debug("category=%s entity=%s", category, ent)
            query = dict(in_dict["query"])
            # Workaround for URL lookups which can contain an = in the
            # path-info section. This confuses Splunk. Solution is to set
            # path-info to PARAM and supply the URL as a param argument.
            if ent == "PARAM":
                ent = query["param"]
            self.logger.debug("query=%s", query)
            # pylint: disable=no-member
            return enrich.lookup(category, ent, app_env, **query)
        except ValueError as err:
            self.logger.error(
                "Invalid lookup request: %s", in_dict["path_info"], exc_info=True
            )
            raise err
        except HTTPError as err:
            return {
                "message": json.loads(err.response.text)["error"]["message"],
                "json": {},
                "status_code": err.response.status_code,
            }
        except Exception as err:
            self.logger.error(err, exc_info=True)
            try:
                message = json.loads(str(err).replace("u'", "'").replace("'", '"'))
                return {
                    "message": message["message"],
                    "json": message,
                    "status_code": message["status"],
                }
            except ValueError:
                message = str(err)
                return {"message": message, "status_code": 500}

    @staticmethod
    def handle_debug(in_dict, _):
        """Remove sensitive data from debug output."""
        in_dict["system_authtoken"] = "REDACTED"
        in_dict.get("session", {})["authtoken"] = "REDACTED"
        # XXX: Better to keep and just redact the token in the auth header?
        in_dict["headers"] = [
            x for x in in_dict.get("headers", []) if x[0] != "Authorization"
        ]
        return 200, {"links": {}, "entry": [{"name": "debug", "content": in_dict}]}

    def upgrade_handler(self, app_env):
        """Primary upgrade handler."""
        migrations.main_upgrade_handler(app_env)

    def handle(self, in_string):
        """Route REST calls."""
        # Phase one: fetch api_token
        timestamp = time.time()
        try:
            in_dict = json.loads(in_string)
            app_env = RfesAppEnv(in_dict, self.logger)
        except Exception as err:
            self.logger.error("Failed to create AppEnv object: %s", err, exc_info=True)
            return {
                "payload": {
                    "links": {},
                    "entry": [
                        {"name": "debug", "content": "Failed to create AppEnv object."}
                    ],
                },
                "status": 500,
            }
        # Phase two: get info about the environment.
        try:
            self.logger.setLevel(app_env.log_level)
        except Exception:
            self.logger.error("Failed to map environment", exc_info=True)
            raise
        # Phase three: handle the request.
        payload = None
        status = -1
        try:
            endpoint_path = in_dict["path_info"].split("/")[0]
            for endpoint, handler in self.endpoints.items():
                if endpoint_path == endpoint:
                    self.logger.debug("endpoint %s found in endpoints", endpoint)
                    status, payload = handler(in_dict, app_env)
                    break

            if payload is None:
                if in_dict["path_info"].startswith("lookup_"):
                    payload = {
                        "entry": [
                            {
                                "name": in_dict["path_info"].split("/")[0],
                                "content": self.handle_lookup(in_dict, app_env),
                            }
                        ]
                    }
                    status = 200
                else:
                    payload = mk_payload(r"Page not found: %s" % (in_dict["path_info"]))
                    status = 404
        except HTTPError as e:
            text = e.response.text
            self.logger.exception("Response had following: {}".format(text))
            search_not_executed_payload = mk_search_not_executed_payload(e.response)
            if search_not_executed_payload is None:
                payload = mk_payload("HTTPError: " + text)
            else:
                payload = search_not_executed_payload
            status = e.response.status_code or 500
        except ValidationError as e:
            status = 400
            payload = mk_payload(str(e))
        except NotFoundError as e:
            status = 404
            payload = mk_payload(str(e))
        except Exception as err:
            self.logger.error("failed during handling phase: %s", err, exc_info=True)
            payload = mk_payload(
                "Internal error in handling phase: "
                r"%s\n%s" % (err, traceback.format_exc())
            )
            status = 500
        else:
            self.logger.debug(
                "handler completed successfully [%d]: %s", status, str(payload)[:200]
            )

        # Store usage statistics
        wau.store_usage(app_env, in_dict, timestamp)
        # self.logger.debug('Log page payload %s', json.dumps(payload)[:200])
        return {"payload": payload, "status": status}

    def setup_logging(self):
        """Setup logging."""
        return setup_logging()


def mk_payload(message):
    """Insert payload message in the proper structure."""
    return {"entry": [{"name": "error", "payload": message}], "message": message}


def mk_search_not_executed_payload(response):
    """Make a payload for "Search not executed" problem.

    Args:
        response (requests.Response): response with problem.

    Returns:
        dict|None: payload for "Search not executed" problem or None if the problem is not "Search not executed".
    """
    if response is None:
        return None

    json_data = response.json()
    if json_data.get("messages"):
        for message in json_data["messages"]:
            if (
                (message.get("text") or "")
                .lower()
                .startswith(
                    "search not executed: the maximum number of concurrent historical "
                    "searches on this instance has been reached."
                )
            ):
                return {
                    "entry": [{"name": "error", "payload": message}],
                    "message": message["text"],
                }
    return None


def mk_error(name, err, logger):
    """Create a return struct for payload with an error."""
    content = json.loads(err.content)
    payload = {
        "message": content["error"]["message"],
        "json": content,
        "status_code": content["error"]["status"],
    }
    return {"entry": [{"name": name, "content": payload}]}
