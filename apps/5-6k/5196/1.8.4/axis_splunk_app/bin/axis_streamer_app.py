import logging
import time
from datetime import datetime

from splunklib.modularinput import Argument, Script, Scheme, EventWriter, InputDefinition

from api.repositories.configurable_api_repository import ConfigurableApiRepository
from auth.oauth.oauth_api_caller_factory import OAuthApiCallerFactory, AXIS_TOKEN_CHECKPOINT_NAME
from auth.oauth.token.token_parser import validate_token, MASK
from stream.api_streamer import ApiStreamer
from stream.output_stream import StanzaOutputStream
from stream.streamer_settings import AxisApiStreamerSettings
from utils import configuration
from utils.configuration import Config
from utils.file_checkpoint_repository import FileStateAccessor, PasswordStateAccessor
from utils.log.custom_splunk_logger import CustomSplunkLogger
from utils.log.logging_utils import formatter, convert_severity
from utils.waiter import SmartWaiter

TOKEN_PARAM_NAME = 'token'
SEVERITY_PARAM_NAME = 'log_severity'
INDEX_PARAM_NAME = 'index'
HOST_PARAM_NAME = 'host'
SOURCETYPE_PARAM_NAME = 'sourcetype'
PASSWORD_USERNAME = 'axis'
APP_ID = 'axis_splunk_app'
SEVERITIES = ["DEBUG", "INFO", "WARNING", "ERROR"]
SEVERITY_TEXT = "Enter DEBUG, INFO, WARNING or ERROR (default value is INFO)"
DEFAULT_LOGGING_SEVERITY = "INFO"
DEFAULT_WAIT_INTERVAL = 0.2


class AxisStreamerApp(Script):
    def __init__(self, settings):  # type: (AxisApiStreamerSettings) -> None
        super(AxisStreamerApp, self).__init__()
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_scheme(self):
        # Returns scheme.
        self.logger.debug("Getting scheme")
        scheme = Scheme("Axis Security")
        scheme.description = "Stream data from Axis Security SIEM API"
        scheme.use_external_validation = True
        scheme.use_single_instance = True

        token = Argument(TOKEN_PARAM_NAME)
        token.data_type = Argument.data_type_string
        token.title = "Secret token"
        token.description = "Token generated in the Axis Security management console"
        token.required_on_create = True

        severity = Argument(SEVERITY_PARAM_NAME)
        severity.data_type = Argument.data_type_string
        severity.title = "Logs Severity"
        severity.description = SEVERITY_TEXT
        severity.required_on_create = False
        severity.required_on_edit = False

        scheme.add_argument(token)
        scheme.add_argument(severity)
        self.logger.debug("Got scheme")
        return scheme

    def validate_input(self, validation_definition):
        self.logger.debug("Validating input parameters")
        token = validation_definition.parameters[TOKEN_PARAM_NAME]
        if not validate_token(token):
            raise Exception("Got invalid token")

        severity_input = validation_definition.parameters.get(SEVERITY_PARAM_NAME, None)
        if severity_input is not None:
            severity = severity_input.strip().upper()
            if len(severity) > 0 and severity not in SEVERITIES:
                raise Exception("Invalid Logs Severity. {}".format(SEVERITY_TEXT))

    def _mask_password(self, input_name):
        try:
            kind, input_name = input_name.split("://")
            item = self.service.inputs.__getitem__((input_name, kind))
            kwargs = {
                TOKEN_PARAM_NAME: MASK,
            }
            item.update(**kwargs).refresh()

        except Exception as e:
            self.logger.error("Error while masking: {}".format(e))
            raise

    def _build_streamers(self, input_name, input_item, config, event_writer):
        # type: (str, dict, Config, EventWriter) -> [ApiStreamer]
        try:
            # Read token
            checkpoint_state = FileStateAccessor(config.checkpoint_path, input_name)

            clear_input_name = input_name.split("://")[-1]
            input_username = "{}_{}".format(PASSWORD_USERNAME, clear_input_name)
            password_state = PasswordStateAccessor(self.service.storage_passwords, input_username)

            self.logger.info("Streaming events for \"{}\"".format(clear_input_name))

            token = input_item[TOKEN_PARAM_NAME]

            if token != MASK:
                self.logger.debug("Token is different than mask. Masking")
                password_state[AXIS_TOKEN_CHECKPOINT_NAME] = token
                try:
                    self._mask_password(input_name)
                except Exception as e:
                    self.logger.error("Error while masking password: {}".format(e))
                    raise

            token = password_state[AXIS_TOKEN_CHECKPOINT_NAME]
            index = input_item.get(INDEX_PARAM_NAME, None)
            host = input_item.get(HOST_PARAM_NAME, None)
            sourcetype = input_item.get(SOURCETYPE_PARAM_NAME, None)
            stanza_output_stream = StanzaOutputStream(event_writer, index, host, sourcetype)
            api_caller = self.settings.api_caller_factory.create(token, password_state)
        except Exception as e:
            self.logger.error("Error while preparing streamer: {}".format(e))
            raise

        streamers = []

        # Initialize streamers
        for repository_config in self.settings.api_repositories:
            api_repository = ConfigurableApiRepository(self.settings.api_host, api_caller, input_name,
                                                       repository_config["name"], repository_config["path"],
                                                       repository_config["sourcetype"])
            api_streamer = ApiStreamer(api_repository, stanza_output_stream, checkpoint_state, password_state,
                                       self.settings.waiter(),
                                       lambda: self.settings.api_caller_factory.create(token, password_state,
                                                                                       invalidate=True),
                                       input_name)
            streamers.append(api_streamer)

        return streamers

    @staticmethod
    def _get_log_level_for_input(input_item):
        severity = input_item.get(SEVERITY_PARAM_NAME, DEFAULT_LOGGING_SEVERITY)
        return severity or DEFAULT_LOGGING_SEVERITY

    def stream_events(self, inputs, ew):  # type: (InputDefinition, EventWriter) -> None
        # Setup logger
        splunk_logger = CustomSplunkLogger(ew)

        splunk_logger.setFormatter(formatter)
        logging.root.handlers = [splunk_logger]

        # Re initialize old logger after initialize Splunk's logger
        self.logger = logging.getLogger(self.__class__.__name__)

        self.logger.debug("Streaming events")
        resolved_inputs = list(inputs.inputs.items())  # Create hard copy of the stream
        config = configuration.build_from_metadata(self._input_definition.metadata)

        min_severity = min([convert_severity(self._get_log_level_for_input(input_name)) for _, input_name in
                            resolved_inputs] or [logging.INFO])

        # Set logger level from input
        splunk_logger.setLevel(min_severity)
        self.logger.setLevel(min_severity)
        logging.root.setLevel(min_severity)

        self.logger.info("Setting log level from input {}".format(logging.getLevelName(min_severity)))

        streamers = []
        for input_name, input_item in resolved_inputs:
            streamers.extend(self._build_streamers(input_name, input_item, config, ew))

        while True:
            for streamer in streamers:
                next_run_time = streamer.waiter.get_next_run()
                if next_run_time > datetime.now():
                    continue

                self.logger.debug(
                    "Streaming data from streamer: {}. input {}".format(streamer.api_repository.name(),
                                                                        streamer.input_name))
                streamer.stream()
                self.logger.debug(
                    "Next run for streamer: {} is {}".format(streamer.api_repository.name(),
                                                             streamer.waiter.get_next_run()))

            time.sleep(DEFAULT_WAIT_INTERVAL)


def init_from_configuration(configuration):
    logging.debug("Initializing. Configuration: {}".format(configuration))
    oauth_api_caller_factory = OAuthApiCallerFactory(
        configuration.OAUTH_HOST,
        configuration.TOKEN_PATH,
        configuration.SCOPES,
        configuration.VERIFY_HTTPS)

    return AxisApiStreamerSettings(
        configuration.API_HOST,
        oauth_api_caller_factory,
        configuration.REPOSITORIES,
        lambda: SmartWaiter(configuration.INTERVAL_SECONDS, configuration.MAX_INTERVAL_SECONDS),
    )
