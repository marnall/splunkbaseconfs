# encoding = utf-8

import json
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
    helper.log_info("jamfmobiledevices collect_events started: input=%r" % helper.get_input_stanza_names())
    headers = {
        'User-Agent': jamfpro.build_user_agent(helper, 'jamfmobiledevices')
    }
    # Parse sections. Splunk modinput serializes multi-value params with '~'
    # when passing them to the input runtime, even when globalConfig.json
    # declares ',' as the delimiter, so accept both.
    raw_sections = helper.get_arg('sections', None)
    all_known_sections = ['general', 'location', 'purchasing', 'applications', 'security', 'network', 'certificates', 'configuration_profiles', 'provisioning_profiles', 'mobile_device_groups', 'extension_attributes']

    if raw_sections:
        if isinstance(raw_sections, str):
            parsed_sections = [s.strip() for s in raw_sections.replace('~', ',').split(',') if s.strip()]
        elif isinstance(raw_sections, list):
            parsed_sections = raw_sections
        else:
            parsed_sections = all_known_sections
    else:
        # Default to all if not specified, or if empty string
        parsed_sections = all_known_sections

    # Parse platforms with the same multi-value handling. Passing the raw
    # tilde-joined string into FilterMobileDeviceMeta._platFormIn would iterate
    # character-by-character, silently matching device model identifiers
    # against single letters (almost always truthy) and breaking the filter.
    raw_platforms = helper.get_arg('platforms', None)
    if isinstance(raw_platforms, str):
        parsed_platforms = [s.strip() for s in raw_platforms.replace('~', ',').split(',') if s.strip()]
    elif isinstance(raw_platforms, list):
        parsed_platforms = raw_platforms
    else:
        parsed_platforms = None

    def _compat(new_key, old_key, default=None):
        v = helper.get_arg(new_key, None)
        return v if v is not None else helper.get_arg(old_key, default)

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
            "jss_url":      creds['jss_url'],
            "jss_username": creds['jss_username'],
            "jss_password": creds['jss_password'],
        },
        "devicesCollection": {
            "details":              helper.get_arg('device_collection_details', None),
            "days_since_contact":   _compat('days_since_contact', 'daysSinceContact', None),
            "exclude_none_managed": _compat('exclude_none_managed', 'excludeNoneManaged', False),
            "platforms":            parsed_platforms,
            "sections":             parsed_sections
        },
        "eventWriter": {
            "host_as_device_name": helper.get_arg('host_as_device_name', None),
            "eventTimeFormat":     helper.get_arg('event_time_format', None)
        },
        "outbound": {
            "use_proxy": False,
            "verifyTLS": True,
            "retryCount": 3,
            "timeOut": 60
        }
    }

    # functions:

    def write_event(thisEvent=None):
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

        event = helper.new_event(data=json.dumps(thisEvent, ensure_ascii=False), source=source, time=eventTime,
                                 host=host,
                                 sourcetype=sourcetype)
        ew.write_event(event)
        return True

    # Jamf URL
    if str(settings['jamfSettings']['jss_url'])[-1] != '/':
        settings['jamfSettings']['jss_url'] = settings['jamfSettings']['jss_url'] + '/'

    if str(settings['jamfSettings']['jss_url']).__contains__("http://"):  # NOSONAR — stripping http:// to enforce https
        settings['jamfSettings']['jss_url'] = settings['jamfSettings']['jss_url'].replace("http://", "")  # NOSONAR

    if str(settings['jamfSettings']['jss_url']).__contains__("https://"):
        settings['jamfSettings']['jss_url'] = settings['jamfSettings']['jss_url'].replace("https://", "")

    jamf_url = settings['jamfSettings']['jss_url']
    jamf_username = settings['jamfSettings']['jss_username']
    jamf_password = settings['jamfSettings']['jss_password']
    try:
        jpro = jamfpro.JamfPro(jamf_url=jamf_url, jamf_username=jamf_username, jamf_password=jamf_password,
                               helper=helper, headers=headers)
    except Exception as e:
        # If the account was auto-created by legacy_migration, point the operator
        # at the most likely cause (stale creds carried over from 2.12.x).
        from legacy_migration import migration_auth_failure_hint
        account_arg = helper.get_arg('account')
        account_name = account_arg.get('name') if isinstance(account_arg, dict) else account_arg
        hint = migration_auth_failure_hint(account_name, 'jamfmobiledevices')
        emit_input_error(
            helper=helper, ew=ew,
            category="auth",
            label="Jamf Pro authentication",
            target_url=creds.get('jss_url') or "(account URL not set)",
            summary="Failed to connect to Jamf Pro: %s%s" % (str(e), hint),
        )
        raise  # Re-raise so splunktaucclib's wrapper logs the traceback and reschedules
    
    mobile_devices = jpro.get_mobile_devices()
    # Collect Computers Process each time

    metaChecker = devices.FilterMobileDeviceMeta()
    if int(settings['devicesCollection']['days_since_contact'] or 0) == 0:
        endEpoch = 0
    else:
        endEpoch = int(str(time.time()).split(".")[0]) - int(settings['devicesCollection']['days_since_contact']) * 86400

    #endEpoch = 0

    countProcess = 0

    countPass = 0

    # === skip_unchanged setup (item 7) ===================================
    # Subset/basic gives us last_inventory_update_epoch (milliseconds) per
    # device, so we can skip the expensive per-device detail fetch when the
    # device hasn't been re-inventoried since the last checkpoint. Unlike
    # the computers input, the subset/basic endpoint isn't sorted by report
    # time, so no pagination short-circuit — savings come purely from
    # skipping the per-device follow-up call.
    skip_unchanged_arg = helper.get_arg('skip_unchanged')
    skip_unchanged = skip_unchanged_arg in (True, 1, '1', 'true', 'True')
    stanza_name = helper.get_input_stanza_names()
    last_seen_epoch = (
        read_checkpoint(helper, 'jamfmobiledevices', stanza_name)
        if skip_unchanged else None
    )
    max_epoch_this_run = last_seen_epoch
    skipped_unchanged_count = 0
    # ====================================================================

    for mobile_device in mobile_devices:
        process, reason = metaChecker.keep_device(deviceMeta=mobile_device,
                                     endEpoch=endEpoch,
                                     excludeNoneManaged=settings['devicesCollection']['exclude_none_managed'],
                                     platformIn=settings['devicesCollection']['platforms'])
        if process:
            # Skip-unchanged check (item 7). last_inventory_update_epoch is
            # millis; convert to seconds for comparison with our checkpoint.
            this_epoch_ms = mobile_device.get('last_inventory_update_epoch')
            this_epoch = (this_epoch_ms / 1000.0) if this_epoch_ms else None
            if (
                skip_unchanged
                and last_seen_epoch is not None
                and this_epoch is not None
                and this_epoch <= last_seen_epoch
            ):
                skipped_unchanged_count += 1
                continue
            if this_epoch is not None and (
                max_epoch_this_run is None or this_epoch > max_epoch_this_run
            ):
                max_epoch_this_run = this_epoch
            try:
                deviceDetails = jpro.get_mobile_devices_details(id=mobile_device['id'], apiVersion="JSSResource")
                thisDevice = devices.MobileDeviceJSSResource(uapiModel=deviceDetails['mobile_device'])
                events = thisDevice.get_splunk_events(sections=settings['devicesCollection']['sections'], buildings={}, departments={})
                for event in events:
                    # Item 5 (partial): the per-event `print(event)` here
                    # corrupted Splunk's modular-input XML stdout stream and
                    # never reached the addon log. Demoted to helper.log_debug
                    # so it's available when developers turn on debug logging
                    # but inert in normal production runs.
                    helper.log_debug("jamfmobiledevices event: %s" % event)
                    write_event(thisEvent=event)
                countProcess += 1
            except Exception as e:
                # Per-device failure: route through the shared emitter so it lands
                # under sourcetype=jamf:input:error with the same key=value schema
                # as config/auth/endpoint failures. Loop continues for other devices.
                jss_id = mobile_device.get('id', 'unknown') if isinstance(mobile_device, dict) else 'unknown'
                emit_input_error(
                    helper=helper, ew=ew,
                    category="record",
                    label="Mobile device inventory record",
                    target_url=settings['jamfSettings']['jss_url'],
                    summary="Error processing mobile device id=%s: %s: %s" % (jss_id, type(e).__name__, e),
                    record_id=jss_id,
                )
        else:
            countPass += 1

    # === post-loop endpoint-error rollup ================================
    # Without this, a 4xx/5xx storm against /JSSResource/mobiledevices/* or
    # the detail endpoints silently produces processed=0 and looks healthy.
    endpoint_errors = jpro.consume_endpoint_errors()
    if endpoint_errors:
        preview = "; ".join(
            "%s (status=%s, %s)" % (u, s if s is not None else "n/a", d)
            for (u, s, d, _perm) in endpoint_errors[:5]
        )
        more = "" if len(endpoint_errors) <= 5 else " (+%d more)" % (len(endpoint_errors) - 5)
        emit_input_error(
            helper=helper, ew=ew,
            category="endpoint",
            label="Mobile device inventory endpoint",
            target_url=settings['jamfSettings']['jss_url'],
            summary="%d Jamf Pro request(s) failed this run: %s%s"
                    % (len(endpoint_errors), preview, more),
        )
        any_permanent = any(perm for (_, _, _, perm) in endpoint_errors)
        if countProcess == 0 and any_permanent:
            _status = next((s for (_, s, _, p) in endpoint_errors if p), None)
            auto_disable_input(helper, "jamfmobiledevices",
                "This input was disabled after Jamf Pro returned HTTP %s on every request this run. "
                "Check your URL and account permissions, then re-enable this input."
                % _status)

    # === post-loop checkpoint write (item 7) =============================
    helper.log_info(
        "jamfmobiledevices: processed=%d skipped_unchanged=%d skipped_filter=%d total=%d skip_unchanged=%s endpoint_errors=%d"
        % (countProcess, skipped_unchanged_count, countPass, len(mobile_devices), skip_unchanged, len(endpoint_errors))
    )
    if (
        skip_unchanged
        and max_epoch_this_run is not None
        and max_epoch_this_run != last_seen_epoch
    ):
        write_checkpoint(helper, 'jamfmobiledevices', stanza_name, max_epoch_this_run)
    # ====================================================================

