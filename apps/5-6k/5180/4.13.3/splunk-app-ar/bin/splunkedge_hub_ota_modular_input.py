"""
(C) 2023 Splunk Inc. All rights reserved.

"""

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

from typing import List, Dict, Any, Optional

import requests
import semver
import time

from splunkar import constants, kvstore, logging
from splunkar.db import hub as hub_db
from splunkar.kvstore.errors import (
    DocumentAlreadyExists,
    DocumentConflictException,
    DocumentNotFoundException,
    UnknownKVStoreException,
)
from splunkar.model.hub import Hub
from splunkar.model.edge_settings import EdgeSettings
from splunkar.model.hub_service import HubService, HubServiceType
from splunkar.util.modular_input_utils import SplunkARModularInput
from splunkar.util.edge import service_discovery_helper
from splunkar.util.edge import constants as edge_constants
from edge_shared.version import VersionUtil

sys.path.remove(make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

LOGGER = logging.get_logger(__name__)
MINIMUM_OTA_SUPPORTED_VERSION = "2.2.3"


class SplunkEdgeHubOTAModularInput(SplunkARModularInput):
    """Modular input to perform pulse logic for Edge Hub devices"""

    title = 'Edge Hub OTA'
    description = 'Edge Hub OTA'
    app = constants.APP_NAME
    name = 'splunkedge_hub_ota_modular_input'
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def __init__(self, logger):
        super().__init__(logger)

    def run(self) -> None:
        self.logger.debug('Starting Edge Hub OTA Modular Input')

        try:
            manifest = self.get_ota_manifest()
            if not manifest:
                return

            # get list of Hubs
            hubs = self.get_hubs()

            # get if ota is currently enabled
            ota_status = self.get_ota_status()

            # update hub services
            self.update_ota_update_services(ota_update_enabled=ota_status, ota_manifest=manifest)

            # update hubs
            self.clear_version_settings(hubs)
            if ota_status:
                self.set_latest_version(hubs, manifest)

            # save Hubs back to kvstore
            self.save_hubs(hubs)
        except Exception as e:
            self.logger.error(f'Error when running OTA Modular Input: {e}')

    def get_ota_manifest(self) -> Optional[Dict[str, Any]]:
        # Get version manifest
        resp = requests.get(f"{edge_constants.OTA_DOMAIN}/manifest.json")
        if resp.status_code != 200:
            self.logger.error(f'Error retrieving OTA manifest: {resp.status_code} {resp.content}')
            return None

        manifest = resp.json()
        return manifest

    def get_hubs(self) -> List[Hub]:
        hubs = hub_db.load_all_hubs(self.session_key)
        return hubs

    def update_ota_update_services(self, ota_update_enabled: bool, ota_manifest: Dict[str, Any]):
        current_ota_update_services = kvstore.load_many(
            auth_header=self.session_key,
            doctype=HubService,
            query={HubService.SCOPE: edge_constants.DEFAULT_SCOPE, HubService.TYPE: str(HubServiceType.OTA_UPDATE)},
        )
        current_timestamp = round(time.time())
        if len(current_ota_update_services) == 0:
            new_ota_update_service = service_discovery_helper.create_ota_update_service(
                scope=edge_constants.DEFAULT_SCOPE,
                timestamp=str(current_timestamp),
                ota_update_enabled=ota_update_enabled,
                ota_manifest=ota_manifest,
            )
            kvstore.create(auth_header=self.session_key, document=new_ota_update_service)
        else:
            for ota_update_service in current_ota_update_services:
                ota_update_service.ota_settings = service_discovery_helper.get_ota_settings_from_manifest(
                    ota_update_enabled=ota_update_enabled, ota_manifest=ota_manifest
                )
                ota_update_service.timestamp = str(current_timestamp)
                kvstore.update(auth_header=self.session_key, document=ota_update_service)

    def save_hubs(self, hubs: List[Hub]):
        for hub in hubs:
            try:
                hub_db.update_hub(self.session_key, hub)
            except (DocumentNotFoundException, DocumentConflictException, UnknownKVStoreException) as e:
                self.logger.error('Failed to save hub. Error: {}'.format(e))
                continue

    def get_ota_status(self):
        edge_settings = kvstore.load(auth_header=self.session_key, doctype=EdgeSettings, key=EdgeSettings.KEY)
        return edge_settings.ota_update_enabled

    def should_update(self, current, available):
        try:
            cur_version = semver.VersionInfo.parse(current)
        except ValueError as e:
            # if we get an invalid semver string, default to 0.0.0 and have the user
            # manually update the device via the device's webserver.
            # this is happening on stacks with devices with outdated firmware
            LOGGER.info(f"invalid semver of {current}. Defaulting to 0.0.0")
            cur_version = semver.VersionInfo(0, 0, 0)

        # Only devices with current version higher than 1.6.0 should be allowed to update.
        # Not implementing this in edge_shared since logic there is also used in edge hub - it will
        # prevent offline updates from happening if implemented there.
        minimum_ota_supported_version = semver.VersionInfo.parse(MINIMUM_OTA_SUPPORTED_VERSION)
        version_diff = cur_version.compare(minimum_ota_supported_version)
        if version_diff < 0:
            return False

        new_version = semver.VersionInfo.parse(available)
        return VersionUtil.should_allow_update_between(cur_version, new_version)

    def clear_version_settings(self, hubs: List[Hub]):
        for hub in hubs:
            hub.latest_version = None
            hub.update_requested = False

    def set_latest_version(self, hubs: List[Hub], manifest: Dict[str, Any]):
        for hub in hubs:
            if hub.model in manifest:
                latest_version = manifest[hub.model]['version']
                if hub.latest_version != latest_version:
                    hub.latest_version = (
                        latest_version
                        if self.should_update(hub.current_version, latest_version)
                        else hub.current_version
                    )
                    hub.update_requested = False
                self.logger.debug(f"Latest version for Hub {hub.name} is {hub.latest_version}")
            else:
                self.logger.warning(
                    f"Hub {hub.name} with model {hub.model} does not have a corresponding update manifest"
                )
                hub.latest_version = None
                hub.update_requested = False


if __name__ == '__main__':
    m = SplunkEdgeHubOTAModularInput(LOGGER)
    m.execute()
