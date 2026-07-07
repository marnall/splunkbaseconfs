from exec_anaconda import exec_anaconda_or_die

exec_anaconda_or_die()

from util import command_util
from cexc import BaseChunkHandler, CommandType
from util.telemetry_util import log_uuid, log_ai_commander_time, Timer
from util.param_util import parse_args
from chunked_controller import ChunkedController
from ai_commander.ai_commander_util import AICommanderUtil
from ai_commander.constants import AI_COMMANDER_COMMAND_CAPABILITIES

import cexc

logger = cexc.get_logger('ai')

PROCESSOR = 'AiCommanderProcessor'


class AICommander(BaseChunkHandler):
    @staticmethod
    def handle_arguments(getinfo: dict) -> dict:
        """
        Parses and validates arguments passed to the AICommander.

        Args:
            getinfo (dict): Dictionary containing search information.

        Returns:
            dict: Processed controller options.
        """
        if len(getinfo['searchinfo']['args']) == 0:
            raise RuntimeError('First argument must be a prompt.')
        raw_options = parse_args(getinfo['searchinfo']['raw_args'])
        controller_options = AICommander.handle_raw_options(raw_options)
        controller_options['processor'] = PROCESSOR
        return controller_options

    @staticmethod
    def handle_raw_options(raw_options: dict) -> dict:
        """
        Validates raw options provided in the command.

        Args:
            raw_options (dict): Raw options extracted from the command.

        Returns:
            dict: Filtered and validated options.
        """
        allowed_options = {'prompt', 'model', 'provider', 'kb_id', 'connection'}

        for key in raw_options['params']:
            if key not in allowed_options:
                raise RuntimeError("Param name {} is not allowed".format(key))

        if 'provider' in raw_options['params'] and 'model' not in raw_options['params']:
            raise RuntimeError("When 'provider' is specified, 'model' must also be specified.")
        if 'model' in raw_options['params'] and 'provider' not in raw_options['params']:
            raise RuntimeError("When 'model' is specified, 'provider' must also be specified.")

        return raw_options

    def setup(self, metadata: dict) -> dict:
        """
        Initializes the AICommander, verifies user eligibility, and prepares the execution environment.

        Args:
            metadata (dict): Metadata associated with the request.

        Returns:
            dict: Execution type and required fields.
        """
        controller_options = self.handle_arguments(self.getinfo)
        is_user_eligible = AICommanderUtil(
            searchinfo=self.getinfo['searchinfo']
        ).check_user_role_eligibility(required_capabilities=AI_COMMANDER_COMMAND_CAPABILITIES)
        if not is_user_eligible:
            raise RuntimeError('User does not have permission to use `ai` command.')
        self.controller = ChunkedController(self.getinfo, controller_options)
        self.totale_df_count = 0
        required_fields = self.controller.get_required_fields()
        exec_type = CommandType.STATEFUL
        return {'type': exec_type, 'required_fields': required_fields}

    def _setup_watchdog(self) -> None:
        """
        Initializes and starts the watchdog to monitor execution.
        """
        """Initialize and start watchdog"""
        self.watchdog = command_util.get_watchdog(time_limit=-1, memory_limit=20000)
        self.watchdog.start()

    def handler(self, metadata: dict, body: bytes) -> tuple[dict, bytes]:
        """
        Handles incoming data chunks and processes them accordingly.

        Args:
            metadata (dict): Metadata of the chunk.
            body (bytes): The data chunk body.

        Returns:
            Tuple[dict, bytes]: Processed metadata and output data.
        """
        if command_util.should_early_return(metadata):
            return {}

        if command_util.is_getinfo_chunk(metadata):
            return self.setup(metadata)
        finished_flag = metadata.get('finished', False)

        if not self.watchdog:
            self._setup_watchdog()

        # Skip to next chunk if this chunk is empty
        if len(body) == 0:
            return {}

        # Load data, execute and collect results.
        with Timer() as load_t:
            self.controller.load_data(body)

        self.totale_df_count += self.controller.processor.df.shape[0]

        logger.debug(f"command=ai," f" spl_load_data_time={load_t.interval}")

        logger.debug(
            f"command=ai,"
            f" chunked_df_rows_count={self.controller.processor.df.shape[0]},"
            f" total_df_rows_count={self.totale_df_count}"
        )

        with Timer() as execute_t:
            self.controller.execute()

        logger.debug(f"command=ai," f" spl_execute_time={execute_t.interval}")
        with Timer() as output_t:
            output_body = self.controller.output_results()

        logger.debug(f"command=ai," f" spl_output_results_time={output_t.interval}")

        if finished_flag:
            # Gracefully terminate watchdog
            if self.watchdog.started:
                self.watchdog.join()

        # Our final farewell
        return ({'finished': finished_flag}, output_body)


if __name__ == "__main__":
    logger.debug("Starting aicommander.py.")
    with Timer() as t:
        AICommander(handler_data=BaseChunkHandler.DATA_RAW).run()
    log_uuid()
    log_ai_commander_time(t.interval)
    logger.debug("Exiting gracefully. Byee!!")
