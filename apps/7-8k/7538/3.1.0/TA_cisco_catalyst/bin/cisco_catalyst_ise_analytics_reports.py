"""Modular input for ISE Input."""

import import_declare_test  # noqa: F401
import json
import paramiko
import time
import re
from hashlib import sha3_512

import cisco_catalyst_exceptions as cce
import consts
import ise.ise_analytics_reports_helper as reportsdata
import logger_manager
import utils
import sys
from splunklib import modularinput as smi


class ISEReportInput(smi.Script):
    """Get the Health Details from Cisco ISE Server."""

    def __init__(self):
        """Initialise ISEReportInput class."""
        super(ISEReportInput, self).__init__()

    def get_scheme(self):
        """Overloaded splunklib modularinput method."""
        scheme = smi.Scheme("cisco_catalyst_ise_analytics_reports")
        scheme.title = ("Cisco ISE Analytics Reports")
        scheme.description = (
            "Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        For other input types, arguments should be get from input_module. Defining new input types could be easier.
        """
        scheme.add_argument(smi.Argument("ise_account", title="ISE Account",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("ise_disk_repo", title="Cisco ISE Disk Repository Name",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("ise_sftp_repo", title="Cisco ISE SFTP Repository Name",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("repo_path", title="Repository Path",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        return scheme

    def determine_report_sourcetype(self, report_filename):
        """Determine the sourcetype for a report based on its filename.

        Args:
            report_filename: Name of the report file

        Returns:
            Appropriate sourcetype string
        """
        if re.search("Posture_Registry_*", report_filename):
            return consts.Sourcetype.ISE_REPORTS_REGISTRY_SOURCETYPE.value
        elif re.search("Posture_Hardware_*", report_filename):
            return consts.Sourcetype.ISE_REPORTS_HARDWARE_SOURCETYPE.value
        elif re.search("Posture_Application_*", report_filename):
            return consts.Sourcetype.ISE_REPORTS_APPLICATIONS_SOURCETYPE.value
        elif re.search("FullReport_*", report_filename):
            return consts.Sourcetype.ISE_REPORTS_FULLREPORT_SOURCETYPE.value
        else:
            return consts.Sourcetype.ISE_REPORTS_DEFAULT_SOURCETYPE.value

    def ingest_report_events(self, report_data, report, report_sourcetype, input_name, input_conf, ew, logger):
        """Ingest report data as Splunk events.

        Args:
            report_data: List of report records
            report: Report filename
            report_sourcetype: Sourcetype for the events
            input_name: Input name
            input_conf: Input configuration
            ew: Event writer
            logger: Logger instance

        Returns:
            Number of events ingested
        """
        logger.info(
            "Creating events for report '{}'. Total records: {}.".format(
                report, len(report_data)
            )
        )

        events_ingested = 0
        for endpoint in report_data:
            try:
                event = smi.Event(
                    source=":".join(
                        ["cisco_catalyst_ise_analytics_reports", input_name]
                    ),
                    index=input_conf.get("index"),
                    sourcetype=report_sourcetype,
                    data=json.dumps(endpoint)
                )
                ew.write_event(event)
                events_ingested += 1
            except Exception as e:
                logger.error("Error writing event for report '{}': {}.".format(report, str(e)))
                continue

        logger.info(
            "Successfully ingested {} event(s) for report '{}' with sourcetype '{}'.".format(
                events_ingested, report, report_sourcetype
            )
        )
        return events_ingested

    def cleanup_fullreport_file(self, report, ise_ssh_ip, ise_ssh_port, ise_ssh_user, ise_ssh_pw, logger):
        """Clean up FullReport files from ISE local disk via SSH.

        Args:
            report: Report filename
            ise_ssh_ip: ISE SSH IP address
            ise_ssh_port: ISE SSH port
            ise_ssh_user: ISE SSH username
            ise_ssh_pw: ISE SSH password
            logger: Logger instance
        """
        ssh = None
        channel = None
        try:
            paramiko.PKey.get_fingerprint = lambda x: sha3_512(x.asbytes()).digest()
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ise_ssh_ip, ise_ssh_port, ise_ssh_user, ise_ssh_pw, timeout=30)
            transport = ssh.get_transport()
            transport.set_keepalive(30)
            channel = ssh.invoke_shell()
            time.sleep(10)
            logger.debug(
                "Attempting to delete report '{}' from ISE local disk for cleanup.".format(
                    report
                )
            )
            channel.send(f"delete disk:/{report}\r\n")
            time.sleep(10)
            logger.info("Exiting ISE CLI on server: {}".format(ise_ssh_ip))
            channel.send('exit\r\n')
            time.sleep(5)
        except Exception as e:
            logger.debug("Error deleting report '{}' from ISE local disk: {}.".format(report, str(e)))
        finally:
            try:
                if channel:
                    channel.close()
                if ssh:
                    ssh.close()
            except Exception:
                pass

    def process_single_report(
        self,
        report,
        reports_data,
        sftp_config,
        repo_path,
        input_name,
        input_conf,
        ew,
        ise_config,
        logger
    ):
        """Process a single report file from SFTP and ingest its data.

        Args:
            report: Report filename
            reports_data: Reports data handler
            sftp_config: Dict containing SFTP repository config (ip, port, user, pw)
            repo_path: Repository path
            input_name: Input name
            input_conf: Input configuration
            ew: Event writer
            ise_config: Dict containing ISE SSH config (ip, port, user, pw)
            logger: Logger instance

        Returns:
            Number of events ingested for this report
        """
        logger.info("Processing report '{}' from SFTP repository.".format(report))

        # Determine report source type
        report_sourcetype = self.determine_report_sourcetype(report)

        # Read CSV from SFTP and convert to JSON
        try:
            report_data = reports_data.read_csv_from_sftp_and_convert(
                sftp_config['ip'], sftp_config['port'], sftp_config['user'], sftp_config['pw'],
                repo_path, report
            )
        except Exception as e:
            logger.error("Error reading report '{}' from SFTP repository: {}.".format(report, str(e)))
            return 0

        if not report_data:
            logger.error("No data retrieved for report '{}'. Skipping ingestion.".format(report))
            return 0

        # Ingest the report events
        try:
            events_ingested = self.ingest_report_events(
                report_data, report, report_sourcetype, input_name, input_conf, ew, logger
            )
        except Exception as e:
            logger.error("Error ingesting events for report '{}': {}.".format(report, str(e)))
            return 0

        # Clean up FullReport files from ISE local disk
        if report.lower().startswith('fullreport'):
            self.cleanup_fullreport_file(
                report, ise_config['ip'], ise_config['port'], ise_config['user'], ise_config['pw'], logger
            )

        return events_ingested

    def ingest_and_clean_data(
        self,
        report_files,
        logger,
        reports_data,
        input_name,
        input_conf,
        ew,
        account_conf_info
    ):
        """Ingest data and clean it from ISE Server."""
        # Create configuration dictionaries
        sftp_config = {
            'ip': account_conf_info.get("sftp_repo_ip"),
            'port': account_conf_info.get("sftp_repo_port"),
            'user': account_conf_info.get("sftp_repo_user"),
            'pw': account_conf_info.get("sftp_repo_pw")
        }
        ise_config = {
            'ip': account_conf_info.get("hostname"),
            'port': account_conf_info.get("ise_ssh_port"),
            'user': account_conf_info.get("username"),
            'pw': account_conf_info.get("password")
        }
        repo_path = input_conf.get('repo_path')

        total_events_ingested = 0

        for report in report_files:
            events_ingested = self.process_single_report(
                report,
                reports_data,
                sftp_config,
                repo_path,
                input_name,
                input_conf,
                ew,
                ise_config,
                logger
            )
            total_events_ingested += events_ingested

        return total_events_ingested

    def setup_and_validate_account(self, session_key, input_name, input_conf, logger):
        """Set up and validate ISE account configuration.

        Args:
            session_key: Splunk session key
            input_name: Input name
            input_conf: Input configuration
            logger: Logger instance

        Returns:
            Tuple of (account_conf_info, ise_disk_repo, ise_sftp_repo)

        Raises:
            cce.ISEInvalidGlobalAccount: If account configuration is invalid
        """
        ise_account = input_conf.get("ise_account")

        if not ise_account:
            raise cce.ISEInvalidGlobalAccount(
                "Invalid ise_account for input '{}'.".format(input_name)
            )

        # Getting account details
        try:
            account_conf = utils.get_account_config(
                session_key, consts.ISE_ACCOUNT_CONF_FILE, logger
            )
            account_conf_info = account_conf.get(ise_account)
            if not account_conf_info:
                raise cce.ISEInvalidGlobalAccount(
                    "ISE account '{}' not found in configuration.".format(ise_account)
                )

            ise_ssh_ip = account_conf_info.get("hostname")
            ise_ssh_user = account_conf_info.get("username")
            ise_ssh_pw = account_conf_info.get("password")
            ise_ssh_port = account_conf_info.get("ise_ssh_port")
            sftp_repo_ip = account_conf_info.get("sftp_repo_ip")
            sftp_repo_user = account_conf_info.get("sftp_repo_user")
            sftp_repo_pw = account_conf_info.get("sftp_repo_pw")
            sftp_repo_port = account_conf_info.get("sftp_repo_port")

            # Validate required account fields
            if not all([ise_ssh_ip, ise_ssh_user, ise_ssh_pw, ise_ssh_port]):
                raise cce.ISEInvalidGlobalAccount(
                    "ISE account '{}' is missing required fields "
                    "(IP Address , Username, ISE SSH Password, ISE SSH Port).".format(ise_account)
                )
            if not all([sftp_repo_ip, sftp_repo_user, sftp_repo_pw, sftp_repo_port]):
                raise cce.ISEInvalidGlobalAccount(
                    "ISE account '{}' is missing required repository fields (Repository Address, Repository User,"
                    " Repository User Password, Repository SFTP Port).".format(ise_account)
                )
        except cce.ISEInvalidGlobalAccount:
            raise
        except Exception as e:
            logger.error("Error retrieving account configuration for account '{}': {}.".format(ise_account, str(e)))
            raise cce.ISEInvalidGlobalAccount(
                "Failed to retrieve account configuration for '{}'.".format(ise_account)
            )

        ise_disk_repo = input_conf.get('ise_disk_repo')
        ise_sftp_repo = input_conf.get('ise_sftp_repo')

        return account_conf_info, ise_disk_repo, ise_sftp_repo

    def process_reports_and_ingest_data(
        self,
        reports_data,
        ise_ssh_ip,
        ise_ssh_user,
        ise_ssh_pw,
        ise_ssh_port,
        ise_disk_repo,
        ise_sftp_repo,
        input_name,
        input_conf,
        ew,
        account_conf_info,
        logger
    ):
        """Process ISE reports and ingest the data.

        Args:
            reports_data: Reports data handler
            ise_ssh_ip: ISE SSH IP
            ise_ssh_user: ISE SSH username
            ise_ssh_pw: ISE SSH password
            ise_ssh_port: ISE SSH port
            ise_disk_repo: ISE disk repository
            ise_sftp_repo: ISE SFTP repository
            input_name: Input name
            input_conf: Input configuration
            ew: Event writer
            account_conf_info: Account configuration info
            logger: Logger instance

        Returns:
            Number of events ingested
        """
        # Generate reports on ISE
        report_files = reports_data.run_reports(ise_ssh_ip, ise_ssh_user, ise_ssh_pw, ise_ssh_port)
        if not report_files:
            logger.error(
                "No reports were generated by ISE server. Data collection cannot proceed."
                "Data collection terminated due to no reports generated."
            )
            return 0

        csv_files_set = set(report_files)
        report_files = list(csv_files_set)
        logger.info("Successfully generated {} report file(s) from ISE server.".format(len(report_files)))

        # Transfer reports to SFTP repository
        transfer_failed_files = []
        for report in report_files:
            try:
                transfer_files = reports_data.move_report(
                    ise_ssh_ip, ise_ssh_user, ise_ssh_pw, ise_ssh_port, report, ise_disk_repo, ise_sftp_repo
                )
                if not transfer_files:
                    transfer_failed_files.append(report)
                    logger.error(
                        "Failed to transfer report '{}' to SFTP repository. It will be skipped.".format(
                            report
                        )
                    )
            except Exception as e:
                transfer_failed_files.append(report)
                logger.error("Error transferring report '{}' to SFTP repository: {}.".format(report, str(e)))

        if transfer_failed_files:
            logger.warning(
                "{} report(s) failed to transfer to SFTP repository and will be skipped.".format(
                    len(transfer_failed_files)
                )
            )
            # Remove failed transfers from processing list
            report_files = [r for r in report_files if r not in transfer_failed_files]

        if not report_files:
            logger.info(
                "No reports available for processing after transfer. Data collection"
                " cannot proceed. Data collection terminated due to no reports available."
            )
            return 0

        # Ingest and clean data
        total_events_ingested = self.ingest_and_clean_data(
            report_files,
            logger,
            reports_data,
            input_name,
            input_conf,
            ew,
            account_conf_info
        )

        logger.info("Data collection completed for input: '{}'. Total ingested events: {}.".format(
            input_name, total_events_ingested
        ))

        return total_events_ingested

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        """Collect the data from the Cisco ISE Server."""
        try:
            session_key = self._input_definition.metadata["session_key"]
            ew = event_writer
            input_name, input_conf = [
                [key.split("/")[-1], val] for key, val in inputs.inputs.items()
            ][0]
            input_conf["input_name"] = input_name
            input_conf["session_key"] = session_key
            input_conf["input_stanza_name"] = "".join(
                ["cisco_catalyst_ise_analytics_reports://", input_name]
            )
            logger = logger_manager.get_logger(
                f"ise_analytics_reports_{input_name}", input_conf["logging_level"]
            )
            logger.info("Data collection started for input: '{}'".format(input_name))

            # Set up and validate account
            account_conf_info, ise_disk_repo, ise_sftp_repo = self.setup_and_validate_account(
                session_key, input_name, input_conf, logger
            )

            # Initialize reports data handler
            reports_data = reportsdata.CiscoISEAnalyticsReports(
                logger=logger,
                input_name=input_name
            )

            # Process reports and ingest data
            self.process_reports_and_ingest_data(
                reports_data,
                account_conf_info.get("hostname"),
                account_conf_info.get("username"),
                account_conf_info.get("password"),
                account_conf_info.get("ise_ssh_port"),
                ise_disk_repo,
                ise_sftp_repo,
                input_name,
                input_conf,
                ew,
                account_conf_info,
                logger
            )

        except cce.ISEInvalidGlobalAccount as e:
            logger.error(
                "Invalid ISE account configuration for input '{}': {}."
                "Data collection terminated due to account configuration error.".format(input_name, str(e))
            )
            logger.error(
                f"instance={input_name}, "
                "error_type=Configuration, "
                "product=Cisco ISE, "
                f"filter_value=cisco_catalyst_ise_analytics_reports://{input_name}, "
                "status=Not Connected,"
            )
        except cce.AuthenticationError as e:
            logger.error(
                "Authentication error for input '{}': {}."
                "Data collection terminated due to authentication failure.".format(input_name, str(e))
            )
            logger.error(
                f"instance={input_name}, "
                "error_type=Configuration, "
                "product=Cisco ISE, "
                f"filter_value=cisco_catalyst_ise_analytics_reports://{input_name}, "
                "status=Not Connected,"
            )
        except KeyError as e:
            logger.error(
                "Missing required configuration parameter for input '{}': {}."
                "Data collection terminated due to configuration error.".format(input_name, str(e)))
            logger.error(
                f"instance={input_name}, "
                "error_type=Configuration, "
                "product=Cisco ISE, "
                f"filter_value=cisco_catalyst_ise_analytics_reports://{input_name}, "
                "status=Not Connected,"
            )
        except Exception as e:
            logger.error(
                "Error during data collection for input '{}': {}."
                "Data collection terminated due to error.".format(input_name, str(e))
            )
            logger.error(
                f"instance={input_name}, "
                "error_type=Configuration, "
                "product=Cisco ISE, "
                f"filter_value=cisco_catalyst_ise_analytics_reports://{input_name}, "
                "status=Not Connected,"
            )


if __name__ == "__main__":
    exit_code = ISEReportInput().run(sys.argv)
    sys.exit(exit_code)
