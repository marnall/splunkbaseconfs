"""How this app builds a splunklib service when nobody hands it one.

One function, and it exists because two callers need a service object and
neither of them is a search command. A search command is handed an
authenticated service by the chunked protocol handler and uses it as it is:

    bin/input_task_poller.py   a modular input, handed a management URI and a
                               session key on stdin by splunkd
    bin/action_detonate.py     an alert action, handed the same two values in
                               its JSON payload

THE APP NAMESPACE IS THE WHOLE POINT OF THIS FILE
-------------------------------------------------
Everything either caller needs from splunkd is a namespaced object: the API
key in this app's `storage/passwords`, the task rows in this app's KV store
collections, and the community setting in this app's own conf file. A service
built with no namespace addresses none of them, and the failure is a 404 from
splunkd on a completely healthy install, which reads as "there is nothing
there" rather than as a misconfiguration. That is the shape of bug that gets
diagnosed as a missing feature.

splunklib's own `Script.service` builds exactly that namespace-less service,
which is why the poller does not use it, and it is the reason this is one
function in one file rather than four lines copied into two modules: a second
copy is how one of the two ends up in the default namespace six months from now.

WHY THIS IS NOT IN ps_client.py
-------------------------------
It is the obvious home, and it is the wrong one. `ps_client` is standard
library only by design (decision D1) and `tests/unit/test_ps_client.py`
asserts it, twice: once that it imports nothing outside the standard library
and once that it does not import splunklib at all. That constraint is load
bearing rather than tidy, because the client has to be constructible with a key
in hand and no vendored SDK on the path, which is how the setup page's test
button and most of the client's own tests drive it. Putting a splunklib import
inside a function there would satisfy the letter of both tests only by making
them weaker, so the code moved instead.
"""

import ps_log
from ps_client import APP_NAME, ClientConfigurationError

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "ps_splunkd"

# The owner namespace both callers want.
#
# "nobody" is the app-level context: it sees the collections the app ships and
# the credential the setup page stored under the app, rather than a private
# copy belonging to whichever user happened to save the search. An alert action
# fires from a scheduled search that may have no interactive owner at all, so a
# user-scoped namespace is not available to it in the first place.
APP_OWNER = "nobody"


def build_service(server_uri, session_key, app=APP_NAME, owner=APP_OWNER):
    """Return an authenticated splunklib service scoped to this app.

    The splunklib import is local to this function so that importing this
    module does not require the vendored SDK on sys.path, matching the rule
    ps_client is held to.

    :param server_uri: the splunkd management URI, as the payload carries it.
    :param session_key: the session token, as the payload carries it.
    :param app: the app namespace. Defaults to this app.
    :param owner: the owner namespace. See APP_OWNER.
    :return: an authenticated splunklib.client.Service.
    :raises ClientConfigurationError: if the URI is not a usable host and port.
        A message rather than a stack trace, because the caller is a background
        process and the only person who will read it is an operator in
        splunkd.log.
    """
    from urllib.parse import urlsplit

    from splunklib.client import Service

    text = "" if server_uri is None else str(server_uri).strip()
    if not text:
        raise ClientConfigurationError(
            "Splunk did not provide a management URI, so the app cannot read "
            "its own configuration or the stored API key."
        )

    parts = urlsplit(text, allow_fragments=False)
    if not parts.hostname or not parts.port or parts.scheme not in ("http", "https"):
        raise ClientConfigurationError(
            "The Splunk management URI is not an http or https host and port, "
            "so the app cannot reach splunkd."
        )

    # NO URI ON THIS LINE AND NO KEY EITHER. The URI is not a secret, but it is
    # configuration and ps_log has no name for it; the session key is a
    # credential and has none either. That is the whitelist working as intended.
    ps_log.debug(LOG_COMPONENT, "service_built", "ok")

    return Service(
        scheme=parts.scheme,
        host=parts.hostname,
        port=parts.port,
        token=session_key,
        app=app,
        owner=owner,
    )
