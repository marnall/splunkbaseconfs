from exec_anaconda import exec_anaconda_or_die

exec_anaconda_or_die()

from util import command_util
from cexc import BaseChunkHandler, CommandType
from util.telemetry_util import log_uuid, Timer
from util.param_util import parse_args
from chunked_controller import ChunkedController

import cexc

logger = cexc.get_logger('agent_status')

PROCESSOR = 'AgentStatusProcessor'


class AgentStatusCommand(BaseChunkHandler):
    @staticmethod
    def handle_arguments(getinfo: dict) -> dict:
        """
        Parses and validates arguments passed to the AgentStatusCommand.

        Args:
            getinfo (dict): Dictionary containing search information.

        Returns:
            dict: Processed controller options.
        """
        raw_options = parse_args(getinfo['searchinfo']['raw_args'])
        controller_options = AgentStatusCommand.handle_raw_options(raw_options)
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
        allowed_options = {'agent_name', 'action', 'user_name'}

        for key in raw_options['params']:
            if key not in allowed_options:
                raise RuntimeError("Param name {} is not allowed".format(key))

        # Validate required parameters
        if 'agent_name' not in raw_options['params']:
            raise RuntimeError("Parameter 'agent_name' is required.")
        if 'action' not in raw_options['params']:
            raise RuntimeError("Parameter 'action' is required.")
        if 'user_name' not in raw_options['params']:
            raise RuntimeError("Parameter 'user_name' is required.")

        # Validate action value
        action = raw_options['params']['action']
        if action not in ['create', 'delete']:
            raise RuntimeError("Parameter 'action' must be either 'create' or 'delete'.")

        return raw_options

    def setup(self, metadata: dict) -> dict:
        """
        Initializes the AgentStatusCommand and prepares the execution environment.

        Args:
            metadata (dict): Metadata associated with the request.

        Returns:
            dict: Execution type and required fields.
        """
        controller_options = self.handle_arguments(self.getinfo)
        self.controller = ChunkedController(self.getinfo, controller_options)
        self.total_df_count = 0
        required_fields = self.controller.get_required_fields()
        exec_type = CommandType.STATEFUL
        return {'type': exec_type, 'required_fields': required_fields}

    def _setup_watchdog(self) -> None:
        """
        Initializes and starts the watchdog to monitor execution.
        """
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

        self.total_df_count += self.controller.processor.df.shape[0]

        logger.debug(f"command=agent_status, spl_load_data_time={load_t.interval}")

        logger.debug(
            f"command=agent_status,"
            f" chunked_df_rows_count={self.controller.processor.df.shape[0]},"
            f" total_df_rows_count={self.total_df_count}"
        )

        with Timer() as execute_t:
            self.controller.execute()

        logger.debug(f"command=agent_status, spl_execute_time={execute_t.interval}")

        with Timer() as output_t:
            output_body = self.controller.output_results()

        logger.debug(f"command=agent_status, spl_output_results_time={output_t.interval}")

        if finished_flag:
            # Gracefully terminate watchdog
            if self.watchdog.started:
                self.watchdog.join()

        # Our final farewell
        return ({'finished': finished_flag}, output_body)


if __name__ == "__main__":
    logger.debug("Starting agent_status.py.")
    with Timer() as t:
        AgentStatusCommand(handler_data=BaseChunkHandler.DATA_RAW).run()
    log_uuid()
    logger.debug(f"Total execution time: {t.interval}")
    logger.debug("Exiting gracefully. Byee!!")
