import urllib.parse
from splunklib import client

APP_NAME = "JAMF-Pro-addon-for-splunk"


def auto_disable_input(helper, input_type, reason=""):
    """Disable the current input stanza via splunkd REST.

    Call AFTER emitting the error event. input_type must be one of
    "jamf", "jamfcomputers", or "jamfmobiledevices". reason is stored
    in the input_status_control field and shown in the UI when the user
    opens the edit form.
    """
    stanza_name = "(unknown)"
    try:
        session_key = helper.context_meta.get("session_key")
        server_uri  = helper.context_meta.get("server_uri") or "https://127.0.0.1:8089"
        stanza_name = helper.get_input_stanza_names()
        if isinstance(stanza_name, list):
            stanza_name = stanza_name[0]
        parsed = urllib.parse.urlparse(server_uri)
        svc = client.connect(
            token=session_key, app=APP_NAME, owner="nobody",
            scheme=parsed.scheme, host=parsed.hostname,
            port=parsed.port or 8089, autologin=True,
        )
        full_key = "{}://{}".format(input_type, stanza_name)
        update = {"disabled": "1"}
        if reason:
            update["input_status_control"] = reason
        svc.confs["inputs"][full_key].update(**update)
        helper.log_error(
            "Input %r auto-disabled: %s. Fix the configuration and re-enable via Inputs.",
            stanza_name, reason or "permanent 4xx error",
        )
    except Exception as exc:
        helper.log_error(
            "auto_disable_input: could not disable %r: %s", stanza_name, exc
        )
