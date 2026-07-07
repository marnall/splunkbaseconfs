from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from http import HTTPStatus
from logging import Logger
from time import sleep
from typing import Any

from splunklib.binding import HTTPError
from splunklib.client import KVStoreCollection, Service


class KVStoreOp(Enum):
    INSERT_KV = 'INSERT_KV'
    UPDATE_KV = 'UPDATE_KV'
    GET_KV = 'GET_KV'
    DELETE_KV = 'DELETE_KV'
    QUERY_KV = 'QUERY_KV'


class UserConfiguration:
    """Represents a user configuration document"""

    def __init__(
        self,
        device_name: str,
        auth_endpoint: str,
        api_endpoint: str,
        api_region: str,
        services_filter: str,
        initial_minutes_back_start: int,
        page_size: int,
        index_name: str,
        integration_display_name: str,
        host: str,
        sourcetype: str,
        enabled=True,
    ):
        self.device_name = device_name
        self.integration_display_name = integration_display_name
        self.auth_endpoint = auth_endpoint
        self.api_endpoint = api_endpoint
        self.api_region = api_region
        self.services_filter = services_filter
        self.initial_minutes_back_start = initial_minutes_back_start
        self.index_name = index_name
        self.sourcetype = sourcetype
        self.host = host
        self.page_size = page_size
        self.enabled = enabled

    def to_dict(self, created_at: datetime = None) -> dict[str, Any]:
        """Convert to KV store document format"""
        now = datetime.now(timezone.utc).isoformat()
        return {
            '_key': f'user_{self.device_name}',
            'device_name': self.device_name,
            'integration_display_name': self.integration_display_name,
            'auth_endpoint': self.auth_endpoint,
            'api_endpoint': self.api_endpoint,
            'api_region': self.api_region,
            'services_filter': self.services_filter,
            'initial_minutes_back_start': self.initial_minutes_back_start,
            'index_name': self.index_name,
            'sourcetype': self.sourcetype,
            'enabled': self.enabled,
            'host': self.host,
            'page_size': self.page_size,
            'created_at': created_at or now,
            'updated_at': now,
        }

    @staticmethod
    def from_dict(data) -> UserConfiguration:
        """Create from KV store document"""
        return UserConfiguration(
            device_name=data['device_name'],
            auth_endpoint=data['auth_endpoint'],
            integration_display_name=data.get('integration_display_name', ''),
            api_endpoint=data['api_endpoint'],
            api_region=data['api_region'],
            services_filter=data['services_filter'],
            sourcetype=data.get('sourcetype'),
            initial_minutes_back_start=data['initial_minutes_back_start'],
            index_name=data.get('index_name', 'main'),
            host=data.get('host', '$decideOnStartup'),
            page_size=data.get('page_size', '500'),
            enabled=data.get('enabled', True),
        )


class SplunkKVStoreDBServices:
    """Enhanced KV Store service for multi-user support"""

    KV_SERVICE_UNAVAILABLE_SLEEP_TIME = 60
    NUM_OF_RETRY_CHECKS_KV_SERVICE_AVAILABLE = 10

    # Document field names
    KV_DOC_ID_KEY = '_key'
    KV_NEXT_PAGE_CURSOR_KEY = 'next_page_cursor'
    KV_LAST_FETCH_TIME_KEY = 'last_fetch_time'
    KV_DEVICE_NAME_KEY = 'device_name'

    def __init__(self, service: Service, logger: Logger, app_name: str):
        self._logger = logger
        self._service = service

        self.user_config_collection = f'{app_name}_collection'
        self.user_checkpoint_collection = f'{app_name}_checkpoint_collection'
        self.global_config_collection = f'{app_name}_global_proxy_config'

        self._wait_on_kv_store_to_load()

    @property
    def logger(self):
        return self._logger

    @property
    def service(self):
        return self._service

    def create_user_config(self, user_config: UserConfiguration):
        """Create or update a user configuration"""
        try:
            collection = self._get_collection(self.user_config_collection)
            collection.data.insert(data=json.dumps(user_config.to_dict()))
            self.logger.info(f'Created user configuration for device: {user_config.device_name}')

        except Exception as exp:
            self._handle_kv_op_failure(exp=exp, op=KVStoreOp.INSERT_KV)

    def get_user_config(self, device_name: str, raw_data=False) -> UserConfiguration | dict[str, Any] | None:
        """Get a specific user configuration"""
        try:
            collection = self._get_collection(self.user_config_collection)
            doc_id = f'user_{device_name}'
            data = self._get_document_by_id(collection, doc_id)
            if raw_data:
                return data

            if data:
                return UserConfiguration.from_dict(data)
            return None

        except Exception as exp:
            self._handle_kv_op_failure(exp=exp, op=KVStoreOp.GET_KV)
            return None

    def get_all_user_configs(self, enabled_only=True) -> list[UserConfiguration | None]:
        """Get all user configurations"""
        try:
            collection = self._get_collection(self.user_config_collection)
            query = {'enabled': True} if enabled_only else {}
            results = list(collection.data.query(query=json.dumps(query)))
            configs = []
            for doc in results:
                try:
                    configs.append(UserConfiguration.from_dict(doc))
                except Exception as e:
                    self.logger.error(f'Failed to parse doc {doc.get("_key")}: {e}')

            return configs
        except Exception as exp:
            self._handle_kv_op_failure(exp=exp, op=KVStoreOp.QUERY_KV)
            return []

    def delete_user_config(self, device_name: str):
        """Delete a user configuration and its checkpoint"""
        # Validate device_name
        if not device_name or not isinstance(device_name, str):
            raise ValueError('Invalid device name')

        self.logger.info(f'=== DELETE_USER_CONFIG STARTED for device: {device_name} ===')

        try:
            config_collection = self._get_collection(self.user_config_collection)
            config_doc_id = f'user_{device_name}'

            self.logger.info(f'Attempting to delete config document')

            existing = self._get_document_by_id(config_collection, config_doc_id)
            if not existing:
                self.logger.warning(f'Configuration not found for device: {device_name}')
                raise ValueError(f'Configuration not found for device: {device_name}')

            # Use json.dumps for safe query construction
            config_collection.data.delete(query=json.dumps({'_key': config_doc_id}))
            self.logger.info('Successfully deleted configuration document')

            verify = self._get_document_by_id(config_collection, config_doc_id)
            if verify:
                self.logger.error('DELETION FAILED - Document still exists')
                raise Exception('Failed to delete configuration from KV store')

            self.logger.info('Deletion verified - document no longer exists')

            checkpoint_collection = self._get_collection(self.user_checkpoint_collection)
            checkpoint_doc_id = f'checkpoint_{device_name}'

            self.logger.info('Attempting to delete checkpoint document')

            try:
                checkpoint_collection.data.delete(query=json.dumps({'_key': checkpoint_doc_id}))
                self.logger.info('Successfully deleted checkpoint document')
            except Exception as e:
                self.logger.warning(f'Checkpoint not found or already deleted: {str(e)}')

            self.logger.info(f'=== DELETE_USER_CONFIG completed for device: {device_name} ===')

        except Exception as exp:
            self.logger.error(f'DELETE_USER_CONFIG failed: {str(exp)}', exc_info=True)
            raise

    def update_user_checkpoint(self, device_name: str, next_page_cursor: str) -> None:
        """Update checkpoint for a specific user"""
        try:
            collection = self._get_collection(self.user_checkpoint_collection)
            doc_id = f'checkpoint_{device_name}'
            data = {
                self.KV_DOC_ID_KEY: doc_id,
                self.KV_DEVICE_NAME_KEY: device_name,
                self.KV_NEXT_PAGE_CURSOR_KEY: next_page_cursor,
                self.KV_LAST_FETCH_TIME_KEY: datetime.now(timezone.utc).isoformat(),
            }
            existing = self._get_document_by_id(collection, doc_id)

            if existing:
                collection.data.update(id=doc_id, data=json.dumps(data))
            else:
                collection.data.insert(data=json.dumps(data))

        except Exception as exp:
            self._handle_kv_op_failure(exp=exp, op=KVStoreOp.UPDATE_KV)

    def find_duplicate_api_endpoint(self, api_endpoint: str, exclude_device_name=None):
        """
        Check if an API endpoint already exists for a different device.
        """
        try:
            collection = self._get_collection(self.user_config_collection)
            query = {'api_endpoint': api_endpoint}
            results = collection.data.query(query=json.dumps(query))

            for doc in results:
                if exclude_device_name and doc.get('device_name') == exclude_device_name:
                    continue
                return doc

            return None

        except Exception as exp:
            self.logger.warning(f'Error checking for duplicate API endpoint: {str(exp)}')
            return None

    def get_user_checkpoint(self, device_name: str) -> str:
        """Get checkpoint for a specific user"""
        try:
            collection = self._get_collection(self.user_checkpoint_collection)
            doc_id = f'checkpoint_{device_name}'
            data = self._get_document_by_id(collection, doc_id)

            if data:
                return data.get(self.KV_NEXT_PAGE_CURSOR_KEY, '')
            return ''

        except Exception as exp:
            self._handle_kv_op_failure(exp=exp, op=KVStoreOp.GET_KV)
            return ''

    def update_user_config(self, config: UserConfiguration, existing_user) -> None:
        """Update an existing user configuration in KV store."""
        try:
            record_key = existing_user.get(self.KV_DOC_ID_KEY)
            created_at = existing_user.get('created_at')

            collection = self._get_collection(self.user_config_collection)
            collection.data.update(record_key, json.dumps(config.to_dict(created_at=created_at)))
            self.logger.info(f'Updated configuration for device: {config.device_name}')

        except Exception as e:
            self.logger.error(f'Failed to update config for device {config.device_name}: {e}', exc_info=True)
            raise

    # Global proxy config methods
    def get_global_proxy_config(self) -> dict | None:
        """Retrieve the global proxy configuration document (key = 'global_proxy')."""
        try:
            collection = self._get_collection(self.global_config_collection)
            doc = self._get_document_by_id(collection, 'global_proxy')
            return doc
        except Exception as exp:
            self._handle_kv_op_failure(exp=exp, op=KVStoreOp.GET_KV)
            return None

    def save_global_proxy_config(self, proxy_data: dict) -> None:
        """Save a new global proxy configuration document with _key='global_proxy'."""
        try:
            collection = self._get_collection(self.global_config_collection)
            now = datetime.now(timezone.utc).isoformat()
            doc = {
                self.KV_DOC_ID_KEY: 'global_proxy',
                'proxy_enabled': bool(proxy_data.get('proxy_enabled', False)),
                'proxy_host': proxy_data.get('proxy_host'),
                'proxy_port': proxy_data.get('proxy_port'),
                'proxy_verify_ssl': bool(proxy_data.get('proxy_verify_ssl', True)),
                'created_at': now,
                'updated_at': now,
            }
            collection.data.insert(data=json.dumps(doc))
            self.logger.info('Saved global proxy configuration')
        except Exception as exp:
            self._handle_kv_op_failure(exp=exp, op=KVStoreOp.INSERT_KV)
            raise

    def update_global_proxy_config(self, proxy_data: dict) -> None:
        """Update existing global proxy document or create it if missing."""
        try:
            collection = self._get_collection(self.global_config_collection)
            existing = self._get_document_by_id(collection, 'global_proxy')
            now = datetime.now(timezone.utc).isoformat()

            doc = {
                self.KV_DOC_ID_KEY: 'global_proxy',
                'proxy_enabled': bool(proxy_data.get('proxy_enabled', False)),
                'proxy_host': proxy_data.get('proxy_host'),
                'proxy_port': proxy_data.get('proxy_port'),
                'proxy_verify_ssl': bool(proxy_data.get('proxy_verify_ssl', True)),
                'updated_at': now,
            }

            if existing:
                # Preserve created_at if present
                if 'created_at' in existing:
                    doc['created_at'] = existing.get('created_at')
                collection.data.update(id='global_proxy', data=json.dumps(doc))
                self.logger.info('Updated global proxy configuration')
            else:
                doc['created_at'] = now
                collection.data.insert(data=json.dumps(doc))
                self.logger.info('Created global proxy configuration')

        except Exception as exp:
            self._handle_kv_op_failure(exp=exp, op=KVStoreOp.UPDATE_KV)
            raise

    def _get_collection(self, collection_name) -> KVStoreCollection:
        """Get a KV store collection.

        Collections are declared statically in default/collections.conf and
        created by Splunk at app install time on both Enterprise and Cloud.

        If the local kvstore cache returns KeyError, refresh once and retry
        before raising a clear error - this guards against stale client-side
        caches that can briefly miss recently-declared collections.
        """
        try:
            return self.service.kvstore[collection_name]
        except KeyError:
            self.logger.warning(f'Collection {collection_name} not visible in local kvstore cache; '
                                f'refreshing and retrying.')
            try:
                self.service.kvstore.get('')
            except Exception:
                pass
            try:
                return self.service.kvstore[collection_name]
            except KeyError:
                self.logger.error(f'KV store collection {collection_name} does not exist. Verify it is '
                                  f'declared in default/collections.conf and that the app was reloaded '
                                  f'after install/upgrade.')
                raise

    @staticmethod
    def _get_document_by_id(collection, doc_id: str):
        """Get a document by ID, return None if not found"""
        try:
            return collection.data.query_by_id(doc_id)
        except HTTPError as e:
            if e.status == HTTPStatus.NOT_FOUND.value:
                return None
            raise

    def _wait_on_kv_store_to_load(self):
        """Wait for KV store to become available"""
        for attempt in range(self.NUM_OF_RETRY_CHECKS_KV_SERVICE_AVAILABLE):
            try:
                self._verify_kv_store_available()
                break
            except HTTPError as http_error:
                if self._should_retry_kv_op(http_error):
                    self.logger.warning(f'KV Store not ready, retry {attempt + 1}')
                    sleep(self.KV_SERVICE_UNAVAILABLE_SLEEP_TIME)
                    continue
                self._handle_kv_store_load_failure(http_error)
            except Exception as exp:
                self._handle_kv_store_load_failure(exp)

    def _verify_kv_store_available(self):
        """Verify KV store is available by querying existing collection"""
        # Query the pre-defined collection from collections.conf
        collection = self.service.kvstore['cyberark_user_configurations']
        collection.data.query()

    @staticmethod
    def _should_retry_kv_op(http_error):
        """Check if KV operation should be retried"""
        return http_error.status == HTTPStatus.SERVICE_UNAVAILABLE.value

    def _handle_kv_store_load_failure(self, exp):
        """Handle KV store load failure"""
        self.logger.exception(f'KV Store failed loading with exception: {str(exp)}')
        raise exp

    def _handle_kv_op_failure(self, exp, op):
        """Handle KV operation failure"""
        self.logger.exception(f'Failure performing operation {op.value} with exception={str(exp)}')
