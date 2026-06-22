"""MCP License Handler - REST endpoint for license verification and activation."""
import sys
import os
import json
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import splunk.admin as admin
import splunk.entity as entity
from mcp_base import MCPBaseHandler
from license_verifier import LicenseVerifier, LicenseError, get_cached_license_status, invalidate_cache

# Phone-home wrapper. Best-effort: errors here must NEVER block a successful
# local activation — the local RSA verifier already proved the license is
# legitimate, so a license-server outage at activation time should not
# prevent the customer from using their license.
try:
    from mcp_license_phone_home import activate_after_local_verify as _phone_home_activate
    logging.getLogger(__name__).info("phone_home import OK at module load")
except Exception as _e:
    logging.getLogger(__name__).warning("phone_home import failed at module load: %s", _e)
    _phone_home_activate = None

logger = logging.getLogger(__name__)

LICENSE_CREDENTIAL_KEY = 'mcp_license_key'


class MCPLicenseHandler(MCPBaseHandler):

    def setup(self):
        self.supportedArgs.addOptArg('license_key')
        # Splunk REST clients pass output_mode=json on every call; declare it
        # supported so the handler doesn't reject the request with HTTP 400
        # "Argument output_mode is not supported by this handler".
        self.supportedArgs.addOptArg('output_mode')

    def _get_server_guid(self):
        """Get this Splunk instance's server GUID."""
        try:
            server_info = entity.getEntity(
                '/server', 'info',
                namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                sessionKey=self.getSessionKey()
            )
            return server_info.get('guid', '')
        except Exception as e:
            logger.error(f"Failed to get server GUID: {e}")
            return ''

    def handleList(self, confInfo):
        """GET: Check current license status."""
        try:
            server_guid = self._get_server_guid()
            license_key = self._get_encrypted_credential(LICENSE_CREDENTIAL_KEY)

            if not license_key:
                confInfo['license'].append('valid', 'false')
                confInfo['license'].append('error', 'No license installed')
                confInfo['license'].append('server_guid', server_guid)
                return

            result = get_cached_license_status(license_key, server_guid)

            confInfo['license'].append('valid', str(result['valid']).lower())
            confInfo['license'].append('server_guid', server_guid)

            if result['valid'] and result['data']:
                data = result['data']
                confInfo['license'].append('license_type', data.get('license_type', ''))
                confInfo['license'].append('email', data.get('email', ''))
                confInfo['license'].append('expiry_date', data.get('expiry_date', ''))
                confInfo['license'].append('days_remaining', str(LicenseVerifier.days_remaining(data)))
                confInfo['license'].append('license_id', data.get('license_id', ''))
                confInfo['license'].append('max_nodes', str(data.get('max_nodes', 0)))
                confInfo['license'].append('features', json.dumps(data.get('features', [])))
            else:
                confInfo['license'].append('error', result.get('error', 'Unknown error'))

        except Exception as e:
            logger.exception("Error checking license status")
            confInfo['license'].append('valid', 'false')
            confInfo['license'].append('error', str(e))

    def handleEdit(self, confInfo):
        """POST: Activate a new license key."""
        try:
            license_key = self.callerArgs.data.get('license_key', [None])[0]
            if not license_key:
                raise admin.ArgValidationException("license_key is required")

            license_key = license_key.strip()
            server_guid = self._get_server_guid()

            if not server_guid:
                confInfo['result'].append('success', 'false')
                confInfo['result'].append('error', 'Could not determine server GUID')
                return

            # Decode + structural validation only. The local RSA signature
            # check has been removed (remote-online verification mode); the
            # RST License Server below is the sole integrity authority.
            verifier = LicenseVerifier()
            try:
                license_data = verifier.validate_full(license_key, server_guid)
            except LicenseError as e:
                confInfo['result'].append('success', 'false')
                confInfo['result'].append('error', str(e))
                return

            # Phone-home FIRST. With no local signature gate, we must not
            # store the license key until the RST License Server has confirmed
            # this host is allowed to use it. A stored-but-unverified key
            # would mislead `_check_license` into thinking activation
            # succeeded.
            if _phone_home_activate is None:
                confInfo['result'].append('success', 'false')
                confInfo['result'].append(
                    'error',
                    'License server SDK unavailable in this build; cannot '
                    'perform remote activation.'
                )
                return

            try:
                ph_result = _phone_home_activate(
                    self, license_data, splunk_version='',
                    splunk_server_guid=server_guid
                ) or {}
            except Exception as e:
                logger.exception("license phone-home activate crashed")
                confInfo['result'].append('success', 'false')
                confInfo['result'].append('error', f'Activation crashed: {e}')
                return

            if not ph_result.get('success'):
                confInfo['result'].append('success', 'false')
                confInfo['result'].append('error', ph_result.get('reason') or 'activation_failed')
                confInfo['result'].append(
                    'message',
                    ph_result.get('message') or 'License server did not confirm activation.'
                )
                return

            # Server confirmed — now persist the license key and run the
            # one-shot v3.0.x KV cleanup.
            stored = self._store_encrypted_credential(LICENSE_CREDENTIAL_KEY, license_key)
            if not stored:
                confInfo['result'].append('success', 'false')
                confInfo['result'].append('error', 'Failed to store license key')
                return

            invalidate_cache()
            self._maybe_run_v2210_migration()

            confInfo['result'].append('success', 'true')
            confInfo['result'].append('license_type', license_data.get('license_type', ''))
            confInfo['result'].append('email', license_data.get('email', ''))
            confInfo['result'].append('expiry_date', license_data.get('expiry_date', ''))
            confInfo['result'].append('days_remaining', str(LicenseVerifier.days_remaining(license_data)))

        except admin.ArgValidationException:
            raise
        except Exception as e:
            logger.exception("Error activating license")
            confInfo['result'].append('success', 'false')
            confInfo['result'].append('error', str(e))

    # Issue #14: _maybe_run_v2210_migration moved to MCPBaseHandler so the
    # migration also fires from the first mcp_query call (handles customers
    # who upgrade without re-activating their license).


admin.init(MCPLicenseHandler, admin.CONTEXT_APP_AND_USER)
