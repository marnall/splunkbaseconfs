from exec_anaconda import exec_anaconda_or_die

exec_anaconda_or_die()

from util import command_util
from cexc import BaseChunkHandler, CommandType
from util.telemetry_util import Timer
from util.param_util import parse_args
from chunked_controller import ChunkedController
from ai_commander.ai_commander_util import AICommanderUtil
from agent_manager.agent_manager import AgentManager
from connection_config_manager.vector_db.config_manager import (
    ConfigManager as VectorDbConnectionManager,
)
from connection_config_manager.mcp.mcp_util import MCPConnectionManager
from connection_config_manager.utils.common_utils import CommonUtils
from connection_config_manager.llm.config_manager import ConfigManager as LLMConfigManager
from util.ai_commander_util import handle_secrets
from util.rest_proxy import rest_proxy_from_searchinfo
from connection_config_manager.mcp.constants import (
    AUTO_REFRESH_ENABLED,
    LAST_REFRESH_AT,
)
from ai_commander.constants import (
    OPENAI,
    BEDROCK,
    ANTHROPIC,
    AZUREOPENAI,
    AGENT_RUN_CAPABILITIES,
    MAX_REQUEST_TIMEOUT,
    DEFAULT_TOKENS_AGENTS,
    DEFAULT_RESPONSE_VARIABILITY,
    MAXIMUM_RESULT_ROWS,
)
from typing import Dict, Any, List
import time
import json

import cexc

logger = cexc.get_logger('aiagent')

PROCESSOR = 'AiAgentProcessor'


class AIAgentCommand(BaseChunkHandler):
    @staticmethod
    def handle_arguments(getinfo: dict) -> dict:
        """
        Parses and validates arguments passed to the AIAgentCommand.

        Args:
            getinfo (dict): Dictionary containing search information.

        Returns:
            dict: Processed controller options.
        """
        if len(getinfo['searchinfo']['args']) == 0:
            raise RuntimeError('Arguments required: agent_name and prompt must be provided.')

        raw_options = parse_args(getinfo['searchinfo']['raw_args'])
        controller_options = AIAgentCommand.handle_raw_options(raw_options)
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

        Raises:
            RuntimeError: If required parameters are missing or invalid parameters are provided.
        """
        allowed_options = {'agent_name', 'prompt'}
        required_options = {'agent_name'}

        # Check for required parameters
        for param in required_options:
            if param not in raw_options['params']:
                raise RuntimeError(f"Required parameter '{param}' is missing.")

        # Check for invalid parameters
        for key in raw_options['params']:
            if key not in allowed_options:
                raise RuntimeError(
                    f"Parameter '{key}' is not allowed. Allowed parameters: {', '.join(allowed_options)}"
                )

        # Validate parameter values
        agent_name = raw_options['params'].get('agent_name', '').strip()
        if not agent_name:
            raise RuntimeError("Parameter 'agent_name' cannot be empty.")

        return raw_options

    def _get_agent_config(self, agent_name: str, searchinfo: dict) -> Dict[str, Any]:
        """
        Retrieves the agent configuration from the agent manager.

        Args:
            agent_name (str): Name of the agent to retrieve
            searchinfo (dict): Search information context

        Returns:
            dict: Agent configuration containing system prompt, tools, etc.

        Raises:
            RuntimeError: If the agent is not found.
        """
        agent_manager = AgentManager(searchinfo)
        agent = agent_manager.get_agent(agent_name)
        if not agent:
            raise RuntimeError(f"Agent '{agent_name}' not found")
        if agent.get("details").get("versions")[0].get("state") != "Available":
            raise RuntimeError(f"Agent '{agent_name}' is not in 'Available' state.")

        logger.info(f"Retrieved agent config for: {agent_name}")
        return agent

    def _get_mcp_configs(self, agent_config: Dict[str, Any], searchinfo: dict) -> dict:
        """
        Retrieves MCP (Model Context Protocol) configurations for the agent.

        Args:
            agent_config (dict): Agent configuration
            searchinfo (dict): Search information context

        Returns:
            dict: Dictionary containing MCP configurations
        """
        mcp_config_manager = MCPConnectionManager(searchinfo)
        mcp_configs = []
        agent_details = agent_config.get('details', {})
        versions = agent_details.get('versions', [])
        common_utils = CommonUtils(searchinfo)
        if versions:
            latest_version = versions[0]  # Assuming first is latest
            tools = latest_version.get('tools', {})
            mcps = tools.get('mcps', [])

            for mcp in mcps:
                mcp_name = mcp['name']
                mcp_tools = mcp.get('tools', [])
                connection_config = mcp_config_manager.get_mcp_connection(
                    mcp_name, include_token=True, is_meta_data=True, is_auth_bypass=True
                )
                mcp_url = connection_config['details'].get('url')
                mcp_token = connection_config['details'].get('token')
                if connection_config['type'] == 'ATLASSIAN':
                    if common_utils.is_token_refresh_required(
                        connection_config['details'].get(LAST_REFRESH_AT, None),
                        connection_config['details'].get(AUTO_REFRESH_ENABLED, False),
                    ):
                        logger.info(
                            f"Refreshing token for MCP connection: {mcp_name} "
                            f"of type ATLASSIAN via REST API"
                        )
                        # Call list_tools REST API to trigger token refresh with admin privileges
                        mcp_token = self._refresh_mcp_token_via_rest(
                            searchinfo, mcp_name, mcp_config_manager
                        )
                connection_details = {'url': mcp_url, 'auth_token': mcp_token}
                current_mcp_config = {
                    'name': mcp_name,
                    'type': connection_config['type'],
                    'tools': mcp_tools,
                    'connection_details': connection_details,
                }
                mcp_configs.append(current_mcp_config)

        logger.info(
            f"Retrieved {len(mcp_configs)} MCP configs for agent: {agent_config.get('name')}"
        )
        return {'mcps': mcp_configs}

    def _refresh_mcp_token_via_rest(
        self, searchinfo: dict, mcp_name: str, mcp_config_manager: MCPConnectionManager
    ) -> str:
        """
        Calls the list_tools REST API to trigger token refresh with admin privileges,
        then retrieves the updated token.

        Args:
            searchinfo (dict): Search information context
            mcp_name (str): Name of the MCP connection

        Returns:
            str: The refreshed token
        """
        try:
            rest_proxy = rest_proxy_from_searchinfo(searchinfo)
            url = (
                f"{rest_proxy.splunkd_uri}/servicesNS/-/Splunk_ML_Toolkit"
                f"/mltk/mcp_connection/tools?output_mode=json"
            )
            payload = json.dumps({"name": mcp_name})
            result = rest_proxy.make_rest_call("POST", url, jsonargs=payload)
            status_code = int(result.get("status", 500))
            if status_code not in (200, 201):
                error_content = result.get("content", "No content")
                error_type = result.get("error_type", "Unknown")
                logger.warning(
                    f"Failed to refresh token via REST API for {mcp_name}: "
                    f"status={status_code}, error_type={error_type}, content={error_content}"
                )
            # Re-fetch the token after refresh
            updated_config = mcp_config_manager.get_mcp_connection(
                mcp_name, include_token=True, is_meta_data=True, is_auth_bypass=True
            )
            return updated_config['details'].get('token', '')
        except Exception as e:
            logger.error(f"Error refreshing MCP token via REST API: {str(e)}")
            # Return original token as fallback
            return ''

    def _get_knowledge_base_configs(
        self, agent_config: Dict[str, Any], searchinfo: dict
    ) -> dict:
        """
        Retrieves Knowledge Base configurations for the agent.

        Args:
            agent_config (dict): Agent configuration
            searchinfo (dict): Search information context

        Returns:
            dict: Dictionary containing Knowledge Base configurations
        """
        vector_db_config_manager = VectorDbConnectionManager(searchinfo)
        vector_dbs = []
        agent_details = agent_config.get('details', {})
        versions = agent_details.get('versions', [])

        if versions:
            latest_version = versions[0]  # Assuming first is latest
            tools = latest_version.get('tools', {})
            knowledge_bases = tools.get('knowledge_bases', [])

            # Get detailed config for each KB from config manager
            all_vector_configs = vector_db_config_manager.get_config(is_auth_bypass=True)
            for item in knowledge_bases:
                if item['type'] == 'VECTOR_DB':
                    current_config = None
                    for config in all_vector_configs:
                        if config.get('name') == item['name']:
                            current_config = config
                            break
                    if not current_config:
                        raise RuntimeError(
                            f"Vector DB config '{item['name']}' not found for agent '{agent_config.get('name')}'"
                        )
                    if current_config['type'] == 'AWS_KB':
                        current_vector_config = {
                            'type': 'AWS_KB',
                            'description': current_config.get('description', ''),
                            'kb_id': current_config['details'].get('kb_id'),
                        }
                        secrets_identifier = current_config['details'].get('secrets', '')
                        secrets_realm = secrets_identifier.split(':')[0]
                        secrets_name = secrets_identifier.split(':')[1]
                        aws_secrets_str = self._fetch_secrets(
                            searchinfo, secrets_realm, secrets_name
                        )
                        aws_secrets_str = json.loads(aws_secrets_str) if aws_secrets_str else {}
                        connection_details = {
                            'region': current_config['details'].get('aws_region'),
                            'aws_access_key_id': aws_secrets_str.get('aws_access_key_id', ''),
                            'aws_access_key_token': aws_secrets_str.get(
                                'aws_access_key_token', ''
                            ),
                            'role_arn': aws_secrets_str.get('role_arn', ''),
                        }
                        current_vector_config['connection_details'] = connection_details
                        vector_dbs.append(current_vector_config)

        logger.info(
            f"Retrieved {len(vector_dbs)} Vector DB configs for agent: {agent_config.get('name')}"
        )
        return {'knowledge_bases': {'vector_dbs': vector_dbs}}

    def _get_llm_config(self, agent_config: Dict[str, Any], searchinfo: dict) -> dict:
        """
        Retrieves LLM configuration for the agent.

        Args:
            agent_config (dict): Agent configuration
            searchinfo (dict): Search information context

        Returns:
            dict: Dictionary containing LLM configuration
        """
        llm_config_manager = LLMConfigManager(searchinfo)
        agent_details = agent_config.get('details', {})
        versions = agent_details.get('versions', [])
        final_config = {}

        if versions:
            latest_version = versions[0]  # Assuming first is latest
            llm_config = latest_version.get('llm', {})
            provider = llm_config.get('provider')
            model = llm_config.get('model')
            stored_config = None
            if provider.lower() != 'splunk_default':
                connection_name = llm_config.get('connection_name')
                if connection_name:
                    stored_config = llm_config_manager.get_llm_config(
                        connection_name, is_auth_bypass=True
                    )
                else:
                    stored_config = llm_config_manager.get_llm_config(
                        provider=provider, model=model, is_auth_bypass=True
                    )
            final_config = {'provider': provider, 'model': model}
            default_temperature = (
                stored_config.get('llm_params', {}).get(
                    'response_variability', DEFAULT_RESPONSE_VARIABILITY
                )
                if stored_config
                else DEFAULT_RESPONSE_VARIABILITY
            )
            response_variability_value = llm_config.get(
                'response_variability', default_temperature
            )
            final_config['response_variability'] = (
                float(response_variability_value)
                if response_variability_value is not None
                else DEFAULT_RESPONSE_VARIABILITY
            )
            default_max_tokens = (
                stored_config.get('llm_params', {}).get('max_tokens', DEFAULT_TOKENS_AGENTS)
                if stored_config
                else DEFAULT_TOKENS_AGENTS
            )
            final_config['max_tokens'] = int(llm_config.get('max_tokens', default_max_tokens))
            default_request_timeout = (
                stored_config.get("connection_details", {}).get(
                    'request_timeout', MAX_REQUEST_TIMEOUT
                )
                if stored_config
                else MAX_REQUEST_TIMEOUT
            )
            final_config['request_timeout'] = int(
                llm_config.get('request_timeout', default_request_timeout)
            )
            default_max_rows = (
                stored_config.get('llm_params', {}).get(
                    'maximum_result_rows', MAXIMUM_RESULT_ROWS
                )
                if stored_config
                else MAXIMUM_RESULT_ROWS
            )
            final_config['max_rows'] = int(
                llm_config.get('maximum_result_rows', default_max_rows)
            )
            if provider == OPENAI or provider == ANTHROPIC:
                final_config['api_key'] = stored_config.get("connection_details", {}).get(
                    'access_token'
                )
                final_config['api_base'] = stored_config.get("connection_details", {}).get(
                    'endpoint'
                )
            elif provider == BEDROCK:
                final_config['aws_access_key_id'] = stored_config.get(
                    "connection_details", {}
                ).get("aws_access_key_id")
                final_config['aws_access_token'] = stored_config.get(
                    "connection_details", {}
                ).get("aws_secret_access_key")
                final_config['aws_region'] = stored_config.get("connection_details", {}).get(
                    "aws_region_name"
                )
                final_config['aws_role_arn'] = stored_config.get("connection_details", {}).get(
                    "aws_role_name"
                )
            elif provider == AZUREOPENAI:
                final_config['api_key'] = stored_config.get("connection_details", {}).get(
                    "access_token"
                )
                final_config['api_base'] = stored_config.get("connection_details", {}).get(
                    "endpoint"
                )
                final_config['api_version'] = stored_config.get("connection_details", {}).get(
                    "azure_api_version"
                )
        return {'llm': final_config}

    def setup(self, metadata: dict) -> dict:
        """
        Initializes the AIAgentCommand, verifies user eligibility, and prepares the execution environment.

        Args:
            metadata (dict): Metadata associated with the request.

        Returns:
            dict: Execution type and required fields.
        """
        controller_options = self.handle_arguments(self.getinfo)

        # Get agent name from parameters
        agent_name = controller_options['params'].get('agent_name')
        searchinfo = self.getinfo['searchinfo']

        # Check user eligibility to run agents
        is_user_eligible = AICommanderUtil(
            searchinfo=self.getinfo['searchinfo']
        ).check_user_role_eligibility(required_capabilities=AGENT_RUN_CAPABILITIES)

        if not is_user_eligible:
            raise RuntimeError(
                "User is not authorized to run agents. Missing required capabilities."
            )

        # Retrieve all agent configurations
        logger.info(f"Retrieving configurations for agent: {agent_name}")

        agent_config = self._get_agent_config(agent_name, searchinfo)
        if (
            controller_options.get('params').get('prompt') is None
            or controller_options.get('params').get('prompt') == ''
        ):
            task_prompt = (
                agent_config.get('details', {}).get("versions", [])[0].get('task_prompt')
            )
            if task_prompt is not None and task_prompt != '':
                controller_options['params']['prompt'] = task_prompt
            else:
                raise RuntimeError(
                    "Prompt not provided in SPL and no default task prompt found in agent configuration."
                )
        mcp_configs = self._get_mcp_configs(agent_config, searchinfo)
        kb_configs = self._get_knowledge_base_configs(agent_config, searchinfo)
        llm_config = self._get_llm_config(agent_config, searchinfo)

        # Add configurations to controller options to pass to processor
        controller_options['agent_config'] = agent_config
        controller_options['mcp_configs'] = mcp_configs
        controller_options['kb_configs'] = kb_configs
        controller_options['llm_config'] = llm_config

        # Initialize the controller with AiAgentProcessor
        self.controller = ChunkedController(self.getinfo, controller_options)
        self.total_df_count = 0

        # Set max_rows_limit from LLM config's Maximum Result Rows, default to 10
        max_rows_value = llm_config.get('llm', {}).get('max_rows', 10)
        self.max_rows_limit = int(max_rows_value) if max_rows_value else 10

        logger.info(f"Set max_rows_limit to {self.max_rows_limit} based on LLM config")

        # Get required fields from the processor
        required_fields = self.controller.get_required_fields()
        exec_type = CommandType.STATEFUL

        logger.info(f"AIAgent command initialized for agent: {agent_name}")

        return {'type': exec_type, 'required_fields': required_fields}

    def _fetch_secrets(self, searchinfo: dict, realm: str, name: str) -> str:
        response = handle_secrets(
            searchinfo,
            name,
            realm=realm,
        )
        if not response or ("status" in response and response.get("status") not in [200, 201]):
            raise RuntimeError("Failed to fetch secret. response: {}".format(response))
        return response.get("clear_password")

    def _setup_watchdog(self) -> None:
        """
        Initializes and starts the watchdog to monitor execution.
        Uses extended time limit for long-running agent operations.
        """
        # Extended memory limit for agent processing with knowledge bases and MCPs
        self.watchdog = command_util.get_watchdog(time_limit=-1, memory_limit=30000)
        self.watchdog.start()
        logger.debug("Watchdog started for aiagent command with extended limits")

    def handler(self, metadata: dict, body: bytes) -> tuple[dict, bytes]:
        """
        Handles incoming data chunks and processes them accordingly.

        Args:
            metadata (dict): Metadata of the chunk.
            body (bytes): The data chunk body.

        Returns:
            Tuple[dict, bytes]: Processed metadata and output data.
        """

        # Early return for specific metadata conditions
        if command_util.should_early_return(metadata):
            return {}

        # Handle getinfo chunk for setup
        if command_util.is_getinfo_chunk(metadata):
            return self.setup(metadata)

        finished_flag = metadata.get('finished', False)

        # Initialize watchdog if not already started
        if not hasattr(self, 'watchdog') or not self.watchdog:
            self._setup_watchdog()

        # Skip empty chunks
        if len(body) == 0:
            return {}

        # Check if we've already processed the maximum number of rows
        if self.total_df_count >= self.max_rows_limit:
            logger.info(
                f"Maximum row limit ({self.max_rows_limit}) already reached. "
                f"Skipping further processing. Current total: {self.total_df_count}"
            )
            # Return empty chunk to continue processing without adding more rows
            return ({'finished': finished_flag}, b'')

        # Load data and track processing metrics
        with Timer() as load_t:
            self.controller.load_data(body)

        current_chunk_rows = self.controller.processor.df.shape[0]

        # Calculate how many rows we can process from this chunk
        remaining_rows = self.max_rows_limit - self.total_df_count
        rows_to_process = min(current_chunk_rows, remaining_rows)

        # Limit the dataframe to only process the allowed number of rows
        if rows_to_process < current_chunk_rows:
            logger.info(
                f"Limiting chunk processing to {rows_to_process} rows "
                f"(out of {current_chunk_rows} available) to stay within limit of {self.max_rows_limit}"
            )
            self.controller.processor.df = self.controller.processor.df.head(rows_to_process)

        self.total_df_count += rows_to_process

        logger.debug(f"command=aiagent, " f"spl_load_data_time={load_t.interval}, ")

        logger.debug(
            f"command=aiagent, "
            f"chunked_df_rows_count={self.controller.processor.df.shape[0]}, "
            f"total_df_rows_count={self.total_df_count}, "
            f"max_rows_limit={self.max_rows_limit}, "
        )

        # Execute agent processing
        with Timer() as execute_t:
            self.controller.execute()

        logger.debug(
            f"command=aiagent, "
            f"spl_execute_time={execute_t.interval}, "
            f"processed_rows={self.controller.processor.total_processed_rows}"
        )

        # Generate output results
        with Timer() as output_t:
            output_body = self.controller.output_results()

        logger.debug(f"command=aiagent, " f"spl_output_results_time={output_t.interval}")

        # Clean up on completion
        if finished_flag:
            # Gracefully terminate watchdog
            if hasattr(self, 'watchdog') and self.watchdog and self.watchdog.started:
                self.watchdog.join()

            logger.info(
                f"AIAgent command completed successfully. "
                f"Total rows processed: {self.total_df_count}"
            )

        # Return processed results
        return ({'finished': finished_flag}, output_body)


if __name__ == "__main__":
    logger.debug("Starting ai_agent.py.")
    with Timer() as t:
        AIAgentCommand(handler_data=BaseChunkHandler.DATA_RAW).run()
    logger.debug("Exiting ai_agent.py gracefully. Byee!!")
