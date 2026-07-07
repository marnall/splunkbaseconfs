import json
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from urllib.parse import urlsplit

from audit_http_client import AuditHttpClient
from aws_credentials_provider import AwsCredentialsProvider
from get_audits_response import GetAuditsResponse
from integration_handler_utils import _get_proxy_config
from logging_setup import setup_logging
from migrations import MigrationManager
from splunk_kv_store_db_services import SplunkKVStoreDBServices, UserConfiguration
from splunk_secrets_manager import SplunkSecretsManager
from splunklib import client
from splunklib.client import Service
from splunklib.modularinput import Argument, Event, EventWriter, InputDefinition, Scheme, Script, ValidationDefinition

APP_NAME = 'cyberark_audit_linux_x86_64'

logger = setup_logging(app_name=APP_NAME)


class CyberArkAuditScript(Script):

    def __init__(self):
        super().__init__()
        self._service = None
        self._input_definition = None
        self._running = True

        self._kv_store = None
        self._secrets_manager = None
        self._integration_clients = {}
        self._ew_lock = threading.Lock()

    REFRESH_TIME_SECONDS = 60
    MAX_WORKERS = 5
    MAX_PAGES_PER_CYCLE = 25
    SESSION_KEY_INPUT = 'session_key'
    SERVER_KEY_INPUT = 'server_uri'

    @property
    def service(self) -> Service | None:
        """ Returns a Splunk service object for this script invocation.
        The service object is created using the session key
        passed to the command invocation on the modular input stream. It is
        available as soon as the :code:`Script.stream_events` method is
        called.
        We are overriding the base Script service property as we are using in addition
        the app parameter which is used as namespace for the splunk services being
        used by the Service object
        :return: :class:`splunklib.client.Service`. A value of None is returned,
            if you call this method before the :code:`Script.stream_events` method
            is called.
        """
        try:
            if self._service is not None:
                return self._service

            if self._input_definition is None:
                return None

            session_key = self._input_definition.metadata[self.SESSION_KEY_INPUT]
            splunkd_uri = self._input_definition.metadata[self.SERVER_KEY_INPUT]
            if not session_key or not splunkd_uri:
                logger.error('Missing session_key or server_uri in metadata')
                return None

            splunkd = urlsplit(splunkd_uri, allow_fragments=False)
            self._service = self._create_splunk_service(session_key, splunkd)

            return self._service
        except Exception as e:
            logger.error(f'Failed to create Splunk service: {e}', exc_info=True)
            return None

    @property
    def kv_store(self):
        """Lazy-loaded KV store instance (reused across all integrations)"""
        if self._kv_store is None:
            self._kv_store = SplunkKVStoreDBServices(service=self.service, logger=logger, app_name=APP_NAME)
        return self._kv_store

    @property
    def secrets_manager(self):
        """Lazy-loaded secrets manager instance (reused across all integrations)"""
        if self._secrets_manager is None:
            self._secrets_manager = SplunkSecretsManager(service=self.service, logger=logger)
        return self._secrets_manager

    def _get_or_create_integration_client(self, config: UserConfiguration) -> AuditHttpClient:
        """Get cached HTTP client or create new one for the device"""
        device_name = config.device_name

        # Return cached client if exists and config hasn't changed
        if device_name in self._integration_clients:
            cached_client = self._integration_clients[device_name]
            if (cached_client.api_endpoint == config.api_endpoint and cached_client.services_filter == config.services_filter):
                logger.debug(f'Reusing cached client for device: {device_name}')
                return cached_client
            logger.info(f'Configuration changed for device: {device_name}, recreating client')

        # Client does not exist or config changed — create a new client
        current_proxy_config = _get_proxy_config(self.kv_store, self.secrets_manager, logger)
        audit_client = self._create_integration_client(device_name, config, current_proxy_config)

        # Cache the client
        self._integration_clients[device_name] = audit_client
        return audit_client

    def _create_integration_client(self, device_name: str, config: UserConfiguration, proxy_config: dict) -> AuditHttpClient:
        logger.info(f'Creating new client for device: {device_name}')

        certificate = self.secrets_manager.get_secret(secret_name=f'cert_{device_name}')
        private_key = self.secrets_manager.get_secret(secret_name=f'pkey_{device_name}')

        credentials_provider = AwsCredentialsProvider(aws_region=config.api_region, auth_endpoint=config.auth_endpoint,
                                                      device_name=device_name, certificate=certificate, private_key=private_key,
                                                      proxy_config=proxy_config, logger=logger)

        audit_client = AuditHttpClient(credentials_provider=credentials_provider, api_endpoint=config.api_endpoint, device_name=device_name,
                                       initial_minutes_back_start=config.initial_minutes_back_start, services_filter=config.services_filter,
                                       page_size=config.page_size, logger=logger, proxy_config=proxy_config)

        return audit_client

    def get_scheme(self):
        """When Splunk starts, it looks for all the modular inputs defined by
        its configuration, and tries to run them with the argument --scheme.
        Splunkd expects the modular inputs to print a description of the
        input in XML on stdout. The modular input framework takes care of all
        the details of formatting XML and printing it. The user need only
        override get_scheme and return a new Scheme object.

        :return: scheme, a Scheme object
        """
        scheme = Scheme('CyberArk Audit for Splunk')
        scheme.description = '⚠️ WARNING: Do not configure here. This input is managed automatically. Go to: CyberArk Audit App → Integration Dashboard to manage integrations.'
        scheme.use_external_validation = False
        scheme.use_single_instance = True

        # No arguments - configuration via UI only
        return scheme

    def _is_app_configured(self):
        """Check if the app has been marked as configured."""
        try:
            if self.service is None:
                logger.warning('Service not initialized - app configuration check skipped')
                return False
            apps = self.service.apps
            app = apps[APP_NAME]
            configured = app.content.get('configured', '0')
            is_configured = configured in ('1', 'true', True)

            logger.debug(f'App configured status: {is_configured}')
            return is_configured

        except Exception as e:
            # Log the actual error but don't crash
            logger.error(f'Failed to check app configuration status: {e}')
            # Return False so the cycle completes and sleeps before retry
            return False

    def stream_events(self, inputs: InputDefinition, ew: EventWriter):
        """This function handles all the action: splunk calls this modular input
        without arguments, streams XML describing the inputs to stdin, and waits
        for XML on stdout describing events.
        If you set use_single_instance to True on the scheme in get_scheme, it
        will pass all the instances of this input to a single instance of this
        script.
        :param inputs: an InputDefinition object
        :param ew: an EventWriter object
        """
        self._input_definition = inputs

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        logger.info('=== STREAM_EVENTS STARTED ===')
        process_count = 0

        # Check and run migrations using KV Store metadata as source of truth
        self._check_and_run_migrations()

        while self._running:
            process_count += 1
            self._run_collection_cycle(process_count, ew)
            if self._running:
                time.sleep(self.REFRESH_TIME_SECONDS)

        logger.info('=== STREAM_EVENTS STOPPED SUCCESSFULLY ===')

    def _check_and_run_migrations(self) -> None:
        """
        Check and run migrations if needed (1.x -> 2.x upgrade).
        Uses KV Store metadata as the single source of truth for migration state.
        """
        try:
            migration_manager = MigrationManager(kv_store=self.kv_store, secret_manager=self.secrets_manager, logger=logger,
                                                 app_name=APP_NAME)
            migration_manager.run_migration()
        except Exception as e:
            logger.error(f'Migration check failed: {str(e)}', exc_info=True)

    def _setup_signal_handlers(self):

        def signal_handler(signum, frame):
            logger.info(f'Received signal {signum}, initiating shutdown...')
            self._running = False

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _run_collection_cycle(self, process_count, ew):
        """Execute a single collection cycle"""
        process_start = time.time()

        try:
            # Check configuration and get integrations
            user_configs = self._get_enabled_integrations()

            if user_configs is None:
                logger.info('Skipping this cycle - no enabled integrations or app not configured')
            else:
                # Process all integrations
                total_events = self._process_all_integrations(user_configs, ew)

                # Log results
                elapsed = time.time() - process_start
                logger.info(f'Total events collected: {total_events}, Execution time: {elapsed:.2f} seconds')

        except Exception as exp:
            elapsed = time.time() - process_start
            logger.error(f'Process #{process_count} FAILED after {elapsed:.2f}s: {exp}', exc_info=True)

    def _get_enabled_integrations(self) -> list[UserConfiguration] | None:
        """Get enabled integrations (using cached KV store)"""
        if not self._is_app_configured():
            logger.warning('App not configured - skipping this cycle')
            return None

        logger.info('App is configured - proceeding with event collection')
        user_configs = self.kv_store.get_all_user_configs(enabled_only=True)
        logger.info(f'Found {len(user_configs)} enabled integration(s)')

        if not user_configs:
            return None

        return user_configs

    def _process_all_integrations(self, user_configs: list[UserConfiguration], ew) -> int:
        """Process all integrations concurrently, returns total event count.

        Each integration runs in its own worker thread. Per-tenant work is network-bound
        (AWS IoT + CyberArk Audit API), so threads provide near-linear speedup with the GIL
        released during socket IO. Failures in one integration do not affect the others.
        """
        total_events = 0

        if not user_configs:
            return total_events

        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS, thread_name_prefix='cyberark-audit') as executor:
            future_to_device = {executor.submit(self._process_integration, cfg, ew): cfg.device_name for cfg in user_configs}
            for future in as_completed(future_to_device):
                device_name = future_to_device[future]
                try:
                    events_count = future.result()
                    total_events += events_count
                    logger.info(f"Integration '{device_name}': {events_count} events")
                except Exception as exp:
                    logger.error(f"Integration '{device_name}' failed: {exp}", exc_info=True)

        return total_events

    def _process_integration(self, config: UserConfiguration, ew: EventWriter) -> int:
        """Process a single integration and return total event count for this cycle.

        Drains pages back-to-back as long as the API returns a ``paging.cursors.after`` cursor,
        without waiting between pages. Bounded by ``MAX_PAGES_PER_CYCLE`` for safety so a
        misbehaving API cannot loop forever; remaining backlog is picked up on the next cycle
        from the saved checkpoint. The ``self._running`` flag is checked between pages so
        shutdown signals (SIGTERM/SIGINT) are honored within one page round-trip.
        Checkpoint is persisted after each page is written for crash-safe resume.
        """
        device_name = config.device_name

        try:
            audit_client = self._get_or_create_integration_client(config)
            checkpoint = self.kv_store.get_user_checkpoint(device_name)
            total_events = 0
            pages_fetched = 0

            for page_num in range(self.MAX_PAGES_PER_CYCLE):
                if not self._running:
                    logger.info(f"Shutdown requested, stopping drain for '{device_name}' "
                                f'after {pages_fetched} page(s)')
                    break

                response = self._fetch_events(audit_client, config, checkpoint)
                total_events += self._write_events(response, config, ew)
                pages_fetched += 1

                next_cursor = response.paging.cursors.after if response.paging else None
                if not next_cursor:
                    logger.info(f"Tenant '{device_name}' caught up after {pages_fetched} page(s)")
                    break

                self.kv_store.update_user_checkpoint(device_name, next_cursor)
                checkpoint = next_cursor
                logger.debug(f"Tenant '{device_name}' drained page {page_num + 1}, more data available")
            else:
                logger.warning(f"Tenant '{device_name}' hit MAX_PAGES_PER_CYCLE="
                               f'{self.MAX_PAGES_PER_CYCLE}; remaining backlog will resume on next cycle')

            return total_events

        except Exception as exp:
            logger.error(f"Failed to process integration '{device_name}': {exp}", exc_info=True)
            raise

    @staticmethod
    def _fetch_events(audit_client: AuditHttpClient, config: UserConfiguration, checkpoint: str) -> GetAuditsResponse:
        """Fetch events from API, either resuming from checkpoint or starting fresh"""
        device_name = config.device_name

        if checkpoint:
            logger.info(f'Resuming from checkpoint for device: {device_name}')
            return audit_client.get_next_audits_page(checkpoint)

        logger.info(f'Starting initial fetch for device: {device_name} '
                    f'(going back {config.initial_minutes_back_start} minutes)')
        return audit_client.get_initial_audits_page()

    def _write_events(self, response, config: UserConfiguration, ew: EventWriter) -> int:
        """Write events to Splunk and return event count.

        Acquires ``self._ew_lock`` around each ``ew.write_event`` call so that concurrent
        per-tenant workers cannot interleave bytes on the modular input's stdout XML stream.
        The lock scope is kept tight (one event at a time) so tenants interleave fairly.
        """
        if not response.data:
            logger.info(f'No events in response for device: {config.device_name}')
            return 0

        events_count = len(response.data)

        for event_data in response.data:
            event = Event()
            event.stanza = config.device_name
            event.sourceType = config.sourcetype
            event.index = config.index_name
            event.host = config.host
            event.data = json.dumps(event_data)
            with self._ew_lock:
                ew.write_event(event)

        logger.debug(f'Written {events_count} events to index "{config.index_name}" '
                     f'for device: {config.device_name}')
        return events_count

    def _update_checkpoint(self, device_name: str, response: GetAuditsResponse) -> None:
        """Update checkpoint if next page is available"""
        if not (response.paging and response.paging.cursors.after):
            logger.info(f'No more pages available for device: {device_name}')
            return

        new_cursor = response.paging.cursors.after
        self.kv_store.update_user_checkpoint(device_name, new_cursor)
        logger.info(f'Updated checkpoint for device: {device_name}')

    @staticmethod
    def _create_splunk_service(session_key, splunkd):
        """Create a Splunk service instance."""
        return client.connect(
            token=session_key,
            app=APP_NAME,
            scheme=splunkd.scheme,
            host=splunkd.hostname,
            port=splunkd.port,
        )


if __name__ == '__main__':
    sys.exit(CyberArkAuditScript().run(sys.argv))
