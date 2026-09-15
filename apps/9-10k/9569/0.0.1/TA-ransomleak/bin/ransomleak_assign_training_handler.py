# encoding = utf-8
"""Splunk-side glue for the `ransomleak_assign_training` alert action.

Referenced from `globalConfig.json` as the alert's `customScript`, so UCC
generates `bin/ransomleak_assign_training.py` around it and never overwrites
this file.

Everything here is configuration reading, iteration and logging. Every decision
worth testing -- the idempotency key, the batch cap, the per-row skip, the
trigger context -- lives in `ransomleak_assign.py`, which imports nothing from
Splunk and is therefore reachable by pytest. docs/follow-ups.md records what the
alternative costs: the two most correctness-relevant lines of the first three
modular inputs shipped with no coverage at all because they sat in a module that
cannot be imported without Splunk's libraries.

NOT RUNTIME-VERIFIED. No Splunk instance was available, so nothing in this file
has ever executed: the `conf_manager` account read, `helper.get_events()` and
the exit codes are verified only by `ucc-gen build` succeeding and by
`py_compile`. The same gap the five input helpers carry.
"""

from solnlib import conf_manager

from ransomleak_assign import (
    DEFAULT_EMAIL_FIELD, parse_max_assignments, parse_reassign_period,
    plan_assignments, send_assignments)
from ransomleak_client import RansomleakClient, should_verify_tls

ADDON_NAME = "TA-ransomleak"

# Exit codes. `run()` in `ModularAlertBase` passes whatever `process_event`
# returns to `sys.exit`, and Splunk renders any non-zero as a failed action, so
# these are the only signal an operator gets in the Alert Actions UI. Distinct
# values rather than a blanket 1 because the three mean genuinely different
# things to whoever is looking: fix the action's configuration, look at the
# server, or nothing happened at all.
EXIT_OK = 0
EXIT_CONFIG = 3
EXIT_PARTIAL_FAILURE = 4


def _get_account(session_key, account_name):
    """Read one configured account, decrypting the stored API token.

    Same realm and conf as the modular inputs read: an operator configures one
    account and both rails use it. Duplicated from the helpers rather than
    shared because the shared `ransomleak_input_base.py` extraction
    docs/follow-ups.md calls for does not exist yet, and this is the fourth call
    site that would move into it.
    """
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-ta-ransomleak_account".format(ADDON_NAME),
    )
    return cfm.get_conf("ta-ransomleak_account").get(account_name)


def process_event(helper, *args, **kwargs):
    account_name = (helper.get_param("account") or "").strip()
    exercise_slug = (helper.get_param("exercise_slug") or "").strip()
    if not account_name:
        helper.log_error("No account selected; cannot assign training.")
        return EXIT_CONFIG
    if not exercise_slug:
        helper.log_error("No exercise slug configured; cannot assign training.")
        return EXIT_CONFIG

    account = _get_account(helper.session_key, account_name)
    if not account:
        # Reachable by deleting an account a saved search still names. Without
        # this the next line raises `'NoneType' object has no attribute 'get'`,
        # which the generated wrapper reports verbatim as an unexpected error --
        # true, and useless to the person who has to fix it.
        helper.log_error(
            "Account '%s' is not configured on this add-on; it may have been "
            "deleted after this alert was set up." % (account_name,))
        return EXIT_CONFIG
    base_url = account.get("base_url")

    # Fail-closed TLS: a DENY-LIST, never an allow-list. The rationale --
    # where an unrecognised value comes from and what is in flight if it
    # silently disables verification -- lives once, in
    # `ransomleak_client.should_verify_tls`. Read it before changing this.
    # The stake is higher here than on the five pull inputs: this request
    # carries a tenant-wide integration token AND an employee's email address,
    # and it WRITES.
    client = RansomleakClient(
        base_url=base_url,
        api_token=account.get("api_token"),
        verify_tls=should_verify_tls(account.get("verify_tls")),
    )

    reassign_days, period_warning = parse_reassign_period(
        helper.get_param("reassign_period"))
    max_assignments, cap_warning = parse_max_assignments(
        helper.get_param("max_assignments"))
    for warning in (period_warning, cap_warning):
        if warning:
            helper.log_warn(warning)

    email_field = (helper.get_param("email_field") or "").strip() or DEFAULT_EMAIL_FIELD

    plan = plan_assignments(
        helper.get_events(),
        exercise_slug,
        email_field=email_field,
        search_name=helper.search_name,
        sid=helper.sid,
        app=helper.app,
        reassign_days=reassign_days,
        max_assignments=max_assignments,
        results_link=helper.settings.get("results_link"),
    )

    for warning in plan.warnings:
        helper.log_warn(warning)
    if plan.duplicates:
        # Not a warning: a search returning one row per event routinely names
        # the same person repeatedly, and collapsing those is the intended
        # behaviour rather than a degradation.
        helper.log_info(
            "%d result row(s) resolved to an assignment already planned in this "
            "firing and were collapsed." % (plan.duplicates,))

    if not plan.requests:
        if plan.skipped:
            # Rows arrived and not one of them yielded an address, which is a
            # configuration mistake (almost always the wrong 'Email field') and
            # not a quiet night. Exiting 0 here would paint the action green in
            # the Alert Actions UI while it assigned nobody, forever -- the same
            # "a failed run still exits 0" shape docs/follow-ups.md records
            # against the modular inputs.
            helper.log_error(
                "No result row produced a usable assignment: all %d row(s) were "
                "skipped. Check the 'Email field' setting against the fields "
                "your search returns." % (len(plan.skipped),))
            return EXIT_CONFIG
        helper.log_info("Nothing to assign: the search returned no results.")
        return EXIT_OK

    outcome = send_assignments(client, plan.requests)

    for email, reason in outcome.failures:
        helper.log_error("Assignment for %s failed: %s" % (email, reason))
    helper.log_info(
        "Assigned '%s' to %d user(s); %d failed. Repeating a firing replays the "
        "same assignments rather than creating new ones."
        % (exercise_slug, len(outcome.created), len(outcome.failures)))

    return EXIT_PARTIAL_FAILURE if outcome.failures else EXIT_OK
