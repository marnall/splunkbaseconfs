# encoding: utf-8
"""
HEC token handler for Cisco Cloud Security Add-on.
Manages HEC tokens securely without storing them in configuration files.
"""

import json
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

import import_declare_test
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError
from solnlib import conf_manager
from solnlib.soln_exceptions import ConfManagerException
from utils import send_ui_notification, make_splunk_request, get_logger, str_to_boolean

logger = get_logger(f"{import_declare_test.ta_name}_hec_token_handler")

# HEC API endpoints
HEC_HTTP_BASE = "/data/inputs/http"
CONF_NAME = "ta_cisco_cloud_security_addon_configure_push_alerts_or_push_events"

def hec_item_path(name: str) -> str:
    """Build HEC item path for create/edit/get/enable/disable operations."""
    return f"{HEC_HTTP_BASE}/{quote(name, safe='')}"

def hec_item_path_single(name: str) -> str:
    """Build HEC item path for delete operations."""
    return f"{HEC_HTTP_BASE.lstrip('/')}/{quote(name, safe='')}"

class Hec_token(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self._ta_name = import_declare_test.ta_name

    # ----------------- helpers -----------------

    @staticmethod
    def _parse_payload(raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, (bytes, str)):
            try:
                return json.loads(raw or "{}")
            except Exception:
                return {}
        return {}

    @staticmethod
    def _get_fixed_sourcetype_and_source() -> Tuple[str, str]:
        """Return fixed sourcetype and source for security events and alerts."""
        return ("cisco:secure_access:security_events_and_alerts", "security_events_and_alerts")

    def _get_conf(self) -> Optional[Any]:
        """Get configuration manager for metadata storage (no tokens stored here)."""
        cfm = conf_manager.ConfManager(self.getSessionKey(), app=self._ta_name)
        try:
            return cfm.get_conf(CONF_NAME)
        except ConfManagerException:
            logger.info("Configuration file missing; attempting to create")
            try:
                return cfm.create_conf(CONF_NAME)
            except Exception:
                logger.error("Failed to create configuration file")
                return None

    def _normalize_stanza_boolean(self, stanza, field: str) -> bool:
        """Normalize stanza boolean field for UCC framework compatibility."""
        if field not in stanza:
            return False
        value = stanza[field][0] if isinstance(stanza[field], list) else stanza[field]
        return str_to_boolean(value)

    def _apply_disabled_to_hec(self, row_name: str, disabled: bool):
        """Toggle HEC input enabled/disabled state."""
        action = "disable" if disabled else "enable"
        try:
            make_splunk_request(
                method="POST",
                endpoint=f"{hec_item_path(row_name)}/{action}",
                session_key=self.getSessionKey(),
                data=None,
                use_json_output=False,
                addon_namespace=True,
            )
        except Exception as e:
            logger.error(f"Failed to {action} HEC token '{row_name}': {e}")
            status_code, user_message = self._parse_http_error(e)
            raise RestError(status_code, f"Failed to {action} HEC token '{row_name}': {user_message}") from e

    # ----------------- helpers for HEC operations -----------------

    def _get_hec_content(self, hec_name: str) -> Dict[str, Any]:
        """Fetch HEC configuration content from Splunk API.

        Raises:
            Exception: Any error from make_splunk_request is propagated
                to the caller.
        """
        resp = make_splunk_request(
            method="GET",
            endpoint=hec_item_path(hec_name),
            session_key=self.getSessionKey(),
            use_json_output=True,
            addon_namespace=True,
        ) or {}
        entry = resp.get("entry", [{}])[0] or {}
        return entry.get("content", {})

    def _sync_stanza_from_hec(self, stanza: Any, hec_content: Dict[str, Any]) -> None:
        """Sync stanza fields from HEC API response.

        Raises:
            RestError: If the token field is missing from hec_content.
        """
        token = hec_content.get("token")
        if not token:
            raise RestError(502, "HEC token not found in API response. The HEC configuration may be incomplete.")

        stanza["token"] = token
        
        # Sync common fields from HEC API
        stanza["disabled"] = str_to_boolean(hec_content.get("disabled", False))
        for field in ["index", "sourcetype", "source", "description"]:
            if field in hec_content:
                stanza[field] = hec_content[field]

    # ----------------- handlers -----------------

    def handleList(self, confInfo):
        """List HEC configurations with dynamic token injection."""
        try:
            AdminExternalHandler.handleList(self, confInfo)
            
            for stanza_name in confInfo:
                stanza = confInfo[stanza_name]
                try:
                    hec_content = self._get_hec_content(stanza_name)
                    self._sync_stanza_from_hec(stanza, hec_content)
                except Exception as e:
                    # Log the error but continue processing other stanzas to avoid complete failure of the list operation
                    logger.error(f"Failed to sync HEC content for '{stanza_name}': {e}")
                         
        except RestError as e:
            status_code, user_message = self._parse_http_error(e)
            logger.error(f"Failed to list HEC configurations due to {user_message} with {status_code}")
            send_ui_notification(self.getSessionKey(), f"Failed to list HEC configurations due to {user_message} with {status_code}")
            raise 
        except Exception as e:
            logger.error(f"Failed to list HEC configurations: {e}")
            status_code, user_message = self._parse_http_error(e)
            send_ui_notification(self.getSessionKey(), f"Failed to retrieve HEC token configurations: {user_message}")
            raise RestError(status_code, f"Failed to retrieve HEC token configurations: {user_message}")

    def _validate_hec_name(self, name: str) -> None:
        """Validate HEC token name against Splunk naming conventions and security requirements."""
        if not name:
            raise RestError(400, "HEC token name cannot be empty. Please provide a valid name.")
        
        if len(name) > 200:
            raise RestError(400, "HEC token name cannot exceed 200 characters. Please use a shorter name.")
        
        if len(name) < 3:
            raise RestError(400, "HEC token name must be at least 3 characters long.")
        
        # Check for invalid characters
        invalid_chars = ['/', '\\', '?', '#', '[', ']', '@', ':', '*', '"', '<', '>', '|', '%', '&', '=', '+']
        found_invalid = [char for char in invalid_chars if char in name]
        if found_invalid:
            raise RestError(400, f"HEC token name contains invalid characters: {', '.join(found_invalid)}. Please use only letters, numbers, hyphens, and underscores.")
        
        # Check for reserved names or patterns
        reserved_patterns = ['http://', 'https://', 'ftp://', 'file://', 'splunk', 'admin', 'system']
        reserved_names = ['default', 'main', 'internal', 'audit', '_internal', 'summary']
        
        name_lower = name.lower()
        for pattern in reserved_patterns:
            if name_lower.startswith(pattern):
                raise RestError(400, f"HEC token name cannot start with '{pattern}'. Please choose a different name.")
        
        if name_lower in reserved_names:
            raise RestError(400, f"'{name}' is a reserved name and cannot be used. Please choose a different name.")
        
        # Check for whitespace at beginning/end
        if name != name.strip():
            raise RestError(400, "HEC token name cannot have leading or trailing whitespace. Please trim the name.")
        
        # Check for internal whitespace (spaces)
        if ' ' in name:
            raise RestError(400, "HEC token name cannot contain spaces. Please use underscores or hyphens instead.")
        
        # Check if name starts with number or special character
        if not (name[0].isalpha() or name[0] == '_'):
            raise RestError(400, "HEC token name must start with a letter or underscore.")

    def _validate_required_fields(self, payload: Dict[str, Any]) -> None:
        """Validate required fields for HEC token creation/update."""
        # Check index
        index_val = payload.get("index", "").strip()
        if not index_val:
            raise RestError(400, "Index field is required. Please specify a target index for the HEC token.")
        
        # Validate index name format
        if len(index_val) < 1:
            raise RestError(400, "Index name cannot be empty.")
        
        if len(index_val) > 80:
            raise RestError(400, "Index name cannot exceed 80 characters.")
        
        # More comprehensive index validation
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', index_val):
            raise RestError(400, "Index name contains invalid characters. Use only letters, numbers, dots, underscores, and hyphens.")
        
        if index_val.startswith('.') or index_val.startswith('_'):
            raise RestError(400, "Index name cannot start with a dot or underscore.")
        
        # Check sourcetype if provided
        sourcetype_val = payload.get("sourcetype", "").strip()
        if sourcetype_val:
            if len(sourcetype_val) > 200:
                raise RestError(400, "Sourcetype cannot exceed 200 characters.")
            
            if not re.match(r'^[a-zA-Z0-9:._-]+$', sourcetype_val):
                raise RestError(400, "Sourcetype contains invalid characters. Use only letters, numbers, colons, dots, underscores, and hyphens.")
        
        # Check source if provided
        source_val = payload.get("source", "").strip()
        if source_val and len(source_val) > 200:
            raise RestError(400, "Source cannot exceed 200 characters.")
        
        # Check description if provided
        description_val = payload.get("description", "").strip()
        if description_val and len(description_val) > 500:
            raise RestError(400, "Description cannot exceed 500 characters.")

    def _parse_http_error(self, error: Exception) -> Tuple[int, str]:
        """Parse HTTP error from make_splunk_request exceptions to extract status code and message."""
        error_str = str(error).lower()
        original_error_str = str(error)
        
        # Extract specific error messages from Splunk API responses
        if "already exists" in error_str:
            # Handle the specific case mentioned in the issue
            if "http://push_alerts already exists" in original_error_str or "http://push_events already exists" in original_error_str:
                return 409, "A HEC token with this name already exists. Please choose a different name or delete the existing token first."
            else:
                return 409, "A configuration with this name already exists. Please use a different name or delete the existing configuration first."
        
        # Check for other specific HTTP status codes and their messages
        elif "409" in error_str:
            return 409, "Resource conflict. The operation cannot be completed due to a conflict with the current state."
        elif "401" in error_str or "unauthorized" in error_str:
            return 401, "Unauthorized access. Please check your credentials and permissions."
        elif "403" in error_str or "forbidden" in error_str:
            return 403, "Access forbidden. You don't have sufficient permissions to perform this action."
        elif "404" in error_str or "not found" in error_str:
            return 404, "Resource not found. The specified HEC token may have been deleted or does not exist."
        elif "400" in error_str or "bad request" in error_str:
            # Look for validation errors in the response
            if "invalid" in error_str and ("index" in error_str or "sourcetype" in error_str):
                return 400, "Invalid configuration parameters. Please verify that the index exists and sourcetype is valid."
            else:
                return 400, "Invalid request parameters. Please check your input values and try again."
        elif "422" in error_str or "unprocessable entity" in error_str:
            return 422, "Request data is invalid or incomplete. Please verify all required fields are filled correctly."
        elif "429" in error_str or "too many requests" in error_str:
            return 429, "Rate limit exceeded. Please wait a moment before trying again."
        elif "500" in error_str or "internal server error" in error_str:
            return 500, "Internal server error. Please contact your system administrator."
        elif "502" in error_str or "bad gateway" in error_str:
            return 502, "Service temporarily unavailable. Please try again later."
        elif "503" in error_str or "service unavailable" in error_str:
            return 503, "Service unavailable. The system may be under maintenance. Please try again later."
        elif "504" in error_str or "gateway timeout" in error_str:
            return 504, "Request timeout. The operation took too long to complete. Please try again."
        elif "connection" in error_str and ("refused" in error_str or "failed" in error_str):
            return 503, "Cannot connect to Splunk service. Please verify that Splunk is running and accessible."
        else:
            # Try to extract meaningful information from the error message
            if "validation" in error_str:
                return 400, f"Validation error: {original_error_str}"
            elif "permission" in error_str or "access" in error_str:
                return 403, f"Permission denied: {original_error_str}"
            else:
                # Generic error handling for unknown errors
                return 500, f"An unexpected error occurred. Details: {original_error_str}"

    def handleCreate(self, confInfo):
        """Create new HEC token."""
        row_name = None
        try:
            payload = self._parse_payload(self.payload)
            row_name = payload.get("name") or str(self.callerArgs.id or "")
            
            if not row_name or not row_name.strip():
                raise RestError(400, "HEC token name cannot be empty or contain only whitespace. Please provide a valid name.")

            # Validate HEC name (catches leading/trailing whitespace before stripping)
            self._validate_hec_name(row_name)

            # Check if HEC token already exists.
            # A 404 from _get_hec_content means the token does not exist yet — safe to proceed.
            try:
                hec_content = self._get_hec_content(row_name)
                if hec_content.get("token"):
                    logger.error(f"HEC token creation conflict: '{row_name}' already exists.")
                    raise RestError(409, f"A HEC token with the name '{row_name}' already exists. Please choose a different name or delete the existing token first.")
            except RestError:
                raise
            except Exception as e:
                status_code, _ = self._parse_http_error(e)
                if status_code != 404:
                    logger.error(f"Failed to check HEC token existence for '{row_name}': {e}")
                    raise RestError(status_code, f"Failed to verify HEC token existence: {str(e)[:100]}")
                # 404 means the token doesn't exist — proceed with creation

            # Set fixed sourcetype and source for security events and alerts
            payload["sourcetype"], payload["source"] = (self._get_fixed_sourcetype_and_source())

            # Validate required fields
            self._validate_required_fields(payload)

            # Prepare HEC request
            hec_req = {
                "name": row_name,
                "index": payload.get("index"),
                "sourcetype": payload.get("sourcetype"),
                "source": payload.get("source"),
                "description": payload.get("description"),
                "disabled": 1 if str_to_boolean(payload.get("disabled", False)) else 0,
            }
            hec_req = {k: v for k, v in hec_req.items() if v not in ("", None)}

            # Create HEC token
            try:
                resp = make_splunk_request(
                    method="POST",
                    endpoint=HEC_HTTP_BASE, 
                    session_key=self.getSessionKey(),
                    data=hec_req,
                    use_json_output=True,
                    addon_namespace=True,
                ) or {}
            except Exception as e:
                status_code, user_message = self._parse_http_error(e)
                logger.error(f"HEC creation failed for '{row_name}': {e}")
                raise RestError(status_code, user_message)

            entry = resp.get("entry",[{}])[0]
            hec_content = entry.get("content", {})
            if not hec_content.get("token"):
                raise RestError(502, "HEC token was created but no token was returned. Please try again.")

            # Prepare payload for UCC config (store common fields)
            payload["disabled"] = str_to_boolean(payload.get("disabled", False))
            self.payload = payload

            # Save to UCC config
            AdminExternalHandler.handleCreate(self, confInfo)
            
            # Sync stanza with HEC response for UI
            if row_name in confInfo:
                try:
                    self._sync_stanza_from_hec(confInfo[row_name], hec_content)
                except RestError as e:
                    logger.error(f"Failed to sync HEC stanza '{row_name}' after creation: {e.message}")
                    raise

            send_ui_notification(self.getSessionKey(), f"HEC Token '{row_name}' created successfully")

        except RestError:
            if row_name:
                send_ui_notification(self.getSessionKey(), f"Failed to create HEC Token '{row_name}'")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating HEC token '{row_name}': {e}")
            if row_name:
                send_ui_notification(self.getSessionKey(), f"Failed to create HEC Token '{row_name}'")
            raise RestError(500, f"Failed to create HEC token: {str(e)[:100]}")

    def _build_hec_update_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Build HEC update payload for editable fields (index, description only)."""
        hec_update = {}
        for field in ["index", "description"]:
            if field in payload and payload.get(field) not in ("", None):
                hec_update[field] = payload[field]
        return hec_update

    def handleEdit(self, confInfo):
        """Update HEC input configuration (index, description, disabled only)."""
        row_name = ""
        try:
            payload = self._parse_payload(self.payload)
            row_name = str(self.callerArgs.id or "").strip()
            
            if not row_name:
                raise RestError(400, "Missing stanza identifier for edit operation.")

            #Since, the enable/disable endpoint has only "disabled" field, we need to validate required fields only when index is being updated via edit (not enable/disable)
            if "index" in payload:
                self._validate_required_fields(payload)

            # Get existing config for disabled state comparison
            original_disabled = False
            try:
                existing_stanza = self._get_conf().get(row_name)  # type: ignore[union-attr]
                if existing_stanza:
                    original_disabled = str_to_boolean(existing_stanza.get("disabled"))
            except Exception:
                pass

            # Handle disabled state change via enable/disable endpoint
            new_disabled = str_to_boolean(payload.get("disabled", original_disabled))
            if "disabled" in payload and original_disabled != new_disabled:
                try:
                    self._apply_disabled_to_hec(row_name, new_disabled)
                except Exception as e:
                    status_code, user_message = self._parse_http_error(e)
                    logger.error(f"Failed to update enabled/disabled state for '{row_name}': {e}")
                    raise RestError(status_code, f"Failed to update enabled/disabled state: {user_message}")

            # Update HEC fields (index, description)
            hec_update = self._build_hec_update_payload(payload)
            if hec_update:
                try:
                    make_splunk_request(
                        method="POST",
                        endpoint=hec_item_path(row_name),
                        session_key=self.getSessionKey(),
                        data=hec_update,
                        use_json_output=False,
                        addon_namespace=True,
                    )
                except Exception as e:
                    status_code, user_message = self._parse_http_error(e)
                    logger.error(f"Failed to update HEC configuration for '{row_name}': {e}")
                    raise RestError(status_code, f"Failed to update HEC configuration: {user_message}")

            # Get updated HEC state
            hec_content = self._get_hec_content(row_name)
            if not hec_content:
                raise RestError(404, f"HEC token '{row_name}' not found after update.")

            # Prepare payload for UCC config (sync editable fields from HEC)
            # Note: Set disabled to None so parent handleEdit calls update() instead of enable/disable
            # The enable/disable is already handled by _apply_disabled_to_hec above
            payload["index"] = hec_content.get("index", payload.get("index"))
            payload["description"] = hec_content.get("description", payload.get("description"))
            payload["disabled"] = None  # Force parent to call update() not enable/disable
            # Do NOT include 'name' in payload - it causes 409 conflict in UCC framework
            payload.pop("name", None)
            self.payload = payload

            # Save to UCC config
            AdminExternalHandler.handleEdit(self, confInfo)
            
            # Update disabled field in conf after the edit (since we set it to None above)
            try:
                conf = self._get_conf()
                if conf:
                    actual_disabled = str_to_boolean(hec_content.get("disabled", False))
                    conf.update(row_name, {"disabled": actual_disabled})
            except Exception as e:
                logger.error(f"Failed to update disabled state in config for '{row_name}': {e}")

            # Sync stanza with HEC response for UI           
            if row_name in confInfo:
                try:
                    self._sync_stanza_from_hec(confInfo[row_name], hec_content )
                except RestError as e:
                    logger.error(f"Failed to sync HEC stanza '{row_name}' after edit: {e.message}")
                    raise
            
            send_ui_notification(self.getSessionKey(), f"HEC Token '{row_name}' updated successfully")

        except RestError:
            if row_name:
                send_ui_notification(self.getSessionKey(), f"Failed to update HEC Token '{row_name}'")
            raise
        except Exception as e:
            if row_name:
                logger.error(f"Unexpected error editing HEC token '{row_name}': {e}")
                send_ui_notification(self.getSessionKey(), f"Failed to update HEC Token '{row_name}'")
            raise RestError(500, f"Failed to update HEC token: {str(e)[:100]}")

    def handleRemove(self, confInfo):
        """Delete HEC input and remove from configuration."""
        row_name = ""
        try:
            row_name = str(self.callerArgs.id or "").strip()
            if not row_name:
                raise RestError(400, "Missing stanza identifier for remove operation.")

            # Delete HEC input from Splunk
            # A 404 means the token is already gone — treat as idempotent and continue cleanup.
            hec_already_deleted = False
            try:
                make_splunk_request(
                    method="DELETE",
                    endpoint=hec_item_path_single(row_name),
                    session_key=self.getSessionKey(),
                    data=None,
                    use_json_output=False,
                    addon_namespace=True,
                )
            except Exception as e:
                status_code, user_message = self._parse_http_error(e)
                if status_code == 404:
                    logger.info(f"HEC token '{row_name}' already deleted, continuing config cleanup.")
                    hec_already_deleted = True
                else:
                    logger.error(f"Failed to delete HEC token '{row_name}': {e}")
                    raise RestError(status_code, f"Failed to delete HEC token: {user_message}")

            # Remove from UCC config
            AdminExternalHandler.handleRemove(self, confInfo)

            if hec_already_deleted:
                send_ui_notification(self.getSessionKey(), f"Configuration for '{row_name}' removed (HEC token was already deleted)")
            else:
                send_ui_notification(self.getSessionKey(), f"HEC Token '{row_name}' deleted successfully")

        except RestError:
            if row_name:
                send_ui_notification(self.getSessionKey(), f"Failed to delete HEC Token '{row_name}'")
            raise
        except Exception as e:
            logger.error(f"Unexpected error removing HEC token '{row_name}': {e}")
            if row_name:
                send_ui_notification(self.getSessionKey(), f"Failed to delete HEC Token '{row_name}'")
            raise RestError(500, f"Failed to delete HEC token: {str(e)[:100]}")