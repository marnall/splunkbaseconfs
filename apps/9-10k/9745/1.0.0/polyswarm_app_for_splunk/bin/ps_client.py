"""The one and only PolySwarm API client for this app.

No other module in this app may build a request, set an Authorization header,
read a credential out of Splunk storage, or choose a timeout. Everything goes
through this file. That keeps the credential handling surface to one module so
it can be reviewed in one sitting.

Why a hand written client and not polyswarm-api
-----------------------------------------------
This is a decision of record, not an oversight. Every polyswarm-api release
from 3.17 onward requires Python 3.10 or newer. Splunk 9.x ships Python 3.9,
and one app tarball has to run on both 9.x and 10.x because a customer installs
the same package across a mixed estate. Pinning an older polyswarm-api to reach
3.9 would mean vendoring a version nobody upstream supports, and it would pull
in requests, urllib3, and their transitive tree, each of which needs its own
pin, its own hash, and its own review.

The app needs a handful of GET endpoints. A thin client over urllib.request costs less
to own than that dependency tree, has no version floor above 3.9, and adds
nothing to the vendored surface. So the client is first-party and standard
library only: urllib.request, json, time. No third-party imports, and that
constraint is enforced by a test.

Layering
--------
    build_config()          pure, no I/O, fully testable
    apply_authorization()   pure, mutates the mapping it is handed
    get_api_key()           I/O seam: Splunk storage/passwords, via splunklib
    PolySwarmClient         the HTTP client, one method per endpoint

Pinned contracts
----------------
Two things in this file are contracts with something outside the app and must
not be tidied up by a future reader. Both are marked CONTRACT at their
definition: the Authorization header format, and the user agent string.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

import ps_log
from ps_sanitize import sanitize, sanitize_message

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "ps_client"

APP_NAME = "polyswarm_app_for_splunk"
APP_VERSION = "1.0.0"

# CONTRACT: the user agent string. Do not change it without reading this.
#
# Two other user agents already exist in PolySwarm's logs for Splunk related
# traffic, and support triages by substring match:
#
#     splunk_polyswarm_api/     the v1 community app, unmaintained
#     polyswarm-api/            the stock Python SDK, any caller
#
# This value is chosen so that no substring of it collides with either. It does
# not contain "splunk_polyswarm_api/" and it does not contain "polyswarm-api/",
# which is why the product name is written PSAppForSplunk with no underscore and
# no hyphen before the version. A well meaning rename to something like
# "polyswarm-api/1.0.0 (splunk)" or "splunk_polyswarm_api/1.0.0" would make this
# app's traffic indistinguishable from the v1 app's in aggregate, and the whole
# reason for a distinct agent is to tell a customer's v1 install from their v2
# install when they report a problem.
#
# THE VERSION HALF IS DERIVED FROM APP_VERSION ABOVE, and that is the release
# bump's own lesson rather than tidiness. The string carried a literal 0.1.0
# through the whole of the build, so bumping the package to a release candidate
# would have shipped an app that reported itself as 1.0.0-rc.1 to Splunk and as
# 0.1.0 to the platform, and adoption analytics would have counted every
# release candidate install as a scaffold install. Composing it here means the
# module holds one version, and tests/unit/test_conf_defaults.py asserts that
# version against default/app.conf so the package and the wire cannot disagree.
USER_AGENT = "PSAppForSplunk/{0}".format(APP_VERSION)

# CONTRACT: the Authorization header carries the API key verbatim.
#
# The PolySwarm REST API at api.polyswarm.network takes the raw key as the
# entire header value. There is no scheme prefix. Sending "Bearer <key>" fails
# authentication with a 401, and the failure looks like a bad key rather than a
# bad header, which is why this is written down here instead of being rediscovered.
AUTHORIZATION_HEADER = "Authorization"
AUTHORIZATION_SCHEME_PREFIX = ""

USER_AGENT_HEADER = "User-Agent"
ACCEPT_HEADER = "Accept"
CONTENT_TYPE_HEADER = "Content-Type"

JSON_CONTENT_TYPE = "application/json"

# The content type the presigned upload PUT declares. See _put_upload().
UPLOAD_CONTENT_TYPE = "text/plain"

DEFAULT_API_URI = "https://api.polyswarm.network/v3"

# The community every request carries when the app has not been told otherwise.
#
# "default" is not a placeholder and not this app's invention: it is the literal
# the polyswarm-api SDK sends, settings.DEFAULT_COMMUNITY, and the platform
# resolves it server side. The recorded sandbox task in
# tests/fixtures/sandbox-submit-recorded.json came back carrying community
# "mainnet1", which is the resolution rather than the request.
#
# WHAT THIS IS NOW, WHICH CHANGED WITH THE COMMUNITY RULE. Design section 4.3
# asks a detonation to default to the account's most private entitled community
# and never silently to a public one, and sending "default" does not implement
# that because the app is not choosing: the platform is. bin/community.py is
# where the choosing happens, per docs/decisions.md D15, and it hands the answer
# to this client's `community` argument. So this constant is what the app sends
# when there is nothing better to send, which is an account entitled to the
# public community only, and it stays the honest answer in that case: the
# platform resolves the account's own community and the task row records where
# the detonation actually went.
DEFAULT_COMMUNITY = "default"

# Splunk kills a search command that stalls, so the client must give up first
# and return a usable error instead of being terminated mid-write.
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 30.0
DEFAULT_TIMEOUT = 30.0

# Bounded retries. Three tries total, not three retries after the first.
DEFAULT_RETRIES = 3
MAX_TRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.5

# Retried: rate limiting and server faults, both of which are transient by
# definition. A 4xx other than 429 is a statement about the request, and
# repeating an identical request cannot change the answer.
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)

# Never retried, at any status, for any reason. An authentication failure that
# is retried three times is three chances to trip a lockout or a rate limiter
# on a key that is simply wrong.
NEVER_RETRY_STATUS_CODES = (400, 401, 403, 404, 405, 409, 422)

# THE PLATFORM IS ALLOWED TO SET THE PACE, AND ONLY ON THE TWO STATUSES THAT
# MEAN "COME BACK LATER".
#
# 429 and 503 are the two answers whose whole content is a waiting time, and
# RFC 9110 section 10.2.3 defines Retry-After on exactly them (plus a 3xx
# redirect this app never follows). A 500 or a 502 is a fault rather than a
# schedule, so a Retry-After arriving on one is ignored and the exponential
# backoff is used, which keeps the header's meaning to the one case where the
# platform is stating a policy.
RETRY_AFTER_HEADER = "Retry-After"
RETRY_AFTER_STATUS_CODES = (429, 503)

# ONLY THE DELAY-SECONDS FORM IS READ. RFC 9110 permits an HTTP-date as well,
# and reading one here would mean converting a date in the past or the future
# against this machine's clock, inside a module whose import surface is the
# standard library minus almost all of it (see the import assertion in
# tests/unit/test_ps_client.py). A header this app cannot parse is treated as
# absent and the exponential backoff is used, which is the same outcome as no
# header at all rather than a failure. Documented in docs/troubleshooting.md
# section 4 so that an operator reading a wait they did not expect has the
# answer in the same place as the log line.

# THE CEILING, AND WHY IT IS THIRTY SECONDS.
#
# A Splunk search command is not free to sleep for as long as a platform asks.
# Three things bound it: the search itself, which a user or a dashboard will
# cancel; the app's own read timeout, DEFAULT_READ_TIMEOUT above, which is 30
# seconds and is the longest this app already accepts for a single request; and
# the alert action's window, where a detonation firing on a schedule has to
# finish before the next firing. Thirty seconds matches the read timeout on
# purpose: it is the delay this app is already willing to spend waiting on one
# request, so honouring a Retry-After up to that figure adds no new worst case
# to a search, and a platform asking for longer than the request timeout is
# asking for a wait that belongs to the next search rather than this one. Two
# sleeps at the ceiling is 60 seconds of a three-try GET, which is inside the
# default 100-second wait a dashboard panel will tolerate.
#
# NOTHING IN THIS MODULE EVER SLEEPS LONGER THAN THIS, whatever the header says
# and whatever max_tries and backoff_factor are set to. The cap is applied to
# the computed delay rather than only to the header, so a configured backoff
# cannot walk past it either.
MAX_RETRY_AFTER_SECONDS = 30.0

# Treated as "the platform has nothing on this indicator" rather than an error.
# 404 is the documented answer for an unknown hash. Both are a normal result for
# a search over arbitrary indicators from an index, not an exceptional
# condition, so they return None and the caller emits an unknown verdict.
#
# 204 IS CONTRACT, NOT CAUTION, AND search_url IS WHERE THAT WAS SETTLED.
#
# This tuple carried 204 before any URL search existed, on the reasoning that
# an artifact could be known while carrying no assertions yet. That reasoning
# was a guess. The live check on 2026-09-04 recorded in
# tests/fixtures/search-url-recorded.json settled it for the URL endpoint: a URL
# the platform holds no record for answers HTTP 204 WITH AN EMPTY BODY. Not a
# 404, and not a 200 carrying an empty result list. So the handling that was
# already here is now the pinned behaviour of a live endpoint, and removing 204
# from this tuple would turn every unknown URL in a customer's proxy logs into a
# failed lookup. The empty-body branch in _decode() is the second half of the
# same contract and carries the same note.
NOT_FOUND_STATUS_CODES = (204, 404)

# ---------------------------------------------------------------------------
# The metadata search, which is the only paginated endpoint in this app
# ---------------------------------------------------------------------------
#
# Mirrored from the polyswarm-api SDK, path and parameter names both, in the
# same way the sandbox constants below are: the SDK is the only executable
# statement of the protocol we have.
#
#     api.search_by_metadata(query, include, exclude, ips, urls, domains)
#       -> resources.Metadata.get(api, query=..., community=api.community,
#                                 include=..., exclude=..., ...)
#       -> core.BaseJsonResource.get, which puts every keyword in the query
#          string on a GET
#
# so the wire form is
#
#     GET /v3/search/metadata/query?query=<q>&community=<c>
#         [&include=<f>...][&exclude=<f>...][&offset=<cursor>&limit=<n>]
#
# RESOURCE_ENDPOINT on resources.Metadata is '/search/metadata/query', which is
# the whole path: unlike the sandbox provider list this is not reached through
# BaseJsonResource.list and nothing appends a '/list' segment to it.
METADATA_SEARCH_PATH = "/search/metadata/query"

# The field catalog. Not called by this app at runtime and named here because
# the catalog is what the query builder's field names are checked against:
# tests/fixtures/metadata-mappings-recorded.json is a pruned capture of it, and
# tests/unit/test_input_intel_pull.py asserts that every field name the query
# names is a field the platform actually declares. A constant rather than a
# comment so that a later caller has one spelling to use.
METADATA_MAPPINGS_PATH = "/search/metadata/mappings"

METADATA_QUERY_PARAM = "query"
METADATA_COMMUNITY_PARAM = "community"
METADATA_INCLUDE_PARAM = "include"
METADATA_EXCLUDE_PARAM = "exclude"

# PAGINATION IS CURSOR BASED AND THE CURSOR IS AN OPAQUE STRING, WHICH IS THE
# ONE THING A READER WILL GUESS WRONG ABOUT THIS ENDPOINT.
#
# The parameter is spelled `offset`, which reads like a row number, and it is
# not one. The recorded live response carries
#
#     "offset": "gAAAAABqoHhB..."
#
# a Fernet-shaped token, and the way to get the next page is to send that
# string straight back. core.PolyswarmRequest.next_page is the SDK doing
# exactly that, and it is where both names come from:
#
#     params['offset'] = self.offset
#     params['limit']  = self.limit
#
# So nothing in this app ever computes an offset, adds a page size to one, or
# starts one at zero. Arithmetic on this value produces a token the platform
# cannot decrypt, and the failure is a page of results that silently is not the
# next page.
METADATA_OFFSET_PARAM = "offset"
METADATA_LIMIT_PARAM = "limit"

# The envelope keys the paginated response carries beside its result list.
#
# has_more is the loop condition. core.PolyswarmRequest.parse_result notes it
# "will always be present, being either False or True", and consume_results
# stops on it rather than on an empty page, which is the behaviour the caller
# here mirrors.
METADATA_HAS_MORE_FIELD = "has_more"

# ---------------------------------------------------------------------------
# The sandbox endpoints, and the one protocol in this app that is not a GET
# ---------------------------------------------------------------------------
#
# Every path and every field name below is mirrored from the polyswarm-api SDK
# rather than read out of documentation, and each one carries the file and the
# method it was mirrored from. The SDK is the only executable statement of this
# protocol we have, and a detonation is the most expensive metered call in the
# product, so "close enough" here is a bill rather than a bug.

# GET, list form. Mirrors resources.SandboxProvider (RESOURCE_ENDPOINT
# "/sandbox/provider") reached through core.BaseJsonResource.list, which
# appends "/list". Recorded live: tests/fixtures/sandbox-providers-recorded.json.
SANDBOX_PROVIDER_LIST_PATH = "/sandbox/provider/list"

# GET, status by task id. Mirrors resources.SandboxTask.RESOURCE_ENDPOINT
# reached through core.BaseJsonResource.get.
SANDBOX_TASK_PATH = "/sandbox/sandboxtask"

# POST to create, PUT to finalize. Mirrors resources.SandboxTask.create_file
# and update_file, both of which append "/instance" to the resource endpoint:
#
#     create_file:  cls._build_request(api, 'POST', cls._create_endpoint(...) + '/instance', ...)
#     update_file:  cls._build_request(api, 'PUT',  cls._update_endpoint(...) + '/instance', ...)
#
# THE "/instance" SEGMENT IS LOAD BEARING AND IT IS EASY TO LOSE. The task
# resource's own endpoint, the one the status GET uses, is the path above with
# no suffix, so a reader tidying these two constants into one would send the
# create to a path that is not the create path. The SDK is the citation.
SANDBOX_TASK_INSTANCE_PATH = "/sandbox/sandboxtask/instance"

# The query parameter the status GET names the task under.
#
# MEASURED FROM THE SDK, NOT GUESSED, AND IT IS NOT "id". api.sandbox_task_status
# calls resources.SandboxTask.get(self, sandbox_task_id=sandbox_task_id), and
# SandboxTask.get adds community=api.community. core.BaseJsonResource.get builds
# its parameters with _get_params, which is _params('GET', *RESOURCE_ID_KEYS),
# and on a GET every keyword lands in the query string whatever RESOURCE_ID_KEYS
# says. So the wire form is
#
#     GET /v3/sandbox/sandboxtask?sandbox_task_id=<id>&community=<community>
#
# RESOURCE_ID_KEYS is ['id'] on this resource and that matters only for the
# finalize PUT, where it is what puts id in the query string and community in
# the body. See sandbox_submit_url().
SANDBOX_TASK_ID_PARAM = "sandbox_task_id"

# Field names in the create body. Mirrored one for one from the create_file
# call in api.sandbox_url.
SANDBOX_ARTIFACT_NAME_FIELD = "artifact_name"
SANDBOX_ARTIFACT_TYPE_FIELD = "artifact_type"
SANDBOX_COMMUNITY_FIELD = "community"
SANDBOX_PROVIDER_SLUG_FIELD = "provider_slug"
SANDBOX_VM_SLUG_FIELD = "vm_slug"
SANDBOX_BROWSER_FIELD = "browser"
SANDBOX_NETWORK_ENABLED_FIELD = "network_enabled"

# The artifact type a URL detonation declares.
SANDBOX_ARTIFACT_TYPE_URL = "URL"

# The task shape's own field names, used ONLY to fill in a finalize answer that
# arrived without one. See sandbox_submit_url()'s receipt note: nothing here
# reads a response for its meaning, and bin/task_store.py is still the one
# reader of the task shape. These names are the ones that module already uses,
# task_store.RESPONSE_TASK_ID_FIELD and its CONFIG_* set, and they are pinned by
# tests/fixtures/sandbox-submit-recorded.json, whose config carries "target" and
# a "provider" and a "vm" object each holding a "slug". They are spelled again
# here rather than imported because ps_client must not depend on a module that
# reads shapes, and tests/unit/test_ps_client.py asserts the two spellings
# against each other so they cannot drift apart in silence.
SANDBOX_CONFIG_FIELD = "config"
SANDBOX_CONFIG_TARGET_FIELD = "target"
SANDBOX_CONFIG_PROVIDER_FIELD = "provider"
SANDBOX_CONFIG_VM_FIELD = "vm"
SANDBOX_SLUG_FIELD = "slug"

# The two fields the client reads out of the create response, and the only two.
#
# Reading anything at all is a departure from the transport-only rule the rest
# of this file keeps, so it is bounded here and explained in sandbox_submit_url:
# the three-step protocol cannot be executed without the task id and the upload
# URL, so these are protocol plumbing rather than interpretation. Every other
# field passes through untouched, and there is still exactly one reader of the
# task shape, bin/task_store.py.
SANDBOX_TASK_ID_FIELD = "id"
SANDBOX_UPLOAD_URL_FIELD = "upload_url"

# The envelope key every v3 response wraps its body in.
#
# Named here because the sandbox protocol is the first place in this app that
# has to read a field out of a response inside the client. The SDK's request
# layer takes json.get('result') unconditionally
# (core.PolyswarmRequest._extract_json_body), which is what makes the envelope a
# platform-wide fact rather than a per-endpoint one, and the recorded providers
# body carries it. Recognised by the TYPE of its value and never by the name
# alone, for the reason cmd_usage.unwrap carries: an object may hold its own
# "result" key.
ENVELOPE_FIELD = "result"

# What the upload step reports itself as on its one log line.
#
# A literal, and never the presigned URL. ps_log's endpoint key is documented
# as an API path with no query parameters, and a presigned URL is the exact
# opposite of that: it is a bearer credential whose authorisation lives in its
# query string. See _put_upload().
SANDBOX_UPLOAD_LOG_ENDPOINT = "/sandbox/upload"

# network_enabled is sent as 1 rather than true, and that is a mirror and not a
# preference. core.BaseJsonResource._params converts a bool with int(v) before
# it reaches the JSON body, so the SDK puts 1 on the wire. A reader "fixing"
# this to a JSON boolean would be changing the request the platform has been
# observed to accept.
SANDBOX_NETWORK_ENABLED_ON = 1

# Splunk credential storage coordinates. The key is written here by the setup
# page and read back through splunklib. It is never in a .conf file.
CREDENTIAL_REALM = "polyswarm_app_for_splunk"
CREDENTIAL_USERNAME = "api_key"

# No module logger here. Everything this module writes goes through ps_log, so
# that the whitelist is the only way a value reaches a log line from the one
# module in the app that holds a credential.


class ClientConfigurationError(Exception):
    """Raised when the app cannot assemble a usable client configuration."""


class ClientError(Exception):
    """Raised when an API call fails in a way the caller cannot recover from.

    Every message reaching this class has already been through the sanitizer.
    """


class AuthenticationError(ClientError):
    """Raised on a 401 or 403. Never retried."""


class RateLimitError(ClientError):
    """Raised when a 429 is still a 429 after every attempt has been spent.

    A SUBCLASS SO THAT NOTHING ALREADY WRITTEN CHANGES BEHAVIOUR. Every caller
    that catches ClientError today catches this too, and the messages are
    identical to the ones ClientError carried before this class existed, so the
    analyst sees no difference. What the subclass adds is the ability to tell
    "we are over the rate limit" apart from "the platform is broken" WITHOUT
    matching on the text of a message, which is what a caller would otherwise
    have to do.

    THE CALLER THIS EXISTS FOR is the enrichment command. A search enriching
    hundreds of indicators that runs into the account's rate limit should stop
    asking and say so on its finish line, where a 502 storm is a different
    conversation. It catches this class specifically, ahead of ClientError:

        except RateLimitError:
            ...  # over the limit: stop, report, do not keep spending
        except ClientError:
            ...  # everything else

    `status` is 429 for the same reason, so a caller that would rather test an
    attribute than an exception class has one, and it is a class attribute
    rather than a constructor argument so that _fail() stays a one-liner and
    nothing needs to construct these by hand.
    """

    status = 429


class ClientConfig(object):
    """An immutable, fully resolved client configuration.

    Holding the credential on this object rather than in module state means a
    test can build one, assert on every field, and throw it away.
    """

    __slots__ = (
        "api_key",
        "uri",
        "community",
        "connect_timeout",
        "read_timeout",
        "retries",
        "backoff_factor",
        "user_agent",
        "verify",
    )

    def __init__(
        self,
        api_key,
        uri,
        community,
        connect_timeout,
        read_timeout,
        retries,
        backoff_factor,
        user_agent,
        verify,
    ):
        self.api_key = api_key
        self.uri = uri
        self.community = community
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.retries = retries
        self.backoff_factor = backoff_factor
        self.user_agent = user_agent
        self.verify = verify

    @property
    def timeout(self):
        """The connect and read pair, in the form the HTTP layer expects."""
        return (self.connect_timeout, self.read_timeout)

    def redact(self, obj):
        """Sanitize an arbitrary value against this config's credential."""
        return sanitize(obj, secrets=(self.api_key,))

    def redact_message(self, text):
        """Sanitize a preformatted message against this config's credential."""
        return sanitize_message(text, secrets=(self.api_key,))

    def __repr__(self):
        # Deliberately omits the credential. A ClientConfig ends up in tracebacks
        # and log lines, so its repr has to be safe by construction.
        return "<ClientConfig uri={0!r} community={1!r} retries={2!r}>".format(
            self.uri, self.community, self.retries
        )


def build_config(
    api_key,
    uri=None,
    community=None,
    connect_timeout=None,
    read_timeout=None,
    retries=None,
    backoff_factor=None,
    user_agent=None,
    verify=True,
):
    """Resolve a complete ClientConfig from partial input. Pure, no I/O.

    :raises ClientConfigurationError: if the credential is missing or the
        numeric settings are outside a workable range.
    """
    if not api_key or not str(api_key).strip():
        raise ClientConfigurationError(
            "No PolySwarm API key is configured. Set one on the app setup page."
        )

    resolved_uri = (uri or DEFAULT_API_URI).rstrip("/")
    if not resolved_uri.startswith("https://"):
        raise ClientConfigurationError(
            "The PolySwarm API URI must use https. Refusing to send a "
            "credential over an unencrypted connection."
        )

    resolved_retries = DEFAULT_RETRIES if retries is None else int(retries)
    if resolved_retries < 0:
        raise ClientConfigurationError("Retry count cannot be negative.")

    resolved_connect = float(
        DEFAULT_CONNECT_TIMEOUT if connect_timeout is None else connect_timeout
    )
    resolved_read = float(
        DEFAULT_READ_TIMEOUT if read_timeout is None else read_timeout
    )
    if resolved_connect <= 0 or resolved_read <= 0:
        raise ClientConfigurationError("Timeouts must be greater than zero.")

    resolved_backoff = float(
        DEFAULT_BACKOFF_FACTOR if backoff_factor is None else backoff_factor
    )
    if resolved_backoff < 0:
        raise ClientConfigurationError("Backoff factor cannot be negative.")

    return ClientConfig(
        api_key=str(api_key).strip(),
        uri=resolved_uri,
        community=community or DEFAULT_COMMUNITY,
        connect_timeout=resolved_connect,
        read_timeout=resolved_read,
        retries=resolved_retries,
        backoff_factor=resolved_backoff,
        user_agent=user_agent or USER_AGENT,
        verify=bool(verify),
    )


def apply_authorization(headers, config):
    """Install the auth and identity headers on a mutable header mapping.

    The API key is written verbatim. There is no scheme prefix. This is the
    only place in the app that assigns the Authorization header, which is why
    it takes the mapping as an argument rather than building a literal.

    See the CONTRACT note on AUTHORIZATION_HEADER above.

    :param headers: a mutable mapping.
    :param config: a ClientConfig from build_config().
    :return: the same mapping, for chaining.
    """
    headers[AUTHORIZATION_HEADER] = AUTHORIZATION_SCHEME_PREFIX + config.api_key
    headers[USER_AGENT_HEADER] = config.user_agent
    headers[ACCEPT_HEADER] = "application/json"
    return headers


def unwrap_envelope(payload):
    """Return the body inside a v3 response envelope, or the payload itself.

    Pure. The envelope is recognised by the TYPE of its "result" value and
    never by the name alone, for the reason cmd_usage.unwrap carries: an object
    is free to hold its own "result" key, and following the name into a boolean
    or a list would report nothing for a response the platform answered.

    Present in this module, and not only in the command layer, because the
    sandbox submit protocol has to read two fields out of a create response
    before it can finish. See sandbox_submit_url().
    """
    if not isinstance(payload, dict):
        return None
    inner = payload.get(ENVELOPE_FIELD)
    if isinstance(inner, dict):
        return inner
    return payload


def read_retry_after(headers):
    """Return the Retry-After delay in seconds, or None when there is none.

    Pure, and deliberately narrow. None means "no usable instruction", and the
    caller falls back to its own exponential backoff, so every unreadable form
    lands in the same place as an absent header:

      * no headers object, or no such header
      * an HTTP-date, which this app does not parse. See the note on
        MAX_RETRY_AFTER_SECONDS: converting a date would mean trusting this
        machine's clock against the platform's inside the one module whose
        import surface is asserted by a test, and the fallback is a backoff
        this app already has
      * a negative number, or anything that is not a number at all

    A zero is returned as 0.0 rather than as None, because "retry immediately"
    is a real instruction and is not the same as no instruction.

    NOT CAPPED HERE. This function reports what the platform asked for; the
    ceiling is applied by the caller, in one place, so that the cap covers the
    exponential backoff as well.

    :param headers: the header mapping off an HTTPError, or anything with a
        get() method. urllib gives an email.message.Message, whose get() is
        case insensitive, and a test may pass a plain dict.
    """
    if headers is None:
        return None

    getter = getattr(headers, "get", None)
    if not callable(getter):
        return None

    try:
        value = getter(RETRY_AFTER_HEADER)
    except Exception:
        # A header container that raises is a container this app does not
        # understand, and a failure reading a hint must never become the
        # failure of the request the hint arrived on.
        return None

    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        seconds = float(int(text))
    except (TypeError, ValueError):
        # An HTTP-date, or anything else. Treated as absent.
        return None

    if seconds < 0:
        return None
    return seconds


def read_task_field(payload, name):
    """Return one protocol field out of a sandbox task response, or None.

    Pure. TWO FIELDS ONLY EVER GO THROUGH HERE, the task id and the upload URL,
    and that is a boundary rather than a coincidence: they are what the
    three-step protocol needs in order to run, so reading them is plumbing.
    Everything else about a task shape is read in bin/task_store.py, which is
    the one reader, and this function is not the place to grow a second one.

    A value that is not a scalar reads as absent, because a mapping or a list
    under either of these names is a shape this app does not understand and
    guessing at it would be worse than refusing.

    :param payload: the decoded response, enveloped or not.
    :param name: the field to read.
    :return: the value as a stripped string, or None.
    """
    body = unwrap_envelope(payload)
    if not isinstance(body, dict):
        return None
    value = body.get(name)
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (dict, list, tuple)):
        return None
    text = str(value).strip()
    return text or None


# ---------------------------------------------------------------------------
# Credential retrieval
# ---------------------------------------------------------------------------


def get_api_key(service):
    """Read the stored PolySwarm API key from Splunk credential storage.

    Takes the splunklib service object a search command already holds as
    self.service, rather than a session key and a management port, because the
    command is handed an authenticated service by the chunked protocol handler
    and there is no reason for this app to build a second connection.

    The key lives in storage/passwords under a fixed realm and username, where
    splunkd keeps it encrypted at rest. It is deliberately not readable from a
    .conf file: files under default/ and local/ are world readable on a search
    head and are copied wholesale into deployment bundles.

    Failures are reported without the value that failed. A missing credential is
    an operator problem, so the message names the realm and the setup step and
    nothing else.

    WHY THE UNDERLYING ERROR TEXT IS DISCARDED
    ------------------------------------------
    Every failure below reports the exception's class name and nothing else. The
    underlying message is deliberately dropped, and this is the one place in the
    app where the sanitizer cannot be the answer.

    The sanitizer's value rule works by replacing known secrets in a string. It
    needs the secret to redact it. This function is what obtains the secret, so
    on every one of these paths there is no key in hand to redact against: a
    failure here means the read did not complete. splunklib's binding layer
    quotes the HTTP exchange it attempted into its exception messages, and a
    storage/passwords exchange can carry a decrypted value, so passing that text
    through sanitize_message() with no secrets would be a no-op that looks like a
    safeguard. That is worse than dropping the text, because it reads as handled.

    The class name is kept because it is the diagnostically useful half and it
    cannot carry a payload: AuthenticationFailed, HTTPError, and ConnectionError
    tell an operator which of the three things went wrong, and none of them is
    derived from the stored value.

    :param service: an authenticated splunklib.client.Service.
    :return: the API key as a string.
    :raises ClientConfigurationError: when no credential is stored, or when
        storage cannot be reached.
    """
    if service is None:
        raise ClientConfigurationError(
            "No Splunk service is available, so the PolySwarm API key cannot "
            "be read from credential storage."
        )

    try:
        storage = service.storage_passwords
    except Exception as error:
        raise ClientConfigurationError(
            "Could not reach Splunk credential storage ({0}). Check that the "
            "app is installed correctly and that splunkd is "
            "reachable.".format(type(error).__name__)
        )

    try:
        for entry in storage:
            if (
                getattr(entry, "realm", None) == CREDENTIAL_REALM
                and getattr(entry, "username", None) == CREDENTIAL_USERNAME
            ):
                value = getattr(entry, "clear_password", None)
                if value and str(value).strip():
                    return str(value).strip()
    except ClientConfigurationError:
        raise
    except Exception as error:
        raise ClientConfigurationError(
            "Could not read the PolySwarm API key from credential storage "
            "({0}). The running user may lack the capability to read "
            "storage/passwords.".format(type(error).__name__)
        )

    raise ClientConfigurationError(
        "No PolySwarm API key is stored under realm '{0}'. Open the app setup "
        "page and save a key.".format(CREDENTIAL_REALM)
    )


# ---------------------------------------------------------------------------
# The client
# ---------------------------------------------------------------------------


class PolySwarmClient(object):
    """A thin, standard library only client for the PolySwarm REST API.

    One method per endpoint the app uses. Nothing is cached across instances
    and nothing is stored at module scope, so a search command builds one,
    uses it for the duration of the search, and drops it.

    Every error path in this class routes through the sanitizer before a
    message is built. The invariant is that the API key is unrecoverable from
    the str() or repr() of anything this class raises, and that is tested.
    """

    def __init__(
        self,
        api_key,
        base_url=None,
        timeout=None,
        max_tries=None,
        backoff_factor=None,
        opener=None,
        community=None,
    ):
        """
        :param api_key: the PolySwarm API key.
        :param base_url: API root, defaults to DEFAULT_API_URI.
        :param timeout: per request timeout in seconds, defaults to 30.
        :param max_tries: total attempts per call, including the first.
        :param backoff_factor: exponential backoff base, in seconds.
        :param opener: a urlopen-compatible callable, for tests. Production
            leaves this None so urllib.request.urlopen is looked up at call
            time rather than bound at construction.
        :param community: the community to scope requests to. NONE MEANS
            DEFAULT_COMMUNITY, which is what every caller sent before
            bin/community.py existed and is what the SDK's own
            settings.DEFAULT_COMMUNITY sends: the platform then resolves the
            account's own community. The argument exists because the community
            is resolved per invocation, from the operator's setting or from the
            account's entitlement, and a client cannot read either: see
            bin/community.py for the rule and docs/decisions.md D15 for why it
            arrives here rather than being read inside this module.
        """
        self.config = build_config(
            api_key,
            uri=base_url,
            community=community,
            read_timeout=timeout,
            backoff_factor=backoff_factor,
        )
        self.base_url = self.config.uri
        self.timeout = DEFAULT_TIMEOUT if timeout is None else float(timeout)
        self.max_tries = MAX_TRIES if max_tries is None else int(max_tries)
        if self.max_tries < 1:
            raise ClientConfigurationError("max_tries must be at least one.")
        self.backoff_factor = self.config.backoff_factor
        self._opener = opener

        # Call counter. The search command's dedup guarantee is that each
        # distinct hash costs one request, and a test asserts on this rather
        # than on a mock's internals.
        self.call_count = 0

    # -- sanitization ----------------------------------------------------

    def _clean(self, value):
        """Sanitize any value against this client's credential."""
        return sanitize_message(value, secrets=(self.config.api_key,))

    def _fail(self, exception_class, template, *args):
        """Build and raise a sanitized exception.

        The template is formatted first and the whole result sanitized, so a
        credential appearing through any argument is removed regardless of
        which argument carried it. Nothing is logged here: the caller decides
        whether a failure is worth a log line, and this keeps a single failure
        from being recorded twice.
        """
        try:
            message = template.format(*args)
        except (IndexError, KeyError, ValueError):
            message = template
        raise exception_class(self._clean(message))

    # -- transport -------------------------------------------------------

    def _build_request(self, url, method="GET", json_body=None):
        """Build one authenticated request against the PolySwarm API.

        :param url: the absolute URL, already built by _build_url().
        :param method: the HTTP method.
        :param json_body: a mapping to send as a JSON body, or None.

        The Content-Type is set explicitly whenever there is a body, because
        urllib picks one for you otherwise: AbstractHTTPHandler.do_request_
        stamps application/x-www-form-urlencoded on any request carrying data
        and no content type, which would describe a JSON body as a form.
        """
        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method)
        headers = {}
        apply_authorization(headers, self.config)
        if data is not None:
            headers[CONTENT_TYPE_HEADER] = JSON_CONTENT_TYPE
        for name, value in headers.items():
            request.add_header(name, value)
        return request

    def _urlopen(self, request, timeout):
        if self._opener is not None:
            return self._opener(request, timeout=timeout)
        return urllib.request.urlopen(request, timeout=timeout)

    def _sleep(self, seconds):
        """Isolated so a test can assert on backoff without waiting."""
        time.sleep(seconds)

    def _backoff_for(self, attempt):
        """Exponential backoff for a zero-based attempt number."""
        return self.backoff_factor * (2 ** attempt)

    def _delay_for(self, attempt, retry_after=None):
        """Seconds to wait before the next attempt. Never above the ceiling.

        THE PLATFORM'S OWN FIGURE WINS WHEN THERE IS ONE, and that is the whole
        point of reading the header: the exponential backoff spends its three
        attempts inside a second and a half, so a platform asking for 30
        seconds used to get three requests 0.5 s and 1 s apart and then a
        failure. That is not a retry, it is a burst against a limiter that has
        already said no, and it makes the customer's rate limit worse rather
        than riding it out.

        The ceiling applies to whatever comes out of here, the backoff
        included, so that no single sleep in this client can exceed
        MAX_RETRY_AFTER_SECONDS however it is configured.

        :param attempt: the zero-based number of the attempt that just failed.
        :param retry_after: the platform's requested delay in seconds from
            read_retry_after(), or None to use the backoff.
        """
        delay = self._backoff_for(attempt) if retry_after is None else retry_after
        if delay > MAX_RETRY_AFTER_SECONDS:
            return MAX_RETRY_AFTER_SECONDS
        if delay < 0:
            return 0.0
        return delay

    def _get(self, path, params=None):
        """GET an API path and return the decoded JSON body, or None.

        One structured log line per request, whatever happens, which is what
        design section 4.6 needs in order to answer "is the app reaching the
        API at all" without a customer turning on debug logging.

        WHAT THE LINE CARRIES, AND WHY IT IS THE PATH AND NOT THE URL
        ------------------------------------------------------------
        endpoint= is `path`, the bare API path. It is never the built URL and
        never anything out of `params`, and that is why the logging lives in
        this wrapper rather than around _build_url: the wrapper is handed the
        two separately and only ever passes the first one on, so the value the
        customer is asking about, a file hash out of their index, has no route
        into the log line. A hash is not a credential, but it is the customer's
        data, it leaves their estate to reach us, and a log is not where that
        decision gets made a second time.

        The transport itself is _request(). Splitting it out is what makes "one
        line per request" true by construction: _request has a dozen terminal
        branches between retries, statuses and decode failures, and a log call
        in each of them is a log call that will one day be missing from a new
        one.

        :param path: path below the base URL, with a leading slash.
        :param params: query parameters as a mapping.
        :return: the decoded body, or None when the platform reports
            not-found. See NOT_FOUND_STATUS_CODES.
        :raises AuthenticationError: on 401 or 403, without retrying.
        :raises ClientError: on any other unrecoverable failure.
        """
        return self._logged("GET", path, params=params)

    def _send(self, method, path, params=None, json_body=None):
        """Send one write request and return the decoded body, or None.

        The non-GET twin of _get(), with the same one-line-per-request logging
        contract and the same rule about what may appear on that line: the API
        path, never the URL and never anything out of the body.

        NOTHING SENT THROUGH HERE IS EVER RETRIED, and the single attempt is
        the point rather than an omission. See sandbox_submit_url(): a retried
        create is a second detonation on the customer's bill, and no HTTP
        status can tell a request that failed from a request that succeeded and
        lost its answer on the way back.

        :param method: POST or PUT.
        :param path: path below the base URL, with a leading slash.
        :param params: query parameters as a mapping.
        :param json_body: a mapping to send as a JSON body, or None.
        """
        return self._logged(method, path, params=params, json_body=json_body)

    def _logged(self, method, path, params=None, json_body=None):
        """The logging wrapper shared by _get() and _send()."""
        timer = ps_log.Timer()
        attempts_before = self.call_count

        try:
            payload = self._request(
                path, params, method=method, json_body=json_body
            )
        except Exception as error:
            # The class name only. The message has already been sanitized on
            # its way into the exception, but a class name cannot carry a
            # payload at all, and the message belongs to the analyst in the
            # search bar rather than to a log aggregator.
            ps_log.info(
                LOG_COMPONENT,
                "request",
                "error",
                endpoint=path,
                reason=type(error).__name__,
                attempts=self.call_count - attempts_before,
                duration_ms=timer.duration_ms,
            )
            raise

        ps_log.info(
            LOG_COMPONENT,
            "request",
            "not_found" if payload is None else "ok",
            endpoint=path,
            attempts=self.call_count - attempts_before,
            duration_ms=timer.duration_ms,
        )
        return payload

    def _request(self, path, params=None, method="GET", json_body=None):
        """The transport for one request. See _get() for the logging contract.

        A GET is retried per RETRY_STATUS_CODES. ANYTHING ELSE IS ATTEMPTED
        ONCE, whatever max_tries says, and the rule is in this function rather
        than at the call sites so that a later endpoint cannot opt into
        retrying a write by forgetting to opt out. A GET is idempotent by
        definition; a POST that creates a metered task is not, and a 502 from a
        proxy does not say whether the task was created before the connection
        broke.

        THE PLATFORM SETS THE PACE ON A 429 OR A 503 WHEN IT SAYS SO. A
        Retry-After on either of those two statuses is honoured, up to
        MAX_RETRY_AFTER_SECONDS, in place of the exponential backoff. See
        _delay_for() and read_retry_after() for the two halves of that, and the
        note on RETRY_AFTER_STATUS_CODES for why the header is read on those
        statuses only.

        A 429 THAT SURVIVES EVERY ATTEMPT RAISES RateLimitError, which is a
        ClientError subclass, so an existing caller sees no change and a caller
        that wants to stop enriching rather than report a fault can catch it.
        """
        url = self._build_url(path, params)
        last_detail = "no attempt was made"
        last_status = None
        tries = self.max_tries if method == "GET" else 1

        for attempt in range(tries):
            self.call_count += 1
            # Reset per attempt: an instruction belongs to the answer it
            # arrived on, so a Retry-After on the first 503 must not still be
            # steering the wait after a later network error.
            retry_after = None
            try:
                response = self._urlopen(
                    self._build_request(url, method=method, json_body=json_body),
                    self.timeout,
                )
            except urllib.error.HTTPError as error:
                status = getattr(error, "code", None)

                if status in NOT_FOUND_STATUS_CODES:
                    return None

                if status in (401, 403):
                    # Never retried. A wrong key stays wrong, and repeating the
                    # request risks a lockout on the customer's account.
                    self._fail(
                        AuthenticationError,
                        "PolySwarm rejected the API key with HTTP {0}. Check "
                        "the key saved on the app setup page.",
                        status,
                    )

                if status in NEVER_RETRY_STATUS_CODES:
                    self._fail(
                        ClientError,
                        "PolySwarm returned HTTP {0} for {1}. The request will "
                        "not be retried.",
                        status,
                        path,
                    )

                if status not in RETRY_STATUS_CODES:
                    self._fail(
                        ClientError,
                        "PolySwarm returned HTTP {0} for {1}.", status, path
                    )

                last_detail = "HTTP {0}".format(status)
                last_status = status
                if status in RETRY_AFTER_STATUS_CODES:
                    retry_after = read_retry_after(
                        getattr(error, "headers", None)
                    )

            except urllib.error.URLError as error:
                # Transport level: DNS, connection refused, TLS, timeout.
                last_detail = "network error ({0})".format(
                    self._clean(str(getattr(error, "reason", error)))
                )
                last_status = None

            else:
                return self._decode(response, path)

            if attempt + 1 < tries:
                self._sleep(self._delay_for(attempt, retry_after))

        # The message is the same one this path has always produced, on purpose:
        # only the class changes, and only when the last answer was a 429.
        self._fail(
            RateLimitError if last_status == 429 else ClientError,
            "PolySwarm request to {0} failed after {1} attempts: {2}",
            path,
            tries,
            last_detail,
        )

    def _build_url(self, path, params=None):
        """Build one absolute URL. Every value is quoted with safe="".

        A LIST OR TUPLE VALUE BECOMES A REPEATED PARAMETER, and that is a
        mirror of the SDK rather than a convenience. The metadata search takes
        its field selection as `include` and `exclude` given more than once,
        which is how resources.Metadata._get_params builds them:

            params.extend(('include', v) for v in include)
            params.extend(('exclude', v) for v in exclude)

        It returns a LIST OF PAIRS for exactly that reason, where every other
        resource in the SDK returns a mapping. Joining the values into one
        comma separated parameter instead would send a single field name with
        commas in it, which selects nothing and reports no error: the response
        simply comes back without the fields that were asked for.

        Names are sorted and each name's own values keep the order they were
        given in. Query parameter order carries no meaning over HTTP, so
        sorting is the house behaviour every other endpoint here already
        depends on in its tests; the within-name order is preserved because it
        costs nothing and a reader comparing a URL against a caller should see
        the list they wrote.

        A None inside a list is skipped, exactly as a None value is skipped,
        so a caller assembling a selection from optional pieces does not have
        to filter it first.
        """
        url = self.base_url + path
        if params:
            pairs = []
            for name in sorted(params):
                value = params[name]
                if value is None:
                    continue
                values = value if isinstance(value, (list, tuple)) else [value]
                quoted_name = urllib.parse.quote(str(name), safe="")
                for item in values:
                    if item is None:
                        continue
                    pairs.append(
                        "{0}={1}".format(
                            quoted_name,
                            urllib.parse.quote(str(item), safe=""),
                        )
                    )
            if pairs:
                url = "{0}?{1}".format(url, "&".join(pairs))
        return url

    def _decode(self, response, path):
        """Read and JSON-decode a successful response body."""
        status = getattr(response, "status", None)
        if status is None:
            getcode = getattr(response, "getcode", None)
            if callable(getcode):
                status = getcode()
        if status in NOT_FOUND_STATUS_CODES:
            return None

        try:
            raw = response.read()
        except Exception as error:
            self._fail(
                ClientError,
                "Could not read the PolySwarm response for {0}: {1}",
                path,
                str(error),
            )

        if not raw:
            # An empty body on a success status reads the same as not-found.
            #
            # Pinned live on 2026-09-04 rather than assumed: a URL search for a
            # URL the platform has no record of returns 204 and sends no body
            # at all. The status check above catches that one, and this branch
            # catches the same shape arriving on any other success status. See
            # the note on NOT_FOUND_STATUS_CODES.
            return None

        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8")
            except UnicodeDecodeError:
                self._fail(
                    ClientError,
                    "The PolySwarm response for {0} was not valid UTF-8.",
                    path,
                )

        try:
            return json.loads(raw)
        except ValueError as error:
            # The body is never quoted into the message. A malformed body from
            # an authenticating proxy can contain the request headers.
            self._fail(
                ClientError,
                "The PolySwarm response for {0} was not valid JSON ({1}).",
                path,
                type(error).__name__,
            )

    def _put_upload(self, upload_url, data):
        """PUT raw bytes to a presigned upload URL. Returns True on success.

        THE ONE REQUEST THIS APP MAKES TO A HOST THAT IS NOT THE POLYSWARM API,
        AND IT CARRIES NO CREDENTIAL.
        --------------------------------------------------------------------
        Step two of the three-step detonation protocol. The create call answers
        with a presigned URL on a storage host, and the artifact is PUT there
        rather than through the API. Three properties of this method are
        deliberate and each one is asserted by a test:

          1. **No Authorization header.** apply_authorization() is not called
             and _build_request() is not used, because that function's whole
             job is to attach the key. The host is not ours, the presigned URL
             already carries its own authorisation in its query string, and
             sending the customer's PolySwarm key to a third party would be a
             credential leak of exactly the class constraint C1 exists for.
             The SDK does the same thing for the same reason:
             resources.SandboxTask.upload_file calls requests.put(self.upload_url,
             data=artifact) with no session and no headers.
          2. **https only.** The body is the customer's URL, which is their
             data, so it does not go out over an unencrypted connection. A
             create response naming an http upload URL is refused rather than
             honoured.
          3. **The URL never appears in a message, a log line, or an
             exception.** A presigned URL is a bearer credential: anyone
             holding it can write to that object for as long as it is valid.
             The sanitizer cannot help here, because its value rule needs the
             secret in hand and this one is minted per request, so the defence
             is that the string is never formatted into anything. The log line
             carries a fixed literal for the endpoint.

        NO RETRY, WHICH IS A DEPARTURE FROM THE SDK. upload_file loops up to
        three times. This attempts once. The upload itself is idempotent, so a
        retry would be safe; what a retry buys is not worth the branch, because
        a failed upload leaves a created task that is never finalized and
        therefore never runs and never bills, which is the cheap failure. The
        expensive failure is on the other side of this method and it is the one
        the single attempt is protecting.

        :param upload_url: the presigned URL from the create response.
        :param data: the bytes to PUT.
        :return: True when the storage host accepted the object.
        :raises ClientError: on any refusal or failure.
        """
        if not upload_url or not str(upload_url).strip():
            self._fail(
                ClientError,
                "PolySwarm created a sandbox task but returned no upload "
                "location, so the artifact could not be uploaded.",
            )

        target = str(upload_url).strip()
        if not target.startswith("https://"):
            self._fail(
                ClientError,
                "PolySwarm returned a sandbox upload location that is not "
                "https. Refusing to send the artifact over an unencrypted "
                "connection.",
            )

        request = urllib.request.Request(target, data=data, method="PUT")
        request.add_header(USER_AGENT_HEADER, self.config.user_agent)
        # Set explicitly, because urllib stamps
        # application/x-www-form-urlencoded on any request that carries a body
        # and no content type, and that would describe a URL string as a form
        # submission. text/plain is what the platform recorded as the uploaded
        # artifact's mimetype in
        # tests/fixtures/sandbox-status-pending-recorded.json.
        request.add_header(CONTENT_TYPE_HEADER, UPLOAD_CONTENT_TYPE)

        timer = ps_log.Timer()
        self.call_count += 1
        try:
            response = self._urlopen(request, self.timeout)
        except urllib.error.HTTPError as error:
            status = getattr(error, "code", None)
            ps_log.info(
                LOG_COMPONENT,
                "sandbox_upload",
                "error",
                endpoint=SANDBOX_UPLOAD_LOG_ENDPOINT,
                status=status,
                duration_ms=timer.duration_ms,
            )
            self._fail(
                ClientError,
                "The sandbox artifact upload was rejected with HTTP {0}. The "
                "detonation was not started.",
                status,
            )
        except urllib.error.URLError as error:
            ps_log.info(
                LOG_COMPONENT,
                "sandbox_upload",
                "error",
                endpoint=SANDBOX_UPLOAD_LOG_ENDPOINT,
                reason=type(error).__name__,
                duration_ms=timer.duration_ms,
            )
            # The reason string is cleaned and the URL is not in it: a URLError
            # carries the transport failure, not the target.
            self._fail(
                ClientError,
                "The sandbox artifact upload could not be completed ({0}). The "
                "detonation was not started.",
                self._clean(str(getattr(error, "reason", error))),
            )

        try:
            response.read()
        except Exception:
            # A storage host answers a PUT with an empty body. Failing to read
            # one is not a failed upload, and the status is what says so.
            pass

        ps_log.info(
            LOG_COMPONENT,
            "sandbox_upload",
            "ok",
            endpoint=SANDBOX_UPLOAD_LOG_ENDPOINT,
            duration_ms=timer.duration_ms,
        )
        return True

    # -- endpoints -------------------------------------------------------

    # THE TWO ACCOUNT ENDPOINTS
    #
    # Both are transport only, in exactly the sense search_hash() is: the
    # decoded body is returned as the API sent it, with no unwrapping of an
    # envelope, no key renaming, and no selection among its contents. There is
    # one reader of each shape, cmd_usage.read_identity() and
    # cmd_usage.read_features(), for the reason decision D4 gives: a
    # convenience unwrap here would be a second, undocumented reader of the
    # same shape, and when the shape moves the two readers move apart.
    #
    # WHAT THESE TWO SPEND, SAID PRECISELY. Neither is an artifact lookup.
    # Neither submits, scans, or detonates anything, so neither consumes the
    # scan or detonation allowances a customer buys, which is why the setup
    # page's test-credentials button can call them and why design 4.6 puts them
    # behind the usage surface. Whether they count against an api_requests
    # feature is a different question and it is not answered: that is P0-6,
    # quota semantics per endpoint, and it is still open. So the caller does not
    # get to treat them as free. See the throttle in bin/usage_store.py.
    #
    # NOT PINNED BY A RECORDING. search_hash's shape is fixed by
    # tests/fixtures/search-hash-recorded.json. These two have no equivalent
    # recording in this repository, and design section 9 records them as
    # verified live at design time rather than captured. The consequence is
    # carried by the readers, which are structurally tolerant and report
    # nothing rather than guessing, and it is written up in docs/decisions.md.

    def whois(self):
        """GET /public/accounts/whois. Identifies the calling account.

        Transport only. Used by the setup page to validate a key and by
        | polyswarmusage for the account identity header.

        :return: the decoded response, or None when the platform returns a
            not-found or an empty body.
        """
        return self._get("/public/accounts/whois")

    def accounts(self):
        """GET /public/accounts. The calling account's plan and quota state.

        Transport only. The source of base_uses, remaining_uses and overage
        per feature for design 4.6's usage and entitlement surface.

        :return: the decoded response, or None when the platform returns a
            not-found or an empty body.
        """
        return self._get("/public/accounts")

    def search_hash(self, sha256):
        """GET /search/hash/sha256 for one file hash.

        Transport only. The decoded body is returned exactly as the API sent
        it, with no reshaping, no key renaming, and no selection among the
        entries in its result list. This client holds no opinion about the
        response shape beyond error handling, so that there is one place that
        reads it: cmd_search.build_output_fields(), against the recorded
        contract in tests/fixtures/search-hash-recorded.json. A convenience
        unwrap here would be a second, undocumented reader of the same shape.

        :param sha256: the hash to look up.
        :return: the decoded response, or None when the platform has nothing.
        :raises ClientConfigurationError: if the hash is empty.
        """
        if not sha256 or not str(sha256).strip():
            raise ClientConfigurationError("A hash is required.")
        return self._get(
            "/search/hash/sha256", params={"hash": str(sha256).strip()}
        )

    def search_url(self, url):
        """GET /search/url for one URL or one bare host name.

        Transport only, in exactly the sense search_hash() is. The decoded body
        is returned as the API sent it, with no reshaping and no selection among
        the entries in its result list, so that there stays exactly one reader
        of the shape: cmd_search.build_output_fields().

        PINNED BY A RECORDING, AND THE RECORDING SAYS ONE READER IS ENOUGH.
        The contract is tests/fixtures/search-url-recorded.json, a scrubbed
        capture of a live GET /v3/search/url on 2026-09-04. It carries the SAME
        envelope keys and the SAME artifact keys as the hash recording next to
        it, down to the set, which is asserted in
        tests/fixtures/test_search_url_fixture_integrity.py rather than believed
        here. That is why wiring this endpoint added no second reader: the one
        that reads a hash response reads this one correctly already.

        THE PARAMETER IS URL ENCODED, AND THAT IS NOT A NICETY. A URL carries
        the exact characters that delimit a query string: ?, &, = and #. Sent
        raw, the value would truncate at the first of them and the platform
        would answer about a different resource than the caller named, with no
        error to show for it. _build_url() quotes every parameter with safe="",
        which escapes every reserved character including the slashes, and there
        is deliberately no second encoder in this method: one encoder, at the
        one place a query string is built.

        A BARE HOST IS A VALID VALUE, AND NOTHING HERE ADDS A SCHEME. The
        recorded response was obtained by querying google.com with no scheme and
        no path, and the platform answered 200 with a full artifact. So a Splunk
        domain field is passed through as it stands. Synthesising an https://
        prefix onto it would ask about a different resource than the event
        names, and would then have to guess between http and https.

        NOT FOUND IS 204 WITH AN EMPTY BODY. Verified live on the same date: a
        URL the platform has no record of answers HTTP 204 and sends no body.
        Both halves of that are already handled, by NOT_FOUND_STATUS_CODES and
        by the empty-body branch in _decode(), and both now carry a note saying
        this endpoint is what turned them from caution into contract. The caller
        sees None and emits an unknown verdict.

        :param url: the URL or host to look up.
        :return: the decoded response, or None when the platform has nothing.
        :raises ClientConfigurationError: if the value is empty.
        """
        if not url or not str(url).strip():
            raise ClientConfigurationError("A URL is required.")
        return self._get("/search/url", params={"url": str(url).strip()})

    def tag_link(self, sha256):
        """GET /tags/link for one artifact's family and tag attribution.

        Transport only, in exactly the sense search_hash() and search_url()
        are. The decoded body is returned as the API sent it, with no
        reshaping, no key renaming and no selection among its contents, so
        there stays exactly one reader of the shape:
        cmd_search.build_attribution_fields().

        THE PARAMETER IS "hash", AND THAT IS MEASURED RATHER THAN INFERRED.
        Verified live on 2026-09-08: the endpoint names the parameter in the
        body of a 400 when it is called with the wrong one, and "hash" is the
        spelling it accepts. It is the same spelling search_hash() uses on a
        different path, which is worth saying out loud because "sha256" reads
        like the obvious name here and is not the one that works.

        NOT FOUND IS 204 WITH AN EMPTY BODY, AND IT IS THE COMMON ANSWER.
        Recorded live on the same date against a benign hash: an artifact with
        no tag link answers HTTP 204 and sends no body. Both halves are
        already handled, by NOT_FOUND_STATUS_CODES and by the empty-body branch
        in _decode(), so the caller sees None. Most artifacts in a customer's
        index have no attribution at all, so None is the ordinary result on this
        endpoint and not an exception: the caller emits no attribution fields
        and no note, because the absence of a family or an actor tag is a fact
        about the artifact rather than a limit of the app.

        PROVISIONAL-SDK: THE RESPONSE SHAPE IS DERIVED FROM THE SDK, NOT FROM A
        RECORDED 200, AND THAT IS WEAKER THAN EVERY OTHER ENDPOINT HERE.
        -----------------------------------------------------------------------
        search_hash() and search_url() are pinned by scrubbed recordings of live
        200 responses, which decision D4 makes the contract. This endpoint has
        no such recording in this repository, and it must not be read as though
        it does.

        What the reader is written against instead is the polyswarm-api SDK's
        own TagLink resource, which constructs itself from the response body and
        therefore names the keys the platform sends:

            {id, sha256, created, updated, first_seen,
             tags: [str], families: [str], emerging: <iso or null>}

        That is a strong source and it is not a recording. The gap is not
        theoretical: a public-scoped key answered 204 on 2026-09-08 even for
        family-list queries, so tag coverage appears to be entitlement gated,
        and an all-204 result is what this app must treat as normal rather than
        as a fault. The consequence is that the shape above has never been
        observed arriving here, only inferred from the code that parses it.

        So the reader is structurally tolerant, omits every field it cannot
        read, and invents nothing, and the open item is written down in
        docs/decisions.md D11: confirm the shape against a recording taken with
        an entitled key, and then pin it the way D4 pins the other two. Until
        that recording exists this endpoint is the one place in the app whose
        response shape rests on a second-hand reading.

        :param sha256: the artifact hash to look up.
        :return: the decoded response, or None when the platform holds no tag
            link for the artifact.
        :raises ClientConfigurationError: if the hash is empty.
        """
        if not sha256 or not str(sha256).strip():
            raise ClientConfigurationError("A hash is required.")
        return self._get("/tags/link", params={"hash": str(sha256).strip()})

    def search_metadata(
        self,
        query,
        community=None,
        include=None,
        exclude=None,
        offset=None,
        limit=None,
    ):
        """GET /search/metadata/query for one metadata query string.

        Transport only, in exactly the sense search_hash() and search_url()
        are. The decoded body is returned as the API sent it, envelope and
        pagination fields included, with no reshaping, no key renaming and no
        selection among the entries in its result list. There is one reader of
        this shape, bin/input_intel_pull.py, and this method deliberately does
        not become a second one: it does not unwrap the envelope, does not
        follow pagination, and does not decide whether a page was the last.

        NOT AN ITERATOR, AND THAT IS THE DESIGN. The SDK's own
        `search_by_metadata` returns a generator that walks every page to
        exhaustion (core.PolyswarmRequest.consume_results), which is the single
        most expensive thing that could be wired into a Splunk app: the caller
        has no way to stop, and every page is a metered request against the
        customer's account. Constraint C11 requires the cap to be declared and
        enforced by the code that spends, so pagination is driven one page at a
        time by the caller, which is the only party that knows its ceiling.

        PINNED BY A RECORDING. tests/fixtures/metadata-search-recorded.json is
        a scrubbed capture of a live 200 on 2026-09-08 and it is the contract.
        The query it was taken with is the v1 form this app mirrors, so the
        recording pins the request as well as the response.

        THE OFFSET IS AN OPAQUE CURSOR AND NOT A ROW NUMBER. See the note on
        METADATA_OFFSET_PARAM. The value to send is the `offset` string the
        previous page returned, verbatim. Nothing here validates it, computes
        it, or starts it at zero, because the platform is the only party that
        can decode it.

        THE COMMUNITY IS SENT ON EVERY CALL. api.search_by_metadata passes
        `community=self.community` unconditionally, so this mirrors that: the
        parameter defaults to the client's configured community, which
        bin/community.py resolved, and the argument exists so one caller can
        scope one search differently without building a second client.

        :param query: the metadata query string.
        :param community: the community to scope the search to. None means the
            community this client was configured with.
        :param include: field paths to return, each sent as its own `include`
            parameter. None sends none, which returns the whole document.
        :param exclude: field paths to omit, sent the same way.
        :param offset: the cursor from the previous page's `offset`, or None
            for the first page.
        :param limit: page size, or None to let the platform choose. The
            recorded response answered 50 when none was asked for.
        :return: the decoded response, or None when the platform has nothing.
        :raises ClientConfigurationError: if the query is empty.
        """
        if query is None or not str(query).strip():
            raise ClientConfigurationError("A metadata query is required.")

        params = {
            METADATA_QUERY_PARAM: str(query).strip(),
            METADATA_COMMUNITY_PARAM: (
                self.config.community if community is None else str(community)
            ),
        }

        # A list or a tuple becomes a repeated parameter in _build_url, which
        # is how the SDK sends these. An empty sequence is dropped rather than
        # sent as an empty value, because `include=` with nothing after it is a
        # request for a field whose name is the empty string.
        if include:
            params[METADATA_INCLUDE_PARAM] = list(include)
        if exclude:
            params[METADATA_EXCLUDE_PARAM] = list(exclude)

        if offset is not None:
            params[METADATA_OFFSET_PARAM] = str(offset)
        if limit is not None:
            params[METADATA_LIMIT_PARAM] = int(limit)

        return self._get(METADATA_SEARCH_PATH, params=params)

    # -- the sandbox -----------------------------------------------------

    def sandbox_providers(self):
        """GET /sandbox/provider/list. The providers and VMs the key may use.

        Transport only, in exactly the sense search_hash() is. The decoded body
        is returned as the API sent it, envelope included, so there is one
        reader of the shape: task_store.read_providers().

        PINNED BY A RECORDING. tests/fixtures/sandbox-providers-recorded.json is
        a live capture from 2026-09-08 and it is the contract. Two facts in it
        are worth stating because a reader would guess otherwise:

          * **The result is a MAPPING KEYED BY PROVIDER SLUG, not a list.**
            {"cape": {...}, "triage": {...}}. The SDK confirms the shape from
            the other side: resources.SandboxProvider.parse_result iterates
            content.keys() and parses content[slug].
          * **Each provider's "vms" is itself a mapping keyed by VM slug**, and
            each VM declares supported_artifact_types. That is what lets a URL
            detonation be refused before it is spent: triage's android-11-x64
            supports FILE only, so submitting a URL to it would book VM time
            for a run that cannot do the job.

        This endpoint spends no scan and no detonation allowance: it lists what
        the account may use. Whether it counts against an api_requests feature
        is P0-6 and unanswered, which is why cmd_detonate caches the answer for
        24 hours rather than calling it per detonation.

        :return: the decoded response, or None when the platform returns a
            not-found or an empty body.
        """
        return self._get(SANDBOX_PROVIDER_LIST_PATH)

    def sandbox_submit_url(self, url, provider_slug, vm_slug, browser=None):
        """Submit one URL for detonation. THREE requests, and one bill.

        THE PROTOCOL, MIRRORED FROM api.sandbox_url AND NOT FROM DOCUMENTATION.
        ---------------------------------------------------------------------
        A URL detonation is not one call. The SDK does it in three and so does
        this method, in this order:

          1. **CREATE.** POST /v3/sandbox/sandboxtask/instance with a JSON body
             of artifact_name, artifact_type "URL", community, provider_slug,
             vm_slug, browser when there is one, and network_enabled. Mirrors
             resources.SandboxTask.create_file, whose keyword names are taken
             from the create_file call inside api.sandbox_url. The answer
             carries the task id and a presigned upload URL.
          2. **UPLOAD.** PUT the URL string's bytes to that presigned URL, on a
             storage host that is not the API. Mirrors
             resources.SandboxTask.upload_file, which is a bare
             requests.put(self.upload_url, data=artifact) with no credential.
             The artifact of a URL detonation IS the URL text: api.sandbox_url
             builds it with LocalArtifact.from_content(url, artifact_type='URL'),
             and the platform recorded it as 25 bytes of ASCII text in
             tests/fixtures/sandbox-status-pending-recorded.json.
          3. **FINALIZE.** PUT /v3/sandbox/sandboxtask/instance?id=<id> with a
             JSON body of {"community": ...}. Mirrors
             resources.SandboxTask.update_file. The split between query string
             and body is not a choice: core.BaseJsonResource._params puts a key
             in the query string when the method is not GET and the key is in
             RESOURCE_ID_KEYS, which on this resource is ['id'], and everything
             else in the body.

        A NON-API HOST IS IN THIS PATH, AND THAT IS A CLOUD VETTING QUESTION.
        Step two egresses to a storage host the app cannot know in advance,
        which is a different thing from talking to one hostname a customer has
        allowlisted. It belongs under P0-8's umbrella, the open question about
        what outbound egress a Cloud-vetted app may perform, and it is written
        up in docs/decisions.md D12 rather than left for a vetting reviewer to
        discover.

        NOTHING HERE IS RETRIED, AND THE CREATE STEP IS WHY.
        ---------------------------------------------------
        _send() attempts a write exactly once. A detonation is the most
        expensive metered call in the product, and no HTTP failure distinguishes
        a create that did not happen from a create that happened and lost its
        answer in transit. So a retried create is a coin flip between one
        detonation and two, and the customer pays for the outcome. Retries stay
        where they are safe: the status GET and the providers GET.

        WHAT THIS READS OUT OF A RESPONSE, AND WHY IT IS ONLY TWO FIELDS.
        The rest of this file is transport only. This method has to read the
        task id and the upload URL, because there is no way to execute steps
        two and three without them. Nothing else is read, nothing is reshaped,
        and the finalize response is returned exactly as it arrived, so
        task_store stays the one reader of the task shape.

        THE ONE EXCEPTION TO THAT, AND IT IS ABOUT NOT LOSING A BILLED
        DETONATION. A finalize that answers 204, or 200 with an empty body, or
        200 with an object that does not repeat the id, comes back with no task
        id in it, and a task row with no id cannot be stored or polled. In that
        case only, the id read for step three is put back and the caller's
        target, provider and VM are filled in beside it. See _submit_receipt().

        :param url: the URL to detonate.
        :param provider_slug: the sandbox provider, for example triage.
        :param vm_slug: the VM image, for example windows11-21h2-x64.
        :param browser: the browser name, or None to let the VM choose.
        :return: the decoded finalize response as the API sent it, or, when
            that answer carries no task id, a receipt carrying the created task
            id and whatever the finalize body did contain.
        :raises ClientConfigurationError: if any required value is empty.
        :raises ClientError: on any failure in any of the three steps.
        """
        target = "" if url is None else str(url).strip()
        if not target:
            raise ClientConfigurationError("A URL is required.")

        provider = "" if provider_slug is None else str(provider_slug).strip()
        if not provider:
            raise ClientConfigurationError("A sandbox provider is required.")

        vm = "" if vm_slug is None else str(vm_slug).strip()
        if not vm:
            raise ClientConfigurationError("A sandbox VM is required.")

        body = {
            # artifact_name is the URL itself. api.sandbox_url assigns
            # artifact_name = url before building the artifact, so the name and
            # the content are the same string.
            SANDBOX_ARTIFACT_NAME_FIELD: target,
            SANDBOX_ARTIFACT_TYPE_FIELD: SANDBOX_ARTIFACT_TYPE_URL,
            SANDBOX_COMMUNITY_FIELD: self.config.community,
            SANDBOX_PROVIDER_SLUG_FIELD: provider,
            SANDBOX_VM_SLUG_FIELD: vm,
            SANDBOX_NETWORK_ENABLED_FIELD: SANDBOX_NETWORK_ENABLED_ON,
        }

        # Omitted rather than sent as null when there is none, because that is
        # what the SDK does: core.BaseJsonResource._params drops every keyword
        # whose value is None before the body is built. preprocessing is left
        # out entirely for the same reason; it exists for QR-code images, which
        # this command does not accept.
        if browser is not None and str(browser).strip():
            body[SANDBOX_BROWSER_FIELD] = str(browser).strip()

        created = self._send(
            "POST", SANDBOX_TASK_INSTANCE_PATH, json_body=body
        )

        task_id = read_task_field(created, SANDBOX_TASK_ID_FIELD)
        if task_id is None:
            self._fail(
                ClientError,
                "PolySwarm accepted the sandbox submission but returned no "
                "task id, so the detonation could not be started.",
            )

        upload_url = read_task_field(created, SANDBOX_UPLOAD_URL_FIELD)
        self._put_upload(upload_url, target.encode("utf-8"))

        finalized = self._send(
            "PUT",
            SANDBOX_TASK_INSTANCE_PATH,
            params={SANDBOX_TASK_ID_FIELD: task_id},
            json_body={SANDBOX_COMMUNITY_FIELD: self.config.community},
        )

        if read_task_field(finalized, SANDBOX_TASK_ID_FIELD) is not None:
            return finalized

        # A FINALIZE THAT ANSWERS WITHOUT A TASK ID IS STILL A DETONATION THE
        # CUSTOMER HAS PAID FOR, AND THE ID IS ALREADY IN HAND.
        #
        # Two shapes reach here, and neither is exotic. A 204 makes _request()
        # return None, and an empty body on any success status makes _decode()
        # return None: both are contract elsewhere in this app, see the note on
        # NOT_FOUND_STATUS_CODES. A 200 carrying an object that simply does not
        # repeat the id is the second.
        #
        # Returning that as it stands used to hand task_store.build_task_row a
        # payload with no id, which produces a row with no task_id, which
        # save_task() refuses because it cannot build a document id from it. The
        # detonation is billed, the VM runs, and nothing in the app can find the
        # task again: PolySwarm's own listing of an account's tasks is the
        # endpoint that hangs, so a lost row is lost for good.
        #
        # So the id from the CREATE step is put back, along with the three
        # values the caller passed, and that is the whole of it. This is not the
        # client acquiring an opinion about a task: every value in the receipt
        # is one this method was handed or read for the protocol's own sake, the
        # platform's own fields are kept exactly as they arrived and are never
        # overwritten, and task_store remains the only module that reads a task
        # shape for its meaning.
        return self._submit_receipt(finalized, task_id, target, provider, vm)

    def _submit_receipt(self, finalized, task_id, target, provider, vm):
        """Return the finalize answer with the task id, and identity, filled in.

        THE PLATFORM'S ANSWER WINS AND THE REQUEST IS THE FALLBACK, which is
        build_task_row's rule applied one step earlier: whatever the finalize
        body did carry is copied through untouched and only the missing pieces
        are supplied. A finalize that answered with a status and a community but
        no id keeps that status and that community.

        The shape is the task shape, because that is what the caller of
        sandbox_submit_url() hands to task_store.build_task_row and a second
        shape would mean a second reader. The envelope is dropped if there was
        one, exactly as build_task_row would have unwrapped it.

        :param finalized: the decoded finalize body, or None.
        :param task_id: the id the CREATE step returned. Never None here.
        :param target: the URL that was submitted.
        :param provider: the provider slug that was requested.
        :param vm: the VM slug that was requested.
        """
        body = unwrap_envelope(finalized)
        receipt = dict(body) if isinstance(body, dict) else {}
        receipt[SANDBOX_TASK_ID_FIELD] = task_id

        config = receipt.get(SANDBOX_CONFIG_FIELD)
        config = dict(config) if isinstance(config, dict) else {}

        existing_target = config.get(SANDBOX_CONFIG_TARGET_FIELD)
        if not (isinstance(existing_target, str) and existing_target.strip()):
            config[SANDBOX_CONFIG_TARGET_FIELD] = target

        for name, value in (
            (SANDBOX_CONFIG_PROVIDER_FIELD, provider),
            (SANDBOX_CONFIG_VM_FIELD, vm),
        ):
            if not isinstance(config.get(name), dict):
                config[name] = {SANDBOX_SLUG_FIELD: value}

        receipt[SANDBOX_CONFIG_FIELD] = config

        # One log line, so an operator can see that this happened at all, and it
        # carries the API path and nothing else. There is deliberately no
        # ps_log key for a task id, let alone for the target, and this is not
        # the place to argue for one: the id reaches the analyst on the row and
        # in the command's own warning, which is where somebody who needs to
        # quote it to support is already looking.
        ps_log.warning(
            LOG_COMPONENT,
            "sandbox_finalize",
            "degraded",
            endpoint=SANDBOX_TASK_INSTANCE_PATH,
        )
        return receipt

    def sandbox_task_status(self, task_id):
        """GET /sandbox/sandboxtask for one task. Transport only.

        Mirrors api.sandbox_task_status, which is
        resources.SandboxTask.get(self, sandbox_task_id=task_id) with
        community=api.community added by SandboxTask.get. The wire form and the
        citation for the parameter name are on SANDBOX_TASK_ID_PARAM.

        RETRIED, UNLIKE THE SUBMIT STEPS. A status read is a GET: it creates
        nothing, bills nothing on the detonation allowance, and repeating it
        cannot produce a second detonation. It is the one part of this protocol
        where a transient 502 should be ridden out rather than surfaced.

        THE ENDPOINT THIS DOES NOT CALL, AND IT IS NOT AN OVERSIGHT.
        /v3/sandbox/sandboxtask/my-tasks HANGS. Design section 0 item 5 records
        it as one of the two open platform bugs, alongside the KG profile 500,
        and the SDK exposes it as api.sandbox_my_tasks_list. A poller that
        listed the account's own tasks would be the obvious way to drive a task
        tray and it is not available, which is why this app keeps its own
        worklist in the ps_sandbox_tasks collection and reads one task at a
        time by id. A reader who "simplifies" the poller onto my-tasks will
        hang a modular input, and nothing in a Splunk input's own logs will say
        why.

        A per-hash listing does exist, GET /sandbox/sandboxtask/list with a
        sha256, mirrored in api.sandbox_task_list. It is not wired here because
        a task row already knows its own id and because that list carries every
        detonation of the artifact, including other accounts' and other
        providers': taking the first row adopts a stranger's status. The client
        apps hit that live and match on id
        (selectOwnTask in the browser app's task store).

        :param task_id: the sandbox task id.
        :return: the decoded response, or None when the platform has nothing.
        :raises ClientConfigurationError: if the task id is empty.
        """
        if task_id is None or not str(task_id).strip():
            raise ClientConfigurationError("A sandbox task id is required.")
        return self._get(
            SANDBOX_TASK_PATH,
            params={
                SANDBOX_TASK_ID_PARAM: str(task_id).strip(),
                SANDBOX_COMMUNITY_FIELD: self.config.community,
            },
        )

    # -- unwired seams ---------------------------------------------------
    #
    # Named for the endpoint each will call, so a caller that reaches one gets
    # a message naming the missing capability rather than a generic failure.
    # These stay NotImplementedError until each response shape is pinned by a
    # recorded live response, the way the hash and URL search responses now are
    # by tests/fixtures/search-hash-recorded.json and
    # tests/fixtures/search-url-recorded.json. Wiring a reader against a guessed
    # shape is what those recordings exist to stop.
    #
    # A DOMAIN IS NOT WAITING ON A SEAM ANY MORE, AND lookup_domain IS STILL
    # HERE. The URL recording was taken by querying a bare host, so a domain is
    # answered by search_url() above and cmd_search routes it there. What
    # lookup_domain would be is a SEPARATE domain endpoint, which no recording
    # in this repository shows exists, so it stays refused rather than being
    # quietly aliased onto search_url: an alias would claim the platform has two
    # routes to the same answer when only one has been observed.
    #
    # AN ADDRESS HAS NO RECORDING AT ALL. There is no recorded response for an
    # IP indicator, so there is no endpoint to call and none is guessed. That is
    # why cmd_search reports an address as unknown with a note rather than
    # sending it somewhere: an invented path would either 404 on every address
    # in a customer's index or, worse, answer about something else.

    def lookup_ioc(self, value, ioc_type):
        """Look up a non-hash indicator. Not wired up yet."""
        raise NotImplementedError(
            "Indicator lookup for type {0} is not implemented. Only file hash "
            "lookup is wired up in this release.".format(ioc_type)
        )

    def lookup_ip(self, address):
        """Look up an IP address indicator. Not wired up yet."""
        raise NotImplementedError(
            "IP address lookup is not implemented. Only file hash lookup is "
            "wired up in this release."
        )

    def lookup_domain(self, domain):
        """Look up a domain through a dedicated domain endpoint. Not wired up.

        Not the same thing as being unable to answer about a domain: search_url
        does that, on the strength of a recording taken against a bare host. See
        the seam note above.
        """
        raise NotImplementedError(
            "A dedicated domain endpoint is not implemented. A domain is "
            "looked up through URL search in this release."
        )

    def __repr__(self):
        # No credential. This object appears in tracebacks.
        return "<PolySwarmClient base_url={0!r} max_tries={1!r}>".format(
            self.base_url, self.max_tries
        )


def get_client(service, **overrides):
    """Return a configured PolySwarmClient for a running search.

    The single entry point for the rest of the app.

    :param service: the splunklib service object from the search command.
    :param overrides: any PolySwarmClient keyword.
    :return: a PolySwarmClient.
    :raises ClientConfigurationError: if the configuration is unusable.
    """
    api_key = get_api_key(service)
    client = PolySwarmClient(api_key, **overrides)
    # No base URL on this line. It is not a secret, but it is configuration and
    # ps_log has no key for it, which is the whitelist working as intended.
    ps_log.debug(LOG_COMPONENT, "client_built", "ok")
    return client
