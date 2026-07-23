import json
import os
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splunk.persistconn.application import PersistentServerConnectionApplication
import _launcher
import k8s_search_lib as lib

class CacheHandler(PersistentServerConnectionApplication):

    def __init__(self, command_line=None, command_arg=None):
        super().__init__()

    def handle(self, in_string):
        try:
            return _dispatch(in_string)
        except lib._SplunkdError as exc:
            return lib.splunkd_error_response(exc)

def _dispatch(in_string):
    request = json.loads(in_string)
    method = request.get('method', 'GET').upper()
    session = request.get('session', {}) or {}
    session_key = session.get('authtoken', '')
    if method != 'DELETE':
        return lib.json_response(405, {'error': 'method not allowed; only DELETE is supported on /k8s_search/cache'})
    if not lib.can_edit_clusters(session_key):
        return lib.json_response(403, {'error': 'the edit_k8s_search_clusters capability is required to flush the cache'})
    try:
        binary = _launcher.binary_path('k8s_search')
    except (_launcher.UnsupportedPlatformError, _launcher.BinaryNotFoundError) as exc:
        return lib.json_response(500, {'error': 'cache-sweep binary unavailable: {}'.format(exc)})
    proc = subprocess.run([binary, 'cache-sweep', '--clear-all'], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=120)
    if proc.returncode != 0:
        return lib.json_response(500, {'error': 'cache-sweep --clear-all failed', 'stderr': proc.stderr.decode('utf-8', errors='replace')})
    return lib.json_response(200, {'status': 'ok', 'summary': proc.stderr.decode('utf-8', errors='replace').strip()})
