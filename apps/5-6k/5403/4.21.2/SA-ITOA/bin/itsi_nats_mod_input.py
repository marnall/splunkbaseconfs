"""
This script will be used as a mod input to enable or disable NATS server
"""
import asyncio
import json
import platform
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import time
import zipfile

import splunk.rest as rest
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import requests
import threading

from ITOA.controller_utils import ITOAError
from ITOA.mod_input_utils import skip_run_during_migration
from ITOA.setup_logging import getLogger4ModInput
import os
from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from SA_ITOA_app_common.solnlib.conf_manager import ConfManager
from ITOA.itoa_common import get_nats_credentials, is_cloud, get_peers
from itsi.itsi_utils import ITOAInterfaceUtils
from itsi.itsi_utils import ItsiMacroReader
from ITOA.itoa_common import is_nats_mod_input_disabled, perform_search
from itsi.itsi_version_compare import VersionComparison
from ITOA.event_management.hec_utils import HECUtil
from ITOA.event_management.push_event_manager import PushEventManager
from ITOA.event_management.itsi_nats_tls_helper import ITSINatsTLSHelper
from ITOA.event_management.itsi_nats_publish import NatsEventPublisher
from ITOA.event_management.notable_event_utils import post_message_to_ui
from ITOA.event_management.itsi_nats_route_monitor import NATSRouteMonitor
from ITOA.storage.itoa_storage import ITOAStorage

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")


class ITSINats(ModularInput):
    title = 'IT Service Intelligence NATS Modular Input'
    description = 'Modular Input to start and stop NATS server for Event Analytics'
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_nats_mod_input'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    owner = 'nobody'
    NATS_VERSION = 'v2.12.4'
    nats_config_path = make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'bin', 'nats', 'nats-js.conf'])
    # Path to nats-unreachable.json file, which is a temporary file used to store unreachable NATS servers
    nats_command = make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'bin', 'nats', 'nats-server'])
    # https://docs.splunk.com/Documentation/Splunk/9.2.0/Installation/Systemrequirements
    SUPPORTED_OS = ['windows', 'linux', 'darwin']
    # Arch types are possible outputs of uname -m or platform.machine()
    # https://en.wikipedia.org/wiki/Uname
    SUPPORTED_ARCH = {
        'arm64': 'arm64',
        'x86_64': 'amd64',
        'amd64': 'amd64',
        'i686': 'amd64',
        'i386': 'amd64'
    }
    enable_rules_engine_in_queue_mode = "| itsichangerulesengineprocess is_disable_all=false is_use_queue_mode=true " \
                                        "is_use_adhoc_search=false is_use_rt_search=false"

    disable_rules_engine_in_queue_mode = "| itsichangerulesengineprocess is_disable_all=false is_use_queue_mode=false " \
                                         "is_use_adhoc_search=false is_use_rt_search=true"
    continue_nats_mod_input = True

    is_shc_enabled = False

    is_auth_enabled = False

    def __init__(self):
        super()
        self.is_license_error_published = False
        self.logger = None
        self.process = None
        self.os = platform.system().lower()
        if self.os == 'windows':
            self.nats_command += '.exe'
            signal.signal(signal.SIGBREAK, self.shutdown_nats)
        signal.signal(signal.SIGINT, self.shutdown_nats)
        signal.signal(signal.SIGTERM, self.shutdown_nats)

    def extra_arguments(self):
        return [{
            'name': "log_level",
            'title': "Logging Level",
            'description': "This is the level at which the modular input will log data."}]

    def get_binary_name(self):
        """
        Finds the right binary name based on OS and arch and returns the binary string name
        @return: name of the binary file
        """
        cfm = ConfManager(self.session_key, 'SA-ITOA')
        conf = cfm.get_conf('itsi_nats')
        settings = conf.get('nats_settings')
        nats_fips_activated = int(settings.get('nats_fips_activated', 1))
        os_architecture_raw = platform.machine().lower()

        if self.os not in self.SUPPORTED_OS:
            raise ITOAError(f'Unsupported OS: {self.os}')

        if os_architecture_raw not in self.SUPPORTED_ARCH:
            raise ITOAError(f'Unsupported architecture: {os_architecture_raw}')

        file_extension = '.zip' if self.os == 'windows' else '.tar.gz'

        if self.is_fips_enabled(self.session_key, self.logger) and nats_fips_activated == 1:
            self.logger.info('FIPS mode is enabled & NATS fips binary config flag is enabled.FIPS binary name will be pickedup')
            binary_name = f'nats-server-{self.NATS_VERSION}-{self.os}-{self.SUPPORTED_ARCH[os_architecture_raw]}-fips{file_extension}'
        elif self.is_fips_enabled(self.session_key, self.logger) and nats_fips_activated == 0:
            self.logger.info('FIPS mode is enabled & NATS fips binary config flag is disabled. Hence enabling real time search')
            perform_search(self.session_key, self.disable_rules_engine_in_queue_mode, self.logger)
            sys.exit(0)
        else:
            binary_name = f'nats-server-{self.NATS_VERSION}-{self.os}-{self.SUPPORTED_ARCH[os_architecture_raw]}{file_extension}'
        self.logger.info(f'Nats binary name: {binary_name}')

        return binary_name

    def cleanup_old_nats_directories(self):
        """
        Delete old NATS extracted directories that are older than the current NATS_VERSION
        """
        try:
            nats_bin_path = make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'bin', 'nats'])
            if not os.path.exists(nats_bin_path):
                self.logger.info('NATS bin directory does not exist, skipping cleanup')
                return
            current_version = self.NATS_VERSION.lstrip('v').split('.')
            current_version_tuple = tuple(int(x) for x in current_version)
            items = os.listdir(nats_bin_path)

            for item in items:
                item_path = os.path.join(nats_bin_path, item)

                # Only process directories that match NATS version pattern
                if not os.path.isdir(item_path):
                    continue
                if not item.startswith('nats-server-v'):
                    continue

                # Extract version from directory name
                try:
                    parts = item.split('-')
                    version_str = None
                    for part in parts:
                        if part.startswith('v') and '.' in part:
                            version_str = part
                            break
                    if not version_str:
                        continue
                    dir_version = version_str.lstrip('v').split('.')
                    dir_version_tuple = tuple(int(x) for x in dir_version)

                    # Compare versions - if directory version is older, delete it
                    if dir_version_tuple < current_version_tuple:
                        shutil.rmtree(item_path)
                        self.logger.info(
                            f'Removed old NATS directory: {item} (version {version_str} < {self.NATS_VERSION})')
                    else:
                        self.logger.info(f'Keeping directory: {item} (version {version_str} >= {self.NATS_VERSION})')

                except (ValueError, IndexError) as e:
                    self.logger.warning(f'Could not parse version from directory name: {item}, skipping. Error: {e}')
                    continue

        except Exception as e:
            self.logger.error(f'Error during cleanup of old NATS directories: {e}')

    def unzip_nats(self):
        """
        Unzips the correct nats binary (.zip for Windows, .tar.gz for other OS) and moves the
        nats-server executable to SA-ITOA/bin/nats/nats-server
        """
        # First check if nats is already unzipped
        nats_binary_zip = self.get_binary_name()
        nats_binary_zip_path = make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'nats', nats_binary_zip])
        self.logger.info(f'Nats binary zip path name: {nats_binary_zip_path}')
        if os.path.isfile(self.nats_command):
            existing_nats_version = self.get_existing_nats_version()
            self.logger.info('Version of the NATS binary to be unzipped : %s', self.NATS_VERSION)
            self.logger.info('Version of the existing NATS binary : %s', existing_nats_version)
            if existing_nats_version == self.NATS_VERSION:
                self.logger.info('Nats is already unzipped! Skipping unzipping step')
                return
            else:
                self.logger.info('A different version of Nats exists. Proceeding with the unzip process')

        if not os.path.isfile(nats_binary_zip_path):
            raise ITOAError(f'Nats binary does not exist: {nats_binary_zip}')

        extract_path = make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'bin', 'nats'])

        # Unzip nats binary based on OS
        if self.os == 'windows':
            # Use zipfile for Windows
            with zipfile.ZipFile(nats_binary_zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            folder_name = nats_binary_zip[:-4]
        else:
            # Use tarfile for Linux/Darwin
            tar = tarfile.open(nats_binary_zip_path, 'r:gz')
            tar.extractall(extract_path)
            tar.close()
            folder_name = nats_binary_zip[:-7]

        # Move nats executable to SA-ITOA/bin folder
        cur_binary_path = make_splunkhome_path(
            ['etc', 'apps', 'SA-ITOA', 'bin', 'nats', folder_name, 'nats-server'])
        if self.os == 'windows':
            cur_binary_path += '.exe'
        os.rename(cur_binary_path, self.nats_command)
        # Clean up old extracted directories before extracting new version
        self.cleanup_old_nats_directories()

    def create_nats_conf_file(self):
        """
        Creates a NATS configuration file for the host OS and arch.
        Writes nats-js.conf to SA-ITOA/bin/nats-js.conf

        """
        cfm = ConfManager(self.session_key, 'SA-ITOA')
        nats_conf = cfm.get_conf('itsi_nats')
        certificates_conf = cfm.get_conf('certificates')
        settings = nats_conf.get('nats_settings')
        certificates_settings = certificates_conf.get('nats_queue')

        max_memory_store = int(settings['max_memory_store'])
        max_file_store = int(settings['max_file_store'])
        max_buffered_msgs = int(settings['max_buffered_msgs'])
        max_buffered_size = int(settings['max_buffered_size'])
        auth_enabled = int(settings['require_auth'])
        self.is_auth_enabled = auth_enabled == 1
        require_tls_client_cert_cloud = int(settings.get('require_tls_client_cert_cloud', 1))
        require_tls_client_cert_on_prem = int(settings.get('require_tls_client_cert_on_prem', 0))
        is_cloud_stack = is_cloud(self.logger, self.session_key)
        tls_enabled = (is_cloud_stack is True and require_tls_client_cert_cloud == 1) or (is_cloud_stack is False and require_tls_client_cert_on_prem == 1)
        host_name = socket.gethostname()
        cert_directory = certificates_settings.get('cert_directory', 'etc/auth/nats')
        ca_cert = certificates_settings.get('ca_cert', 'ca-cert.pem')
        client_cert = certificates_settings.get('client_cert', 'client-cert.pem')
        client_cert_key = certificates_settings.get('client_cert_key', 'client-key.pem')
        store_dir = 'nats/data'
        peers = get_peers(self.logger, self.session_key, socket.gethostname(), False)
        if peers:
            self.is_shc_enabled = True

        conf = {
            'server_name': f'{host_name}-itsi-ea-cluster',
            'listen': 4222,
            'http_port': 8222,
            'debug': False,
            'trace': False,
            'logfile_size_limit': 5242880,
            'logfile_max_num': 5,
            'log_file': f'{SPLUNK_HOME}/var/log/splunk/itsi-nats-server.log'
        }
        tls = {
            'cert_file': f'{SPLUNK_HOME}/{cert_directory}/{client_cert}',
            'key_file': f'{SPLUNK_HOME}/{cert_directory}/{client_cert_key}',
            'ca_file': f'{SPLUNK_HOME}/{cert_directory}/{ca_cert}',
            'verify': True
        }

        if os.path.isfile(self.nats_config_path):
            self.logger.info('nats-js.conf is already created!')
            with open(self.nats_config_path, 'r') as f:
                content = f.read()
            conf = json.loads(content)

            if tls_enabled == 1 and 'tls' not in conf:
                self.logger.info('TLS is enabled and the tls section is not present in nats-js conf')
                conf['tls'] = tls
                if 'cluster' in conf:
                    conf['cluster']['tls'] = tls
            elif tls_enabled == 0 and 'tls' in conf:
                self.logger.info('TLS is disabled but tls section is present in nats-js conf')
                del conf['tls']
                if 'cluster' in conf and 'tls' in conf['cluster']:
                    del conf['cluster']['tls']
            else:
                self.logger.info('nats-js conf file has the correct configuration and no changes are needed')
                return
        else:
            self.logger.info('nats-js.conf is not present, so creating one')

            if self.os == 'windows':
                conf['log_file'] = conf['log_file'].replace('/', '\\')
                tls['cert_file'] = tls['cert_file'].replace('/', '\\')
                tls['key_file'] = tls['key_file'].replace('/', '\\')
                tls['ca_file'] = tls['ca_file'].replace('/', '\\')
                store_dir = store_dir.replace('/', '\\')

            if tls_enabled == 1:
                conf['tls'] = tls

            jetstream = {
                'store_dir': store_dir,
                'max_memory_store': max_memory_store,
                'max_file_store': max_file_store,
                'max_buffered_msgs': max_buffered_msgs,
                'max_buffered_size': max_buffered_size
            }

            # Add a user in default SYSTEM account in NATS
            accounts = {
                "$SYS": {
                    'users': [
                        {
                            'user': 'sys',
                            'pass': ''
                        }
                    ]
                }
            }
            conf['jetstream'] = jetstream
            # for now, disabling accounts support
            conf['accounts'] = accounts

            # get nats credentials from storage/passwords
            passwords_uri = "/services/storage/passwords/nats-admin?output_mode=json"
            credentials = get_nats_credentials(self.session_key, passwords_uri, auth_enabled)

            if self.is_auth_enabled and credentials:
                username = credentials['clear_password'].split(':')[0]
                password = credentials['clear_password'].split(':')[1]
                hash = credentials['clear_password'].split(':')[2]

                authorization = {
                    'ADMIN': {
                        'publish': '>',
                        'subscribe': '>'
                    },
                    'users': [
                        {
                            'user': username,
                            'password': hash,
                            'permissions': str('$ADMIN')
                        }
                    ]
                }
                conf['authorization'] = authorization

            if self.is_shc_enabled:
                if self.is_auth_enabled == 1:
                    cluster = {
                        'name': 'itsi-ea-cluster',
                        'listen': f'{host_name}:4248',
                        'routes': [f'nats://{username}:{password}@{peer}:4248' for peer in peers]
                    }
                else:
                    cluster = {
                        'name': 'itsi-ea-cluster',
                        'listen': f'{host_name}:4248',
                        'routes': [f'nats://{peer}:4248' for peer in peers]
                    }
                if tls_enabled == 1:
                    cluster['tls'] = tls
                conf['cluster'] = cluster

        f = open(self.nats_config_path, 'w')
        f.write(json.dumps(conf))
        f.close

    def is_fips_enabled(self, session_key, logger):
        try:
            response, content = rest.simpleRequest(
                "/services/server/info?output_mode=json",
                sessionKey=session_key,
                method="GET",
                raiseAllErrors=True,
            )
            parsed_content = json.loads(content)
            if parsed_content["entry"][0]["content"]["fips_mode"]:
                logger.info('FIPS mode is enabled')
                return True
            else:
                logger.info('FIPS mode is disabled ')
                return False
        except Exception as e:
            logger.error('Error while fetching server info and fips flag status : %s', str(e))
            return False

    @skip_run_during_migration
    def do_run(self, input_config):
        logger = getLogger4ModInput(input_config)
        self.logger = logger
        cfm = ConfManager(self.session_key, 'SA-ITOA')
        conf = cfm.get_conf('itsi_nats')
        settings = conf.get('nats_settings')
        pulse_frequency = int(settings.get('pulse_frequency', 60))
        require_tls_client_cert_cloud = int(settings.get('require_tls_client_cert_cloud', 1))
        require_tls_client_cert_on_prem = int(settings.get('require_tls_client_cert_on_prem', 0))
        is_cloud_stack = is_cloud(self.logger, self.session_key)
        tls_enabled = (is_cloud_stack is True and require_tls_client_cert_cloud == 1) or (is_cloud_stack is False and require_tls_client_cert_on_prem == 1)
        while self.continue_nats_mod_input:
            is_valid_license = self.is_suite_license_available(logger)
            if is_valid_license and not self.is_migration_pending(logger):
                self.is_license_error_published = False  # Reset license_error_published flag
                # Shutdown existing nats-server instances to make sure output is being captured
                logger.info('Starting ITSI NATS Modular Input')
                try:
                    self.unzip_nats()
                except Exception as e:
                    logger.error(str(e))
                    # start Rules Engine in rt search mode
                    perform_search(self.session_key, self.disable_rules_engine_in_queue_mode, logger)
                    logger.info('Failed to extract nats-server binary. Starting Rules Engine in rt search mode')
                    sys.exit(0)
                self.shutdown_nats(None, None)
                # if TLS is enabled, prepare TLS certificates
                if tls_enabled == 1:
                    ITSINatsTLSHelper(self.session_key, self.logger).prepare_tls_certificates()
                # Create nats conf file
                self.create_nats_conf_file()

                # start Rules Engine in Queue Mode
                perform_search(self.session_key, self.enable_rules_engine_in_queue_mode, logger)
                logger.info('Rules Engine has started in queue mode')
                try:
                    nats_metrics_enabled = int(settings.get('require_nats_metrics', 1))
                    nats_route_monitor_enabled = int(settings.get('enable_nats_route_monitor', 1))
                    if self.os == 'windows':
                        self.create_nats_service_in_windows()
                        bash_command = ['sc.exe', 'start', 'nats-server']
                        subprocess.run(bash_command)
                        time.sleep(5)
                        self.spawn_jetstream_and_metrics_and_routes_threads(nats_metrics_enabled,
                                                                            nats_route_monitor_enabled)
                        while self.is_nats_service_in_windows_running():
                            time.sleep(1)
                    else:
                        bash_command = [self.nats_command, '-c', self.nats_config_path]
                        with subprocess.Popen(
                            bash_command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            cwd=make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'bin']),
                            universal_newlines=True
                        ) as process:
                            self.process = process
                            self.spawn_jetstream_and_metrics_and_routes_threads(nats_metrics_enabled,
                                                                                nats_route_monitor_enabled)
                            while process.poll() is None:
                                for output in iter(process.stderr.readline, ''):
                                    logger.info(output)
                                time.sleep(1)
                    logger.info('NATS server has stopped')
                    is_valid_license = self.is_suite_license_available(logger)
                    if is_valid_license:
                        self.is_license_error_published = False  # Reset license_error_published flag
                        if is_nats_mod_input_disabled(self.session_key, logger):
                            # stop Rules Engine in Queue Mode
                            perform_search(self.session_key, self.disable_rules_engine_in_queue_mode, logger)
                            logger.info('Rules Engine has started in rt search mode')
                            self.continue_nats_mod_input = False
                    else:
                        if not self.is_license_error_published:
                            license_err_msg = 'Invalid license detected, skipping Rules Engine setup.'
                            logger.error(license_err_msg)
                            post_message_to_ui(self.session_key, license_err_msg, 'warn')
                            self.is_license_error_published = True

                        if is_nats_mod_input_disabled(self.session_key, logger):
                            self.continue_nats_mod_input = False

                except Exception as e:
                    logger.error(str(e))
                    sys.exit(0)
            else:
                if not self.is_license_error_published:
                    license_err_msg = 'Skipping NATS and Rules Engine setup due to invalid license or pending migration.'
                    logger.error(license_err_msg)
                    post_message_to_ui(self.session_key, license_err_msg, 'warn')
                    self.is_license_error_published = True

            time.sleep(pulse_frequency)

    def spawn_jetstream_and_metrics_and_routes_threads(self, nats_metrics_enabled, nats_route_monitor_enabled):
        nats_jetstream_thread = threading.Thread(target=self.add_or_upsert_jetstream, name="nats_jetstream")
        nats_jetstream_thread.daemon = True
        nats_jetstream_thread.start()
        if nats_metrics_enabled == 1:
            nats_metrics_thread = threading.Thread(target=self.ingest_nats_metrics, name="nats_metrics")
            nats_metrics_thread.daemon = True
            nats_metrics_thread.start()

        if nats_route_monitor_enabled:
            if self.is_shc_enabled:
                self.logger.info('NATS Route Monitor is enabled. Starting NATS Route Monitor')
                monitor = NATSRouteMonitor(
                    self.session_key,
                    self.nats_config_path,
                    self.logger,
                    self.is_auth_enabled)
                nats_route_thread = threading.Thread(target=monitor.monitor_routes, name="nats_routes_check")
                nats_route_thread.daemon = True
                nats_route_thread.start()

    def shutdown_nats(self, signum, frame):
        if self.logger is not None:
            self.logger.info('Shutting down NATS')
        shutdown_cmd = [self.nats_command, '--signal', 'quit']
        subprocess.run(shutdown_cmd)

    def is_migration_pending(self, logger):
        cfm = ConfManager(self.session_key, 'SA-ITOA')
        conf = cfm.get_conf('itsi_nats')
        settings = conf.get('nats_settings')
        migration_completed_check = int(settings.get('require_migration_completed_check', 1))
        if migration_completed_check == 1:
            version_compare = VersionComparison()
            should_migrate = version_compare.should_render_migration_page(self.session_key)
            if should_migrate:
                logger.info('Migration pending. NATS Server will be started after migration is completed')
                return True
            else:
                logger.info("No pending migration for starting NATS Server")
                return False
        else:
            return False

    def is_suite_license_available(self, logger):
        cfm = ConfManager(self.session_key, 'SA-ITOA')
        conf = cfm.get_conf('itsi_nats')
        settings = conf.get('nats_settings')
        suite_license_check = int(settings.get('require_license', 1))
        if suite_license_check == 1:
            if ITOAStorage().wait_for_storage_init(self.session_key):
                try:
                    response, contents = rest.simpleRequest( path="/servicesNS/nobody/SA-ITOA/storage/collections/data/itsi_event_grouping_status/",
                                                             sessionKey=self.session_key)
                    data = json.loads(contents)
                    if data:
                        is_event_groupping_disabled = data[0]['itsi_event_grouping_flag_value']
                        if not is_event_groupping_disabled:
                            logger.info("Event groupping is enabled")
                            return True
                        else:
                            logger.info("Event groupping is disabled")
                            return False
                    else:
                        logger.info("Entry for groupping status does not exist")
                        return False
                except Exception as e:
                    logger.error("Exception while fetching event groupping status", str(e))
                    return False
        else:
            return True

    def add_or_upsert_jetstream(self):
        cfm = ConfManager(self.session_key, 'SA-ITOA')
        conf = cfm.get_conf('itsi_nats')
        settings = conf.get('nats_settings')
        retry_limit = int(settings.get('max_retry_jet_stream_creation', 5))
        jetstream_creation_retry_wait_time = int(settings.get('jetstream_creation_retry_wait_time', 60))
        retry_attempt = 0
        while retry_attempt < retry_limit:
            try:
                event_publisher = NatsEventPublisher(self.session_key, self.logger)
                asyncio.run(event_publisher.setup_NATS())
                self.logger.info('Jetstream upsert operation completed successfully')
                break
            except Exception as e:
                self.logger.error('Error occurred while doing jetstream upsert operation : %s', e)
                retry_attempt = retry_attempt + 1
                time.sleep(jetstream_creation_retry_wait_time)

    def ingest_nats_metrics(self):
        # Get  nats monitoring settings from itsi_nats.conf file
        cfm = ConfManager(self.session_key, 'SA-ITOA')
        conf = cfm.get_conf('itsi_nats')
        monitoring_settings = conf.get('nats_settings')
        nats_endpoints = json.loads(monitoring_settings['monitoring_endpoint_configs'])
        hec_utils = HECUtil(self.session_key)
        hec_token_name = 'nats_hec'
        response, content = rest.simpleRequest(
            '/services/configs/conf-server/noahService',
            getargs={'output_mode': 'json'},
            sessionKey=self.session_key,
            raiseAllErrors=False,
            rawResult=True
        )
        status = response.status
        if status == 200:
            self.logger.info('Detected Noah environment. Not initializing HEC tokens')
        elif status == 404:
            self.logger.info('Noah environment not detected. Initializing HEC.')
            itsi_nats_metrics_macro = ItsiMacroReader(self.session_key, 'itsi_nats_metrics_index')
            hec_utils.setup_hec_token(session_key=self.session_key, token_name=hec_token_name, app='itsi', index=itsi_nats_metrics_macro.index)
        if self.os == 'windows':
            while self.is_nats_service_in_windows_running():
                self.push_nats_metrics_to_index(nats_endpoints, hec_token_name)
        else:
            while self.process.poll() is None:
                self.push_nats_metrics_to_index(nats_endpoints, hec_token_name)
        self.logger.info('Nats stopped')

    def push_nats_metrics_to_index(self, nats_endpoints, hec_token_name):
        for nats_endpoint in nats_endpoints:
            try:
                nats_url = f'http://localhost:8222/{nats_endpoint["endpoint"]}'
                response = requests.get(nats_url)
                push_manager = PushEventManager(self.session_key, token_name=hec_token_name)
                host = socket.gethostname()
                push_manager.push_event(event=json.loads(response.content), source="nats", sourcetype=nats_endpoint['sourcetype'], host=host)
                self.logger.info("successfully pushed")
            except Exception as e:
                self.logger.error('Error occurred while getting %s data from nats: %s', nats_endpoint, e)
                pass
        time.sleep(30)
        self.logger.info('Next round of nats metrics')

    def get_existing_nats_version(self):
        version = ''
        try:
            get_version_cmd = [self.nats_command, '--version']
            nats_server_output = subprocess.check_output(get_version_cmd, stderr=subprocess.STDOUT)
            if nats_server_output.startswith(b"nats-server: "):
                # The format of `nats-server --version` is:
                # `b'nats-server: v2.10.22'`
                # We extract just the second (v2.10.22) part
                version = nats_server_output.strip().split(b" ")[1].decode()
            return version
        except Exception as e:
            self.logger.error('Error occurred while retrieving the version of existing NATS binary: %s', e)
            return version

    def create_nats_service_in_windows(self):
        try:
            self.stop_nats_service_in_windows()
            self.delete_nats_service_in_windows()
            create_nats_service_cmd = f'sc.exe create nats-server binPath= "{self.nats_command} -c {self.nats_config_path}"'
            subprocess.run(create_nats_service_cmd, shell=True)
        except Exception as e:
            self.logger.error('Error occurred while creating NATS service: %s', e)
            raise e

    def stop_nats_service_in_windows(self):
        try:
            stop_nats_service_cmd = ['sc.exe', 'stop', 'nats-server']
            subprocess.run(stop_nats_service_cmd)
        except Exception as e:
            self.logger.error('Error occurred while stopping NATS service: %s', e)

    def delete_nats_service_in_windows(self):
        try:
            delete_nats_service_cmd = ['sc.exe', 'delete', 'nats-server']
            subprocess.run(delete_nats_service_cmd)
        except Exception as e:
            self.logger.error('Error occurred while deleting NATS service: %s', e)

    def is_nats_service_in_windows_running(self):
        nats_service_query_cmd = ['sc.exe', 'query', 'nats-server']
        query_process = subprocess.Popen(nats_service_query_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = query_process.communicate()

        if query_process.returncode != 0:
            self.logger.info(f"Failed to query the service nats-server. Error: {stderr.decode().strip()}")
            return False
        output = stdout.decode()
        if "RUNNING" in output:
            return True
        else:
            self.logger.info("The service nats-server has stopped")
            return False


if __name__ == '__main__':
    worker = ITSINats()
    worker.execute()
    sys.exit(0)
