#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library
import os
import sys
import json
import time

# Logging
import logging
from logging.handlers import RotatingFileHandler

# Networking
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_decision_maker.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()  # root logger - Good to get it only once.
for hdlr in log.handlers[:]:  # remove the existing file handlers
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)  # set the new handler
# set the log level to INFO, DEBUG as the default is ERROR
log.setLevel(logging.INFO)

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# import Splunk
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo, trackme_vtenant_account

# import TrackMe get data libs
from trackme_libs_get_data import (
    get_feeds_datagen_kv_collection,
    get_sampling_kv_collection,
    search_kv_collection_restmode,
    search_kv_collection_searchmode,
    search_kv_collection_sdkmode,
)

# import automatic label assignment rule engine (pure, I/O-free)
from trackme_libs_autolabels import (
    parse_auto_labels_rules,
    tenant_has_enabled_auto_labels,
    reconcile_entity_labels,
)

# Import trackme decisionmaker libs
from trackme_libs_decisionmaker import (
    convert_epoch_to_datetime,
    get_monitoring_time_status,
    get_outliers_status,
    get_data_sampling_status,
    get_future_status,
    get_future_metrics_status,
    get_is_under_dcount_host,
    get_logical_groups_collection_records,
    get_dsm_latency_status,
    get_dsm_delay_status,
    resolve_variable_delay_threshold,
    resolve_lagging_class_threshold,
    set_dsm_status,
    set_dhm_status,
    set_mhm_status,
    set_flx_status,
    set_fqm_status,
    set_wlk_status,
    apply_blocklist,
    dynamic_priority_lookup,
    dynamic_tags_lookup,
    dynamic_sla_class_lookup,
    get_sla_timer,
    dsm_sampling_lookup,
    sampling_anomaly_status,
    flx_thresholds_lookup,
    fqm_thresholds_lookup,
    wlk_thresholds_lookup,
    flx_check_dynamic_thresholds,
    fqm_check_dynamic_thresholds,
    flx_drilldown_searches_lookup,
    flx_default_metrics_lookup,
    calculate_score,
)

# import threshold intent-lock predicates (scheduled decision maker must honour pins)
from trackme_libs_threshold_intent import (
    is_delay_threshold_locked,
    is_lag_threshold_locked,
)

# import trackme libs disruption queue
from trackme_libs_disruption_queue import (
    disruption_queue_lookup,
    disruption_queue_update,
    disruption_queue_get_duration,
)
from trackme_libs_entity_maintenance import (
    entity_maintenance_lookup,
    apply_entity_maintenance_override,
    clear_entity_maintenance_fields,
)

# Import TrackMe splk-flx libs
from trackme_libs_splk_flx import trackme_flx_gen_metrics

# Import TrackMe splk-fqm libs
from trackme_libs_splk_fqm import trackme_fqm_gen_metrics

# Import TrackMe utils libs
from trackme_libs_utils import get_uuid


@Configuration(distributed=False)
class TrackMeDecisionMaker(StreamingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** Specify the TrackMe component.""",
        require=True,
        default=None,
        validate=validators.Match("component", r"^(dsm|dhm|mhm|wlk|flx|fqm)$"),
    )

    """
    This function ensures that records have the same list of fields to allow Splunk to automatically extract these fields
    If a given result does not have a given field, it will be added to the record as an empty value    
    """

    def generate_fields(self, records):
        all_keys = set()
        for record in records:
            all_keys.update(record.keys())

        for record in records:
            for key in all_keys:
                if key not in record:
                    record[key] = ""
            yield record

    def get_tenant_metric_idx(self):
        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % self._metadata.searchinfo.session_key,
            "Content-Type": "application/json",
        }

        # get the index conf for this tenant
        url = "%s/services/trackme/v2/vtenants/tenant_idx_settings" % (
            self._metadata.searchinfo.splunkd_uri
        )
        data = {"tenant_id": self.tenant_id, "idx_stanza": "trackme_metric_idx"}

        # Retrieve and set the tenant idx, if any failure, logs and use the global index
        try:
            response = requests.post(
                url,
                headers=header,
                data=json.dumps(data, indent=1),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 204):
                error_msg = f'instance_id={self.instance_id}, failed to retrieve the tenant metric index, response.status_code="{response.status_code}", response.text="{response.text}"'
                logging.error(error_msg)
                raise Exception(error_msg)
            else:
                response_data = json.loads(json.dumps(response.json(), indent=1))
                tenant_trackme_metric_idx = response_data["trackme_metric_idx"]
        except Exception as e:
            error_msg = (
                f'instance_id={self.instance_id}, failed to retrieve the tenant metric index, exception="{str(e)}"'
            )
            logging.error(error_msg)
            raise Exception(error_msg)

        return tenant_trackme_metric_idx

    """
    Stream function
    """

    def stream(self, records):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # set instance_id
        self.instance_id = get_uuid()

        # Get virtual tenant account
        vtenant_conf = trackme_vtenant_account(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )

        # get metric index
        metric_index = self.get_tenant_metric_idx()

        #
        # System level settings
        #

        system_future_tolerance = float(
            reqinfo["trackme_conf"]["splk_general"][
                "splk_general_feeds_future_tolerance"
            ]
        )

        #
        # System level default minimal disruption period
        #

        default_disruption_min_time_sec = int(
            vtenant_conf["default_disruption_min_time_sec"]
        )

        #
        # Tenant level default monitoring time policy
        #

        try:
            default_monitoring_time_policy = vtenant_conf["monitoring_time_policy"]
        except Exception as e:
            default_monitoring_time_policy = "all_time"

        #
        # Automatic label assignment — setup (zero cost when no rules)
        #
        # Rules live as a JSON list on the vtenant_account (already loaded
        # above), so reading them adds no I/O. When at least one rule is
        # enabled we load the per-tenant label-assignment collection ONCE so
        # the per-record reconcile can compute deltas without per-entity reads;
        # the collection is keyed by "{component}:{object_id}" (== the entity
        # _key prefixed by component), matching dynamic_labels_lookup. All
        # auto-label work is wrapped so it can never break state computation.
        #
        auto_labels_active = False
        auto_labels_rules = []
        auto_labels_assign_collection = None
        auto_labels_assign_dict = {}
        auto_labels_deltas = {}  # assign_key -> (final_label_ids, applied_map, object_id)
        try:
            auto_labels_rules = parse_auto_labels_rules(vtenant_conf)
            auto_labels_active = tenant_has_enabled_auto_labels(auto_labels_rules)
            if auto_labels_active:
                # Defense-in-depth: never process auto-labels for a disabled
                # tenant. The per-tenant tracker saved-search is already
                # unscheduled when a tenant is disabled, but gate here too
                # (consistent with other per-tenant batch work). tenant_status
                # lives on the KV record, NOT the conf-derived vtenant_conf, so
                # read it from kv_trackme_virtual_tenants. Gated behind enabled
                # rules (one query, only for tenants that use the feature) and
                # fail-open: a lookup error leaves the feature active rather than
                # silently disabling it on a transient glitch.
                try:
                    _vt_records = self.service.kvstore[
                        "kv_trackme_virtual_tenants"
                    ].data.query(query=json.dumps({"tenant_id": self.tenant_id}))
                    if _vt_records and str(
                        _vt_records[0].get("tenant_status", "enabled")
                    ).lower() != "enabled":
                        auto_labels_active = False
                        logging.info(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                            f'component="{self.component}", tenant is disabled; '
                            f'skipping all auto-label work for this run.'
                        )
                except Exception as e:
                    logging.warning(
                        f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                        f'component="{self.component}", could not verify tenant_status '
                        f'for auto-labels (proceeding), exception="{str(e)}"'
                    )
            if not auto_labels_active:
                logging.debug(
                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                    f'component="{self.component}", auto-labels early-out: no enabled '
                    f'rules, skipping all auto-label work for this run.'
                )
            if auto_labels_active:
                auto_labels_assign_collection_name = (
                    f"kv_trackme_label_assignments_tenant_{self.tenant_id}"
                )
                # Guard on collection existence (same pattern as the
                # entity-maintenance block above). The collection is provisioned
                # at tenant creation, but on a freshly-migrated / partially-set-up
                # tenant it may be briefly absent — treat that as "no existing
                # assignments" rather than letting the bare kvstore[...] raise a
                # KeyError that the outer except would log as an ERROR every run.
                # auto_labels_assign_collection stays None as a signal to skip the
                # flush write until the collection exists.
                if auto_labels_assign_collection_name in self.service.kvstore:
                    auto_labels_assign_collection = self.service.kvstore[
                        auto_labels_assign_collection_name
                    ]
                    (
                        _al_records,
                        _al_keys,
                        auto_labels_assign_dict,
                        _al_last_page,
                    ) = search_kv_collection_sdkmode(
                        logging,
                        self.service,
                        auto_labels_assign_collection_name,
                        page=1,
                        page_count=0,
                        orderby="keyid",
                    )
                else:
                    logging.info(
                        f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                        f'component="{self.component}", auto-labels assignment '
                        f'collection not present yet; starting with empty '
                        f'assignments and skipping the flush write this run.'
                    )
        except Exception as e:
            logging.error(
                f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                f'component="{self.component}", auto-labels setup failed (feature '
                f'disabled for this run, state computation unaffected), '
                f'exception="{str(e)}"'
            )
            auto_labels_active = False

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "get_priority_collection_records"

        # dynamic priority, for all components
        # get priority collection
        priority_collection_name = (
            f"kv_trackme_{self.component}_priority_tenant_{self.tenant_id}"
        )
        priority_collection = self.service.kvstore[priority_collection_name]
        (
            priority_records,
            priority_collection_keys,
            priority_collection_dict,
            last_page,
        ) = search_kv_collection_sdkmode(
            logging, self.service, priority_collection_name, page=1, page_count=0, orderby="keyid"
        )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "get_tags_collection_records"

        # get tags collection
        tags_collection_name = (
            f"kv_trackme_{self.component}_tags_tenant_{self.tenant_id}"
        )
        tags_collection = self.service.kvstore[tags_collection_name]
        (
            tags_records,
            tags_collection_keys,
            tags_collection_dict,
            last_page,
        ) = search_kv_collection_sdkmode(
            logging, self.service, tags_collection_name, page=1, page_count=0, orderby="keyid"
        )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "get_sla_collection_records"

        # dynamic sla_class, for all components
        # get sla collection
        sla_collection_name = f"kv_trackme_{self.component}_sla_tenant_{self.tenant_id}"
        sla_collection = self.service.kvstore[sla_collection_name]
        (
            sla_records,
            sla_collection_keys,
            sla_collection_dict,
            last_page,
        ) = search_kv_collection_sdkmode(
            logging, self.service, sla_collection_name, page=1, page_count=0, orderby="keyid"
        )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "get_disruption_queue_collection_records"

        # get disruption queue collection
        disruption_queue_collection_name = (
            f"kv_trackme_common_disruption_queue_tenant_{self.tenant_id}"
        )
        disruption_queue_collection = self.service.kvstore[
            disruption_queue_collection_name
        ]
        (
            disruption_queue_records,
            disruption_queue_collection_keys,
            disruption_queue_collection_dict,
            last_page,
        ) = search_kv_collection_sdkmode(
            logging, self.service, disruption_queue_collection_name, page=1, page_count=0, orderby="keyid"
        )

        logging.debug(
            f'instance_id={self.instance_id}, disruption_queue_collection_dict="{json.dumps(disruption_queue_collection_dict, indent=2)}"'
        )

        # get per-entity maintenance collection. A missing collection (older
        # tenant not yet backfilled by the general health manager) is expected
        # and degrades to empty; a genuine read failure (auth/session) must NOT
        # silently disable maintenance, so only a MISSING collection is treated
        # as empty and real read errors propagate.
        entity_maintenance_collection_name = (
            f"kv_trackme_common_entity_maintenance_tenant_{self.tenant_id}"
        )
        if entity_maintenance_collection_name in self.service.kvstore:
            (
                _entity_maintenance_records,
                entity_maintenance_collection_keys,
                entity_maintenance_collection_dict,
                _last_page,
            ) = search_kv_collection_sdkmode(
                logging, self.service, entity_maintenance_collection_name, page=1, page_count=0, orderby="keyid"
            )
        else:
            logging.info(
                f'instance_id={self.instance_id}, maintenance collection="{entity_maintenance_collection_name}" not present yet; skipping maintenance override for this run'
            )
            entity_maintenance_collection_keys = []
            entity_maintenance_collection_dict = {}

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        #
        # SLA timer
        #

        sla_classes = {}
        sla_default_class = None

        sla_classes = reqinfo["trackme_conf"]["sla"]["sla_classes"]
        # try loading the JSON
        try:
            sla_classes = json.loads(sla_classes)
            sla_default_class = reqinfo["trackme_conf"]["sla"]["sla_default_class"]
            if not len(sla_default_class) > 0 or sla_default_class not in sla_classes:
                sla_default_class = "silver"
                logging.error(
                    f'instance_id={self.instance_id}, Invalid sla_default_class="{sla_default_class}", this SLA class is not part of the SLA classes, applying fallback configuration'
                )

        except:
            logging.error(
                f'instance_id={self.instance_id}, Error loading sla_classes JSON, please check the configuration, the JSON is not valid JSON, applying fallback configuration, exception="{str(e)}"'
            )
            sla_classes = json.loads(
                '{"platinum": {"sla_threshold": 14400, "rank": 3}, "gold": {"sla_threshold": 86400, "rank": 2}, "silver": {"sla_threshold": 172800, "rank": 1}}'
            )
            sla_default_class = "silver"

        # retrieve the score for the tenant and component
        scores_dict = calculate_score(self.service, self.tenant_id, self.component, tenant_trackme_metric_idx=metric_index)
        logging.info(
            f'instance_id={self.instance_id}, scores_dict="{json.dumps(scores_dict, indent=2)}"'
        )

        #
        # variable delay collection (DSM and DHM)
        #

        variable_delay_collection_dict = {}
        if self.component in ["dsm", "dhm"]:

            # set task
            #
            task_start = time.time()
            task_instance_id = get_uuid()
            task_name = "get_variable_delay_collection_records"

            variable_delay_collection_name = (
                f"kv_trackme_{self.component}_variable_delay_tenant_{self.tenant_id}"
            )
            try:
                (
                    variable_delay_records,
                    variable_delay_collection_keys,
                    variable_delay_collection_dict,
                    last_page,
                ) = search_kv_collection_sdkmode(
                    logging, self.service, variable_delay_collection_name, page=1, page_count=0, orderby="keyid"
                )
            except Exception as e:
                logging.warning(
                    f'instance_id={self.instance_id}, failed to load variable delay collection="{variable_delay_collection_name}", exception="{str(e)}", variable delay will not be applied'
                )
                variable_delay_collection_dict = {}

            logging.debug(
                f'instance_id={self.instance_id}, variable_delay_collection_dict has {len(variable_delay_collection_dict)} records'
            )

            # end task
            #
            task_end = time.time()
            task_run_time = round((task_end - task_start), 3)
            logging.info(
                f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
            )

        #
        # lagging classes collection (DSM and DHM)
        #

        lagging_classes_records = []
        if self.component in ["dsm", "dhm"]:

            # set task
            #
            task_start = time.time()
            task_instance_id = get_uuid()
            task_name = "get_lagging_classes_collection_records"

            lagging_classes_collection_name = (
                f"kv_trackme_{self.component}_lagging_classes_tenant_{self.tenant_id}"
            )
            try:
                (
                    lagging_classes_records,
                    lagging_classes_collection_keys,
                    lagging_classes_collection_dict,
                    last_page,
                ) = search_kv_collection_sdkmode(
                    logging, self.service, lagging_classes_collection_name, page=1, page_count=0, orderby="keyid"
                )
            except Exception as e:
                logging.warning(
                    f'instance_id={self.instance_id}, failed to load lagging classes collection="{lagging_classes_collection_name}", exception="{str(e)}", lagging classes will not be applied'
                )
                lagging_classes_records = []

            logging.debug(
                f'instance_id={self.instance_id}, lagging_classes_records has {len(lagging_classes_records)} records'
            )

            # end task
            #
            task_end = time.time()
            task_run_time = round((task_end - task_start), 3)
            logging.info(
                f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
            )

        #
        # splk-dsm specific collections
        #

        if self.component == "dsm":

            # set task
            #
            task_start = time.time()
            task_instance_id = get_uuid()
            task_name = "get_sampling_collection_records"

            # Data sampling
            sampling_collection_name = (
                f"kv_trackme_dsm_data_sampling_tenant_{self.tenant_id}"
            )
            sampling_collection = self.service.kvstore[sampling_collection_name]
            sampling_records, sampling_collection_keys, sampling_collection_dict = (
                get_sampling_kv_collection(
                    sampling_collection, sampling_collection_name
                )
            )

            # end task
            #
            task_end = time.time()
            task_run_time = round((task_end - task_start), 3)
            logging.info(
                f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
            )

        # dhm specific

        if self.component == "dhm":
            macro_name = (
                f"trackme_dhm_default_splk_dhm_alert_policy_tenant_{self.tenant_id}"
            )
            macro_current = self.service.confs["macros"][macro_name]
            default_splk_dhm_alerting_policy = macro_current.content.get("definition")
            # remove double quotes from default_splk_dhm_alerting_policy
            default_splk_dhm_alerting_policy = default_splk_dhm_alerting_policy.replace(
                '"', ""
            )

            logging.debug(
                f'instance_id={self.instance_id}, default_splk_dhm_alerting_policy="{default_splk_dhm_alerting_policy}"'
            )

        #
        # component specific collections
        #

        if self.component in ["dsm", "dhm", "mhm", "flx", "fqm", "wlk"]:

            # set task
            #
            task_start = time.time()
            task_instance_id = get_uuid()
            task_name = "get_datagen_collection_records"

            # datagen
            datagen_collection_name = (
                f"kv_trackme_{self.component}_allowlist_tenant_{self.tenant_id}"
            )
            datagen_collection = self.service.kvstore[datagen_collection_name]
            (
                datagen_records,
                datagen_collection_keys,
                datagen_collection_dict,
                datagen_collection_blocklist_not_regex_dict,
                datagen_collection_blocklist_regex_dict,
            ) = get_feeds_datagen_kv_collection(
                datagen_collection, datagen_collection_name, self.component
            )

            logging.debug(
                f'instance_id={self.instance_id}, datagen_collection_dict="{json.dumps(datagen_collection_dict, indent=2)}"'
            )

            logging.debug(
                f'instance_id={self.instance_id}, datagen_collection_blocklist_not_regex_dict="{json.dumps(datagen_collection_blocklist_not_regex_dict, indent=2)}"'
            )

            logging.debug(
                f'instance_id={self.instance_id}, datagen_collection_blocklist_regex_dict="{json.dumps(datagen_collection_blocklist_regex_dict, indent=2)}"'
            )

            # end task
            #
            task_end = time.time()
            task_run_time = round((task_end - task_start), 3)
            logging.info(
                f'instance_id={self.instance_id}, instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
            )

        # Initialize thresholds_collection_dict as safe default for all components;
        # it gets populated in the component-specific blocks below (FLX, FQM, WLK)
        thresholds_collection_dict = {}

        #
        # splk-flx specific collections
        #

        if self.component == "flx":

            # set task
            #
            task_start = time.time()
            task_instance_id = get_uuid()
            task_name = "get_thresholds_collection_records"

            # Thresholds
            thresholds_collection_name = (
                f"kv_trackme_flx_thresholds_tenant_{self.tenant_id}"
            )
            thresholds_collection = self.service.kvstore[thresholds_collection_name]
            (
                thresholds_records,
                thresholds_collection_keys,
                thresholds_collection_dict,
                last_page,
            ) = search_kv_collection_sdkmode(
                logging, self.service, thresholds_collection_name, page=1, page_count=0, orderby="keyid"
            )

            logging.debug(
                f'instance_id={self.instance_id}, thresholds_collection_dict="{json.dumps(thresholds_collection_dict, indent=2)}"'
            )

            # end task
            #
            task_end = time.time()
            task_run_time = round((task_end - task_start), 3)
            logging.info(
                f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
            )

            # set task
            #
            task_start = time.time()
            task_instance_id = get_uuid()
            task_name = "get_drilldown_searches_collection_records"

            # Drilldown searches
            drilldown_searches_collection_name = (
                f"kv_trackme_flx_drilldown_searches_tenant_{self.tenant_id}"
            )
            drilldown_searches_collection = self.service.kvstore[drilldown_searches_collection_name]
            (
                drilldown_searches_records,
                drilldown_searches_collection_keys,
                drilldown_searches_collection_dict,
                last_page,
            ) = search_kv_collection_sdkmode(
                logging, self.service, drilldown_searches_collection_name, page=1, page_count=0, orderby="keyid"
            )

            logging.debug(
                f'instance_id={self.instance_id}, drilldown_searches_collection_dict="{json.dumps(drilldown_searches_collection_dict, indent=2)}"'
            )

            # end task
            #
            task_end = time.time()
            task_run_time = round((task_end - task_start), 3)
            logging.info(
                f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
            )

            # set task
            #
            task_start = time.time()
            task_instance_id = get_uuid()
            task_name = "get_default_metrics_collection_records"

            # Default metrics
            default_metrics_collection_name = (
                f"kv_trackme_flx_default_metric_tenant_{self.tenant_id}"
            )
            default_metrics_collection = self.service.kvstore[default_metrics_collection_name]
            (
                default_metrics_records,
                default_metrics_collection_keys,
                default_metrics_collection_dict,
                last_page,
            ) = search_kv_collection_sdkmode(
                logging, self.service, default_metrics_collection_name, page=1, page_count=0, orderby="keyid"
            )

            logging.debug(
                f'instance_id={self.instance_id}, default_metrics_collection_dict="{json.dumps(default_metrics_collection_dict, indent=2)}"'
            )

            # end task
            #
            task_end = time.time()
            task_run_time = round((task_end - task_start), 3)
            logging.info(
                f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
            )

        #
        # splk-fqm specific collections
        #

        if self.component == "fqm":

            # set task
            #
            task_start = time.time()
            task_instance_id = get_uuid()
            task_name = "get_thresholds_collection_records"

            # Thresholds
            thresholds_collection_name = (
                f"kv_trackme_fqm_thresholds_tenant_{self.tenant_id}"
            )
            thresholds_collection = self.service.kvstore[thresholds_collection_name]
            (
                thresholds_records,
                thresholds_collection_keys,
                thresholds_collection_dict,
                last_page,
            ) = search_kv_collection_sdkmode(
                logging, self.service, thresholds_collection_name, page=1, page_count=0, orderby="keyid"
            )

            logging.debug(
                f'instance_id={self.instance_id}, thresholds_collection_dict="{json.dumps(thresholds_collection_dict, indent=2)}"'
            )

            # end task
            #
            task_end = time.time()
            task_run_time = round((task_end - task_start), 3)
            logging.info(
                f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
            )

        #
        # splk-wlk specific collections
        #

        if self.component == "wlk":

            # set task
            #
            task_start = time.time()
            task_instance_id = get_uuid()
            task_name = "get_thresholds_collection_records"

            # Thresholds
            thresholds_collection_name = (
                f"kv_trackme_wlk_thresholds_tenant_{self.tenant_id}"
            )
            try:
                thresholds_collection = self.service.kvstore[thresholds_collection_name]
                (
                    thresholds_records,
                    thresholds_collection_keys,
                    thresholds_collection_dict,
                    last_page,
                ) = search_kv_collection_sdkmode(
                    logging, self.service, thresholds_collection_name, page=1, page_count=0, orderby="keyid"
                )
            except Exception:
                thresholds_collection_dict = {}

            logging.debug(
                f'instance_id={self.instance_id}, thresholds_collection_dict="{json.dumps(thresholds_collection_dict, indent=2)}"'
            )

            # end task
            #
            task_end = time.time()
            task_run_time = round((task_end - task_start), 3)
            logging.info(
                f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
            )

        #
        # Virtual tenant account settings
        #

        # outliers tenant level settings
        # outliers tenant level settings (deprecated - kept for backward compatibility)
        # These are no longer used with score-based approach, but kept for backward compatibility
        tenant_outliers_set_state = int(vtenant_conf.get("outliers_set_state", 1))
        tenant_data_sampling_set_state = int(vtenant_conf.get("data_sampling_set_state", 1))

        #
        # Logical groups collection records
        #

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "get_logical_groups_collection_records"

        logical_group_coll = self.service.kvstore[
            f"kv_trackme_common_logical_group_tenant_{self.tenant_id}"
        ]

        (
            logical_coll_records,
            logical_coll_dict,
            logical_coll_members_list,
            logical_coll_members_dict,
            logical_coll_count,
        ) = get_logical_groups_collection_records(logical_group_coll)

        # log debug
        logging.debug(
            f'instance_id={self.instance_id}, function get_logical_groups_collection_records, logical_coll_dict="{json.dumps(logical_coll_dict, indent=2)}", logical_coll_count="{logical_coll_count}"'
        )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # Process records
        processed_records = []
        records_count = 0

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "process_records"
        
        for record in records:
            records_count += 1
            try:
                new_record = {}

                # append_record boolean, True by default unless specific use cases
                append_record = True

                # get object_value and key
                object_value = record.get("object", None)
                logging.debug(
                    f'instance_id={self.instance_id}, object="{object_value}", record="{json.dumps(record, indent=2)}"'
                )

                # save the current value of object_state in the record as kvcurrent_object_state, we manipulate real state calculations
                # and we need the original state in some conditions (sla)
                record["kvcurrent_object_state"] = record.get("object_state", "N/A")

                # The value for key is normally in the field keyid, but in some cases it is in the field key or _key
                # use keyid, key, _key in that order of preference
                if "keyid" in record:
                    key_value = record.get("keyid", None)
                elif "object_id" in record:
                    key_value = record.get("object_id", None)
                elif "key" in record:
                    key_value = record.get("key", None)
                elif "_key" in record:
                    key_value = record.get("_key", None)
                else:
                    key_value = None

                # get the score for the object and add to the record
                try:
                    score = int(scores_dict.get(key_value, {}).get("score", 0))
                except:
                    score = 0
                try:
                    score_outliers = int(scores_dict.get(key_value, {}).get("score_outliers", 0))
                except:
                    score_outliers = 0
                score_source = scores_dict.get(key_value, {}).get("score_source", [])
                record["score"] = score
                record["score_outliers"] = score_outliers
                record["score_source"] = score_source

                #
                # Dynamic priority
                #

                dynamic_priority_lookup(
                    key_value,
                    priority_collection_keys,
                    priority_collection_dict,
                    record,
                )

                #
                # Dynamic tags
                #

                dynamic_tags_lookup(
                    key_value,
                    tags_collection_keys,
                    tags_collection_dict,
                    record,
                )

                #
                # Dynamic sla_class
                #

                dynamic_sla_class_lookup(
                    key_value,
                    sla_collection_keys,
                    sla_collection_dict,
                    record,
                )

                #
                # Disruption queue
                #
                
                # Aggregate disruption_min_time_sec: take maximum value across all trackers
                aggregated_disruption_min_time_sec = default_disruption_min_time_sec
                if "disruption_min_time_sec" in record:
                    try:
                        disruption_min_time_value = record.get("disruption_min_time_sec")
                        if disruption_min_time_value:
                            disruption_times_by_tracker = None
                            
                            # Parse if it's a JSON string
                            if isinstance(disruption_min_time_value, str):
                                try:
                                    disruption_times_by_tracker = json.loads(disruption_min_time_value)
                                except (json.JSONDecodeError, TypeError):
                                    # If parsing fails, might be old format numeric value
                                    try:
                                        aggregated_disruption_min_time_sec = max(
                                            default_disruption_min_time_sec,
                                            int(float(disruption_min_time_value))
                                        )
                                    except (ValueError, TypeError):
                                        pass
                            elif isinstance(disruption_min_time_value, dict):
                                disruption_times_by_tracker = disruption_min_time_value
                            else:
                                # Numeric value (old format)
                                try:
                                    aggregated_disruption_min_time_sec = max(
                                        default_disruption_min_time_sec,
                                        int(float(disruption_min_time_value))
                                    )
                                except (ValueError, TypeError):
                                    pass
                            
                            # If tracker-keyed format, take maximum across all trackers
                            if disruption_times_by_tracker and isinstance(disruption_times_by_tracker, dict):
                                max_disruption_time = max(
                                    int(float(v)) for v in disruption_times_by_tracker.values()
                                )
                                aggregated_disruption_min_time_sec = max(
                                    default_disruption_min_time_sec,
                                    max_disruption_time
                                )
                    except Exception as e:
                        logging.error(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                            f'failed to aggregate disruption_min_time_sec, exception="{str(e)}"'
                        )

                disruption_queue_record = disruption_queue_lookup(
                    key_value,
                    disruption_queue_collection_keys,
                    disruption_queue_collection_dict,
                    aggregated_disruption_min_time_sec,
                )
                if disruption_queue_record:
                    logging.debug(
                        f'instance_id={self.instance_id}, disruption_queue_record="type={type(disruption_queue_record)}, {json.dumps(disruption_queue_record, indent=2)}"'
                    )

                #
                # splk-dsm
                #

                # get record fields depending on the component
                if self.component == "dsm":

                    # first check blocklist
                    if (
                        datagen_collection_blocklist_not_regex_dict
                        or datagen_collection_blocklist_regex_dict
                    ):
                        append_record = apply_blocklist(
                            record,
                            datagen_collection_blocklist_not_regex_dict,
                            datagen_collection_blocklist_regex_dict,
                        )

                    if append_record:

                        # get outliers and data sampling
                        try:
                            isOutlier = int(record.get("isOutlier", 0))
                        except:
                            isOutlier = 0

                        try:
                            OutliersDisabled = int(record.get("OutliersDisabled", 0))
                        except:
                            OutliersDisabled = 0

                        try:
                            isAnomaly = int(record.get("isAnomaly", 0))
                        except:
                            isAnomaly = 0

                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", isAnomaly="{isAnomaly}"'
                        )

                        # get future_tolerance
                        future_tolerance = record.get("future_tolerance", 0)
                        try:
                            future_tolerance = float(future_tolerance)
                        except:
                            future_tolerance = 0

                        #
                        # DSM Sampling
                        #

                        # call function dsm_sampling_lookup
                        dsm_sampling_lookup(
                            object_value,
                            sampling_collection_keys,
                            sampling_collection_dict,
                            record,
                        )

                        # check the value of allow_adaptive_delay (accepted values: true, false - as string)
                        allow_adaptive_delay = record.get("allow_adaptive_delay", "true")
                        if allow_adaptive_delay not in ["true", "false"]:
                            # log a warning
                            logging.warning(
                                f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", allow_adaptive_delay="{allow_adaptive_delay}" is not a valid value (accepted values: true, false), setting to "true"'
                            )                            
                            allow_adaptive_delay = "true"
                            # update the record
                            record["allow_adaptive_delay"] = "true"

                        # get actual primary KPI values
                        data_last_ingestion_lag_seen = record.get(
                            "data_last_ingestion_lag_seen", 0
                        )
                        if data_last_ingestion_lag_seen == "":
                            data_last_ingestion_lag_seen = 0
                        try:
                            data_last_ingestion_lag_seen = float(
                                data_last_ingestion_lag_seen
                            )
                        except:
                            data_last_ingestion_lag_seen = 0
                        data_last_lag_seen = record.get("data_last_lag_seen", 0)

                        # get per entity thresholds
                        data_max_lag_allowed = float(
                            record.get("data_max_lag_allowed", 0)
                        )
                        data_max_delay_allowed = float(
                            record.get("data_max_delay_allowed", 0)
                        )

                        # resolve lagging class threshold (overrides entity thresholds if matched)
                        lc_matched = False
                        lc_delay_mode = None
                        lc_resolved_delay = None
                        lc_active_slot = None
                        if lagging_classes_records:
                            (
                                lc_matched,
                                lc_override_lag,
                                lc_override_delay,
                                lc_delay_mode,
                                lc_resolved_delay,
                                lc_active_slot,
                                lc_match_info,
                            ) = resolve_lagging_class_threshold(
                                record, lagging_classes_records
                            )
                            if lc_matched:
                                # Threshold intent lock — a pinned threshold is
                                # never overridden by a lagging class on the
                                # scheduled decision-maker (persistence) path.
                                if lc_override_lag is not None and not is_lag_threshold_locked(
                                    record
                                ):
                                    data_max_lag_allowed = lc_override_lag
                                    record["data_max_lag_allowed"] = lc_override_lag
                                if (
                                    lc_delay_mode == "static"
                                    and lc_override_delay is not None
                                    and not is_delay_threshold_locked(record)
                                ):
                                    data_max_delay_allowed = lc_override_delay
                                    record["data_max_delay_allowed"] = lc_override_delay
                                # populate transient lagging class fields on the record for UI visibility
                                record["lagging_class_matched"] = "true"
                                record["lagging_class_name"] = str(lc_match_info.get("name", ""))
                                record["lagging_class_level"] = str(lc_match_info.get("level", ""))
                                record["lagging_class_match_mode"] = str(lc_match_info.get("match_mode", ""))
                                record["lagging_class_delay_mode"] = str(lc_delay_mode) if lc_delay_mode else ""
                                record["lagging_class_key"] = str(lc_match_info.get("_key", ""))
                                logging.debug(
                                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", lagging_class_matched=True, lc_match_info="{lc_match_info}", lc_delay_mode="{lc_delay_mode}", data_max_lag_allowed="{data_max_lag_allowed}", data_max_delay_allowed="{data_max_delay_allowed}"'
                                )
                        if not lc_matched:
                            record["lagging_class_matched"] = "false"
                            record["lagging_class_name"] = ""
                            record["lagging_class_level"] = ""
                            record["lagging_class_match_mode"] = ""
                            record["lagging_class_delay_mode"] = ""
                            record["lagging_class_key"] = ""

                        min_dcount_threshold = record.get("min_dcount_threshold", 0)
                        try:
                            min_dcount_threshold = float(min_dcount_threshold)
                        except:
                            min_dcount_threshold = 0

                        # get dcount host related information
                        min_dcount_host = record.get("min_dcount_host", "any")
                        try:
                            min_dcount_host = float(min_dcount_host)
                        except:
                            pass
                        min_dcount_field = record.get("min_dcount_field", None)

                        # Get logical group information

                        # get logical group information: object_group_key
                        object_group_key = record.get("object_group_key", "")

                        # from logical_coll_dict, get object_logical_group_dict by object_group_key, this is sent to the status function
                        object_logical_group_dict = logical_coll_dict.get(
                            object_group_key, {}
                        )

                        # get data_last_ingest, data_last_time_seen, data_last_time_seen_idx (epochtime)
                        data_last_ingest = record.get("data_last_ingest", 0)
                        try:
                            data_last_ingest = float(data_last_ingest)
                        except:
                            pass
                        data_last_time_seen = record.get("data_last_time_seen", 0)
                        if data_last_time_seen == "":
                            data_last_time_seen = 0
                        try:
                            data_last_time_seen = float(data_last_time_seen)
                        except:
                            data_last_time_seen = 0
                        data_last_time_seen_idx = record.get(
                            "data_last_time_seen_idx", 0
                        )
                        try:
                            data_last_time_seen_idx = float(data_last_time_seen_idx)
                        except:
                            pass

                        # get monitoring time policy and rules (new fields)
                        monitoring_time_policy = record.get("monitoring_time_policy", None)
                        # if unset yet, use the tenant level and add to the record
                        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
                            monitoring_time_policy = default_monitoring_time_policy
                            record["monitoring_time_policy"] = default_monitoring_time_policy
                        monitoring_time_rules = record.get("monitoring_time_rules", None)
                        
                        # call get_monitoring_time_status and define isUnderMonitoring, monitoring_anomaly_reason, isUnderMonitoringMsg
                        (
                            isUnderMonitoring,
                            monitoring_anomaly_reason,
                            isUnderMonitoringMsg,
                        ) = get_monitoring_time_status(
                            monitoring_time_policy,
                            monitoring_time_rules,
                        )

                        # Get score data for this object_id (key_value) from scores_dict
                        score_data = scores_dict.get(key_value, {})
                        score = score_data.get("score", 0)
                        score_outliers = score_data.get("score_outliers", 0)
                        
                        # call get_outliers_status and define isOutlier (with hybrid scoring)
                        isOutlier = get_outliers_status(
                            isOutlier, OutliersDisabled, tenant_outliers_set_state, score_outliers=score_outliers
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", OutliersDisabled="{OutliersDisabled}", tenant_outliers_set_state="{tenant_outliers_set_state}", score_outliers="{score_outliers}"'
                        )

                        # call get_data_sampling_status and define isAnomaly
                        isAnomaly = get_data_sampling_status(
                            record.get("data_sample_status_colour"),
                            record.get("data_sample_feature"),
                            tenant_data_sampling_set_state,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isAnomaly="{isAnomaly}", tenant_data_sampling_set_state="{tenant_data_sampling_set_state}"'
                        )

                        # call get_future_status and define isFuture
                        (
                            isFuture,
                            isFutureMsg,
                            merged_future_tolerance,
                        ) = get_future_status(
                            future_tolerance,
                            system_future_tolerance,
                            data_last_lag_seen,
                            data_last_ingestion_lag_seen,
                            data_last_time_seen,
                            data_last_ingest,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isFuture="{isFuture}", future_tolerance="{future_tolerance}", system_future_tolerance="{system_future_tolerance}", merged_future_tolerance="{merged_future_tolerance}", data_last_lag_seen="{data_last_lag_seen}", isFutureMsg="{isFutureMsg}"'
                        )

                        # call get_is_under_dcount_host and define isUnderDcountHost
                        (
                            isUnderDcountHost,
                            isUnderDcountHostMsg,
                        ) = get_is_under_dcount_host(
                            min_dcount_host, min_dcount_threshold, min_dcount_field
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isUnderDcountHost="{isUnderDcountHost}", isUnderDcountHostMsg="{isUnderDcountHostMsg}", min_dcount_host="{min_dcount_host}", min_dcount_threshold="{min_dcount_threshold}"'
                        )

                        # call get_dsm_latency_status and define isUnderLatencyAlert and isUnderLatencyMessage
                        (
                            isUnderLatencyAlert,
                            isUnderLatencyMessage,
                        ) = get_dsm_latency_status(
                            data_last_ingestion_lag_seen,
                            data_max_lag_allowed,
                            data_last_ingest,
                            data_last_time_seen,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isUnderLatencyAlert="{isUnderLatencyAlert}", isUnderLatencyMessage="{isUnderLatencyMessage}", data_last_ingestion_lag_seen="{data_last_ingestion_lag_seen}", data_max_lag_allowed="{data_max_lag_allowed}", data_last_ingest="{data_last_ingest}", data_last_time_seen="{data_last_time_seen}"'
                        )

                        # resolve variable delay threshold
                        # Lagging class variable delay takes precedence over entity-level variable delay
                        # Lagging class static delay is authoritative and skips entity-level variable delay
                        if lc_matched and lc_delay_mode == "variable":
                            # Use lagging class variable delay
                            resolved_threshold = lc_resolved_delay
                            active_slot_name = lc_active_slot
                            is_variable = True
                        elif lc_matched and lc_delay_mode == "static":
                            # Lagging class static delay is authoritative, do not allow
                            # entity-level variable delay to override it
                            resolved_threshold = None
                            active_slot_name = None
                            is_variable = False
                        else:
                            # No lagging class match, fall through to entity-level variable delay
                            variable_delay_record = variable_delay_collection_dict.get(key_value, None)
                            (
                                resolved_threshold,
                                active_slot_name,
                                is_variable,
                            ) = resolve_variable_delay_threshold(
                                record,
                                variable_delay_record,
                            )

                        # Threshold intent lock — a pinned delay threshold must
                        # govern the decision/alert path and IGNORE lagging
                        # classes. But a locked VARIABLE-policy entity must keep
                        # evaluating against its OWN slots (time-aware), not
                        # collapse to a flat static value. Re-resolve from the
                        # entity's own variable-delay record: variable entities
                        # keep their slots, static entities resolve to
                        # is_variable=False and use the pinned data_max_delay_allowed.
                        if is_delay_threshold_locked(record):
                            variable_delay_record = variable_delay_collection_dict.get(key_value, None)
                            (
                                resolved_threshold,
                                active_slot_name,
                                is_variable,
                            ) = resolve_variable_delay_threshold(
                                record,
                                variable_delay_record,
                            )

                        # populate transient variable delay fields on the record
                        if is_variable:
                            record["variable_delay_active_slot"] = str(active_slot_name) if active_slot_name else ""
                            record["variable_delay_active_threshold"] = str(int(round(resolved_threshold, 0)))
                        else:
                            record["variable_delay_active_slot"] = ""
                            record["variable_delay_active_threshold"] = ""

                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", variable_delay_policy="{record.get("variable_delay_policy", "static")}", is_variable="{is_variable}", active_slot_name="{active_slot_name}", resolved_threshold="{resolved_threshold}", lc_matched="{lc_matched}", lc_delay_mode="{lc_delay_mode}"'
                        )

                        # call get_dsm_delay_status and define isUnderDelayAlert and isUnderDelayMessage
                        (
                            isUnderDelayAlert,
                            isUnderDelayMessage,
                        ) = get_dsm_delay_status(
                            data_last_lag_seen,
                            data_max_delay_allowed,
                            data_last_ingest,
                            data_last_time_seen,
                            resolved_max_delay_allowed=resolved_threshold if is_variable else None,
                            variable_delay_slot_name=active_slot_name if is_variable else None,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isUnderDelayAlert="{isUnderDelayAlert}", isUnderDelayMessage="{isUnderDelayMessage}", data_last_lag_seen="{data_last_lag_seen}", data_max_delay_allowed="{data_max_delay_allowed}", resolved_threshold="{resolved_threshold}", data_last_ingest="{data_last_ingest}", data_last_time_seen="{data_last_time_seen}"'
                        )

                        # call set_dsm_status and define object_state and anomaly_reason (with hybrid scoring)
                        (
                            object_state,
                            status_message,
                            status_message_json,
                            anomaly_reason,
                        ) = set_dsm_status(
                            logging,
                            self._metadata.searchinfo.splunkd_uri,
                            self._metadata.searchinfo.session_key,
                            self.tenant_id,
                            record,
                            isOutlier,
                            isAnomaly,
                            isFuture,
                            isFutureMsg,
                            isUnderMonitoring,
                            isUnderMonitoringMsg,
                            isUnderDcountHost,
                            isUnderDcountHostMsg,
                            object_logical_group_dict,
                            isUnderLatencyAlert,
                            isUnderLatencyMessage,
                            isUnderDelayAlert,
                            isUnderDelayMessage,
                            disruption_queue_collection,
                            disruption_queue_record,
                            source_handler="trackmedecisionmaker",
                            monitoring_anomaly_reason=monitoring_anomaly_reason,
                            score=score,
                            score_outliers=score_outliers,
                            vtenant_account=vtenant_conf,
                            delay_is_variable=is_variable,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, set_dsm_status, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
                        )

                        # insert our main fields
                        new_record["object_state"] = object_state
                        new_record["status_message"] = " | ".join(status_message)
                        new_record["status_message_json"] = status_message_json
                        new_record["anomaly_reason"] = "|".join(anomaly_reason)

                        # future tolerance
                        try:
                            new_record["future_tolerance"] = int(
                                round(merged_future_tolerance, 0)
                            )
                        except:
                            new_record["future_tolerance"] = -600

                        # convert data_last_time_seen to last_time from epoch
                        last_time = convert_epoch_to_datetime(data_last_time_seen)
                        new_record["last_time"] = last_time

                        # convert data_last_ingest to last_ingest from epoch
                        last_ingest = convert_epoch_to_datetime(data_last_ingest)
                        new_record["last_ingest"] = last_ingest

                        # convert data_last_time_seen_idx to last_time_idx from epoch
                        last_time_idx = convert_epoch_to_datetime(data_last_time_seen)
                        new_record["last_time_idx"] = last_time_idx

                        # get and convert latest_flip_time from epoch
                        latest_flip_time_human = record.get("latest_flip_time", 0)
                        try:
                            latest_flip_time_human = float(latest_flip_time_human)
                        except:
                            latest_flip_time_human = 0
                        new_record["latest_flip_time_human"] = (
                            convert_epoch_to_datetime(latest_flip_time_human)
                        )

                        # sla_timer
                        get_sla_timer(record, sla_classes, sla_default_class)

                #
                # splk-dhm
                #

                elif self.component == "dhm":

                    # first check blocklist
                    if (
                        datagen_collection_blocklist_not_regex_dict
                        or datagen_collection_blocklist_regex_dict
                    ):
                        append_record = apply_blocklist(
                            record,
                            datagen_collection_blocklist_not_regex_dict,
                            datagen_collection_blocklist_regex_dict,
                        )

                    if append_record:

                        # get splk_dhm_st_summary
                        splk_dhm_st_summary = record.get("splk_dhm_st_summary", None)
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", splk_dhm_st_summary="{splk_dhm_st_summary}"'
                        )

                        # get outliers and data sampling
                        try:
                            isOutlier = int(record.get("isOutlier", 0))
                        except:
                            isOutlier = 0

                        try:
                            OutliersDisabled = int(record.get("OutliersDisabled", 0))
                        except:
                            OutliersDisabled = 0

                        try:
                            isAnomaly = int(record.get("isAnomaly", 0))
                        except:
                            isAnomaly = 0

                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", isAnomaly="{isAnomaly}"'
                        )

                        # get future_tolerance
                        future_tolerance = record.get("future_tolerance", 0)
                        try:
                            future_tolerance = float(future_tolerance)
                        except:
                            future_tolerance = 0

                        # check the value of allow_adaptive_delay (accepted values: true, false - as string)
                        allow_adaptive_delay = record.get("allow_adaptive_delay", "true")
                        if allow_adaptive_delay not in ["true", "false"]:
                            # log a warning
                            logging.warning(
                                f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", allow_adaptive_delay="{allow_adaptive_delay}" is not a valid value (accepted values: true, false), setting to "true"'
                            )                            
                            allow_adaptive_delay = "true"
                            # update the record
                            record["allow_adaptive_delay"] = "true"

                        # get actual primary KPI values
                        data_last_ingestion_lag_seen = record.get(
                            "data_last_ingestion_lag_seen", 0
                        )
                        if data_last_ingestion_lag_seen == "":
                            data_last_ingestion_lag_seen = 0
                        try:
                            data_last_ingestion_lag_seen = float(
                                data_last_ingestion_lag_seen
                            )
                        except:
                            data_last_ingestion_lag_seen = 0
                        data_last_lag_seen = record.get("data_last_lag_seen", 0)

                        # get per entity thresholds
                        data_max_lag_allowed = float(
                            record.get("data_max_lag_allowed", 0)
                        )
                        data_max_delay_allowed = float(
                            record.get("data_max_delay_allowed", 0)
                        )

                        # resolve lagging class threshold (overrides entity thresholds if matched)
                        lc_matched = False
                        lc_delay_mode = None
                        lc_resolved_delay = None
                        lc_active_slot = None
                        if lagging_classes_records:
                            (
                                lc_matched,
                                lc_override_lag,
                                lc_override_delay,
                                lc_delay_mode,
                                lc_resolved_delay,
                                lc_active_slot,
                                lc_match_info,
                            ) = resolve_lagging_class_threshold(
                                record, lagging_classes_records
                            )
                            if lc_matched:
                                # Threshold intent lock — a pinned threshold is
                                # never overridden by a lagging class on the
                                # scheduled decision-maker (persistence) path.
                                if lc_override_lag is not None and not is_lag_threshold_locked(
                                    record
                                ):
                                    data_max_lag_allowed = lc_override_lag
                                    record["data_max_lag_allowed"] = lc_override_lag
                                if (
                                    lc_delay_mode == "static"
                                    and lc_override_delay is not None
                                    and not is_delay_threshold_locked(record)
                                ):
                                    data_max_delay_allowed = lc_override_delay
                                    record["data_max_delay_allowed"] = lc_override_delay
                                # populate transient lagging class fields on the record for UI visibility
                                record["lagging_class_matched"] = "true"
                                record["lagging_class_name"] = str(lc_match_info.get("name", ""))
                                record["lagging_class_level"] = str(lc_match_info.get("level", ""))
                                record["lagging_class_match_mode"] = str(lc_match_info.get("match_mode", ""))
                                record["lagging_class_delay_mode"] = str(lc_delay_mode) if lc_delay_mode else ""
                                record["lagging_class_key"] = str(lc_match_info.get("_key", ""))
                                logging.debug(
                                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", lagging_class_matched=True, lc_match_info="{lc_match_info}", lc_delay_mode="{lc_delay_mode}", data_max_lag_allowed="{data_max_lag_allowed}", data_max_delay_allowed="{data_max_delay_allowed}"'
                                )
                        if not lc_matched:
                            record["lagging_class_matched"] = "false"
                            record["lagging_class_name"] = ""
                            record["lagging_class_level"] = ""
                            record["lagging_class_match_mode"] = ""
                            record["lagging_class_delay_mode"] = ""
                            record["lagging_class_key"] = ""

                        # Get logical group information

                        # get logical group information: object_group_key
                        object_group_key = record.get("object_group_key", "")

                        # from logical_coll_dict, get object_logical_group_dict by object_group_key, this is sent to the status function
                        object_logical_group_dict = logical_coll_dict.get(
                            object_group_key, {}
                        )

                        # get data_last_ingest, data_last_time_seen, data_last_time_seen_idx (epochtime)
                        data_last_ingest = record.get("data_last_ingest", 0)
                        try:
                            data_last_ingest = float(data_last_ingest)
                        except:
                            pass
                        data_last_time_seen = record.get("data_last_time_seen", 0)
                        if data_last_time_seen == "":
                            data_last_time_seen = 0
                        try:
                            data_last_time_seen = float(data_last_time_seen)
                        except:
                            data_last_time_seen = 0
                        data_last_time_seen_idx = record.get(
                            "data_last_time_seen_idx", 0
                        )
                        try:
                            data_last_time_seen_idx = float(data_last_time_seen_idx)
                        except:
                            pass

                        # get monitoring time policy and rules (new fields)
                        monitoring_time_policy = record.get("monitoring_time_policy", None)
                        # if unset yet, use the tenant level and add to the record
                        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
                            monitoring_time_policy = default_monitoring_time_policy
                            record["monitoring_time_policy"] = default_monitoring_time_policy
                        monitoring_time_rules = record.get("monitoring_time_rules", None)
                        
                        # call get_monitoring_time_status and define isUnderMonitoring, monitoring_anomaly_reason, isUnderMonitoringMsg
                        (
                            isUnderMonitoring,
                            monitoring_anomaly_reason,
                            isUnderMonitoringMsg,
                        ) = get_monitoring_time_status(
                            monitoring_time_policy,
                            monitoring_time_rules,
                        )

                        # Get score data for this object_id (key_value) from scores_dict
                        score_data = scores_dict.get(key_value, {})
                        score = score_data.get("score", 0)
                        score_outliers = score_data.get("score_outliers", 0)
                        
                        # call get_outliers_status and define isOutlier (with hybrid scoring)
                        isOutlier = get_outliers_status(
                            isOutlier, OutliersDisabled, tenant_outliers_set_state, score_outliers=score_outliers
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", OutliersDisabled="{OutliersDisabled}", tenant_outliers_set_state="{tenant_outliers_set_state}", score_outliers="{score_outliers}"'
                        )

                        # call get_future_status and define isFuture
                        (
                            isFuture,
                            isFutureMsg,
                            merged_future_tolerance,
                        ) = get_future_status(
                            future_tolerance,
                            system_future_tolerance,
                            data_last_lag_seen,
                            data_last_ingestion_lag_seen,
                            data_last_time_seen,
                            data_last_ingest,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isFuture="{isFuture}", future_tolerance="{future_tolerance}", system_future_tolerance="{system_future_tolerance}", merged_future_tolerance="{merged_future_tolerance}", data_last_lag_seen="{data_last_lag_seen}", isFutureMsg="{isFutureMsg}"'
                        )

                        # call get_dsm_latency_status and define isUnderLatencyAlert and isUnderLatencyMessage
                        (
                            isUnderLatencyAlert,
                            isUnderLatencyMessage,
                        ) = get_dsm_latency_status(
                            data_last_ingestion_lag_seen,
                            data_max_lag_allowed,
                            data_last_ingest,
                            data_last_time_seen,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isUnderLatencyAlert="{isUnderLatencyAlert}", isUnderLatencyMessage="{isUnderLatencyMessage}", data_last_ingestion_lag_seen="{data_last_ingestion_lag_seen}", data_max_lag_allowed="{data_max_lag_allowed}", data_last_ingest="{data_last_ingest}", data_last_time_seen="{data_last_time_seen}"'
                        )

                        # resolve variable delay threshold
                        # Lagging class variable delay takes precedence over entity-level variable delay
                        # Lagging class static delay is authoritative and skips entity-level variable delay
                        if lc_matched and lc_delay_mode == "variable":
                            # Use lagging class variable delay
                            resolved_threshold = lc_resolved_delay
                            active_slot_name = lc_active_slot
                            is_variable = True
                        elif lc_matched and lc_delay_mode == "static":
                            # Lagging class static delay is authoritative, do not allow
                            # entity-level variable delay to override it
                            resolved_threshold = None
                            active_slot_name = None
                            is_variable = False
                        else:
                            # No lagging class match, fall through to entity-level variable delay
                            variable_delay_record = variable_delay_collection_dict.get(key_value, None)
                            (
                                resolved_threshold,
                                active_slot_name,
                                is_variable,
                            ) = resolve_variable_delay_threshold(
                                record,
                                variable_delay_record,
                            )

                        # Threshold intent lock — a pinned delay threshold must
                        # govern the decision/alert path and IGNORE lagging
                        # classes. But a locked VARIABLE-policy entity must keep
                        # evaluating against its OWN slots (time-aware), not
                        # collapse to a flat static value. Re-resolve from the
                        # entity's own variable-delay record: variable entities
                        # keep their slots, static entities resolve to
                        # is_variable=False and use the pinned data_max_delay_allowed.
                        if is_delay_threshold_locked(record):
                            variable_delay_record = variable_delay_collection_dict.get(key_value, None)
                            (
                                resolved_threshold,
                                active_slot_name,
                                is_variable,
                            ) = resolve_variable_delay_threshold(
                                record,
                                variable_delay_record,
                            )

                        # populate transient variable delay fields on the record
                        if is_variable:
                            record["variable_delay_active_slot"] = str(active_slot_name) if active_slot_name else ""
                            record["variable_delay_active_threshold"] = str(int(round(resolved_threshold, 0)))
                        else:
                            record["variable_delay_active_slot"] = ""
                            record["variable_delay_active_threshold"] = ""

                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", variable_delay_policy="{record.get("variable_delay_policy", "static")}", is_variable="{is_variable}", active_slot_name="{active_slot_name}", resolved_threshold="{resolved_threshold}", lc_matched="{lc_matched}", lc_delay_mode="{lc_delay_mode}"'
                        )

                        # call get_dsm_delay_status and define isUnderDelayAlert and isUnderDelayMessage
                        (
                            isUnderDelayAlert,
                            isUnderDelayMessage,
                        ) = get_dsm_delay_status(
                            data_last_lag_seen,
                            data_max_delay_allowed,
                            data_last_ingest,
                            data_last_time_seen,
                            resolved_max_delay_allowed=resolved_threshold if is_variable else None,
                            variable_delay_slot_name=active_slot_name if is_variable else None,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isUnderDelayAlert="{isUnderDelayAlert}", isUnderDelayMessage="{isUnderDelayMessage}", data_last_lag_seen="{data_last_lag_seen}", data_max_delay_allowed="{data_max_delay_allowed}", resolved_threshold="{resolved_threshold}", data_last_ingest="{data_last_ingest}", data_last_time_seen="{data_last_time_seen}"'
                        )

                        # call set_dhm_status and define object_state and anomaly_reason (with hybrid scoring)
                        (
                            object_state,
                            status_message,
                            status_message_json,
                            anomaly_reason,
                            splk_dhm_alerting_policy,
                        ) = set_dhm_status(
                            logging,
                            self._metadata.searchinfo.splunkd_uri,
                            self._metadata.searchinfo.session_key,
                            self.tenant_id,
                            record,
                            isOutlier,
                            isFuture,
                            isFutureMsg,
                            isUnderMonitoring,
                            isUnderMonitoringMsg,
                            object_logical_group_dict,
                            isUnderLatencyAlert,
                            isUnderLatencyMessage,
                            isUnderDelayAlert,
                            isUnderDelayMessage,
                            default_splk_dhm_alerting_policy,
                            disruption_queue_collection,
                            disruption_queue_record,
                            source_handler="trackmedecisionmaker",
                            monitoring_anomaly_reason=monitoring_anomaly_reason,
                            score=score,
                            score_outliers=score_outliers,
                            vtenant_account=vtenant_conf,
                            delay_is_variable=is_variable,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
                        )

                        # insert our main fields
                        new_record["object_state"] = object_state
                        new_record["status_message"] = " | ".join(status_message)
                        new_record["status_message_json"] = status_message_json
                        new_record["anomaly_reason"] = "|".join(anomaly_reason)

                        # future tolerance
                        try:
                            new_record["future_tolerance"] = int(
                                round(merged_future_tolerance, 0)
                            )
                        except:
                            new_record["future_tolerance"] = -600

                        # specific for dhm
                        new_record["splk_dhm_alerting_policy"] = (
                            splk_dhm_alerting_policy
                        )

                        # convert data_last_time_seen to last_time from epoch
                        last_time = convert_epoch_to_datetime(data_last_time_seen)
                        new_record["last_time"] = last_time

                        # convert data_last_ingest to last_ingest from epoch
                        last_ingest = convert_epoch_to_datetime(data_last_ingest)
                        new_record["last_ingest"] = last_ingest

                        # convert data_last_time_seen_idx to last_time_idx from epoch
                        last_time_idx = convert_epoch_to_datetime(data_last_time_seen)
                        new_record["last_time_idx"] = last_time_idx

                        # get and convert latest_flip_time from epoch
                        latest_flip_time_human = record.get("latest_flip_time", 0)
                        try:
                            latest_flip_time_human = float(latest_flip_time_human)
                        except:
                            latest_flip_time_human = 0
                        new_record["latest_flip_time_human"] = (
                            convert_epoch_to_datetime(latest_flip_time_human)
                        )

                        # sla_timer
                        get_sla_timer(record, sla_classes, sla_default_class)

                #
                # splk-mhm
                #

                elif self.component == "mhm":

                    # first check blocklist
                    if (
                        datagen_collection_blocklist_not_regex_dict
                        or datagen_collection_blocklist_regex_dict
                    ):
                        append_record = apply_blocklist(
                            record,
                            datagen_collection_blocklist_not_regex_dict,
                            datagen_collection_blocklist_regex_dict,
                        )

                    if append_record:

                        # get metric_details
                        metric_details = record.get("metric_details", None)
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", metric_details="{metric_details}"'
                        )

                        # Get logical group information

                        # get logical group information: object_group_key
                        object_group_key = record.get("object_group_key", "")

                        # from logical_coll_dict, get object_logical_group_dict by object_group_key, this is sent to the status function
                        object_logical_group_dict = logical_coll_dict.get(
                            object_group_key, {}
                        )

                        # get metric_last_time_seen (epochtime)
                        metric_last_time_seen = record.get("metric_last_time_seen", 0)
                        try:
                            metric_last_time_seen = float(metric_last_time_seen)
                        except:
                            pass

                        # Get score data for this object_id (key_value) from scores_dict
                        score_data = scores_dict.get(key_value, {})
                        score = score_data.get("score", 0)
                        score_outliers = score_data.get("score_outliers", 0)

                        # call get_future_metrics_status and define isFuture
                        isFuture, isFutureMsg = get_future_metrics_status(
                            system_future_tolerance,
                            metric_last_time_seen,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isFuture="{isFuture}", system_future_tolerance="{system_future_tolerance}", metric_last_time_seen="{metric_last_time_seen}", isFutureMsg="{isFutureMsg}"'
                        )

                        # get monitoring time policy and rules
                        monitoring_time_policy = record.get("monitoring_time_policy", None)
                        # if unset yet, use the tenant level and add to the record
                        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
                            monitoring_time_policy = default_monitoring_time_policy
                            record["monitoring_time_policy"] = default_monitoring_time_policy
                        monitoring_time_rules = record.get("monitoring_time_rules", None)

                        # call get_monitoring_time_status and define isUnderMonitoring, monitoring_anomaly_reason, isUnderMonitoringMsg
                        (
                            isUnderMonitoring,
                            monitoring_anomaly_reason,
                            isUnderMonitoringMsg,
                        ) = get_monitoring_time_status(
                            monitoring_time_policy,
                            monitoring_time_rules,
                        )

                        # call set_mhm_status and define object_state and anomaly_reason (with hybrid scoring)
                        (
                            object_state,
                            status_message,
                            status_message_json,
                            anomaly_reason,
                        ) = set_mhm_status(
                            logging,
                            self._metadata.searchinfo.splunkd_uri,
                            self._metadata.searchinfo.session_key,
                            self.tenant_id,
                            record,
                            metric_details,
                            isFuture,
                            isFutureMsg,
                            isUnderMonitoring,
                            isUnderMonitoringMsg,
                            object_logical_group_dict,
                            disruption_queue_collection,
                            disruption_queue_record,
                            source_handler="trackmedecisionmaker",
                            monitoring_anomaly_reason=monitoring_anomaly_reason,
                            score=score,
                            score_outliers=score_outliers,
                            vtenant_account=vtenant_conf,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
                        )

                        # insert our main fields
                        new_record["object_state"] = object_state
                        new_record["status_message"] = " | ".join(status_message)
                        new_record["status_message_json"] = status_message_json
                        new_record["anomaly_reason"] = "|".join(anomaly_reason)

                        # convert metric_last_time_seen to last_time from epoch
                        last_time = convert_epoch_to_datetime(metric_last_time_seen)
                        new_record["last_time"] = last_time

                        # get and convert latest_flip_time from epoch
                        latest_flip_time_human = record.get("latest_flip_time", 0)
                        try:
                            latest_flip_time_human = float(latest_flip_time_human)
                        except:
                            latest_flip_time_human = 0
                        new_record["latest_flip_time_human"] = (
                            convert_epoch_to_datetime(latest_flip_time_human)
                        )

                        # sla_timer
                        get_sla_timer(record, sla_classes, sla_default_class)

                #
                # splk-flx
                #

                # get record fields depending on the component
                elif self.component == "flx":

                    # first check blocklist
                    if (
                        datagen_collection_blocklist_not_regex_dict
                        or datagen_collection_blocklist_regex_dict
                    ):
                        append_record = apply_blocklist(
                            record,
                            datagen_collection_blocklist_not_regex_dict,
                            datagen_collection_blocklist_regex_dict,
                        )

                    if append_record:

                        # get outliers
                        try:
                            isOutlier = int(record.get("isOutlier", 0))
                        except:
                            isOutlier = 0

                        try:
                            OutliersDisabled = int(record.get("OutliersDisabled", 0))
                        except:
                            OutliersDisabled = 0

                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}"'
                        )

                        # get monitoring time policy and rules (new fields)
                        monitoring_time_policy = record.get("monitoring_time_policy", None)
                        # if unset yet, use the tenant level and add to the record
                        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
                            monitoring_time_policy = default_monitoring_time_policy
                            record["monitoring_time_policy"] = default_monitoring_time_policy
                        monitoring_time_rules = record.get("monitoring_time_rules", None)

                        # Get logical group information

                        # get logical group information: object_group_key
                        object_group_key = record.get("object_group_key", "")

                        # from logical_coll_dict, get object_logical_group_dict by object_group_key, this is sent to the status function
                        object_logical_group_dict = logical_coll_dict.get(
                            object_group_key, {}
                        )

                        # call get_monitoring_time_status and define isUnderMonitoring, monitoring_anomaly_reason, isUnderMonitoringMsg
                        (
                            isUnderMonitoring,
                            monitoring_anomaly_reason,
                            isUnderMonitoringMsg,
                        ) = get_monitoring_time_status(
                            monitoring_time_policy,
                            monitoring_time_rules,
                        )

                        # Aggregate tracker-keyed JSON fields for concurrent trackers support
                        # Aggregate metrics: merge all trackers' metrics into a single dict
                        # This MUST be done BEFORE flx_check_dynamic_thresholds which expects aggregated metrics
                        if "metrics" in record:
                            try:
                                metrics_value = record.get("metrics")
                                if metrics_value:
                                    metrics_by_tracker = None
                                    
                                    # Parse if it's a JSON string
                                    if isinstance(metrics_value, str):
                                        try:
                                            metrics_by_tracker = json.loads(metrics_value)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format, skip aggregation
                                            pass
                                    elif isinstance(metrics_value, dict):
                                        metrics_by_tracker = metrics_value
                                    
                                    if metrics_by_tracker and isinstance(metrics_by_tracker, dict):
                                        # Check if it's tracker-keyed format (values are dicts) or old format (direct metrics dict)
                                        aggregated_metrics = {}
                                        is_tracker_keyed = False
                                        
                                        for key, value in metrics_by_tracker.items():
                                            if isinstance(value, dict):
                                                # Check if value looks like metrics (has numeric/string values) or tracker data
                                                # If all values in the nested dict are simple types, it's likely metrics
                                                if all(isinstance(v, (int, float, str, bool)) or v is None for v in value.values()):
                                                    # This is tracker-keyed format, merge all trackers' metrics
                                                    aggregated_metrics.update(value)
                                                    is_tracker_keyed = True
                                                else:
                                                    # Nested structure, might be tracker data
                                                    is_tracker_keyed = True
                                                    aggregated_metrics.update(value)
                                            else:
                                                # Simple value, old format
                                                break
                                        
                                        if is_tracker_keyed:
                                            # Remove internal "status" field from aggregated metrics if present
                                            # (This is a user metric named "status", not the entity status field)
                                            # NOTE: Do NOT capture this as fresh_status_from_search - it's a user metric, not entity status!
                                            # See GitHub issue: https://github.com/trackme-limited/trackme-report-issues/issues/1513
                                            if "status" in aggregated_metrics:
                                                del aggregated_metrics["status"]
                                            
                                            # Update record with aggregated metrics as dict (for backward compatibility)
                                            # Keep as dict since flx_check_dynamic_thresholds expects a dict
                                            # Handle empty aggregated_metrics case (e.g., {"tracker1": {}})
                                            record["metrics"] = aggregated_metrics
                                        elif not is_tracker_keyed:
                                            # Old format, keep as-is but ensure it's a dict and remove status field
                                            if isinstance(metrics_value, str):
                                                try:
                                                    old_metrics = json.loads(metrics_value)
                                                    if isinstance(old_metrics, dict) and "status" in old_metrics:
                                                        del old_metrics["status"]
                                                    record["metrics"] = old_metrics
                                                except:
                                                    record["metrics"] = {}
                                            else:
                                                if isinstance(metrics_by_tracker, dict) and "status" in metrics_by_tracker:
                                                    metrics_by_tracker = metrics_by_tracker.copy()
                                                    del metrics_by_tracker["status"]
                                                record["metrics"] = metrics_by_tracker
                            except Exception as e:
                                logging.error(
                                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                                    f'failed to aggregate metrics, exception="{str(e)}"'
                                )

                        # flx thresholds lookup
                        flx_thresholds_lookup(
                            object_value,
                            key_value,
                            record,
                            thresholds_collection_dict,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, dynamic_thresholds="{json.dumps(record.get("dynamic_thresholds", {}), indent=2)}"'
                        )

                        # flx check dynamic thresholds
                        threshold_alert, threshold_messages, threshold_scores = (
                            flx_check_dynamic_thresholds(
                                logging,
                                record.get("dynamic_thresholds", {}),
                                record.get("metrics", {}),
                            )
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, object_value="{object_value}", key_value="{key_value}", threshold_alert="{threshold_alert}", threshold_messages="{threshold_messages}", dynamic_thresholds="{json.dumps(record.get("dynamic_thresholds", {}), indent=2)}", metrics_record="{json.dumps(record.get("metrics", {}), indent=2)}"'
                        )

                        # flx drilldown searches lookup
                        try:
                            flx_drilldown_searches_lookup(
                                self.tenant_id,
                                record.get("tracker_name", ""),
                                record.get("account", "local"),
                                record,
                                drilldown_searches_collection_dict,
                            )
                            logging.debug(
                                f'instance_id={self.instance_id}, drilldown_search="{record.get("drilldown_search", "")}", drilldown_search_earliest="{record.get("drilldown_search_earliest", "")}", drilldown_search_latest="{record.get("drilldown_search_latest", "")}", drilldown_searches="{json.dumps(record.get("drilldown_searches", []), indent=2)}"'
                            )
                        except Exception as e:
                            logging.error(f"instance_id={self.instance_id}, Error in flx_drilldown_searches_lookup: {str(e)}")

                        # flx default metrics lookup
                        try:
                            flx_default_metrics_lookup(
                                self.tenant_id,
                                record.get("tracker_name", ""),
                                record,
                                default_metrics_collection_dict,
                            )
                            logging.debug(
                                f'instance_id={self.instance_id}, default_metric="{record.get("default_metric", "")}"'
                            )
                        except Exception as e:
                            logging.error(f"instance_id={self.instance_id}, Error in flx_default_metrics_lookup: {str(e)}")

                        # Get score data for this object_id (key_value) from scores_dict
                        score_data = scores_dict.get(key_value, {})
                        score = score_data.get("score", 0)
                        score_outliers = score_data.get("score_outliers", 0)
                        
                        # call get_outliers_status and define isOutlier (with hybrid scoring)
                        isOutlier = get_outliers_status(
                            isOutlier, OutliersDisabled, tenant_outliers_set_state, score_outliers=score_outliers
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", OutliersDisabled="{OutliersDisabled}", tenant_outliers_set_state="{tenant_outliers_set_state}", score_outliers="{score_outliers}"'
                        )

                        # Preserve tracker-keyed JSON for status, status_description and status_description_short
                        # We'll aggregate them temporarily for set_flx_status, then restore for proper merging in trackmepersistentfields
                        # IMPORTANT: The macro preserves status as status_preserved, but we need to check if it's tracker-keyed format
                        # If status_preserved exists and is tracker-keyed JSON, use it; otherwise check status field
                        status_tracker_keyed = None
                        status_desc_tracker_keyed = None
                        status_desc_short_tracker_keyed = None
                        
                        # Check if macro preserved tracker-keyed format (status_preserved field)
                        # The macro preserves status before mvindex operation
                        if "status_preserved" in record:
                            status_preserved = record.get("status_preserved")
                            if isinstance(status_preserved, str):
                                try:
                                    parsed = json.loads(status_preserved)
                                    if isinstance(parsed, dict):
                                        # It's tracker-keyed format from macro preservation
                                        status_tracker_keyed = status_preserved
                                except (json.JSONDecodeError, TypeError):
                                    pass
                            elif isinstance(status_preserved, dict):
                                status_tracker_keyed = json.dumps(status_preserved)
                        
                        # If not found in preserved field, check status field directly
                        if not status_tracker_keyed and "status" in record:
                            status_raw = record.get("status")
                            # Check if it's already tracker-keyed format (JSON string or dict)
                            if isinstance(status_raw, str):
                                # Try to parse as JSON to verify it's tracker-keyed format
                                try:
                                    parsed_status = json.loads(status_raw)
                                    if isinstance(parsed_status, dict):
                                        # It's tracker-keyed format, preserve it
                                        status_tracker_keyed = status_raw
                                except (json.JSONDecodeError, TypeError):
                                    # Not valid JSON, might be old format
                                    pass
                            elif isinstance(status_raw, dict):
                                # Already a dict (tracker-keyed format)
                                status_tracker_keyed = json.dumps(status_raw)
                        
                        # Check if macro preserved tracker-keyed format (status_description_preserved field)
                        if "status_description_preserved" in record:
                            status_desc_preserved = record.get("status_description_preserved")
                            if isinstance(status_desc_preserved, str):
                                try:
                                    parsed = json.loads(status_desc_preserved)
                                    if isinstance(parsed, dict):
                                        # It's tracker-keyed format from macro preservation
                                        status_desc_tracker_keyed = status_desc_preserved
                                except (json.JSONDecodeError, TypeError):
                                    # Check if it contains " | " separator (already aggregated)
                                    if " | " not in status_desc_preserved:
                                        status_desc_tracker_keyed = status_desc_preserved
                            elif isinstance(status_desc_preserved, dict):
                                status_desc_tracker_keyed = json.dumps(status_desc_preserved)
                        
                        # If not found in preserved field, check status_description field directly
                        if not status_desc_tracker_keyed and "status_description" in record:
                            status_desc_raw = record.get("status_description")
                            # Check if it's tracker-keyed format
                            if isinstance(status_desc_raw, str):
                                # Try to parse as JSON to verify it's tracker-keyed format
                                try:
                                    parsed_desc = json.loads(status_desc_raw)
                                    if isinstance(parsed_desc, dict):
                                        # It's tracker-keyed format, preserve it
                                        status_desc_tracker_keyed = status_desc_raw
                                except (json.JSONDecodeError, TypeError):
                                    # Check if it contains " | " separator (already aggregated)
                                    if " | " not in status_desc_raw:
                                        # Might be old format single string
                                        status_desc_tracker_keyed = status_desc_raw
                            elif isinstance(status_desc_raw, dict):
                                # Already a dict (tracker-keyed format)
                                status_desc_tracker_keyed = json.dumps(status_desc_raw)
                        
                        # Check if macro preserved tracker-keyed format (status_description_short_preserved field)
                        if "status_description_short_preserved" in record:
                            status_desc_short_preserved = record.get("status_description_short_preserved")
                            if isinstance(status_desc_short_preserved, str):
                                try:
                                    parsed = json.loads(status_desc_short_preserved)
                                    if isinstance(parsed, dict):
                                        # It's tracker-keyed format from macro preservation
                                        status_desc_short_tracker_keyed = status_desc_short_preserved
                                except (json.JSONDecodeError, TypeError):
                                    if " | " not in status_desc_short_preserved:
                                        status_desc_short_tracker_keyed = status_desc_short_preserved
                            elif isinstance(status_desc_short_preserved, dict):
                                status_desc_short_tracker_keyed = json.dumps(status_desc_short_preserved)
                        
                        # If not found in preserved field, check status_description_short field directly
                        if not status_desc_short_tracker_keyed and "status_description_short" in record:
                            status_desc_short_raw = record.get("status_description_short")
                            # Similar logic as status_description
                            if isinstance(status_desc_short_raw, str):
                                try:
                                    parsed_desc_short = json.loads(status_desc_short_raw)
                                    if isinstance(parsed_desc_short, dict):
                                        status_desc_short_tracker_keyed = status_desc_short_raw
                                except (json.JSONDecodeError, TypeError):
                                    if " | " not in status_desc_short_raw:
                                        status_desc_short_tracker_keyed = status_desc_short_raw
                            elif isinstance(status_desc_short_raw, dict):
                                status_desc_short_tracker_keyed = json.dumps(status_desc_short_raw)
                        
                        # Aggregate status temporarily for set_flx_status: worst-status logic (2 > 3 > 1)
                        if "status" in record:
                            try:
                                status_str = record.get("status")
                                if status_str:
                                    aggregated_status = None
                                    
                                    if isinstance(status_str, str):
                                        try:
                                            status_by_tracker = json.loads(status_str)
                                            if isinstance(status_by_tracker, dict):
                                                # Tracker-keyed format: apply worst-status logic
                                                status_values = list(status_by_tracker.values())
                                                if status_values:
                                                    # Worst-status logic: 2 (red) > 3 (orange) > 1 (green)
                                                    if 2 in status_values:
                                                        aggregated_status = 2  # Red
                                                    elif 3 in status_values:
                                                        aggregated_status = 3  # Orange
                                                    else:
                                                        aggregated_status = 1  # Green (all are 1)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format integer string
                                            try:
                                                aggregated_status = int(status_str)
                                            except (ValueError, TypeError):
                                                pass
                                    elif isinstance(status_str, dict):
                                        # Already a dict, apply worst-status logic
                                        status_values = list(status_str.values())
                                        if status_values:
                                            if 2 in status_values:
                                                aggregated_status = 2  # Red
                                            elif 3 in status_values:
                                                aggregated_status = 3  # Orange
                                            else:
                                                aggregated_status = 1  # Green
                                    elif isinstance(status_str, int):
                                        # Old format integer, use as-is
                                        aggregated_status = status_str
                                    
                                    # Temporarily update record with aggregated status for set_flx_status
                                    if aggregated_status is not None:
                                        record["status"] = aggregated_status
                            except Exception as e:
                                logging.error(
                                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                                    f'failed to aggregate status, exception="{str(e)}"'
                                )
                        
                        # Determine number of trackers to decide if we need prefix
                        num_trackers = 1
                        if "tracker_name" in record:
                            try:
                                tracker_name_value = record.get("tracker_name")
                                if tracker_name_value:
                                    if isinstance(tracker_name_value, str):
                                        try:
                                            tracker_names = json.loads(tracker_name_value)
                                            if isinstance(tracker_names, list):
                                                num_trackers = len(tracker_names)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be comma-separated string
                                            if "," in tracker_name_value:
                                                num_trackers = len([t.strip() for t in tracker_name_value.split(",")])
                                    elif isinstance(tracker_name_value, list):
                                        num_trackers = len(tracker_name_value)
                            except Exception:
                                pass
                        
                        # Aggregate status_description temporarily for set_flx_status: concatenate all trackers' descriptions
                        if "status_description" in record:
                            try:
                                status_desc_str = record.get("status_description")
                                if status_desc_str:
                                    if isinstance(status_desc_str, str):
                                        try:
                                            status_desc_by_tracker = json.loads(status_desc_str)
                                            if isinstance(status_desc_by_tracker, dict):
                                                # Check if it's tracker-keyed format
                                                status_descriptions = []
                                                for tracker_name, desc in status_desc_by_tracker.items():
                                                    if desc:
                                                        # Only add prefix if multiple trackers
                                                        if num_trackers > 1:
                                                            status_descriptions.append(f"{tracker_name}: {desc}")
                                                        else:
                                                            status_descriptions.append(desc)
                                                
                                                if status_descriptions:
                                                    # Temporarily update record with aggregated status_description for set_flx_status
                                                    record["status_description"] = " | ".join(status_descriptions)
                                                else:
                                                    # Empty, keep as-is
                                                    pass
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format string, keep as-is
                                            pass
                                    elif isinstance(status_desc_str, dict):
                                        # Already a dict, aggregate
                                        status_descriptions = []
                                        for tracker_name, desc in status_desc_str.items():
                                            if desc:
                                                # Only add prefix if multiple trackers
                                                if num_trackers > 1:
                                                    status_descriptions.append(f"{tracker_name}: {desc}")
                                                else:
                                                    status_descriptions.append(desc)
                                        
                                        if status_descriptions:
                                            # Temporarily update record with aggregated status_description for set_flx_status
                                            record["status_description"] = " | ".join(status_descriptions)
                            except Exception as e:
                                logging.error(
                                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                                    f'failed to aggregate status_description, exception="{str(e)}"'
                                )
                        
                        # Aggregate status_description_short temporarily for set_flx_status: concatenate all trackers' descriptions
                        if "status_description_short" in record:
                            try:
                                status_desc_short_str = record.get("status_description_short")
                                if status_desc_short_str:
                                    if isinstance(status_desc_short_str, str):
                                        try:
                                            status_desc_short_by_tracker = json.loads(status_desc_short_str)
                                            if isinstance(status_desc_short_by_tracker, dict):
                                                # Check if it's tracker-keyed format
                                                status_descriptions_short = []
                                                for tracker_name, desc in status_desc_short_by_tracker.items():
                                                    if desc:
                                                        # Only add prefix if multiple trackers
                                                        if num_trackers > 1:
                                                            status_descriptions_short.append(f"{tracker_name}: {desc}")
                                                        else:
                                                            status_descriptions_short.append(desc)
                                                
                                                if status_descriptions_short:
                                                    # Temporarily update record with aggregated status_description_short for set_flx_status
                                                    record["status_description_short"] = " | ".join(status_descriptions_short)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format string, keep as-is
                                            pass
                                    elif isinstance(status_desc_short_str, dict):
                                        # Already a dict, aggregate
                                        status_descriptions_short = []
                                        for tracker_name, desc in status_desc_short_str.items():
                                            if desc:
                                                # Only add prefix if multiple trackers
                                                if num_trackers > 1:
                                                    status_descriptions_short.append(f"{tracker_name}: {desc}")
                                                else:
                                                    status_descriptions_short.append(desc)
                                        
                                        if status_descriptions_short:
                                            # Temporarily update record with aggregated status_description_short for set_flx_status
                                            record["status_description_short"] = " | ".join(status_descriptions_short)
                            except Exception as e:
                                logging.error(
                                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                                    f'failed to aggregate status_description_short, exception="{str(e)}"'
                                )
                        
                        # Store upstream status values from the current search run
                        # These are the "live" values from the tracker execution, separate from potentially stale KVstore values
                        # See GitHub issue: https://github.com/trackme-limited/trackme-report-issues/issues/1513
                        # - upstream_status: Used by set_flx_status for status_not_met logic
                        # - upstream_status_description/short: Stored for visibility in UI and debugging
                        #   (allows comparison between live search results and persisted state)
                        if "status" in record:
                            record["upstream_status"] = record.get("status")
                        if "status_description" in record:
                            record["upstream_status_description"] = record.get("status_description")
                        if "status_description_short" in record:
                            record["upstream_status_description_short"] = record.get("status_description_short")
                        
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                            f'upstream_status="{record.get("upstream_status")}", upstream fields stored from current search run'
                        )
                        
                        # Generate per-tracker status messages before calling set_flx_status
                        # This allows us to store individual messages per tracker in status_message_json
                        per_tracker_status_messages = []
                        # Only generate per-tracker messages if we have valid tracker-keyed data
                        # Both status and status_description must be tracker-keyed format (JSON strings that parse to dicts)
                        if status_tracker_keyed and status_desc_tracker_keyed:
                            try:
                                # Parse tracker-keyed status and status_description
                                status_by_tracker = None
                                status_desc_by_tracker = None
                                
                                if isinstance(status_tracker_keyed, str):
                                    try:
                                        status_by_tracker = json.loads(status_tracker_keyed)
                                    except (json.JSONDecodeError, TypeError):
                                        pass
                                elif isinstance(status_tracker_keyed, dict):
                                    status_by_tracker = status_tracker_keyed
                                
                                if isinstance(status_desc_tracker_keyed, str):
                                    try:
                                        status_desc_by_tracker = json.loads(status_desc_tracker_keyed)
                                    except (json.JSONDecodeError, TypeError):
                                        pass
                                elif isinstance(status_desc_tracker_keyed, dict):
                                    status_desc_by_tracker = status_desc_tracker_keyed
                                
                                # Generate status message for each tracker
                                if isinstance(status_by_tracker, dict) and isinstance(status_desc_by_tracker, dict):
                                    # Verify we have tracker-keyed data (dict with multiple keys)
                                    if len(status_by_tracker) > 0 and len(status_desc_by_tracker) > 0:
                                        # Sort tracker names for consistent ordering
                                        sorted_tracker_names = sorted(status_by_tracker.keys())
                                        for tracker_name in sorted_tracker_names:
                                            tracker_status = status_by_tracker.get(tracker_name)
                                            tracker_status_desc = status_desc_by_tracker.get(tracker_name, "unknown")
                                            
                                            if tracker_status is None:
                                                continue
                                            
                                            # Skip if status_description contains " | " (already aggregated)
                                            if isinstance(tracker_status_desc, str) and " | " in tracker_status_desc:
                                                logging.warning(
                                                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                                                    f'tracker="{tracker_name}" has aggregated status_description, skipping per-tracker message generation'
                                                )
                                                continue
                                            
                                            try:
                                                tracker_status_int = int(tracker_status)
                                            except (ValueError, TypeError):
                                                tracker_status_int = 1
                                            
                                            # Generate status message for this tracker (same format as set_flx_status)
                                            # Use only this tracker's description, not the aggregated one
                                            # Only add prefix if multiple trackers
                                            if num_trackers > 1:
                                                status_desc_with_prefix = f"{tracker_name}: {tracker_status_desc}"
                                            else:
                                                status_desc_with_prefix = tracker_status_desc
                                            
                                            if tracker_status_int == 1:
                                                tracker_msg = f"The entity status is complying with monitoring rules (status: {tracker_status_int}, status_description: {status_desc_with_prefix})"
                                            else:
                                                tracker_msg = f"The entity status is not complying with monitoring rules (status: {tracker_status_int}, status_description: {status_desc_with_prefix})"
                                            
                                            per_tracker_status_messages.append(tracker_msg)
                                        
                                        logging.debug(
                                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                                            f'generated {len(per_tracker_status_messages)} per-tracker status messages from {len(sorted_tracker_names)} trackers'
                                        )
                                    else:
                                        logging.debug(
                                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                                            f'tracker-keyed data is empty, cannot generate per-tracker messages'
                                        )
                                else:
                                    logging.debug(
                                        f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                                        f'tracker-keyed data is not in expected format: status_by_tracker={type(status_by_tracker)}, status_desc_by_tracker={type(status_desc_by_tracker)}'
                                    )
                            except Exception as e:
                                logging.error(
                                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                                    f'failed to generate per-tracker status messages, exception="{str(e)}"'
                                )
                        
                        # call set_flx_status and define object_state and anomaly_reason (with hybrid scoring)
                        (
                            object_state,
                            status_message,
                            status_message_json,
                            anomaly_reason,
                        ) = set_flx_status(
                            logging,
                            self._metadata.searchinfo.splunkd_uri,
                            self._metadata.searchinfo.session_key,
                            self.tenant_id,
                            record,
                            isOutlier,
                            isUnderMonitoring,
                            isUnderMonitoringMsg,
                            object_logical_group_dict,
                            threshold_alert,
                            threshold_messages,
                            disruption_queue_collection,
                            disruption_queue_record,
                            source_handler="trackmedecisionmaker",
                            score=score,
                            score_outliers=score_outliers,
                            threshold_scores=threshold_scores,
                            vtenant_account=vtenant_conf,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
                        )
                        
                        # Replace status_message_json["status_message"] with per-tracker messages if available
                        # Otherwise keep the aggregated message from set_flx_status
                        if per_tracker_status_messages:
                            # Use per-tracker messages for better visibility
                            # Each tracker gets its own message in the array
                            status_message_json["status_message"] = per_tracker_status_messages
                            logging.debug(
                                f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                                f'replaced status_message_json with {len(per_tracker_status_messages)} per-tracker messages'
                            )
                        else:
                            # If no per-tracker messages were generated (e.g., old format), keep the aggregated message
                            # This ensures backward compatibility
                            logging.debug(
                                f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", '
                                f'using aggregated status_message from set_flx_status (no per-tracker messages generated)'
                            )
                        
                        # Restore tracker-keyed JSON for status, status_description and status_description_short
                        # This ensures proper merging in trackmepersistentfields
                        if status_tracker_keyed is not None:
                            record["status"] = status_tracker_keyed
                        if status_desc_tracker_keyed is not None:
                            record["status_description"] = status_desc_tracker_keyed
                        if status_desc_short_tracker_keyed is not None:
                            record["status_description_short"] = status_desc_short_tracker_keyed

                        # insert our main fields
                        new_record["object_state"] = object_state
                        new_record["status_message"] = " | ".join(status_message)
                        new_record["status_message_json"] = status_message_json
                        new_record["anomaly_reason"] = "|".join(anomaly_reason)

                        # get and convert latest_flip_time from epoch
                        latest_flip_time_human = record.get("latest_flip_time", 0)
                        try:
                            latest_flip_time_human = float(latest_flip_time_human)
                        except:
                            latest_flip_time_human = 0
                        new_record["latest_flip_time_human"] = (
                            convert_epoch_to_datetime(latest_flip_time_human)
                        )

                        # sla_timer
                        get_sla_timer(record, sla_classes, sla_default_class)

                        # specific to flx, generate the status metric
                        try:
                            trackme_flx_gen_metrics(
                                record.get("_time", time.time()),
                                self.tenant_id,
                                object_value,
                                key_value,
                                metric_index,
                                json.dumps({"status": int(record.get("status", 1))}),
                            )
                        except Exception as e:
                            error_msg = f'instance_id={self.instance_id}, Failed to call trackme_flx_gen_metrics with exception="{str(e)}"'
                            logging.error(error_msg)

                #
                # splk-fqm
                #

                # get record fields depending on the component
                elif self.component == "fqm":

                    # first check blocklist
                    if (
                        datagen_collection_blocklist_not_regex_dict
                        or datagen_collection_blocklist_regex_dict
                    ):
                        append_record = apply_blocklist(
                            record,
                            datagen_collection_blocklist_not_regex_dict,
                            datagen_collection_blocklist_regex_dict,
                        )

                    if append_record:

                        # get outliers
                        try:
                            isOutlier = int(record.get("isOutlier", 0))
                        except:
                            isOutlier = 0

                        try:
                            OutliersDisabled = int(record.get("OutliersDisabled", 0))
                        except:
                            OutliersDisabled = 0

                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}"'
                        )

                        # get monitoring time policy and rules (new fields)
                        monitoring_time_policy = record.get("monitoring_time_policy", None)
                        # if unset yet, use the tenant level and add to the record
                        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
                            monitoring_time_policy = default_monitoring_time_policy
                            record["monitoring_time_policy"] = default_monitoring_time_policy
                        monitoring_time_rules = record.get("monitoring_time_rules", None)

                        # Get logical group information

                        # get logical group information: object_group_key
                        object_group_key = record.get("object_group_key", "")

                        # from logical_coll_dict, get object_logical_group_dict by object_group_key, this is sent to the status function
                        object_logical_group_dict = logical_coll_dict.get(
                            object_group_key, {}
                        )

                        # call get_monitoring_time_status and define isUnderMonitoring, monitoring_anomaly_reason, isUnderMonitoringMsg
                        (
                            isUnderMonitoring,
                            monitoring_anomaly_reason,
                            isUnderMonitoringMsg,
                        ) = get_monitoring_time_status(
                            monitoring_time_policy,
                            monitoring_time_rules,
                        )

                        # fqm thresholds lookup
                        fqm_thresholds_lookup(
                            object_value,
                            key_value,
                            record,
                            thresholds_collection_dict,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, dynamic_thresholds="{json.dumps(record.get("dynamic_thresholds", {}), indent=2)}"'
                        )

                        # fqm check dynamic thresholds
                        threshold_alert, threshold_messages, threshold_scores = (
                            fqm_check_dynamic_thresholds(
                                logging,
                                record.get("dynamic_thresholds", {}),
                                record.get("metrics", {}),
                            )
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, object_value="{object_value}", key_value="{key_value}", threshold_alert="{threshold_alert}", threshold_messages="{threshold_messages}", dynamic_thresholds="{json.dumps(record.get("dynamic_thresholds", {}), indent=2)}", metrics_record="{json.dumps(record.get("metrics", {}), indent=2)}"'
                        )

                        # Get score data for this object_id (key_value) from scores_dict
                        score_data = scores_dict.get(key_value, {})
                        score = score_data.get("score", 0)
                        score_outliers = score_data.get("score_outliers", 0)
                        
                        # call get_outliers_status and define isOutlier (with hybrid scoring)
                        isOutlier = get_outliers_status(
                            isOutlier, OutliersDisabled, tenant_outliers_set_state, score_outliers=score_outliers
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", OutliersDisabled="{OutliersDisabled}", tenant_outliers_set_state="{tenant_outliers_set_state}", score_outliers="{score_outliers}"'
                        )

                        # call set_fqm_status and define object_state and anomaly_reason (with hybrid scoring)
                        (
                            object_state,
                            status_message,
                            status_message_json,
                            anomaly_reason,
                        ) = set_fqm_status(
                            logging,
                            self._metadata.searchinfo.splunkd_uri,
                            self._metadata.searchinfo.session_key,
                            self.tenant_id,
                            record,
                            isOutlier,
                            isUnderMonitoring,
                            isUnderMonitoringMsg,
                            object_logical_group_dict,
                            threshold_alert,
                            threshold_messages,
                            disruption_queue_collection,
                            disruption_queue_record,
                            source_handler="trackmedecisionmaker",
                            score=score,
                            score_outliers=score_outliers,
                            threshold_scores=threshold_scores,
                            vtenant_account=vtenant_conf,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
                        )

                        # insert our main fields
                        new_record["object_state"] = object_state
                        new_record["status_message"] = " | ".join(status_message)
                        new_record["status_message_json"] = status_message_json
                        new_record["anomaly_reason"] = "|".join(anomaly_reason)

                        # get and convert latest_flip_time from epoch
                        latest_flip_time_human = record.get("latest_flip_time", 0)
                        try:
                            latest_flip_time_human = float(latest_flip_time_human)
                        except:
                            latest_flip_time_human = 0
                        new_record["latest_flip_time_human"] = (
                            convert_epoch_to_datetime(latest_flip_time_human)
                        )

                        # sla_timer
                        get_sla_timer(record, sla_classes, sla_default_class)

                        # specific to fqm, generate the status metric
                        try:
                            trackme_fqm_gen_metrics(
                                record.get("_time", time.time()),
                                self.tenant_id,
                                object_value,
                                key_value,
                                metric_index,
                                json.dumps({"status": int(record.get("status", 1))}),
                            )
                        except Exception as e:
                            error_msg = f'instance_id={self.instance_id}, Failed to call trackme_fqm_gen_metrics with exception="{str(e)}"'
                            logging.error(error_msg)

                #
                # splk-wlk
                #

                # get record fields depending on the component
                elif self.component == "wlk":

                    # first check blocklist
                    if (
                        datagen_collection_blocklist_not_regex_dict
                        or datagen_collection_blocklist_regex_dict
                    ):
                        append_record = apply_blocklist(
                            record,
                            datagen_collection_blocklist_not_regex_dict,
                            datagen_collection_blocklist_regex_dict,
                        )

                    if append_record:

                        # get outliers
                        try:
                            isOutlier = int(record.get("isOutlier", 0))
                        except:
                            isOutlier = 0

                        try:
                            OutliersDisabled = int(record.get("OutliersDisabled", 0))
                        except:
                            OutliersDisabled = 0

                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}"'
                        )

                        # get monitoring time policy and rules (new fields)
                        monitoring_time_policy = record.get("monitoring_time_policy", None)
                        # if unset yet, use the tenant level and add to the record
                        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
                            monitoring_time_policy = default_monitoring_time_policy
                            record["monitoring_time_policy"] = default_monitoring_time_policy
                        monitoring_time_rules = record.get("monitoring_time_rules", None)
                        
                        # call get_monitoring_time_status and define isUnderMonitoring, monitoring_anomaly_reason, isUnderMonitoringMsg
                        (
                            isUnderMonitoring,
                            monitoring_anomaly_reason,
                            isUnderMonitoringMsg,
                        ) = get_monitoring_time_status(
                            monitoring_time_policy,
                            monitoring_time_rules,
                        )

                        # Get score data for this object_id (key_value) from scores_dict
                        score_data = scores_dict.get(key_value, {})
                        score = score_data.get("score", 0)
                        score_outliers = score_data.get("score_outliers", 0)
                        
                        # call get_outliers_status and define isOutlier (with hybrid scoring)
                        isOutlier = get_outliers_status(
                            isOutlier, OutliersDisabled, tenant_outliers_set_state, score_outliers=score_outliers
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", isOutlier="{isOutlier}", OutliersDisabled="{OutliersDisabled}", tenant_outliers_set_state="{tenant_outliers_set_state}", score_outliers="{score_outliers}"'
                        )

                        # wlk thresholds lookup
                        wlk_thresholds_lookup(
                            object_value,
                            key_value,
                            record,
                            thresholds_collection_dict,
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, dynamic_thresholds="{json.dumps(record.get("dynamic_thresholds", {}), indent=2)}"'
                        )

                        # call set_wlk_status and define object_state and anomaly_reason (with hybrid scoring)
                        (
                            object_state,
                            status_message,
                            status_message_json,
                            anomaly_reason,
                        ) = set_wlk_status(
                            logging,
                            self._metadata.searchinfo.splunkd_uri,
                            self._metadata.searchinfo.session_key,
                            self.tenant_id,
                            record,
                            isOutlier,
                            isUnderMonitoring,
                            isUnderMonitoringMsg,
                            disruption_queue_collection,
                            disruption_queue_record,
                            source_handler="trackmedecisionmaker",
                            monitoring_anomaly_reason=monitoring_anomaly_reason,
                            score=score,
                            score_outliers=score_outliers,
                            vtenant_account=vtenant_conf,
                            dynamic_thresholds=record.get("dynamic_thresholds", {}),
                        )
                        logging.debug(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", object_value="{object_value}", key_value="{key_value}", object_state="{object_state}", status_message="{status_message}", anomaly_reason="{anomaly_reason}"'
                        )

                        # insert our main fields
                        new_record["object_state"] = object_state
                        new_record["status_message"] = " | ".join(status_message)
                        new_record["status_message_json"] = status_message_json
                        new_record["anomaly_reason"] = "|".join(anomaly_reason)

                        # get and convert latest_flip_time from epoch
                        latest_flip_time_human = record.get("latest_flip_time", 0)
                        try:
                            latest_flip_time_human = float(latest_flip_time_human)
                        except:
                            latest_flip_time_human = 0
                        new_record["latest_flip_time_human"] = (
                            convert_epoch_to_datetime(latest_flip_time_human)
                        )

                        # sla_timer
                        get_sla_timer(record, sla_classes, sla_default_class)

            #
            # End per component processing
            #

            except Exception as e:
                logging.error(
                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", component="{self.component}", Error processing record, record="{json.dumps(record, indent=2)}", exception="{str(e)}"'
                )
                continue  # Proceed with next record

            #
            # End per component processing
            #

            if append_record:

                # add all key value pairs from the original record to new_record if not present already
                for key, value in record.items():
                    if key not in new_record:
                        new_record[key] = value

                # per-entity maintenance override (TOP precedence) — applied as
                # the FINAL state mutation so it wins over the computed state and
                # every other blue/protection layer (ACK, disruption grace,
                # logical group). Inert once the window expires.
                maintenance_record = entity_maintenance_lookup(
                    key_value,
                    entity_maintenance_collection_keys,
                    entity_maintenance_collection_dict,
                )
                if maintenance_record:
                    apply_entity_maintenance_override(new_record, maintenance_record)
                else:
                    # No active window — strip any stale maintenance metadata
                    # carried over from the original record (line above copies
                    # prior fields into new_record) so an expired window does
                    # not leave is_under_maintenance=1 behind.
                    clear_entity_maintenance_fields(new_record)

                # add new_record to processed_records
                processed_records.append(new_record)

                #
                # Automatic label assignment — per-record evaluation
                #
                # Reads the finalised new_record (object_state already mutated
                # by the maintenance override above, so a protected entity does
                # not trip alert/recovery triggers). Pure + fail-open: any error
                # is swallowed so it can never block the record. Assignment
                # deltas are accumulated and flushed once after the loop.
                #
                if auto_labels_active:
                    try:
                        assign_key = f"{self.component}:{key_value}"
                        existing_assign = auto_labels_assign_dict.get(assign_key) or {}
                        try:
                            existing_label_ids = json.loads(
                                existing_assign.get("label_ids", "[]")
                            )
                        except Exception:
                            existing_label_ids = []
                        # The once-only marker for manual non-edge rules
                        # (discovered / custom_filter). It lives on the assignment
                        # record, so it is lost if the record is deleted when the
                        # entity's last label is removed — the documented
                        # resurrection edge (see the flush delete path below).
                        applied_map = existing_assign.get("auto_applied", {})

                        # Prior persisted state vs freshly-computed state.
                        # The tracker macros rename the persisted object_state to
                        # object_previous_state BEFORE this command runs (dsm via
                        # an explicit rename, the other components via
                        # "object_state as object_previous_state" in the
                        # persistent-fields lookup), so inside the command the
                        # prior state lives in object_previous_state — NOT
                        # object_state (which is the field WE write with the new
                        # state). A brand-new entity has no prior row, so its
                        # object_previous_state is null here (the "discovered"
                        # sentinel is only injected by SPL AFTER the command).
                        # This is the same signal the flip logic uses.
                        prior_state = record.get("object_previous_state")
                        new_state = new_record.get("object_state")
                        is_new = (not prior_state) or (
                            str(prior_state).strip() in ("", "discovered")
                        )

                        # eligibility filters can reference `component`; ensure
                        # it is present without mutating the persisted record.
                        eval_entity = dict(new_record)
                        eval_entity.setdefault("component", self.component)

                        (
                            final_label_ids,
                            applied_out,
                            labels_changed,
                        ) = reconcile_entity_labels(
                            auto_labels_rules,
                            eval_entity,
                            prior_state,
                            new_state,
                            is_new,
                            applied_map,
                            existing_label_ids,
                        )

                        if labels_changed:
                            auto_labels_deltas[assign_key] = (
                                final_label_ids,
                                applied_out,
                                key_value,
                            )
                    except Exception as e:
                        logging.error(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                            f'component="{self.component}", key_value="{key_value}", '
                            f'auto-labels per-record evaluation failed (skipped, state '
                            f'computation unaffected), exception="{str(e)}"'
                        )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        #
        # Automatic label assignment — single batched flush
        #
        # One write per changed entity to the per-tenant label-assignment
        # collection: upsert when the entity keeps labels, delete when the
        # reconcile emptied it (matches the UI's delete-on-empty). The whole
        # flush is fail-open — a failure here never affects the state results
        # already yielded.
        #
        # Guard on the collection handle: it is None when the assignment
        # collection did not yet exist at setup (see the existence check above).
        # In that rare window we skip the write this run rather than raise an
        # AttributeError; the next run (once the collection exists) persists.
        if auto_labels_active and auto_labels_deltas and auto_labels_assign_collection is not None:
            try:
                records_to_save = []
                keys_to_delete = []
                now_str = str(time.time())
                for assign_key, (
                    final_label_ids,
                    applied_out,
                    object_id_value,
                ) in auto_labels_deltas.items():
                    if final_label_ids:
                        # batch_save is a full-record upsert — preserve ctime on
                        # update, set it on first creation, so auto-created
                        # assignment records stay consistent with UI-created ones.
                        existing_assign = auto_labels_assign_dict.get(assign_key) or {}
                        records_to_save.append(
                            {
                                "_key": assign_key,
                                "object_id": object_id_value,
                                "component": self.component,
                                "label_ids": json.dumps(final_label_ids),
                                "auto_applied": json.dumps(applied_out),
                                "updated_by": "auto_labels",
                                "ctime": existing_assign.get("ctime", now_str),
                                "mtime": now_str,
                            }
                        )
                    else:
                        # Reconcile emptied the entity's labels — delete the
                        # assignment record (matches the UI's delete-on-empty).
                        # NOTE: this also drops the auto_applied marker; this is
                        # the documented resurrection edge (a manual non-edge rule
                        # whose sole label is removed can re-fire next run). Do not
                        # "fix" by keeping empty records — that would diverge from
                        # the UI and leave orphaned rows.
                        keys_to_delete.append(assign_key)

                # chunked batch upsert (KV batch_save replaces whole records)
                for i in range(0, len(records_to_save), 500):
                    auto_labels_assign_collection.data.batch_save(
                        *records_to_save[i : i + 500]
                    )
                deleted_count = 0
                for assign_key in keys_to_delete:
                    try:
                        auto_labels_assign_collection.data.delete_by_id(assign_key)
                        deleted_count += 1
                    except Exception as del_exc:
                        # 404 = already absent (concurrent delete / prior cleanup):
                        # expected, ignore silently. Anything else is a real failure
                        # — the stale labels stay attached, so surface it and do NOT
                        # count it as a successful delete (keeps the reported count
                        # honest rather than logging a delete that did not happen).
                        if getattr(del_exc, "status", None) == 404:
                            continue
                        logging.warning(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                            f'component="{self.component}", auto_labels delete failed for '
                            f'assignment key="{assign_key}", exception="{str(del_exc)}"'
                        )

                logging.info(
                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                    f'component="{self.component}", auto_labels_flush=1, '
                    f'upserts="{len(records_to_save)}", deletes="{deleted_count}", '
                    f'delete_failures="{len(keys_to_delete) - deleted_count}"'
                )
            except Exception as e:
                logging.error(
                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                    f'component="{self.component}", auto-labels flush failed '
                    f'(non-fatal, state results already yielded), exception="{str(e)}"'
                )

        # Always emit one INFO summary per run when the feature is active, even
        # with zero deltas — so "active but produced nothing" is greppable and a
        # silent no-op can never again be mistaken for "the code didn't run".
        if auto_labels_active:
            logging.info(
                f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                f'component="{self.component}", auto_labels_active=1, '
                f'rules="{len(auto_labels_rules)}", deltas="{len(auto_labels_deltas)}"'
            )

        #
        # Render
        #

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "render_records"

        for yield_record in self.generate_fields(processed_records):
            # logging
            logging.debug(f'instance_id={self.instance_id}, yield_record="{json.dumps(yield_record, indent=2)}"')

            # yield record
            yield yield_record

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # performance counter
        logging.info(
            f'trackmedecisionmaker has terminated, tenant_id="{self.tenant_id}", component="{self.component}", instance_id="{self.instance_id}", upstream_records="{records_count}", processed_records="{len(processed_records)}", run_time="{round(time.time() - start, 3)}"'
        )


dispatch(TrackMeDecisionMaker, sys.argv, sys.stdin, sys.stdout, __name__)
