"""Daily phone-home to the RST License Server.

Registered in default/inputs.conf as a Splunk **modular input** (not a plain
``[script://...]`` scripted input). The reason is auth: scripted inputs do
not receive a session token, so they cannot read storage/passwords or
configs/conf-mcp without running an extra splunkd authentication round-trip
that adds failure modes. Modular inputs receive ``session_key`` over stdin
XML for free, which keeps this module short and reliable.

Failure semantics: never crash the input. Any error is logged and we exit
0. A failed heartbeat is just deferred to tomorrow's run; the splunk app
keeps using its locally-cached signed token until the offline_grace window
expires (see mcp_base._check_license).
"""
import logging
import os
import sys
import xml.etree.ElementTree as ET

# Splunk ships its own OpenSSL 3.x at /opt/splunk/lib/libssl.so.3 but does
# NOT install the legacy provider config. cryptography 40+ tries to load
# the legacy provider eagerly and crashes with
# "OpenSSL 3.0's legacy provider failed to load" on first use. We don't
# need any legacy algorithms (only RSA-PSS, AES-GCM, SHA-256), so opt out
# explicitly. Setting this AFTER cryptography is already imported is too
# late — set it before any imports that pull in OpenSSL bindings.
os.environ.setdefault('CRYPTOGRAPHY_OPENSSL_NO_LEGACY', '1')

# Splunk 10.x ships both python3.9 and python3.13. Its `python3` symlink
# points at 3.9 (which has no `cryptography` module), so a modular input
# launched via the symlink can't import the SDK's verifier. The vendored
# fallback we ship for 9.x (cryptography 40 manylinux2014) needs OpenSSL 1.1
# / libssl.so.3 which isn't on the runtime path of every Splunk image
# either. The cleanest fix: if a 3.13 interpreter exists alongside the
# current one, re-exec under it BEFORE we import any cryptography-using
# modules. On 9.x there is no 3.13 — we stay on 3.9 + vendored.
def _maybe_reexec_under_python313():
    if sys.version_info[:2] >= (3, 13):
        return  # already on 3.13 (or newer)
    candidates = []
    cur = sys.executable or ''
    if cur:
        # Sibling 3.13 binary in the same dir as the current interpreter.
        candidates.append(os.path.join(os.path.dirname(cur), 'python3.13'))
    candidates.extend([
        '/opt/splunk/bin/python3.13',
        '/usr/bin/python3.13',
        '/usr/local/bin/python3.13',
    ])
    for cand in candidates:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            os.execv(cand, [cand, __file__, *sys.argv[1:]])

_maybe_reexec_under_python313()

# Make bin/lib/ importable for license_verifier + mcp_license_phone_home.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

logger = logging.getLogger('mcp_license_heartbeat')


# Modular-input scheme. Splunk calls the script with --scheme on registration
# to learn what arguments it accepts. We don't take any user-configurable
# args because the upstream URL / app_id come from mcp.conf [license_server].
_SCHEME_XML = """<?xml version="1.0" encoding="UTF-8"?>
<scheme>
    <title>RST License Heartbeat</title>
    <description>Daily phone-home to the RST License Server (activate refresh + telemetry).</description>
    <use_external_validation>false</use_external_validation>
    <streaming_mode>simple</streaming_mode>
    <!-- single_instance=false: splunkd respawns the script on every
         interval tick. Our script is a single-shot heartbeat (does its
         work, exits 0). With single_instance=true splunkd would expect
         a long-lived process and only schedule once per restart. -->
    <use_single_instance>false</use_single_instance>
    <endpoint>
        <args>
            <arg name="name">
                <title>Stanza Name</title>
                <description>Internal name; the heartbeat itself takes no parameters.</description>
                <data_type>string</data_type>
            </arg>
        </args>
    </endpoint>
</scheme>
"""


def main():
    if '--scheme' in sys.argv:
        sys.stdout.write(_SCHEME_XML)
        return 0
    if '--validate-arguments' in sys.argv:
        return 0  # no args to validate

    # Modular input run: parse session_key from stdin XML.
    try:
        raw = sys.stdin.read()
        if not raw:
            return 0
        root = ET.fromstring(raw)
        session_key = root.findtext('session_key') or ''
    except Exception as e:
        # Don't bubble — splunkd will log stderr but a malformed config
        # should not retry-storm. Best-effort: exit 0.
        logger.warning('mod-input config parse failed: %s', e)
        return 0

    if not session_key:
        logger.info('no session_key supplied; skipping heartbeat')
        return 0
    # Minimal sanity guard against accidental injection (e.g. a misconfigured
    # input piping garbage into stdin). Splunk session tokens are typically
    # >100 chars of [A-Za-z0-9_+/=^]; a short or whitespace-laden value is
    # almost certainly not a real token, and refusing to proceed is cheaper
    # than letting splunkd's REST layer return cryptic 401s on every call.
    if len(session_key) < 32 or any(c.isspace() for c in session_key):
        logger.warning('session_key fails sanity check; skipping heartbeat')
        return 0

    try:
        _do_heartbeat(session_key)
    except Exception as e:
        logger.warning('heartbeat error (non-fatal, will retry next interval): %s', e)
    return 0


def _do_heartbeat(session_key: str) -> None:
    """Load the cached license, locally validate it to recover license_data,
    then call the SDK's heartbeat_if_due() (which itself decides whether
    enough time has elapsed since the last heartbeat to issue a new one)."""
    from mcp_license_phone_home import heartbeat_if_due
    from license_verifier import LicenseVerifier, LicenseError

    handler = _ModInputHandlerShim(session_key)

    license_key = handler._get_encrypted_credential('mcp_license_key')
    if not license_key:
        # No license installed — nothing to phone home about.
        return

    server_guid = handler._get_server_guid()
    if not server_guid:
        return

    try:
        verifier = LicenseVerifier()
        license_data = verifier.validate_full(license_key, server_guid)
    except LicenseError as e:
        # Locally-invalid licenses skip heartbeat; the user-facing _check_license
        # will surface the same error on the next admin call.
        logger.info('local license validation failed; skipping heartbeat: %s', e)
        return

    metrics = {'source': 'modinput-daily'}
    # Best-effort 24h query-volume snapshot. license-server uses this
    # for usage-anomaly detection (queries spiking unusually often,
    # off-hours activity that suggests a sold-on license, etc.).
    try:
        from usage_tracker import get_query_stats_24h
        metrics.update(get_query_stats_24h())
    except Exception as e:
        logger.info('could not collect query stats for heartbeat: %s', e)
    heartbeat_if_due(handler, license_data, metrics=metrics)


class _ModInputHandlerShim:
    """Mini handler whose duck-typed surface matches what mcp_license_phone_home
    expects from MCPBaseHandler. Re-implemented (rather than reused) because
    MCPBaseHandler inherits from ``admin.MConfigHandler`` which expects to be
    instantiated by Splunk's admin framework — not from a long-running input.

    The duplication here is small and intentional. If the surface grows we
    should extract a `bin/lib/splunk_credentials.py` shared module; for now
    the cost of an extra module exceeds the duplication's drag.
    """

    def __init__(self, session_key: str):
        self._session_key = session_key

    def getSessionKey(self):  # noqa: N802 — Splunk SDK casing.
        return self._session_key

    def _get_encrypted_credential(self, credential_key, raise_on_error=False):
        import splunk.entity as entity  # noqa: PLC0415 — splunkd-only import.
        try:
            entities = entity.getEntities(
                ['storage', 'passwords'],
                namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                sessionKey=self._session_key,
            )
        except Exception as e:
            if raise_on_error:
                raise
            logger.warning('storage/passwords lookup failed: %s', e)
            return None
        for _, c in entities.items():
            try:
                if c['eai:acl']['app'] == 'AI_Query_Assistant_for_Splunk' \
                        and c['username'] == credential_key:
                    return c['clear_password']
            except (KeyError, TypeError):
                continue
        return None

    def _store_encrypted_credential(self, credential_key, credential_value):
        import splunk.entity as entity  # noqa: PLC0415
        try:
            try:
                entity.deleteEntity(
                    ['storage', 'passwords'], ':%s:' % credential_key,
                    namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                    sessionKey=self._session_key,
                )
            except Exception:
                pass  # may not exist yet
            new_credential = entity.Entity(
                ['storage', 'passwords'], credential_key,
                contents={'password': credential_value or ''},
                namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
            )
            entity.setEntity(new_credential, sessionKey=self._session_key)
            return True
        except Exception as e:
            logger.warning("storage/passwords write failed for %s: %s", credential_key, e)
            return False

    def _get_config(self):
        import splunk.entity as entity  # noqa: PLC0415
        cfg = {}
        for stanza in ('ai', 'security', 'integration', 'query', 'license_server'):
            try:
                ent = entity.getEntity(
                    '/configs/conf-mcp', stanza,
                    namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                    sessionKey=self._session_key,
                )
                cfg[stanza] = dict(ent)
            except Exception:
                cfg[stanza] = {}
        return cfg

    def _get_server_guid(self) -> str:
        import splunk.entity as entity  # noqa: PLC0415
        try:
            info = entity.getEntity(
                '/server', 'info',
                namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                sessionKey=self._session_key,
            )
            return info.get('guid', '')
        except Exception as e:
            logger.warning('failed to read server guid: %s', e)
            return ''


if __name__ == '__main__':
    sys.exit(main())
