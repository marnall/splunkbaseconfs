"""One-shot migration of 2.12.6-style input stanzas to the 3.0.0 account-driven schema.

Idempotent: runs from each modular input wrapper before it tries to read its config,
re-checks per-stanza on each fire, and is a no-op once a stanza has been migrated.

Per stanza of jamf / jamfcomputers / jamfmobiledevices, classify into one of five
states and act accordingly:

    A. account set, account exists in storage           -> skip (healthy)
                                                           NOTE: we don't probe
                                                           whether the stored
                                                           credentials still work
                                                           against Jamf Pro.
                                                           Bad creds in an
                                                           existing account are
                                                           an operator problem,
                                                           not a migration one.
    B. account set, account missing, legacy creds gone  -> log warning, skip
                                                           (operator must fix in UI;
                                                           prevents splunktaucclib
                                                           from crash-looping)
    C. account set, account missing, legacy creds OK    -> recreate the account with
                                                           the same name (repair mode);
                                                           no stanza patch needed.
                                                           Restricted to names that
                                                           match `migrated_<type>_*`
                                                           so a stanza writer can't
                                                           hijack a hand-named account.
    D. no account, legacy creds OK                      -> create account, patch stanza
                                                           to reference it (typical
                                                           2.12.6 -> 3.0.0 upgrade)
    E. no account, no legacy creds                      -> skip (fresh 3.x install)

The account POST goes through JamfProAccountValidator, which probes Jamf Pro; if the
credentials are bad, the migration aborts for that stanza and retries next fire.
409 (account already exists) is treated as success — POST is idempotent.

Old credential fields are left in the raw conf in (C) and (D) — the new schema simply
ignores them. We don't try to delete them because the REST API won't accept the legacy
field names.

Field renames (camelCase -> snake_case) are applied during fresh migration:
    excludeNoneManaged -> exclude_unmanaged
    daysSinceContact   -> days_since_contact
"""

import import_declare_test  # noqa: F401  pylint: disable=unused-import

import json
import logging
import re
from urllib.parse import urlparse, urlencode

import requests

from splunklib import binding, client
from solnlib.credentials import CredentialManager, CredentialNotExistException


APP_NAME = "JAMF-Pro-addon-for-splunk"
ACCOUNT_CONF = "jamf_pro_addon_for_splunk_account"

LEGACY_FIELDS_BY_TYPE = {
    "jamf":              ("jss_url",  "username",     "password"),
    "jamfcomputers":     ("jss_url",  "jss_username", "jss_password"),
    "jamfmobiledevices": ("jssUrl",   "jssUsername",  "jssPassword"),
}

RENAMES = {
    "excludeNoneManaged": "exclude_unmanaged",
    "daysSinceContact":   "days_since_contact",
}

_logger = logging.getLogger("legacy_migration")


def is_splunkd_not_ready(exc):
    """True if exc is a connection-refused error, indicating splunkd hasn't
    finished starting yet (common right after a restart). Used by the input
    wrappers to downgrade the log noise from these transient failures."""
    import errno
    if isinstance(exc, ConnectionRefusedError):
        return True
    if isinstance(exc, OSError) and exc.errno == errno.ECONNREFUSED:
        return True
    # The splunklib client wraps lower-level OSError in its own exception
    # types whose str() carries the original message but not the errno.
    return "Connection refused" in str(exc)


def _splunkd_connect(session_key, splunkd_uri):
    """Open a splunklib.client.Service against the local splunkd from a SPLUNKD_URI."""
    parsed = urlparse(splunkd_uri)
    return client.connect(
        token=session_key,
        app=APP_NAME,
        owner="nobody",
        scheme=parsed.scheme or "https",
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 8089,
        autologin=True,
    )


def _slugify(value):
    """Make a stanza-name-safe slug from an arbitrary string."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return slug or "default"


def is_migrated_account_name(account_name, input_type):
    """True if the account name matches the legacy_migration auto-create pattern."""
    if not account_name:
        return False
    return account_name.startswith("migrated_{}_".format(input_type))


def migration_auth_failure_hint(account_name, input_type):
    """Return a one-line operator-friendly hint to append to an auth-failure log message.

    When the failing account was auto-created by legacy_migration (from a 2.12.x
    upgrade), the most likely cause of token-auth failure is that the credentials
    we carried over from the old config are no longer valid against Jamf Pro
    (e.g., expired API client, rotated password). This hint points the operator
    to the right UI location to verify.

    Returns "" if the account isn't migration-managed — caller appends as-is.
    """
    if not is_migrated_account_name(account_name, input_type):
        return ""
    return (
        " NOTE: account %r was auto-created by the 2.12.x → 3.0.0 in-place "
        "migration. The credentials carried over from your old config may no "
        "longer be valid against Jamf Pro. Open Configuration → Accounts → %s "
        "and use Test Credentials to verify."
        % (account_name, account_name)
    )


def _stanza_has_account(stanza_content):
    """True if the stanza already references a configured account."""
    return bool(stanza_content.get("account"))


def _stanza_has_legacy_creds(stanza_content, input_type):
    """True if the stanza has the 2.12.6 per-input credential fields."""
    url_f, _, _ = LEGACY_FIELDS_BY_TYPE[input_type]
    return bool(stanza_content.get(url_f))


def _read_decrypted_password(session_key, input_type, stanza_name, password_field):
    """Read the decrypted password for a 2.12.6 input stanza.

    UCC stores encrypted REST fields as a chunked JSON blob in
    storage_passwords under the realm
    ``__REST_CREDENTIAL__#<app>#data/inputs/<input_type>`` keyed by stanza name.
    solnlib's CredentialManager reassembles the chunks and decrypts.
    """
    realm = "__REST_CREDENTIAL__#{}#data/inputs/{}".format(APP_NAME, input_type)
    cm = CredentialManager(session_key=session_key, app=APP_NAME, realm=realm)
    try:
        blob = cm.get_password(stanza_name)
    except (CredentialNotExistException, TypeError):
        return None
    try:
        data = json.loads(blob)
    except (TypeError, ValueError):
        return None
    return data.get(password_field)


def _list_existing_account_names(service):
    """Return the set of currently-stored account stanza names (excludes [default])."""
    try:
        accounts = service.confs[ACCOUNT_CONF]
    except (KeyError, binding.HTTPError):
        return set()
    return {stanza.name for stanza in accounts if stanza.name != "default"}


def normalize_jamf_api_call(session_key, splunkd_uri):
    """Normalize v2-style free-text api_call values on the 'jamf' input type.

    Until 2026-05-18 the api_call field was free-text. v3 made it a
    singleSelect of {computer, mobile_device, custom}; search_name carries
    the saved-search name (for the two search modes) or the custom
    JSSResource path. Operators upgrading from v2 who typed a literal path
    into api_call (the most common mistake — the UI label was "Endpoint"
    and the help text encouraged it) used to get silent fallthrough and no
    data; on v3 they get a loud "Unknown endpoint type" error.

    This pass auto-recovers the common cases so the upgrade is silent for
    those users, and leaves the rare-but-possible bad cases (typo'd path,
    truly unrecognized value) to fail loudly via _emit_endpoint_error.

    Mappings (case-insensitive prefix match; preserves saved-search name case):
        * api_call already in {computer, mobile_device, custom}    no change
        * api_call empty or missing                                no change
        * /JSSResource/advancedcomputersearches/name/<X>        -> computer + search_name=X
        * /JSSResource/advancedmobiledevicesearches/name/<X>    -> mobile_device + search_name=X
        * anything else                                         -> custom + search_name=<value>

    search_name is only populated if the stanza didn't already have one;
    if the operator set both api_call AND search_name in v2 (rare but
    possible) we preserve their search_name.

    Idempotent. Logs every normalization with before/after so the operator
    can audit and (if the heuristic guessed wrong) fix it in the UI.
    """
    try:
        service = _splunkd_connect(session_key, splunkd_uri)
    except Exception as exc:  # pragma: no cover
        _logger.warning("normalize_jamf_api_call: could not connect to splunkd: %s", exc)
        return

    try:
        inputs_conf = service.confs["inputs"]
    except KeyError:
        return

    cs_prefix = "JSSResource/advancedcomputersearches/name/"
    ms_prefix = "JSSResource/advancedmobiledevicesearches/name/"

    for stanza in inputs_conf:
        if "://" not in stanza.name:
            continue
        kind, _ = stanza.name.split("://", 1)
        if kind != "jamf":
            continue

        content = stanza.content
        api_call = (content.get("api_call") or "").strip()
        if not api_call or api_call in ("computer", "mobile_device", "custom"):
            continue

        # Strip leading/trailing slashes so '/JSSResource/x' and
        # 'JSSResource/x' are matched the same way.
        path = api_call.strip("/")

        if path.lower().startswith(cs_prefix.lower()):
            new_mode = "computer"
            recovered_search = path[len(cs_prefix):]
        elif path.lower().startswith(ms_prefix.lower()):
            new_mode = "mobile_device"
            recovered_search = path[len(ms_prefix):]
        else:
            new_mode = "custom"
            recovered_search = path

        patch = {"api_call": new_mode}
        existing_search = (content.get("search_name") or "").strip()
        if not existing_search and recovered_search:
            patch["search_name"] = recovered_search

        try:
            stanza.update(**patch)
            search_suffix = (
                "" if "search_name" not in patch
                else " (search_name set to %r)" % patch["search_name"]
            )
            _logger.info(
                "normalize_jamf_api_call: stanza %s api_call=%r -> %r%s. "
                "If this is wrong, edit the input in the Splunk UI.",
                stanza.name, api_call, new_mode, search_suffix,
            )
        except binding.HTTPError as exc:
            _logger.warning(
                "normalize_jamf_api_call: failed to update stanza %s (HTTP %s)",
                stanza.name, exc.status,
            )


def cleanup_legacy_client_prefix(session_key, splunkd_uri):
    """Strip the legacy "client:" prefix from stored account usernames.

    Earlier broken migration code stored API client IDs as "client:<uuid>";
    the runtime auth path now uses the auth_type field instead, so the prefix
    is dead weight (and leaks into the Accounts table column).

    Idempotent — only touches accounts whose username currently starts with
    "client:". Safe to run on every input fire.
    """
    try:
        service = _splunkd_connect(session_key, splunkd_uri)
    except Exception as exc:  # pragma: no cover
        _logger.warning("client_prefix_cleanup: could not connect to splunkd: %s", exc)
        return

    try:
        accounts = service.confs[ACCOUNT_CONF]
    except (KeyError, binding.HTTPError):
        return

    for stanza in accounts:
        if stanza.name == "default":
            continue
        username = stanza.content.get("username", "") or ""
        if not username.startswith("client:"):
            continue
        clean_username = username[len("client:"):]
        try:
            service.post(
                "configs/conf-{}/{}".format(ACCOUNT_CONF, stanza.name),
                username=clean_username,
                auth_type="api_client",
            )
            _logger.info(
                "client_prefix_cleanup: stripped client: prefix from account %s",
                stanza.name,
            )
        except binding.HTTPError as exc:
            _logger.warning(
                "client_prefix_cleanup: failed to clean account %s (HTTP %s)",
                stanza.name, exc.status,
            )


def _create_account_stub(service, account_name, url_hint=""):
    """Create a placeholder account with blank credentials.

    Used when credential decryption fails during migration — the stanza is
    still converted to the new schema (so it appears in the Inputs UI) but
    the account has no working credentials. The operator must fill them in
    and re-enable the input manually.
    """
    try:
        service.post(
            "configs/conf-{}".format(ACCOUNT_CONF),
            name=account_name,
            jss_url=url_hint or "",
            auth_type="api_client",
            username="",
            password="",
        )
    except binding.HTTPError as exc:
        if exc.status != 409:  # 409 = already exists, that's fine
            _logger.warning(
                "legacy_migration: failed to create stub account %s (HTTP %s)",
                account_name, exc.status,
            )


def _test_connectivity(url, username, password):
    """Attempt a real Jamf Pro auth call and return (ok: bool, reason: str).

    Uses requests directly (no splunktaucclib helper) so it can be called
    from migration context before any modular input is running.

    Mirrors the auth logic in JamfUAPIAuthToken.get_token():
    - username starting with "client:" -> OAuth2 client_credentials grant
    - otherwise                        -> basic-auth bearer token endpoint
    """
    try:
        normalized = url.rstrip("/")
        if not normalized.startswith("https://"):
            normalized = "https://" + normalized.lstrip("https://").lstrip("http://")  # NOSONAR — enforcing https

        if username.startswith("client:"):
            client_id = username[len("client:"):]
            resp = requests.post(
                normalized + "/api/v1/oauth/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=urlencode({
                    "client_id": client_id,
                    "client_secret": password,
                    "grant_type": "client_credentials",
                }),
                timeout=15,
                verify=True,
            )
        else:
            resp = requests.post(
                normalized + "/api/v1/auth/token",
                auth=(username, password),
                timeout=15,
                verify=True,
            )

        if resp.status_code == 200:
            return True, ""
        return False, "HTTP {} from Jamf Pro auth endpoint".format(resp.status_code)

    except requests.exceptions.ConnectionError as exc:
        return False, "connection error: {}".format(exc)
    except requests.exceptions.Timeout:
        return False, "connection timed out"
    except Exception as exc:
        return False, "unexpected error: {}".format(exc)


def migrate_legacy_inputs(session_key, splunkd_uri, input_type):
    """Migrate old-schema stanzas of the given input_type. Idempotent."""
    if input_type not in LEGACY_FIELDS_BY_TYPE:
        return

    try:
        service = _splunkd_connect(session_key, splunkd_uri)
    except Exception as exc:  # pragma: no cover
        _logger.warning("legacy_migration: could not connect to splunkd: %s", exc)
        return

    url_field, user_field, pass_field = LEGACY_FIELDS_BY_TYPE[input_type]

    try:
        inputs_conf = service.confs["inputs"]
    except KeyError:
        return

    existing_accounts = _list_existing_account_names(service)

    for stanza in inputs_conf:
        if "://" not in stanza.name:
            continue
        kind, name = stanza.name.split("://", 1)
        if kind != input_type:
            continue
        content = stanza.content
        has_account = _stanza_has_account(content)
        has_legacy_creds = _stanza_has_legacy_creds(content, input_type)

        # Classify state.
        if has_account and content["account"] in existing_accounts:
            continue  # healthy, already migrated
        # Only ever repair accounts this script itself created — names starting
        # with "migrated_<input_type>_". Otherwise an operator who edits
        # inputs.conf could trick this path into clobbering a hand-named account
        # by pointing a stanza's `account =` at it together with legacy creds.
        repair_prefix = "migrated_{}_".format(input_type)
        is_dangling_managed_repair = (
            has_account and content["account"].startswith(repair_prefix)
        )
        if not has_legacy_creds:
            if has_account:
                # Dangling reference with no creds to recover from. Splunktaucclib
                # would otherwise raise GlobalConfigError on every fire — log a
                # clear, actionable message so the operator can fix it in the UI.
                _logger.warning(
                    "legacy_migration: stanza %s references missing account '%s' "
                    "and has no legacy credentials to recover from. Open the input "
                    "in the Splunk UI and pick a valid account.",
                    stanza.name, content["account"],
                )
            continue
        if has_account and not is_dangling_managed_repair:
            # Dangling reference to an account *we didn't create*. Refuse to
            # recreate it from stanza-supplied creds — that would let a
            # stanza writer hijack a hand-named account. Operator must fix.
            _logger.warning(
                "legacy_migration: stanza %s references missing account '%s' "
                "which is not a migration-managed name (expected prefix '%s'). "
                "Refusing to recreate from stanza credentials. Pick a valid "
                "account in the Splunk UI.",
                stanza.name, content["account"], repair_prefix,
            )
            continue
        # Either fresh-migration (no account yet) or dangling repair of a
        # migration-managed name. In both cases legacy creds are present.
        is_repair = is_dangling_managed_repair

        url = content.get(url_field)
        username = content.get(user_field)
        password = _read_decrypted_password(session_key, input_type, name, pass_field)
        if not (url and username and password):
            # Credentials unavailable (key mismatch, no stored password, etc.).
            # Still convert the stanza to the new schema so it appears in the
            # Inputs UI — but disable it and point it at a stub account with
            # blank credentials. The operator can fill in credentials and
            # re-enable via Configuration → Accounts + Inputs.
            account_name = "migrated_{}_{}".format(input_type, _slugify(name))[:50]
            _create_account_stub(service, account_name, url_hint=url or "")
            patch = {
                "account": account_name,
                "disabled": "1",
                "input_status_control": (
                    "This input was disabled during upgrade from v2 because its credentials "
                    "could not be read from the previous version. Open Configuration → "
                    "Accounts → %s, enter valid credentials, then re-enable this input."
                    % account_name
                ),
            }
            for old, new in RENAMES.items():
                if old in content and new not in content:
                    patch[new] = content[old]
            try:
                stanza.update(**patch)
                _logger.warning(
                    "legacy_migration: stanza %s — credentials could not be "
                    "decrypted; created stub account '%s' and disabled input. "
                    "Open Configuration → Accounts → %s and enter valid "
                    "credentials, then re-enable the input.",
                    stanza.name, account_name, account_name,
                )
            except binding.HTTPError as exc:
                _logger.warning(
                    "legacy_migration: stanza %s — could not patch stanza "
                    "(HTTP %s) after credential failure",
                    stanza.name, exc.status,
                )
            continue

        if is_repair:
            # Reuse the name the stanza already points at so we don't have to
            # patch the stanza after recreating the account.
            account_name = content["account"]
        else:
            account_name = "migrated_{}_{}".format(input_type, _slugify(name))[:50]

        # Translate the legacy username convention into the new auth_type field.
        # 2.12.6 marked an API Client by prefixing the username with "client:".
        if username.startswith("client:"):
            account_auth_type = "api_client"
            account_username = username[len("client:"):]
        else:
            account_auth_type = "password"
            account_username = username

        # Test the credentials against the live Jamf Pro instance before
        # committing the migration. A failure here likely means the credentials
        # have rotated since they were saved in 2.12.x, or the host is
        # unreachable. We still create the account and patch the stanza so the
        # input appears in the UI, but we disable it so it doesn't produce a
        # stream of auth errors on every fire.
        conn_ok, conn_reason = _test_connectivity(url, username, password)
        if not conn_ok:
            _logger.warning(
                "legacy_migration: stanza %s — connectivity test failed (%s); "
                "will migrate to new schema but disable input. Open "
                "Configuration → Accounts → migrated_%s_%s and verify "
                "credentials, then re-enable the input.",
                stanza.name, conn_reason, input_type, _slugify(name),
            )

        # 1) Create the account (or reuse an existing migrated account with the same name).
        try:
            service.post(
                "configs/conf-{}".format(ACCOUNT_CONF),
                name=account_name,
                jss_url=url,
                auth_type=account_auth_type,
                username=account_username,
                password=password,
            )
            if is_repair:
                _logger.info(
                    "legacy_migration: recreated dangling account %s for stanza %s",
                    account_name, stanza.name,
                )
            else:
                _logger.info("legacy_migration: created account %s", account_name)
        except binding.HTTPError as exc:
            if exc.status == 409:
                if is_repair:
                    # We classified the account as missing earlier in this pass,
                    # but the POST said it already exists. A sibling input fire
                    # likely recreated it between our snapshot and our write.
                    _logger.info(
                        "legacy_migration: account %s reappeared between snapshot "
                        "and POST (likely a concurrent input fire); leaving in place",
                        account_name,
                    )
                else:
                    _logger.info(
                        "legacy_migration: account %s already exists, reusing", account_name
                    )
            else:
                _logger.warning(
                    "legacy_migration: failed to create account %s for stanza %s "
                    "(HTTP %s) — will retry next fire",
                    account_name, stanza.name, exc.status,
                )
                continue

        # 2) For a fresh migration, patch the input stanza to reference the account
        #    and apply field renames. For a repair, the stanza already points at
        #    the right account name — no patch needed.
        if is_repair:
            continue
        patch = {"account": account_name}
        if not conn_ok:
            patch["disabled"] = "1"
            patch["input_status_control"] = (
                "This input was disabled during upgrade from v2 because the "
                "connectivity test failed (%s). Open Configuration → Accounts → %s, "
                "verify the URL and credentials, then re-enable this input."
                % (conn_reason, account_name)
            )
        for old, new in RENAMES.items():
            if old in content and new not in content:
                patch[new] = content[old]
        try:
            stanza.update(**patch)
            _logger.info(
                "legacy_migration: stanza %s now references account %s%s",
                stanza.name, account_name,
                " (disabled — connectivity test failed)" if not conn_ok else "",
            )
        except binding.HTTPError as exc:
            _logger.warning(
                "legacy_migration: failed to update stanza %s (HTTP %s)",
                stanza.name, exc.status,
            )
