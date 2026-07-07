"""Main Ingestion Script for Splunk to ingest IOCs and ThreatModels into the KVStore."""
import logging
import os
import sys
import time
import traceback
import glob
import shutil
import six
from ts.settings import get_working_dir
import ts.settings as settings
from ts.optic_client import Optic
from ts.tm_data_manager import TmDataManager
from ts.es_data_manager import SplunkEnterpriseSecurity
import util.utils as utils
import util.splunk_access
from splunklib.modularinput import Script, Scheme, Argument
from logger import setup_logger


class TSIngestIOC(Script):
    """
    Class to link the Threatstream IOC ingestion to a modular input, most of the settings
    are already in ts_setup.conf
    """

    abort_time = 60 * 60 * 12
    mask = "<redacted>"

    def get_scheme(self):
        """
        Splunklib method used to create the arguments for the script
        """
        scheme = Scheme("Anomali IOC Ingestion")
        scheme.description = "Anomali Ingest IOCs"
        scheme.use_single_instance = False
        scheme.streaming_mode_xml = True
        scheme.use_external_validation = True

        remote_update = Argument("remote_update")
        remote_update.data_type = Argument.data_type_boolean
        remote_update.description = "Whether to update a remote instance of Splunk with IOCs"
        remote_update.required_on_create = True
        remote_update.required_on_edit = True
        scheme.add_argument(remote_update)

        es = Argument("es_intel_upload")
        es.data_type = Argument.data_type_boolean
        es.description = "Whether to upload to Splunk ES TIF (True) or Threatstream KVStore (False)"
        es.required_on_create = True
        es.required_on_edit = True
        scheme.add_argument(es)

        remote_host = Argument("remote_host")
        remote_host.data_type = Argument.data_type_string
        remote_host.description = "Remote Splunk Host to update"
        remote_host.required_on_create = False
        scheme.add_argument(remote_host)

        remote_username = Argument("remote_username")
        remote_username.description = "Remote Splunk username to use"
        remote_username.data_type = Argument.data_type_string
        remote_username.required_on_create = False
        scheme.add_argument(remote_username)

        remote_password = Argument("remote_password")
        remote_password.description = "Remote Splunk password to use"
        remote_password.data_type = Argument.data_type_string
        remote_password.required_on_create = False
        scheme.add_argument(remote_password)

        remote_port = Argument("remote_port")
        remote_port.description = "Remote Splunkd port to use"
        remote_port.data_type = Argument.data_type_number
        remote_port.required_on_create = False
        scheme.add_argument(remote_port)

        return scheme

    def validate_input(self, validation_definition):
        """SplunkSDK method to validate the content of the ModularInput Introspection scheme"""
        pass

    def stream_events(self, inputs, ew):
        """
        Method to stream and output events/logs to the Splunk ecosystem
        """

        local_splunk_sessionkey = self._input_definition.metadata["session_key"]

        for input_name, input_item in six.iteritems(inputs.inputs):

            # Read in required variables from the scheme defined in self.get_scheme
            remote_update = input_item.get("remote_update", False)
            remote_host = input_item.get("remote_host", "unknown")
            remote_username = input_item.get("remote_username", "unknown")
            remote_password = input_item.get("remote_password", "unknown")
            remote_port = input_item.get("remote_port", 8089)
            es = input_item.get("es_intel_upload", False)

            ts_logger = setup_logger("ts_ioc_ingest", static_msg_part=input_name[16:])
            # Read in setup_config to determine whether to read files or download
            local_splunk_conn = util.splunk_access.SplunkAccess(logger=ts_logger, session_key=local_splunk_sessionkey)

            local_splunk_setup_config = local_splunk_conn.config
            loglevel = local_splunk_setup_config.get_loglevel()
            ts_logger.setLevel(loglevel)

            ts_logger.info("Config Values: es_intel_upload %s" % es)
            ts_logger.info(util.utils.log_python_version())

            if isinstance(es, str):
                if es.lower() == "false" or es == "0" or es == "":
                    es = False
            elif isinstance(es, int):
                if es == 0:
                    es = False
            elif es is None:
                es = False
            else:
                es = True

            app_to_update = "SplunkEnterpriseSecuritySuite" if es else "threatstream"

            # Override the previous variables to ensure the new logger takes affect
            local_splunk_conn = util.splunk_access.SplunkAccess(logger=ts_logger, session_key=local_splunk_sessionkey)
            local_splunk_setup_config = local_splunk_conn.get_config_manager()

            cred_store = local_splunk_conn.get_cred_store()
            username, apikey = cred_store.get('ts_optic_cred')

            ts_logger.info("ts_ioc_ingest> contacted local splunk Instance")
            setup_config = local_splunk_setup_config.get_config_object()
            ts_logger.info("ts_ioc_ingest> setup config JSON object returned")

            has_setup_params_changed = setup_params_changed(setup_config, local_splunk_conn.kvsm, ts_logger)

            ts_logger.info("ts_ioc_ingest> setup_config_changed_since_last_run: %s" % bool(has_setup_params_changed))

            validate_sufficient_setup_params(setup_config, username, apikey, ts_logger)

            # If setup has changed, we deffo want to delete all tm files on all Splunk SHC peers
            if has_setup_params_changed:
                ts_logger.info("ts_ioc_ingest> deleting existing threatmodels from disk")
                delete_tm_directories()

            # Encrypt username and password into cred store and redact username/password
            if remote_password != "unknown" and remote_password != self.mask and remote_password:
                self.mask_and_encrypt(
                    username=remote_username,
                    password=remote_password,
                    splunkd=local_splunk_conn,
                    input_name=input_name,
                    input_item=input_item,
                    logger=ts_logger,
                )
                ts_logger.debug("Returning control to main process")

            # Strip the pre-pend, we only want the actual input name
            input_name = input_name[16:]

            # We check if cluster is enabled and we are on victoria exp, if so we continue execution and let splunk
            # decide modular input execution (SPK-616, SPK-679, SPK-684).
            # 
            # For all other cases we determine if we are on cluster captain and only execute on that member.
            if local_splunk_conn.is_shc_enabled() and local_splunk_conn.is_victoria_exp():
                ts_logger.info("ts_ioc_ingest> Victoria Experience Detected. Captaincy is determined by splunk env.")
            elif local_splunk_conn.is_shc_enabled() and not local_splunk_conn.is_shc_captain():
                ts_logger.warn("ts_ioc_ingest> Not Running on Search Head Captain. Process Terminated.")
                return

            if has_setup_params_changed:
                ts_logger.info("ts_ioc_ingest> deleting threatmodel checkpoints actor_last_downloaded_modified_ts, "
                               "tipreport_last_downloaded_modified_ts from runtime_states")

                utils.delete_runtime_state("actor_last_downloaded_modified_ts", local_splunk_conn.kvsm)
                utils.delete_runtime_state("tipreport_last_downloaded_modified_ts", local_splunk_conn.kvsm)
                save_ts_ioc_ingest_setup_params(setup_config, local_splunk_conn.kvsm)

            # Logic to determine whether to update a remote splunk instance or update locally
            if remote_update == 1 or remote_update == "1" or remote_update == "true":
                ts_logger.info("ts_ioc_ingest> building remote splunk connection")
                cleartext_username, remote_password = cred_store.get("ts_remote_splunk_{}".format(input_name))

                remote_splunk_conn = util.splunk_access.SplunkAccess(
                    host=remote_host,
                    username=remote_username,
                    port=remote_port,
                    password=remote_password,
                    logger=ts_logger,
                    app=app_to_update
                )
            else:
                ts_logger.info("ts_ioc_ingest> updating local host")
                remote_splunk_conn = None

            if es:
                if remote_splunk_conn is not None:
                    try:
                        remote_splunk_conn.service.apps["SplunkEnterpriseSecuritySuite"]
                    except:
                        err_msg = "ts_ioc_ingest> Splunk Enterprise Security not installed on %s, "\
                                  "exiting modinput" % remote_host
                        ts_logger.error(err_msg)
                        sys.exit(1)

                elif local_splunk_conn is not None:
                    try:
                        local_splunk_conn.service.apps["SplunkEnterpriseSecuritySuite"]
                    except:
                        err_msg = "ts_ioc_ingest> Splunk Enterprise Security not installed locally" \
                                  ", exiting modinput"
                        ts_logger.error(err_msg)
                        sys.exit(1)

            remote_splunk_conn = remote_splunk_conn if remote_splunk_conn else local_splunk_conn

            # Determine whether to download iocs/TM or utilise integrator files
            if setup_config.get("siem_integrator") in ("1", 1) or setup_config.get("optic_link") in ("1", 1):
                # Read IOC files locally
                ts_logger.info("ts_ioc_ingest> detected legacy integrator configuration, picking up snapshot from filesystem")
                self.monitor_ioc_files(local_splunk=local_splunk_conn, logger=ts_logger, es=es)

            elif setup_config.get("optic") in ("1", 1):
                # Download the IOC files from Optic
                if setup_config.get("force_sync", False) in ["1", "True", "true"]:
                    ts_logger.info("ts_ioc_ingest> Force sync enabled, deleting tm files at %s" % settings.get_ts_data_dir())
                    files_to_remove = glob.glob(os.path.join(settings.get_ts_data_dir(), "**/*.json"),recursive=True)
                    for file in files_to_remove:
                        try:
                            os.remove(file)
                        except OSError:
                            ts_logger.warning("Unable to remove tm file %s" % file)

                    ts_logger.info("Tm Files deleted")

                ts_logger.info("ts_ioc_ingest> Detected snapshot download configuration, downloading snapshot")
                self.download_iocs(local_splunk=local_splunk_conn, logger=ts_logger, es=es)

            else:
                ts_logger.error("ts_ioc_ingest> unable to determine whether direct download or "
                                "Integrator options have been selected")
                sys.exit(1)

            # Ingest to KVStores
            try:
                if not es:
                    TmDataManager(splunka=remote_splunk_conn, logger=ts_logger).process_data()
                else:
                    # Add the data to the Splunk TIF
                    SplunkEnterpriseSecurity(splunkd=remote_splunk_conn, logger=ts_logger).process_data()
            except:
                status = "error"
                ts_logger.error(traceback.format_exc())
            else:
                status = "successful"
            finally:
                ts_logger.info("ts_ioc_ingest> Finished executing. status=%s" % status)

    @staticmethod
    def download_iocs(local_splunk=None, logger=None, es=False):
        # type: (util.splunk_access.SplunkAccess, logging.Logger, bool) -> None
        """Download the Snapshot and ThreatModels since last checkpoint"""

        # Validate dir structure exists, create if it doesnt
        if not os.path.exists(get_working_dir()):
            logger.info("ts_ioc_ingest> creating the working directory %s" % (get_working_dir()))
            os.mkdir(get_working_dir())
        
        # 2. Download snapshot
        try:
            # Get Snapshot Id from setup config
            local_splunk_setup_config = local_splunk.config.setup_config()
            snapshot_id = local_splunk_setup_config.get('snapshot_id', "")
            logger.info("ts_ioc_ingest>download_iocs snapshot_id: %s" % snapshot_id)

            t0 = time.time()
            Optic(splunka=local_splunk, logger=logger).snapshot.download(snapshot_id=snapshot_id)
            logger.info('OpticClient Download time: %s seconds' % round(time.time() - t0))
        except Exception:
            logger.error("ts_ioc_ingest> Unable to download the IOC snapshot, "
                         "please review traceback info")
            logger.error(traceback.format_exc())
            sys.exit(1)  # Deliberately through a bad exit code

        # 3. Delete old ioc files - prevents issues with old
        logger.info("Deleting lookup files at %s" % settings.get_lookup_dir())
        files_to_remove = glob.glob(os.path.join(settings.get_lookup_dir(), "*.gz"))
        for file in files_to_remove:
            try:
                os.remove(file)
            except OSError:
                logger.warning("Unable to remove old ioc file %s" % file)

        logger.info("Lookup Files deleted")

        # 4. Extract snapshot to lookups directory
        logger.info("Extracting snapshot to lookups directory ")
        utils.extract_tar_file(settings.snapshot_location, settings.get_lookup_dir())

        # 5. Download TMs and process - skip if using es or tms already present
        if not es:
            if os.path.exists(settings.tm_file_location):
                logger.info("Extracting ThreatModels from bundled file")
                handle_tm_file(logger)
            else:
                logger.info("Starting ThreatModel Poll Download")
                optic = Optic(splunka=local_splunk, logger=logger)
                optic.tipreports.poll()
                optic.actors.poll()

        else:
            logger.info("ThreatModels are not supported by ES Threat Intelligence Framework. "
                        "Skipping")

    @staticmethod
    def monitor_ioc_files(local_splunk=None, logger=None, es=False):
        # type: (util.splunk_access.SplunkAccess, logging.Logger, bool) -> None
        """
        Legacy Integrator code. Used to import IOCs when the snapshot resides on disk in threatstream/lookups.
        If remote_splunk service object is not provided, the local_splunk service object will be used instead

        Args:
            local_splunk (obj): the local splunk service object
            logger (obj): the modinput EventWriter
            es (bool): whether the iocs are going to the Splunk Intelligence Framework

        Returns:

        """
        # Get the files transferred on LOCAL Splunk
        logger.info("ts_ioc_ingest> Attempting to find Integrator pushed files")
        lookup_files = glob.glob(os.path.join(settings.get_lookup_dir(), "*.gz"))
        last_ingest = utils.get_runtime_state_value("ts_data_timestamp", kvsm=local_splunk.kvsm) or 0 # TODO: check this is correct
        if last_ingest:
            last_ingest = float(last_ingest)

        if not lookup_files:
            logger.info("ts_ioc_ingest> Unable to find files to ingest from Integrator")
            sys.exit(1)

        # Check if the files have been updated since last ingest
        to_ingest = False
        for file in lookup_files:
            mod_time = os.path.getmtime(file)
            if mod_time > last_ingest:
                to_ingest = True
                break

        if not to_ingest:
            logger.info("ts_ioc_ingest> Data not processed - %s have not been updated since last "
                        "ingest %s" % (lookup_files, last_ingest))
            sys.exit(1)

        logger.info("ts_ioc_ingest> Found updated Integrator files")

        ts = util.utils.integrator_legacy_get_gz_files_in_lookup_dir_ts_signiture()
        t0 = time.time()

        while True:
            time.sleep(30)   # wait n seconds to make sure that no more files are being updated
            new_ts = util.utils.integrator_legacy_get_gz_files_in_lookup_dir_ts_signiture()
            if ts == new_ts:
                break
            ts = new_ts
            if time.time() - t0 > 5 * 60:
                logger.info("ts_ioc_ingest> IOC/TM files are still being updated, unable to "
                            "continue ingestion")
                sys.exit(1)

        if os.path.exists(settings.tm_file_location) and not es:
            logger.info("ts_ioc_ingest> Extracting ThreatModel files")
            handle_tm_file(logger)

        with open(settings.get_ts_data_timestamp_token_file(), 'w') as file_handler:
            ts_data_timestamp = time.time()
            logger.info("ts_ioc_ingest> update %s, mod_time=%s", settings.get_ts_data_timestamp_token_file(), ts_data_timestamp)
            file_handler.write(str(ts_data_timestamp))

    def mask_and_encrypt(self, username=None, password=None, splunkd=None, input_name=None,
                         logger=None, input_item=None):
        # type: (str, str, splunklib.client.Service, str, logging.Logger, dict) -> None
        """
        This function will take the username and password and encrypt them in the credstore. Additionally, this dunction
        will mask the password in the source config (inputs.conf)

        Args:
            password (str): password to mask
            splunkd (obj): SplunkAccess object
            input_item (obj): input to redact
        """

        logger.info("ts_ioc_ingest> encrypting credential")

        kind, input_name = input_name.split("://")
        item = splunkd.service.inputs.__getitem__((input_name, kind))

        cred_store = splunkd.get_cred_store()
        cred_store.set("ts_remote_splunk_%s" % input_name, username, password)

        logger.info("ts_ioc_ingest> masking input credential")

        kwargs = {
            "remote_password": self.mask,
            "remote_update": input_item.get("remote_update", False),
            "es_intel_upload": input_item.get("es_intel_upload", False),
            "remote_host": input_item.get("remote_host", None),
            "remote_port": input_item.get("remote_port", 8089),
            "remote_username": input_item.get("remote_username")
        }

        item.update(**kwargs).refresh()
        kwargs.pop("remote_password")
        logger.debug("ts_ioc_ingest> updating input name %s of type %s" % (input_item, kind))
        logger.debug("Input item refreshed")


def delete_tm_directories():
    """Delete the TM directories on this box"""

    shutil.rmtree(os.path.join(settings.get_threat_model_dir(), "tm_actor"), ignore_errors=True)
    shutil.rmtree(os.path.join(settings.get_threat_model_dir(), "tm_tipreport"), ignore_errors=True)


def save_ts_ioc_ingest_setup_params(setup_conf, kvsm):
    # type: (dict, object) -> None
    """Save the knowledge of the setup params to the kvstore"""

    utils.save_runtime_state("ts_ioc_ingest_url", str(setup_conf.get("url")), kvsm)
    utils.save_runtime_state("ts_ioc_ingest_tm_poll_time", str(setup_conf.get("tm_poll_time")), kvsm)
    utils.save_runtime_state("ts_ioc_ingest_siem_integrator", str(setup_conf.get("siem_integrator")), kvsm)
    utils.save_runtime_state("ts_ioc_ingest_optic_link", str(setup_conf.get("optic_link")), kvsm)


def setup_params_changed(setup_conf, kvsm, logger):
    # type: (dict, object, logging.Logger) -> bool
    """Whether the setup params have deviated from the last run """

    ts_ioc_ingest_saved_settings = {
        "url": None,
        "tm_poll_time": None,
        "siem_integrator": None,
        "optic_link": None,
    }

    for key in ts_ioc_ingest_saved_settings:
        runtime_state = utils.get_runtime_state_value("ts_ioc_ingest_%s" % key, kvsm)
        if runtime_state is not None: # We don't specifically test  out for None
            ts_ioc_ingest_saved_settings[key] = runtime_state
        else:
            ts_ioc_ingest_saved_settings[key] = None

    setup_params = {
        "url": str(setup_conf.get("url")),
        "tm_poll_time": str(setup_conf.get("tm_poll_time")),
        "siem_integrator": str(setup_conf.get("siem_integrator")),
        "optic_link": str(setup_conf.get("optic_link"))
    }

    ts_ioc_ingest = set(ts_ioc_ingest_saved_settings.items())
    setup = set(setup_params.items())

    diff = ts_ioc_ingest - setup

    logger.debug("ts_ioc_ingest> setup_params: %s" % setup_params)
    logger.debug("ts_ioc_ingest> ts_ingest_memory: %s" % ts_ioc_ingest_saved_settings)
    logger.debug("ts_ioc_ingest> different: %s, has_changed: %s" % (diff, bool(diff)))

    return bool(diff)


def validate_sufficient_setup_params(setup_conf, username, apikey, logger):
    """Ensures that the setup parameters are appropriate to run the ts_ioc_ingest process"""

    logger.info("ts_ioc_ingest> validating setup process parameters")
    # Check that setup has been run and we have the parameters to proceed

    if setup_conf.get("siem_integrator") in ("1", 1) or setup_conf.get("optic_link") in ("1", 1):
        # Where an instance is configured for Integrator Splunk destination
        pass
    elif setup_conf.get("url") and username and apikey:
        # Ensure we have the correct parameters for snapshot/tm polling
        pass
    else:
        logger.error("ts_ioc_ingest> Insufficient parameters to proceed, cancelling ingest process."
                     " Expecting (siem_integrator or optic_link) OR (url and username and apikey)")
        raise ValueError("insufficient setup parameters to proceed")

    logger.info("ts_ioc_ingest> found appropriate settings")


def handle_tm_file(logger=None):
    """Ensure that the threat_model.tar.gz file is always handled the same way, either from Splunk
    dest or from """
    # Remove old TM files, this is important to ease the processing in the tm_data_manager process
    shutil.rmtree(settings.get_ts_data_dir())

    # Recreate the working ts_data directory
    os.mkdir(settings.get_ts_data_dir())

    # Extract the directory from the tar file
    utils.extract_tar_file(settings.tm_file_location, settings.get_ts_data_dir())

    if len(os.listdir(settings.get_threat_model_dir())) == 0:
        if logger:
            logger.info("ts_ioc_ingest> %s is empty", settings.get_threat_model_dir())
        utils.extract_tar_file(settings.tm_file_location, settings.get_threat_model_dir())

if __name__ == "__main__":
    sys.exit(TSIngestIOC().run(sys.argv))
