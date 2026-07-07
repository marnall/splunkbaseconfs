"""OCSF CIM Addon REST Handler for Sourcetype Configuration.

This module provides a Splunk REST handler for managing OCSF-CIM TA sourcetype configuration.
The handler allows administrators to configure which sourcetypes should be processed with OCSF to CIM mappings.

The REST handler supports three main operations:
    - LIST: Retrieve current sourcetype configuration
    - CREATE: Update sourcetype configuration with new values
    - RELOAD: Regenerate props.conf stanzas and macros based on current configuration

Security Features:
    - Admin-only access control via restmap.conf configuration
    - Comprehensive audit logging with user attribution for all operations
    - Input validation and error handling with detailed logging
    - Secure session key management for Splunk API interactions

Example Usage:
    GET /services/ocsf-cim/ocsf-sourcetypes
    POST /services/ocsf-cim/ocsf-sourcetypes -d "name=test-config&sourcetypes=test"
    POST /services/ocsf-cim/ocsf-sourcetypes/_reload

Attributes:
    ADDON_CONFIG (str): Configuration file name for the addon
    ADDON_ID (str): Splunk app identifier
    logger (logging.Logger): Module-specific logger for audit trails
"""
import os
import sys
import logging


from splunk import admin
import splunk

sys.path.append(
    os.path.join(os.path.dirname(__file__), "..", "lib")
)  # noqa: F401 isort: skip

# pylint: disable=wrong-import-position
import splunklib.client
from splunk.clilib import cli_common as cli

ADDON_CONFIG = "ocsf_cim_addon_for_splunk"
ADDON_ID = "ocsf_cim_addon_for_splunk"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class OCSFSourcetypesConfig(admin.MConfigHandler):
    """REST handler for OCSF-CIM TA sourcetype configuration management.

    This class extends Splunk's MConfigHandler to provide a REST API for managing
    OCSF-CIM TA sourcetype configurations. It handles the dynamic creation and updating
    of props.conf stanzas and macros based on user-specified sourcetypes.

    The handler enforces admin-level access control and provides audit logging for all
    configuration changes, including user attribution, operation details, and success/failure status.

    Attributes:
        handledActions (list): Supported REST actions (LIST, CREATE, RELOAD)

    Example:
        GET /services/ocsf-cim/ocsf-sourcetypes
        POST /services/ocsf-cim/ocsf-sourcetypes -d "name=test-config&sourcetypes=test"
        POST /services/ocsf-cim/ocsf-sourcetypes/_reload
    """

    handledActions = [admin.ACTION_LIST, admin.ACTION_CREATE, admin.ACTION_RELOAD]

    def __init__(self, scriptMode, ctxInfo, request=None):
        """Initialize the REST handler with Splunk context."""
        super().__init__(scriptMode, ctxInfo, request)

    def setup(self):
        """Validate requested action and configure required arguments."""
        if self.requestedAction not in self.handledActions:
            raise admin.BadActionException(
                f"This handler does not support this action ({self.requestedAction})."
            )
        if self.requestedAction == admin.ACTION_CREATE:
            self.supportedArgs.addReqArg("sourcetypes")

    def handleList(self, confInfo):
        """Handle LIST action to retrieve current OCSF sourcetype configuration.

        This method processes GET requests to the REST endpoint and returns the current
        list of sourcetypes configured for OCSF-CIM processing. It reads the configuration
        from the addon's config file and populates the response with each configured sourcetype.

        Args:
            confInfo (splunk.admin.ConfigInfo): Splunk configuration info object to populate
                with response data. Each sourcetype is added as a separate entry.

        Example Response:
            GET /services/ocsf-cim/ocsf-sourcetypes returns configured sourcetypes
        """
        # Log the LIST action with user context
        user = self.userName or "unknown"
        logger.info("[OCSF-CIM] Action=LIST started: user=%s action=list", user)

        try:
            parsed_sourcetypes = self._read_sourcetypes()

            for sourcetype in parsed_sourcetypes:
                confInfo[sourcetype].append("text", sourcetype)

            logger.info(
                "[OCSF-CIM] Action=LIST completed: user=%s sourcetypes_count=%d",
                user,
                len(parsed_sourcetypes),
            )
        except Exception as e:
            logger.error(
                "[OCSF-CIM] Action=LIST failed: user=%s error=%s", user, str(e)
            )
            raise

    def handleCreate(self, confInfo):
        """Handle CREATE action to update OCSF sourcetype configuration.

        This method processes POST requests to update the list of sourcetypes that should
        be processed with OCSF-CIM mappings. It updates the addon's configuration file
        with the new sourcetype list and automatically triggers a reload to regenerate
        the corresponding props.conf stanzas and macros. The method enforces admin-level access control.

        Args:
            confInfo (splunk.admin.ConfigInfo): Splunk configuration info object (not used
                in this implementation but required by the interface)

        Example Usage:
            POST /services/ocsf-cim/ocsf-sourcetypes -d "name=config&sourcetypes=syslog,windows"
        """
        # Get user context and request details for audit logging
        user = self.userName or "unknown"
        data = self.callerArgs.data

        logger.info("[OCSF-CIM] Action=CREATE started: user=%s action=create", user)

        try:
            # Trigger reload handler
            self.shouldReload = True

            service = self._get_client()

            # Parse new sourcetypes
            sourcetypes = data.get("sourcetypes")
            sourcetypes_str = ",".join(sourcetypes)

            # Update configuration
            addon_config = service.confs[ADDON_CONFIG]
            addon_config["general"].update(**{"ocsf_sourcetypes": sourcetypes_str})

            logger.info(
                "[OCSF-CIM] Action=CREATE completed: user=%s sourcetypes_updated=%s",
                user,
                sourcetypes_str,
            )

            # Response
            self.handleReload()

        except Exception as e:
            logger.error(
                "[OCSF-CIM] Action=CREATE failed: user=%s error=%s",
                user,
                str(e),
            )
            raise

    def handleReload(self, confInfo=None):
        """Handle RELOAD action to regenerate props.conf stanzas and macros.

        This method is the core processing engine that regenerates Splunk configuration
        based on the current sourcetype settings.

        The method endpoint is not exposed in the UI and is only automatically triggered by
        handleCreate(). The method enforces admin-level access control.

        Args:
            confInfo (splunk.admin.ConfigInfo, optional): Splunk configuration info object
                (not used in this implementation but required by the interface)

        Example Usage:
            POST /services/ocsf-cim/ocsf-sourcetypes/_reload
        """
        # Log reload action with user context
        user = self.userName or "unknown"
        logger.info("[OCSF-CIM] Action=RELOAD started: user=%s action=reload", user)

        try:
            service = self._get_client()
            sourcetypes = self._read_sourcetypes()

            logger.info(
                "[OCSF-CIM] Action=RELOAD processing: user=%s sourcetypes=%s",
                user,
                sourcetypes,
            )

            # Update Macro
            clauses = [f"sourcetype={s}" for s in sourcetypes] + ["sourcetype=_ocsf"]
            macro_definition = "(" + " OR ".join(clauses) + ")"
            service.confs["macros"]["ocsf_sourcetypes"].update(
                **{"definition": macro_definition}
            )

            # Update Stanzas
            stanza_keys = self._get_ocsf_stanza(service)
            self._clear_local_props(service)

            if len(sourcetypes) == 0 or (
                len(sourcetypes) == 1 and sourcetypes[0] == ""
            ):
                logger.info(
                    "[OCSF-CIM] Action=RELOAD: user=%s no_sourcetypes_configured", user
                )
                return

            props_created = 0

            for sourcetype in sourcetypes:
                try:
                    stanza = (
                        service.confs["props"]
                        .create(sourcetype, app=ADDON_ID, sharing="app")
                        .refresh()
                    )
                    res = stanza.update(**stanza_keys)
                    props_created += 1
                    logger.debug(
                        "[OCSF-CIM] Action=RELOAD: user=%s created_props_stanza=%s",
                        user,
                        sourcetype,
                    )
                except Exception as exc:
                    service.confs["props"][sourcetype].update(**stanza_keys)
                    logger.debug(
                        "[OCSF-CIM] Action=RELOAD: user=%s updated_props_stanza=%s",
                        user,
                        sourcetype,
                    )

            self._reload_endpoint("/services/configs/conf-props/")
            self._reload_endpoint("/services/configs/conf-macros/")

            logger.info(
                "[OCSF-CIM] Action=RELOAD completed: user=%s props_created=%d macro_updated=true",
                user,
                props_created,
            )

        except Exception as e:
            logger.error(
                "[OCSF-CIM] Action=RELOAD failed: user=%s error=%s", user, str(e)
            )
            raise

    def _read_sourcetypes(self):
        """Read the ocsf_sourcetypes configuration from the addon's configuration.

        Returns:
            list: List of sourcetypes from the addon's configuration, empty list if not set

        Note:
            The ocsf_sourcetypes configuration is a comma-separated list of sourcetypes.
        """
        addon_config = self.readConf(ADDON_CONFIG)
        if addon_config:
            raw_sourcetypes = addon_config["general"]["ocsf_sourcetypes"]
            return raw_sourcetypes.split(",")
        return []

    def _get_ocsf_stanza(self, service):
        """Get the ocsf stanza from the props.conf configuration.

        Returns:
            dict: Dictionary of key-value pairs from the ocsf stanza, empty dictionary if not found

        Note:
            The ocsf stanza contains the configuration for the ocsf sourcetype.
        """
        eval_stanzas = {}

        for key, value in service.confs["props"]["_ocsf"].content.items():
            if key.lower().startswith("eval-") or key.lower().startswith("fieldalias-"):
                eval_stanzas[key] = value

        return eval_stanzas

    def _get_client(self):
        """Get a Splunk client instance for API operations.

        Returns:
            splunklib.client.Service: Splunk client instance for API operations

        Note:
            The client instance is used to perform API operations on the Splunk instance.
        """
        return splunklib.client.connect(
            app=ADDON_ID, token=self.getSessionKey(), sharing="app"
        )

    def _clear_local_props(self, service):
        """Clear local props.conf stanzas that were previously created by this handler.

        This method removes props.conf stanzas from the local directory that were
        created by previous runs of this handler. It provides detailed logging
        of the clearing process including success/failure counts.

        Args:
            service (splunklib.client.Service): Splunk service instance for API operations

        Logs:
            - INFO: Summary of stanzas to clear and final counts
            - DEBUG: Individual stanza clearing operations and failures
        """
        user = self.userName or "unknown"
        stanzas = self._get_local_defined_stanzas()

        logger.info(
            "[OCSF-CIM] clearing local props: user=%s stanzas_to_clear=%s",
            user,
            stanzas,
        )

        cleared_count = 0
        failed_count = 0

        for stanza in stanzas:
            try:
                service.confs["props"].delete(stanza)
                cleared_count += 1
                logger.debug(
                    "[OCSF-CIM] cleared props stanza: user=%s stanza=%s", user, stanza
                )
            except Exception as exc:
                # If we can't delete, it may be gone already
                failed_count += 1
                logger.debug(
                    "[OCSF-CIM] failed to clear props stanza: user=%s stanza=%s error=%s",
                    user,
                    stanza,
                    str(exc),
                )

        logger.info(
            "[OCSF-CIM] local props cleared: user=%s cleared=%d failed=%d",
            user,
            cleared_count,
            failed_count,
        )

    def _get_local_defined_stanzas(self):
        """Get local props.conf stanzas defined in the addon's local directory.

        Reads the local props.conf file to identify stanzas that were created
        by this handler and need to be managed (cleared/updated).

        Returns:
            list: List of stanza names from local props.conf, empty list if file doesn't exist

        Note:
            The local directory contains user-specific or runtime-generated configurations
            that override the default configurations in the default directory.
        """
        app_dir = os.path.dirname(os.path.dirname(__file__))
        local_props_path = os.path.join(app_dir, "local", "props.conf")

        if os.path.exists(local_props_path):
            local_props = cli.readConfFile(local_props_path)
            return [name for name in local_props]

        return []

    def _reload_endpoint(self, endpoint):
        """Reload a Splunk configuration endpoint to apply changes.

        This method triggers a reload of Splunk configuration endpoints (like props.conf
        or macros.conf) to ensure that changes made via the API are immediately applied
        without requiring a full Splunk restart.

        Args:
            endpoint (str): Splunk REST endpoint path (e.g., "/services/configs/conf-props/")

        Raises:
            Exception: If the endpoint reload fails
        """
        splunk.rest.simpleRequest(
            "%s/_reload" % endpoint,
            method="POST",
            postargs=dict(),
            sessionKey=self.getSessionKey(),
        )


admin.init(OCSFSourcetypesConfig, admin.CONTEXT_NONE)
