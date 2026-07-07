"""
(C) 2020 Splunk Inc. All rights reserved.

Modular input to migrate data from pre-splexit splapp into the SplunkTV companion app
"""

import sys
from http import HTTPStatus
from typing import List, Type
import os
from dataclasses import asdict

import json
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'splunk_app_tv', 'lib']))
from splunk import rest
from solnlib import modular_input
from secure_gateway_sdk.services import kvstore_service as kvstore
from secure_gateway_sdk.util.splunk_utils import modular_input_utils
from splunk_tv.util.logging import get_logger
from splunk_tv.models.models import DroneModeTvConfig, DroneModeIPad, TVBookmark, CollectionModel, DashboardGroup
from splunk_tv.util import constants

os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

class DataMigrationModularInput(modular_input.ModularInput):
    """
    Modular Input to initialize companion app with Splunk Secure Gateway
    """
    title = 'Data Migration Modular Input'
    description = 'Migrates data from Cloudgateway app to SplunkTV app'
    app = 'splunk_app_tv'
    name = 'splunk_tv_data_migration_modular_input'
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    logger = get_logger(logger_name=f'{name}.app')
    rest_uri = rest.makeSplunkdUri()
    cloudgateway_url = f'{rest_uri}services/apps/local/{constants.LEGACY_SPLAPP_APP_NAME}'
    models_to_process = [DroneModeTvConfig, DroneModeIPad, TVBookmark, DashboardGroup]

    def __init__(self):
        super(DataMigrationModularInput, self).__init__()
        self.disabled_on_start = False

    def do_run(self, input_config):
        if not modular_input_utils.modular_input_should_run(self.session_key, self.logger):
            self.logger.debug("SplunkTV data migration will not run")
            return

        self.logger.debug('Starting SplunkTV data migration')
        try:
            kvstore.wait_until_ready(session_key=self.session_key)
            users = self.get_all_users()
            if not self.should_run(users=users):
                return
            if self.disabled_on_start:
                self.logger.debug('Splunk Cloud Gateway is not enabled. Exiting...')

            for user in users:
                for model in self.models_to_process:
                    self.process_collection(user=user, model=model)
        except TimeoutError as timeout:
            self.logger.exception('Failed to migrate SplunkTV data due to timeout waiting for kvstore: %s', timeout)
            raise timeout
        except Exception as exception:
            self.logger.exception('Unexpected error while migrating SplunkTV data: %s', exception)
            raise exception

        self.logger.debug('Successfully finished SplunkTV data migration')

    def process_collection(self, user: str, model: Type[CollectionModel]):
        """Method which reads data from the collection (described by collection_model) in the splapp namespace
           and copies over the collections records to the new SplunkTV namespace
        """
        records = self.get_collection_records(user=user, model=model, namespace=constants.LEGACY_SPLAPP_APP_NAME)
        if records:
            records = [asdict(record) for record in records]  # Need to write as json, so marshal to dict
            new_kvstore = kvstore.KVStoreCollectionAccessObject(rest_uri=self.rest_uri, owner=user,
                                                                namespace=constants.SPLUNK_TV_APP_NAME,
                                                                collection=model.collection_name,
                                                                logger=self.logger, session_key=self.session_key)
            new_kvstore.insert_multiple_items(items=records)

    def get_collection_records(self, user: str, model: Type[CollectionModel], namespace: str) -> List[CollectionModel]:
        collection_access_obj = kvstore.KVStoreCollectionAccessObject(rest_uri=self.rest_uri, owner=user,
                                                                      namespace=namespace,
                                                                      collection=model.collection_name,
                                                                      logger=self.logger, session_key=self.session_key)
        _, response = collection_access_obj.get_all_items()
        response_body = json.loads(response)
        records = [model.unmarshal(json_obj=record) for record in response_body]
        return records

    def should_run(self, users: List[str]) -> bool:
        # We need to check if the user has the cloudgateway app installed; if not, we just don't migrate
        app_info = self.get_cloudgateway_app()
        if not app_info:
            self.logger.debug('SplunkTV data migration modular input will not run because no previous installation of Splunk Cloud Gateway')
            return False
        if app_info['entry'][0]['content']['disabled']:
            self.disabled_on_start = True


        # We also need to check that for all users, there is no data in the SplunkTV namespace.
        # If there is, then it means that our migration has already succeed, or some users have begun migrating
        # data over, in which case we want to avoid migrating automatically to avoid data duplication problems
        for user in users:
            for model in self.models_to_process:
                record = self.get_collection_records(user=user, model=model, namespace=constants.SPLUNK_TV_APP_NAME)
                if record:
                    self.logger.debug('SplunkTV data migration modular input will not run because there is already tv data')
                    return False
        return True

    def get_all_users(self) -> List[str]:
        get_users_uri = '/services/authentication/users?output_mode=json'
        _, response = rest.simpleRequest(path=get_users_uri, sessionKey=self.session_key, method='GET')
        response_body = json.loads(response)
        users = [user['name'] for user in response_body['entry']]
        users.append(constants.NOBODY)  # nobody is always a user
        return users

    def get_cloudgateway_app(self):
        request_url = self.cloudgateway_url

        response, content = rest.simpleRequest(
            request_url,
            sessionKey=self.session_key,
            method=constants.GET,
            getargs={'output_mode': 'json'},
            rawResult=True
        )
        if response.status != HTTPStatus.OK:
            return None

        return json.loads(content)


if __name__ == '__main__':
    worker = DataMigrationModularInput()
    worker.execute()
