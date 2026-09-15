#!/usr/bin/env python3
"""
Splunk custom search command: | certcheck [mode=all|inputs|outputs] [check=static|live]

Analyses SSL/TLS certificate configurations present on this Splunk instance
by reading Splunk configuration via btool and performing static certificate
chain verification.  Results are returned as search events — one row per
active configuration component.

Uses the Splunk v2 chunked external command protocol (chunked = true in
commands.conf).  The command is a *generating* command: it emits rows from
nothing and should appear at the start of a search pipeline:

    | certcheck
    | certcheck mode=inputs
    | certcheck mode=outputs
    | certcheck check=live
    | certcheck mode=outputs check=live

Arguments
---------
mode=all|inputs|outputs
    Limit results to input-side configs, output-side configs, or both
    (default: all).

check=static|live
    ``static`` (default) — only static on-disk certificate analysis:
    chain verification, expiry checks, and component-specific rules.
    No outbound network connections are made.
    ``live`` — also attempts a live outbound SSL handshake for each
    output config to verify the remote server certificate in real time.

Protocol summary
----------------
Splunk writes two chunks to the process stdin and reads one chunk back from
stdout for each chunk.

  1. getinfo exchange  — Splunk sends an empty-body chunk with action=getinfo;
                         we reply declaring our capabilities.
  2. execute exchange  — Splunk sends an empty-body chunk with action=execute;
                         we reply with a CSV body containing all result rows.

Each chunk is framed as::

    chunked 1.0,<metadata_length>,<body_length>\n
    <metadata JSON bytes>
    <body bytes>
"""

import csv
import io
import json
import logging
import os
import sys

# ---------------------------------------------------------------------------
# Path bootstrapping
#
# When Splunk runs a chunked command it sets the working directory to the
# app's bin/ directory and places bin/ on sys.path.  The ptk_bottle_opener
# package lives one level above bin/ (i.e. in the app root), so we add that
# directory explicitly.  We also add bin/lib/ where vendored pure-Python
# dependencies (pem) are installed, and the repository root for development
# environments where the package has been installed with "pip install -e .".
# ---------------------------------------------------------------------------
_BIN_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_BIN_DIR)
_REPO_ROOT = os.path.dirname(_APP_DIR)
_LIB_DIR = os.path.join(_BIN_DIR, 'lib')

for _p in (_LIB_DIR, _BIN_DIR, _APP_DIR, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ptk_bottle_opener.conf_lib as conf_lib  # noqa: E402
from ptk_bottle_opener.conf_lib import check_cert_chain_with_ca  # noqa: E402

# ---------------------------------------------------------------------------
# Logging
#
# Splunk captures stderr from external commands.  We write structured log
# lines there so they land in splunkd.log / the internal index.
# ---------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='%(levelname)s pid=%(process)d %(name)s: %(message)s',
)
log = logging.getLogger('certcheck')

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Output field names — order here is the column order in the CSV body.
FIELDS = [
    'component',
    'priority',
    'is_active',
    'server_cert',
    'ca_cert',
    'client_cert',
    'status',
    'messages',
]

# Config classes to instantiate, in engineering priority order.
# Mirrors the loop in tools/cert_ffp.py::main().
_CONFIG_CLASSES = [
    conf_lib.SplunkHECConfig,               # inputs [http]
    conf_lib.SplunkSplunkTCPInConfig,       # inputs [splunktcp-ssl://]
    conf_lib.SplunkInputsSSLConfig,         # inputs [SSL]
    conf_lib.SplunkOutputsTCPOutConfig,     # outputs [tcpout:]
    conf_lib.SplunkWebConfig,               # web [settings]
    conf_lib.SplunkKVStoreConfig,           # server [kvstore]
    conf_lib.SplunkReplicationConfig,       # server [replication_port-ssl://]
    conf_lib.SplunkDeploymentServerConfig,  # serverclass + server [sslConfig]
    conf_lib.SplunkCLIConfig,               # server [sslConfig] cliVerifyServerName
    conf_lib.SplunkDeploymentClientConfig,  # deploymentclient [deployment-client]
]

# ---------------------------------------------------------------------------
# Chunked protocol I/O
# ---------------------------------------------------------------------------


def _read_chunk(fin):
    """Read one chunk from *fin* (a binary-mode file).

    Splunk v2 chunked external command protocol framing::

        chunked 1.0,<metadata_length>,<body_length>\\n
        <metadata JSON bytes>
        <body bytes>

    Returns ``(meta_dict, body_bytes)`` or ``(None, None)`` on EOF.
    """
    start_line = fin.readline()
    if not start_line:
        return None, None
    start_line = start_line.rstrip(b'\n')
    # Expected: b'chunked 1.0,<meta_len>,<body_len>'
    try:
        _, lengths = start_line.split(b',', 1)
        meta_len_s, body_len_s = lengths.split(b',', 1)
        meta_len = int(meta_len_s)
        body_len = int(body_len_s)
    except (ValueError, IndexError):
        log.error('Malformed chunk start line: %r', start_line)
        return None, None
    meta_bytes = fin.read(meta_len)
    meta = json.loads(meta_bytes.decode('utf-8')) if meta_len else {}
    body = fin.read(body_len) if body_len else b''
    return meta, body


def _write_chunk(fout, meta, body=b''):
    """Write one chunk to *fout* (a binary-mode file).

    Splunk v2 chunked external command protocol framing::

        chunked 1.0,<metadata_length>,<body_length>\\n
        <metadata JSON bytes>
        <body bytes>
    """
    meta_bytes = json.dumps(meta).encode('utf-8')
    start_line = f'chunked 1.0,{len(meta_bytes)},{len(body)}\n'
    fout.write(start_line.encode('utf-8'))
    fout.write(meta_bytes)
    if body:
        fout.write(body)
    fout.flush()


# ---------------------------------------------------------------------------
# Certificate-check orchestration
# ---------------------------------------------------------------------------


def _check_one(co, splunk_home, debug=False, check='static'):
    """Run all applicable verifications for a single config object *co*.

    Mirrors the ``_process_config_object`` logic in tools/cert_ffp.py but
    returns structured data instead of printing.

    Args:
        co: Config object to verify.
        splunk_home (str): Path to the Splunk installation root.
        debug (bool): Enable debug output.
        check (str): ``'static'`` for on-disk analysis only; ``'live'`` to
            also attempt outbound SSL connections for output configs.

    Returns:
        tuple[bool, list[str]]: ``(overall_ok, messages)``
    """
    all_ok = True
    msgs = []

    co_server_cert = co.get_server_cert()
    co_ca_cert = co.get_ca_cert_file()

    # Static chain check for input configs that have a server cert.
    chain_ok = None
    if co.is_input_port() and co_server_cert is not None:
        chain_ok, chain_msgs = check_cert_chain_with_ca(
            co_server_cert, co_ca_cert, debug=debug)
        msgs.extend(chain_msgs)
        all_ok = all_ok and chain_ok

    # Outbound verification for output configs (only when check='live').
    outbound_ok = None
    if (check == 'live'
            and co.is_output_port()
            and hasattr(co, 'attempt_outbound_verification')):
        outbound_ok, outbound_msgs = co.attempt_outbound_verification()
        msgs.extend(outbound_msgs)
        all_ok = all_ok and outbound_ok

    # Static local cert analysis (expiry check).  Run whenever outbound
    # verification was not attempted or did not succeed.
    if outbound_ok is None or not outbound_ok:
        static_ok, static_msgs = co.attempt_static_local_cert_analysis()
        if static_msgs:
            msgs.extend(static_msgs)
        if not static_ok:
            all_ok = False

    # Component-specific extra checks (e.g. KVStore subject requirements).
    if hasattr(co, 'extra_verification'):
        extra_ok, extra_msgs = co.extra_verification()
        if extra_msgs:
            msgs.extend(extra_msgs)
        all_ok = all_ok and extra_ok

    return all_ok, msgs


def _build_row(co, ok, msgs):
    """Convert a config object and its verification result into a field dict."""
    client_cert = ''
    if co.is_output_port() and hasattr(co, 'get_client_cert'):
        client_cert = co.get_client_cert() or ''

    return {
        'component': co.get_short_desc(),
        'priority': str(getattr(co, 'eng_priority', '')),
        'is_active': '1',
        'server_cert': co.get_server_cert() or '',
        'ca_cert': co.get_ca_cert_file() or '',
        'client_cert': client_cert,
        'status': 'ok' if ok else 'fail',
        'messages': ' | '.join(str(m) for m in msgs if m),
    }


def run_checks(splunk_home, mode='all', debug=False, check='static'):
    """Instantiate all config classes and run verification.

    Args:
        splunk_home (str): Path to the Splunk installation root.
        mode (str): ``'all'``, ``'inputs'``, or ``'outputs'``.
        debug (bool): Pass debug flag through to check functions.
        check (str): ``'static'`` for on-disk analysis only; ``'live'`` to
            also attempt live outbound SSL connections for output configs.

    Returns:
        list[dict]: One dict per active configuration entry, keyed by FIELDS.
    """
    rows = []

    # server.conf [sslConfig] acts as the shared fallback for most configs.
    try:
        srv_ssl_conf = conf_lib.SplunkServerSSLConfig(
            splunk_home=splunk_home, verbose=debug)
    except Exception as exc:
        log.error('Failed to load server.conf [sslConfig]: %s', exc)
        srv_ssl_conf = None

    for cls in _CONFIG_CLASSES:
        try:
            co = cls(splunk_home=splunk_home,
                     fallback_conf=srv_ssl_conf,
                     verbose=debug)
        except Exception as exc:
            log.warning('Failed to instantiate %s: %s', cls.__name__, exc)
            continue

        # Mode filter: skip configs that don't match the requested direction.
        if mode == 'inputs' and not co.is_input_port():
            continue
        if mode == 'outputs' and not co.is_output_port():
            continue

        # Container configs (e.g. multiple tcpout groups, replication ports)
        # expose sub-configs via get_config_count() / get_config_entry().
        entries = []
        if co.get_config_count() > 0:
            for idx in range(co.get_config_count()):
                entry = co.get_config_entry(idx)
                if entry is not None:
                    entries.append(entry)
        else:
            entries = [co]

        for entry in entries:
            if not entry.is_active():
                continue

            # Input configs with no server cert are not yet configured; skip.
            if entry.is_input_port() and entry.get_server_cert() is None:
                continue

            try:
                ok, msgs = _check_one(entry, splunk_home, debug=debug,
                                      check=check)
            except Exception as exc:
                log.error('Error checking %s: %s', entry.get_short_desc(), exc)
                ok = False
                msgs = [f'Internal error: {exc}']

            rows.append(_build_row(entry, ok, msgs))

    return rows


# ---------------------------------------------------------------------------
# CSV serialisation
# ---------------------------------------------------------------------------

# The Splunk v2 chunked protocol requires every field column to be accompanied
# by a ``__mv_<field>`` companion column.  The SDK's RecordWriterV2 always
# emits both; without the __mv_ columns Splunk treats the rows as raw events
# and the fields do not appear in the table view.
_MV_FIELDS = [col for pair in zip(FIELDS, [f'__mv_{f}' for f in FIELDS])
              for col in pair]


def _rows_to_csv(rows):
    """Serialise *rows* (list of dicts) to UTF-8 CSV bytes.

    Emits interleaved ``field, __mv_field, ...`` columns as required by the
    Splunk v2 chunked external command protocol so that results appear as
    structured fields in the table/event viewer rather than raw events.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator='\r\n')
    writer.writerow(_MV_FIELDS)
    for row in rows:
        out = []
        for field in FIELDS:
            out.append(row.get(field, ''))
            out.append('')          # __mv_ companion; empty = single value
        writer.writerow(out)
    return buf.getvalue().encode('utf-8')


# ---------------------------------------------------------------------------
# Argument parsing helpers
# ---------------------------------------------------------------------------


def _parse_mode(args_list):
    """Extract ``mode=<value>`` from the raw args list Splunk passes us.

    Splunk delivers command arguments as a list of strings in
    ``searchinfo.args`` (e.g. ``['mode=inputs']``).  We do not use argparse
    here because the chunked protocol hands us a pre-tokenised list.

    Returns:
        str: One of ``'all'``, ``'inputs'``, ``'outputs'``.  Defaults to
        ``'all'`` for unrecognised or absent values.
    """
    valid = {'all', 'inputs', 'outputs'}
    for arg in args_list:
        if arg.startswith('mode='):
            val = arg.split('=', 1)[1].strip().lower()
            if val in valid:
                return val
            log.warning('Unrecognised mode=%r; defaulting to "all"', val)
    return 'all'


def _parse_check(args_list):
    """Extract ``check=<value>`` from the raw args list Splunk passes us.

    Returns:
        str: One of ``'static'``, ``'live'``.  Defaults to ``'static'`` for
        unrecognised or absent values.
    """
    valid = {'static', 'live'}
    for arg in args_list:
        if arg.startswith('check='):
            val = arg.split('=', 1)[1].strip().lower()
            if val in valid:
                return val
            log.warning('Unrecognised check=%r; defaulting to "static"', val)
    return 'static'


# ---------------------------------------------------------------------------
# Main protocol loop
# ---------------------------------------------------------------------------


def main():
    # Use raw binary streams so we control framing exactly.
    fin = sys.stdin.buffer
    fout = sys.stdout.buffer

    # ------------------------------------------------------------------
    # CLI shortcut: if stdin is a terminal (not a pipe from splunkd),
    # there will be no chunked protocol frames.  Run directly and print
    # CSV to stdout so the script is usable as:
    #   splunk cmd python3 cmd_cert_ffp.py [mode=inputs|outputs|all]
    # ------------------------------------------------------------------
    if sys.stdin.isatty():
        splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
        debug = os.environ.get('CERTCHECK_DEBUG', '').lower() in ('1', 'true', 'yes')
        mode = _parse_mode(sys.argv[1:])
        check = _parse_check(sys.argv[1:])
        log.info('CLI mode: splunk_home=%s mode=%s check=%s', splunk_home, mode, check)
        rows = run_checks(splunk_home, mode=mode, debug=debug, check=check)
        sys.stdout.buffer.write(_rows_to_csv(rows))
        return

    # ------------------------------------------------------------------
    # Step 1: getinfo exchange
    # ------------------------------------------------------------------
    meta, _ = _read_chunk(fin)
    if meta is None:
        log.error('EOF on stdin before getinfo chunk; exiting')
        sys.exit(1)

    log.info('getinfo received: action=%s', meta.get('action'))

    searchinfo = meta.get('searchinfo', {})
    args_list = searchinfo.get('args', [])
    mode = _parse_mode(args_list)
    check = _parse_check(args_list)

    # SPLUNK_HOME is set in the environment by splunkd when it launches the
    # command process.  Fall back to /opt/splunk for local testing.
    splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
    debug = os.environ.get('CERTCHECK_DEBUG', '').lower() in ('1', 'true', 'yes')

    log.info('certcheck starting: splunk_home=%s mode=%s check=%s debug=%s',
             splunk_home, mode, check, debug)

    # Reply to getinfo.
    # Send only the keys the SDK sends.  Extra keys such as 'error', 'warn',
    # 'inspector', and 'streaming_command_will_restart' cause splunkd 10.x to
    # treat the getinfo reply as an error and close stdin without sending the
    # execute chunk, which appears as "Expected execute chunk, got: None".
    #
    # type=reporting routes results to the statistics pipeline, which causes
    # Splunk to display the Statistics tab (table view) by default rather than
    # the Events tab (raw event list).  With generating=true in commands.conf,
    # splunkd does not wait for upstream events before sending the execute chunk.
    _write_chunk(fout, {
        'type': 'reporting',
        'generating': True,
        'required_fields': FIELDS,
        'clear_required_fields': True,
    })

    # ------------------------------------------------------------------
    # Step 2: execute exchange
    # ------------------------------------------------------------------
    meta, _ = _read_chunk(fin)
    if meta is None or meta.get('action') != 'execute':
        log.error('Expected execute chunk, got: %s', meta)
        _write_chunk(fout, {
            'finished': True,
            'error': 'Protocol error: expected execute chunk',
        })
        sys.exit(1)

    log.info('execute received')

    try:
        rows = run_checks(splunk_home, mode=mode, debug=debug, check=check)
        body = _rows_to_csv(rows)
        log.info('certcheck complete: %d row(s) produced', len(rows))
        _write_chunk(fout, {'finished': True, 'error': ''}, body)
    except Exception as exc:
        log.exception('Unhandled exception in run_checks')
        _write_chunk(fout, {'finished': True, 'error': str(exc)})
        sys.exit(1)


if __name__ == '__main__':
    main()
