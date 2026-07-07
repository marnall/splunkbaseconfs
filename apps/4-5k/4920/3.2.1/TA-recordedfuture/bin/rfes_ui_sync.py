"""Syncronize Views and Panels with API."""

from recordedfuture.correlation import usecases
from recordedfuture.api.splunk_api import SplunkClient
from recordedfuture.api.rfclient import RFClient
from rfes_menu import Menu
from recordedfuture.core.constants import (
    INCIDENT_STATE,
    SAVEDSEARCHES_FILENAME,
    THREAT_HUNT_PROFILE_COLLECTION,
)

INTERNAL_ID = "correlation_{}"
VIEWS = [
    "rfes_correlation_edit_reg",
    "rfes_correlation_edit_model",
    "ti_framework_edit",
]


def sync_ui_element(app_env, template_id, internal_id=None, func=None, **kwargs):
    """Update local copy of a UI element if needed.

    :param app_env:       The app_env global.
    :param template_id:   The name of the view template in the bfi.
    :param internal_id:   The id used for checkpoint, it's the template id if not given.
    :param func:          A function that takes content and does transformations.
    """

    internal_id = template_id if not internal_id else internal_id
    checkpoint = app_env.get_checkpoint(internal_id)
    etag = checkpoint.get("etag", "")

    rfclient = RFClient(app_env)
    view = rfclient.config.get_view(template_id, etag)

    # idempotent. Either using content from bfi which should be empty if 304
    # or get the content from the checkpoint.
    content = view["content"] or checkpoint.get("content", "")

    data = {"etag": view["etag"], "content": content}
    app_env.set_checkpoint(internal_id, data)

    # NOTE in the checkpoint we want to save the template, NOT the content
    # with any transformations applied to it. This avoids 'caching' issues.
    client = SplunkClient(app_env)
    if func is not None:
        content = func(content)

    client.ui.post_view(template_id, content)
    return len(view["content"]) != 0


def sync_landing_page(app_env):
    internal_id = "rfes_landing_page"
    checkpoint = app_env.get_checkpoint(internal_id)
    etag = checkpoint.get("etag", "")
    # We want regular correlations and RBA
    stanzas = app_env.all_correlations
    app_env.logger.debug(f"Found these correlations stanzas: {stanzas}")

    correlations = [
        {
            "use_case": stanza["use_case"],
            "rule_id": stanza["id"],
            "category": stanza["category"],
            "label": stanza["label"],
        }
        for stanza in stanzas.values()
    ]

    alert_stanzas = app_env.get_stanzas("alert", update=True)
    app_env.logger.debug("Found these %s stanzas: %s", "alert", alert_stanzas)

    alerts = [
        (stanza["alert_rule_id"], stanza["alert_rule_name"])
        for stanza in alert_stanzas.values()
        if stanza.get("alert_rule_id") and stanza.get("enabled") == "on"
    ]

    playbook_alert_stanzas = app_env.get_stanzas("playbook_alert", update=True)
    app_env.logger.debug(
        "Found these %s stanzas: %s", "playbook_alert", playbook_alert_stanzas
    )

    playbook_alerts = [
        (stanza["alert_rule_id"], stanza["alert_rule_name"])
        for stanza in playbook_alert_stanzas.values()
        if stanza.get("alert_rule_id") and stanza.get("enabled") == "on"
    ]

    sigma_rules = [
        {"id": rule_id, "title": stanza.get("title")}
        for rule_id, stanza in app_env.get_stanzas("sigma", update=True).items()
        if stanza.get("state") == "active"
    ]

    client = SplunkClient(app_env)
    threat_hunt_profiles = [
        {
            "name": profile.get("name"),
            "target": profile.get("target"),
            "target_type": profile.get("target_type"),
            "target_id": profile.get("target_id"),
        }
        for profile in client.storage.get_checkpoint(THREAT_HUNT_PROFILE_COLLECTION)
    ]

    rfclient = RFClient(app_env)
    json_data = {
        "alerts": alerts,
        "correlations": correlations,
        "playbook_alerts": playbook_alerts,
        "sigma_rules": sigma_rules,
        "threat_hunt_profiles": threat_hunt_profiles,
    }
    app_env.logger.info("Collected the data: %s" % json_data)

    # Temporarily replaced internal_id with "rfes_landing_page_21" until we have BFI versioning
    view = rfclient.config.post_view("rfes_landing_page_21", etag, json_data=json_data)
    app_env.logger.debug("View content: %s", view["content"][:200])
    content = view["content"] or checkpoint.get("content", "")

    data = {"etag": view["etag"], "content": content}
    app_env.set_checkpoint(internal_id, data)
    client.ui.post_view(internal_id, content)
    return len(view["content"]) != 0


def sync_ui_elements(_, app_env):
    """Synchronize all view.

    Go through the configuration and synchronize the views stated in the
    configuration.
    """
    status = dict()

    def _sync_element_list(category):
        """Sync each element in a list of stanzas."""
        stanzas = app_env.get_stanzas(category)
        app_env.logger.debug("Found these %s stanzas: %s", category, stanzas)
        _status = []
        views = {stanza["view_id"] for stanza in stanzas.values()}
        for view_id in list(views):
            app_env.logger.info("%s stanza %s: %s", category, stanzas, view_id)
            length = sync_ui_element(app_env, view_id)
            if length:
                _status.append(view_id)
        return _status

    def _sync_correlations():
        """Checks if any old correlation rules exist. If so, upgrade them."""
        from recordedfuture.migration import migrations  # due to circular import

        stanzas = app_env.get_stanzas("correlation")
        splunk_client = SplunkClient(app_env)
        saved_searches = splunk_client.config.get_config(
            SAVEDSEARCHES_FILENAME, filter="correlation_view"
        )

        for saved_search_stanza in saved_searches.get("entry", [{}]):
            saved_search = saved_search_stanza.get("content").get("search")
            rule_id = saved_search_stanza.get("name").replace("correlation_view_", "")
            rf_conf_stanza = stanzas.get(rule_id)
            if rf_conf_stanza is None:  # INTEGR-3767
                continue
            if rf_conf_stanza.get("cached") and "outputlookup" in saved_search:
                # Search was created in 2.1.1 and needs to be rewritten.
                usecases.remove_outputlookup_from_subsearch(
                    app_env,
                    rf_conf_stanza,
                    saved_search_stanza,
                )

        status = []
        for stanza in stanzas.values():
            cached = stanza.get("cached")
            # If correlation config does not have cached field they were configured in an old app version
            if not cached:
                migrations.upgrade_correlation_rule(app_env, stanza)
            status.append(stanza["view_id"])
        return status

    def _sync_sigma():
        """Updates a checkpoint used for Sigma in v2.1"""
        client = SplunkClient(app_env)
        client.storage.get_checkpoint(INCIDENT_STATE)
        search = "| outputlookup append=true create_empty=true sigma_detections.csv"
        client.searches.search(search)

    # Sync enrichment view
    status["enrichment"] = _sync_element_list("enrichment")

    # Sync search views
    status["search"] = _sync_element_list("search")

    # Upgrade some correlations, Upgrade must happen first.
    status["correlation"] = _sync_correlations()

    # Sync correlation view
    status["cached_correlation"] = _sync_element_list("correlation")

    _sync_sigma()

    # Sync other views
    for view in VIEWS:
        status[view] = sync_ui_element(app_env, view)

    # Sync landing page/view
    status["landing"] = sync_landing_page(app_env)

    # Extend to include other types of view when needed

    # Re-generate menu
    menu = Menu(app_env)
    menu.setup()

    return (
        200,
        {
            "links": {},
            "entry": [{"name": key, "content": value} for key, value in status.items()],
        },
    )


def sync_single_ui_element(in_dict, app_env):
    """Handle handle_sync_ui_element."""
    query = dict(in_dict["query"])
    element_id = query["element_id"]

    results = sync_ui_element(app_env, element_id)
    entry = {"name": "sync_ui_element", "content": results}
    return (200, {"links": {}, "entry": [entry]})


def sync_landing_page_endpoint(_, app_env):
    sync_landing_page(app_env)
    return 200, {"links": {}, "entry": []}
