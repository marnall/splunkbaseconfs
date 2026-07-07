# encoding = utf-8
import splunklib.client as client
from splunklib.binding import HTTPError
from logger import Logger
from enums import ModInputType, ModularInputConfig
from exceptions import ModularInputExistsException, ModularInputNotFoundException


class ModularInputManager:
    APP_NAME = "cisco-cloud-security"
    OWNER = "nobody"

    def __init__(self, session_key, host="localhost", port=8089):
        """
        Initializes the ModularInputManager.

        Args:
            session_key (str): The Splunk session key for authentication.
            host (str, optional): The Splunk management host. Defaults to "localhost".
            port (int, optional): The Splunk management port. Defaults to 8089.
        """
        self._logger = Logger()
        self.service = client.connect(
            host=host, port=port, token=session_key, app=self.APP_NAME, owner=self.OWNER
        )

    def _get_inputs(self):
        """
        Returns the Inputs collection object.

        Note:
            This does not fetch all inputs immediately. It returns a handle to the collection.
            Specific inputs are fetched only when accessed via __getitem__ or when iterating.

        Returns:
            splunklib.client.Inputs: The inputs collection object.
        """
        return self.service.inputs

    def create_input(self, input_kind, input_name, config: ModularInputConfig):
        """
        Creates a new modular input.

        Args:
            input_kind (InputType or str): The kind of modular input (e.g., InputType.APP_DISCOVERY).
            input_name (str): The name of the input to create.
            config (ModularInputConfig): The configuration object containing input parameters.

        Returns:
            splunklib.client.Input: The created input object.

        Raises:
            ModularInputExistsException: If an input with the same name and kind already exists.
            ValueError: If required configuration parameters are missing.
            Exception: If creation fails for other reasons.
        """
        try:
            if not all(
                [config.interval, config.index, config.log_level, config.org_id]
            ):
                raise ValueError(f"Missing required fields for creation.")

            inputs = self._get_inputs()
            kind_value = (
                input_kind.value if isinstance(input_kind, ModInputType) else input_kind
            )

            params = config.to_splunk_params()
            self._logger.info(f"Creating modular input {input_name} of kind {kind_value} with params: {params}")
            new_input = inputs.create(input_name, kind_value, **params)
            self._logger.info(
                f"Created modular input {input_name} of kind {kind_value}"
            )
            return new_input
        except HTTPError as e:
            if e.status == 409:
                self._logger.error(
                    f"Input {input_name} of kind {input_kind} already exists."
                )
                raise ModularInputExistsException(
                    f"Input {input_name} of kind {input_kind} already exists."
                )
            else:
                self._logger.error(f"Failed to create input {input_name}: {str(e)}")
                raise
        except Exception as e:
            self._logger.error(f"Failed to create input {input_name}: {str(e)}")
            raise

    def get_input(self, input_kind, input_name) -> ModularInputConfig:
        """
        Retrieves a modular input configuration.

        Args:
            input_kind (ModInputType or str): The kind of modular input.
            input_name (str): The name of the input to retrieve.

        Returns:
            ModularInputConfig: The configuration object containing input parameters.

        Raises:
            ModularInputNotFoundException: If the input does not exist.
            Exception: If retrieval fails for other reasons.
        """
        try:
            inputs = self._get_inputs()
            kind_value = (
                input_kind.value if isinstance(input_kind, ModInputType) else input_kind
            )

            current_input = inputs[(input_name, kind_value)]

            interval_value = current_input.content.get('interval')
            time_window_value = current_input.content.get('time_window')
            config = ModularInputConfig(
                interval=int(interval_value) if interval_value else None,
                index=current_input.content.get('index'),
                log_level=current_input.content.get('Log_Level'),
                org_id=current_input.content.get('org_id'),
                time_window=int(time_window_value) if time_window_value else None,
            )

            self._logger.info(
                f"Retrieved modular input {input_name} of kind {kind_value}"
            )
            return config
        except KeyError:
            self._logger.error(f"Input {input_name} of kind {input_kind} not found.")
            raise ModularInputNotFoundException(
                f"Input {input_name} of kind {input_kind} not found."
            )
        except Exception as e:
            self._logger.error(f"Failed to retrieve input {input_name}: {str(e)}")
            raise

    def update_input(self, input_kind, input_name, config: ModularInputConfig):
        """
        Updates an existing modular input.

        Args:
            input_kind (InputType or str): The kind of modular input.
            input_name (str): The name of the input to update.
            config (ModularInputConfig): The configuration object containing updated parameters.

        Returns:
            splunklib.client.Input: The updated input object.

        Raises:
            ModularInputNotFoundException: If the input does not exist.
            Exception: If update fails for other reasons.
        """
        try:
            inputs = self._get_inputs()
            kind_value = (
                input_kind.value if isinstance(input_kind, ModInputType) else input_kind
            )

            params = config.to_splunk_params()

            current_input = inputs[(input_name, kind_value)]
            current_input.update(**params)
            self._logger.info(
                f"Updated modular input {input_name} of kind {kind_value}"
            )
            return current_input
        except KeyError:
            self._logger.error(f"Input {input_name} of kind {input_kind} not found.")
            raise ModularInputNotFoundException(
                f"Input {input_name} of kind {input_kind} not found."
            )
        except Exception as e:
            self._logger.error(f"Failed to update input {input_name}: {str(e)}")
            raise

    def delete_input(self, input_kind, input_name):
        """
        Deletes a modular input.

        Args:
            input_kind (InputType or str): The kind of modular input.
            input_name (str): The name of the input to delete.

        Raises:
            ModularInputNotFoundException: If the input does not exist.
            Exception: If deletion fails for other reasons.
        """
        try:
            inputs = self._get_inputs()
            kind_value = (
                input_kind.value if isinstance(input_kind, ModInputType) else input_kind
            )
            inputs.delete(input_name, kind_value)
            self._logger.info(
                f"Deleted modular input {input_name} of kind {kind_value}"
            )
        except KeyError:
            msg = f"Input {input_name} of kind {input_kind} not found."
            self._logger.error(msg)
            raise ModularInputNotFoundException(msg)
        except HTTPError as e:
            if e.status == 404:
                msg = f"Input {input_name} of kind {input_kind} not found."
                self._logger.error(msg)
                raise ModularInputNotFoundException(msg)
            else:
                self._logger.error(f"Failed to delete input {input_name}: {str(e)}")
                raise
        except Exception as e:
            self._logger.error(f"Failed to delete input {input_name}: {str(e)}")
            raise
