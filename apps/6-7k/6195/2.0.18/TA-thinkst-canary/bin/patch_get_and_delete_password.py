#!/usr/bin/python
#
# Patch to avoid CredentialNotExistException when proxy password is empty
# There could still be a warning in the logs, but it won't cause failures
import os
import sys
try:
    from solnlib import credentials as solnlib_credentials
except ModuleNotFoundError:
    addon_root = os.path.dirname(__file__)
    aob_lib_path = os.path.join(addon_root, "ta_thinkst_canary", "aob_py3")
    if aob_lib_path not in sys.path:
        sys.path.insert(0, aob_lib_path)
    from solnlib import credentials as solnlib_credentials

_original_get_password = solnlib_credentials.CredentialManager.get_password
_original_delete_password = solnlib_credentials.CredentialManager.delete_password

def _safe_get_password(self, user, *args, **kwargs):
    """
    Skip credential lookup if proxy password field is empty. 
    This prevents CredentialNotExistException when the proxy is disabled or not populated.
    """
    realm = kwargs.get("realm", "")
    if "proxy" in user or "proxy" in realm.lower():
        try:
            password = _original_get_password(self, user, *args, **kwargs)
            return password
        except Exception:
            return "{\"proxy_password\":\"\"}"
    return _original_get_password(self, user, *args, **kwargs)

def _safe_delete_password(self, user, *args, **kwargs):
    """
    Skip credential deletion if proxy password field is empty. 
    This prevents CredentialNotExistException when the proxy is disabled or not populated.
    """
    realm = kwargs.get("realm", "")
    if "proxy" in user or "proxy" in realm.lower():
        try:
            return _original_delete_password(self, user, *args, **kwargs)
        except Exception:
            return
    return _original_delete_password(self, user, *args, **kwargs)


try:
    solnlib_credentials.CredentialManager.get_password = _safe_get_password
    solnlib_credentials.CredentialManager.delete_password = _safe_delete_password
except Exception as e:
    pass

try:
    from ta_thinkst_canary.aob_py3.solnlib import credentials as vendored_credentials
    vendored_credentials.CredentialManager.get_password = _safe_get_password
    vendored_credentials.CredentialManager.delete_password = _safe_delete_password
except Exception as e:
    pass