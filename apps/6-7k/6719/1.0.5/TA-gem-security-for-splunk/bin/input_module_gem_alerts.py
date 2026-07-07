# encoding = utf-8

import json

import gem_checkpoint
import gem_token

APP_NAME = "TA-gem-security-for-splunk"
CHECKPOINT_NAME = "gem-security-notifications-since"
NOTIFICATIONS_BACKEND = "https://app.gem.security/api/integrations/notification/"
HTTP_UNAUTHORIZED = 401


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    name = helper.get_arg("name")
    global_account = helper.get_arg("global_account")
    token = gem_token.Token(helper, global_account["client_id"], global_account["client_secret"])

    checkpoint = gem_checkpoint.Checkpoint(helper, "{}-{}".format(CHECKPOINT_NAME, name))
    since = checkpoint.value

    helper.log_debug("Requesting notifications since={}".format(since))
    resp = helper.send_http_request(
        NOTIFICATIONS_BACKEND,
        "GET",
        headers={
            "authorization": token.get(),
        },
        parameters={
            "ordering": "created",
            "created__gt": since,
        },
        timeout=60.0,
    )

    if resp.status_code == HTTP_UNAUTHORIZED:
        token.clear_cache()

    resp.raise_for_status()
    notifications = resp.json()
    helper.log_debug("Got {} notifications".format(len(notifications)))

    for notification in notifications:
        event = helper.new_event(
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            data=json.dumps(notification),
        )
        ew.write_event(event)

    if notifications:
        checkpoint.value = notifications[-1]["created"]
