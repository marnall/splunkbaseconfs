# encoding = utf-8

import json
from datetime import datetime, timedelta, timezone
import logging
import os
import time

try:
    from uapi_models import devices, jamfpro
    from account_helper import get_jamf_credentials
    from checkpoint_store import read as read_checkpoint, write as write_checkpoint
    from error_reporting import emit_input_error
    from input_lifecycle import auto_disable_input
except ImportError:
    from .uapi_models import devices, jamfpro
    from .account_helper import get_jamf_credentials
    from .checkpoint_store import read as read_checkpoint, write as write_checkpoint
    from .error_reporting import emit_input_error
    from .input_lifecycle import auto_disable_input


# Map the UI's event_time_format option value to the internal token consumed
# by JamfComputer.splunk_hec_events. timeAsReport is a legacy alias for
# timeAsLastInventoryUpdate so older configs still resolve correctly.
TIME_AS_TOKENS = {
    "timeAsReport": "report",
    "timeAsLastInventoryUpdate": "report",
    "timeAsLastContact": "contact",
    "timeAsScript": "script",
}


# Static Variables
def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # name_of_the_modular_input = definition.parameters.get('name_of_the_modular_input', None)
    # jss_url = definition.parameters.get('jss_url', None)
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    # multiple_dropdown = definition.parameters.get('multiple_dropdown', None)
    # radio_buttons = definition.parameters.get('radio_buttons', None)
    # run_time = definition.parameters.get('run_time', None)
    # write_computer_diffs = definition.parameters.get('write_computer_diffs', None)
    pass


def collect_events(helper, ew):
    """
    This is the main execution function
    """
    helper.log_info("jamfcomputers collect_events started: input=%r" % helper.get_input_stanza_names())
    headers = {
        'User-Agent': jamfpro.build_user_agent(helper, 'jamfcomputers')
    }
    # Account lookup via shared helper
    creds = get_jamf_credentials(helper)
    if not (creds.get('jss_url') and creds.get('jss_username') and creds.get('jss_password')):
        account = helper.get_arg('account')
        account_name = account.get('name') if isinstance(account, dict) else account
        emit_input_error(
            helper=helper, ew=ew,
            category="config",
            label="Account configuration",
            target_url="(no request was made)",
            summary="Account %r is missing required credentials (URL, username, or password)" % account_name,
        )
        return

    settings = {
        "jamfSettings": {
            "jss_url": creds['jss_url'],
            "jss_username": creds['jss_username'],
            "jss_password": creds['jss_password'],
        },
        "computerCollection": {
            "details": helper.get_arg('computer_collection_details', None),
            "days_since_contact": helper.get_arg('days_since_contact', None),
            "exclude_none_managed": (
                helper.get_arg('exclude_none_managed', None)
                if helper.get_arg('exclude_none_managed', None) is not None
                else helper.get_arg('excludeNoneManaged', None)
            ),
            "sections": helper.get_arg('sections', None)
        },
        "eventWriter": {
            "host_as_device_name": helper.get_arg('host_as_device_name', None),
            "eventTimeFormat": helper.get_arg('event_time_format', None) or "timeAsScript"
        },
        "outbound": {
            "use_proxy": False,
            "verifyTLS": True,
            "retryCount": 3,
            "timeOut": 60
        }
    }

    # Validate days_since_contact up-front. If we deferred this to
    # get_computers_page (a nested fn), returning from there on a bad value
    # would crash the outer pagination loop (theseComputers.__len__() on None).
    days_since_contact_raw = settings['computerCollection']['days_since_contact']
    if days_since_contact_raw not in (None, "", str(0)):
        try:
            int(days_since_contact_raw)
        except (ValueError, TypeError):
            emit_input_error(
                helper=helper, ew=ew,
                category="config",
                label="days_since_contact filter",
                target_url="(no request was made)",
                summary="days_since_contact=%r is not a positive integer; refusing to fetch without the intended cutoff filter"
                        % days_since_contact_raw,
            )
            return

    # Jamf URL
    if str(settings['jamfSettings']['jss_url'])[-1] != '/':
        settings['jamfSettings']['jss_url'] = settings['jamfSettings']['jss_url'] + '/'

    if str(settings['jamfSettings']['jss_url']).__contains__("http://"):  # NOSONAR — stripping http:// to enforce https
        settings['jamfSettings']['jss_url'] = settings['jamfSettings']['jss_url'].replace("http://", "")  # NOSONAR

    if str(settings['jamfSettings']['jss_url']).__contains__("https://"):
        settings['jamfSettings']['jss_url'] = settings['jamfSettings']['jss_url'].replace("https://", "")

    #
    # Functions:
    #

    def write_event(thisEvent=None):
        """
        """
        #
        #   This class is to help with the writing to the Splunk Event writer
        #
        #

        if "index" in thisEvent:
            index = thisEvent['index']
            del thisEvent['index']
        else:
            index = helper.get_output_index()

        if "host" in thisEvent:
            host = thisEvent['host']
            del thisEvent['host']
        else:
            host = "Jamf-TA-AddOn"

        if "sourcetype" in thisEvent:
            sourcetype = thisEvent['sourcetype']
            del thisEvent['sourcetype']
        else:
            sourcetype = "_json"

        if "time" in thisEvent:
            eventTime = thisEvent['time']
            del thisEvent['time']
        else:
            eventTime = time.time()

        if "source" in thisEvent:
            source = thisEvent['source']
            del thisEvent['source']
        else:
            source = "jssInventory"

        if index is not None:
            event = helper.new_event(data=json.dumps(thisEvent, ensure_ascii=False), source=source, time=eventTime,
                                     index=index,
                                     host=host,
                                     sourcetype=sourcetype)
        else:
            event = helper.new_event(data=json.dumps(thisEvent, ensure_ascii=False), source=source, time=eventTime,
                                     host=host,
                                     sourcetype=sourcetype)
        ew.write_event(event)
        return True

    def get_computers_page(pageNumber=0, jss=None):

        FILTERS = {}
        if settings['computerCollection']['exclude_none_managed']:
            FILTERS['managed'] = {'value': True}
        # days_since_contact is pre-validated at the top of collect_events,
        # so int() can't fail here. Falsy/zero/None means "no cutoff filter".
        if settings['computerCollection']['days_since_contact'] not in (None, "", str(0)):
            time_s = datetime.now(timezone.utc) - timedelta(
                days=int(settings['computerCollection']['days_since_contact']))
            FILTERS['lastContactTime'] = {
                'value': time_s.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                'operator': '>'
            }

        sections_raw = settings['computerCollection']['sections']
        if isinstance(sections_raw, str):
            # Splunk modinput serializes multi-value params with '~' when passing
            # them to the input runtime, even when globalConfig.json declares ','
            # as the delimiter, so accept both.
            sections = [s.strip() for s in sections_raw.replace('~', ',').split(',') if s.strip()]
        else:
            sections = list(sections_raw) if sections_raw else []

        requiredSections = ['GENERAL', 'USER_AND_LOCATION', 'HARDWARE']

        for requiredSection in requiredSections:
            if requiredSection not in sections:
                sections.append(requiredSection)

        computers = jss.get_computers_page_number(filters=FILTERS, sections=sections,
                                               sortKey="&sort=general.reportDate%3Adesc", pageNumber=pageNumber)
        return computers


    # Collect Computers Process each time
    notDone = True
    pageCount = 0
    meta_keys = ['supervised', 'managed', 'name', 'serial_number', 'udid', 'id', 'assigned_user', 'department',
                 'building', 'room', 'eventID', 'reportDate']

    # Map the UI selection (timeAs*) into the internal token consumed by
    # JamfComputer.splunk_hec_events. timeAsReport is kept as a legacy alias
    # for timeAsLastInventoryUpdate so configs from older installs still work.
    raw_event_time_format = settings['eventWriter']['eventTimeFormat']
    timeAs = TIME_AS_TOKENS.get(raw_event_time_format)
    if timeAs is None:
        helper.log_warning(
            "Unknown event_time_format %r; falling back to 'script'. "
            "Valid values: %s",
            raw_event_time_format, ", ".join(TIME_AS_TOKENS.keys())
        )
        timeAs = "script"

    try:
        jamfPro = jamfpro.JamfPro(jamf_url=settings['jamfSettings']['jss_url'],
                                    jamf_username=settings['jamfSettings']['jss_username'],
                                    jamf_password=settings['jamfSettings']['jss_password'],
                                    helper=helper, headers=headers)
    except Exception as e:
        # If the account was auto-created by legacy_migration (i.e. the customer
        # just upgraded from 2.12.x and we carried their old creds forward), give
        # them a concrete next-step pointer instead of a generic config check.
        from legacy_migration import migration_auth_failure_hint
        account_arg = helper.get_arg('account')
        account_name = account_arg.get('name') if isinstance(account_arg, dict) else account_arg
        hint = migration_auth_failure_hint(account_name, 'jamfcomputers')
        emit_input_error(
            helper=helper, ew=ew,
            category="auth",
            label="Jamf Pro authentication",
            target_url=creds.get('jss_url') or "(account URL not set)",
            summary="Failed to connect to Jamf Pro: %s%s" % (str(e), hint),
        )
        raise  # Re-raise so splunktaucclib's wrapper logs the traceback and reschedules

    if not jamfPro:
        # Defensive: jamfpro.JamfPro() raises on failure rather than returning
        # None, so this branch is "should never happen". Still, surface it.
        helper.log_error("Unable to create the Jamf Pro connection object")
        raise RuntimeError("jamfpro.JamfPro() returned a falsy object without raising")

    # === skip_unchanged setup ===========================================
    # Per the 3.0.0 implementation plan (item 6): on each fire, look up the
    # last reportDate we already emitted events for. Because the Jamf API
    # call below is sorted by general.reportDate DESC, the first computer
    # whose reportDate is at-or-before the checkpoint tells us the rest of
    # this page AND all subsequent pages are also stale — we can stop
    # fetching. Reduces both Jamf API calls and Splunk index volume on
    # low-interval poll schedules.
    skip_unchanged_arg = helper.get_arg('skip_unchanged')
    skip_unchanged = skip_unchanged_arg in (True, 1, '1', 'true', 'True')
    stanza_name = helper.get_input_stanza_names()
    last_seen_epoch = (
        read_checkpoint(helper, 'jamfcomputers', stanza_name)
        if skip_unchanged else None
    )
    max_epoch_this_run = last_seen_epoch
    skipped_unchanged_count = 0
    processed_count = 0

    def _parse_report_epoch(computer_record):
        """Parse general.reportDate to a UTC epoch float, or None if missing/malformed.

        Tolerates both ISO formats Jamf has used (with and without subsecond),
        matching uapi_models/jamfpro.py:420-422. Treat None as "no checkpoint
        signal from this computer" — caller scans and processes normally.
        """
        try:
            rd = computer_record.get('general', {}).get('reportDate')
        except (AttributeError, TypeError):
            return None
        if not rd:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                return datetime.strptime(rd, fmt).replace(tzinfo=timezone.utc).timestamp()
            except (TypeError, ValueError):
                continue
        return None
    # ====================================================================

    while notDone:
        theseComputers = get_computers_page(pageNumber=pageCount, jss=jamfPro)
        if theseComputers.__len__() == 0:
            # Item 4: drop out of the loop so the post-loop checkpoint write
            # below can run. The original `return None` skipped that work.
            notDone = False
            continue
        pageCount += 1
        for computer in theseComputers:
            # Skip-unchanged short-circuit (item 6). The API list is sorted
            # by reportDate DESC, so the first computer at-or-before the
            # checkpoint means everything else is also stale.
            this_epoch = _parse_report_epoch(computer)
            if (
                skip_unchanged
                and last_seen_epoch is not None
                and this_epoch is not None
                and this_epoch <= last_seen_epoch
            ):
                skipped_unchanged_count += 1
                notDone = False  # rest of pagination is stale too
                break
            if this_epoch is not None and (
                max_epoch_this_run is None or this_epoch > max_epoch_this_run
            ):
                max_epoch_this_run = this_epoch
            try:
                newComputer = devices.JamfComputer(computerDetails=computer, source="uapi")
                events = newComputer.splunk_hec_events(meta_keys=meta_keys,
                                                       nameAsHost=settings['eventWriter']['host_as_device_name'],
                                                       timeAs=timeAs)
                for event in events:
                    write_event(event)
                processed_count += 1
            except Exception as E:
                # Per-record failure: route through the shared emitter so it lands
                # under sourcetype=jamf:input:error with the same key=value schema
                # as config/auth/endpoint failures. Loop continues for other records.
                jss_id = computer.get('id', 'unknown') if isinstance(computer, dict) else 'unknown'
                emit_input_error(
                    helper=helper, ew=ew,
                    category="record",
                    label="Computer inventory record",
                    target_url=settings['jamfSettings']['jss_url'],
                    summary="Error processing computer id=%s: %s: %s" % (jss_id, type(E).__name__, E),
                    record_id=jss_id,
                )

    # === post-loop endpoint-error rollup ================================
    # Without this, a 4xx/5xx storm against /api/v1/computers-inventory
    # silently produces processed=0 and looks healthy in the Inputs UI.
    endpoint_errors = jamfPro.consume_endpoint_errors()
    if endpoint_errors:
        preview = "; ".join(
            "%s (status=%s, %s)" % (u, s if s is not None else "n/a", d)
            for (u, s, d, _perm) in endpoint_errors[:5]
        )
        more = "" if len(endpoint_errors) <= 5 else " (+%d more)" % (len(endpoint_errors) - 5)
        emit_input_error(
            helper=helper, ew=ew,
            category="endpoint",
            label="Computer inventory endpoint",
            target_url=settings['jamfSettings']['jss_url'],
            summary="%d Jamf Pro request(s) failed this run: %s%s"
                    % (len(endpoint_errors), preview, more),
        )
        any_permanent = any(perm for (_, _, _, perm) in endpoint_errors)
        if processed_count == 0 and any_permanent:
            _status = next((s for (_, s, _, p) in endpoint_errors if p), None)
            auto_disable_input(helper, "jamfcomputers",
                "This input was disabled after Jamf Pro returned HTTP %s on every request this run. "
                "Check your URL and account permissions, then re-enable this input."
                % _status)

    # === post-loop checkpoint write =====================================
    helper.log_info(
        "jamfcomputers: processed=%d skipped_unchanged=%d pages=%d skip_unchanged=%s endpoint_errors=%d"
        % (processed_count, skipped_unchanged_count, pageCount, skip_unchanged, len(endpoint_errors))
    )
    if (
        skip_unchanged
        and max_epoch_this_run is not None
        and max_epoch_this_run != last_seen_epoch
    ):
        write_checkpoint(helper, 'jamfcomputers', stanza_name, max_epoch_this_run)
    # ====================================================================
