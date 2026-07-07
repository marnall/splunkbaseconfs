import json
import logging
import os
import sys
from datetime import datetime
from hashlib import sha256
from logging.handlers import RotatingFileHandler

from client import CyberintClient
from rest_client import RestError
from runner import CyberintRunner
from utils import validate_url

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from splunklib.client import connect
from splunklib.modularinput import Argument, Event, EventWriter, InputDefinition, Scheme
from splunklib.modularinput import Script as BaseScript
from splunklib.modularinput import ValidationDefinition


class Script(BaseScript):
    APP = os.path.basename(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    USERNAME = 'cyberint_secret'

    def get_scheme(self) -> Scheme:
        """
        Getting Cyberint data input scheme.

        Returns:
            Scheme: The input scheme for the user.
        """

        scheme = Scheme('Cyberint Splunk Connector')
        scheme.description = 'Contact *Cyberint Support* to get an API token'

        scheme.add_argument(
            Argument('api_url',
                     title='Cyberint URL',
                     description='The URL of Cyberint. For example, https://example.cyberint.io.',
                     required_on_create=True))
        scheme.add_argument(
            Argument('api_token',
                     title='Secret Key for API Token',
                     description=
                     'The key from the secrets management page that represents the API token.',
                     required_on_create=True))
        scheme.add_argument(
            Argument('start_time',
                     title='Start Time',
                     description='The time to start pulling incidents from Cyberint.'))

        return scheme

    def validate_input(self, definition: ValidationDefinition):
        """
        Validating the input from the user.

        Args:
            definition (ValidationDefinition): The parameters from the user.

        Raises:
            ValueError: The input from the client is not valid.
        """

        session_key = definition.metadata['session_key']
        api_token = self._get_plain_api_token(session_key, definition.parameters['api_token'])
        api_url = definition.parameters['api_url']

        validate_url(api_url)

        try:
            with CyberintClient(api_url, api_token) as cyberint:
                if cyberint.list_alerts(1, 10) is None:
                    raise ValueError('Got invalid response from Cyberint client')
        except RestError as err:
            raise ValueError(f'Got error from Cyberint client: {err}') from err
        except KeyError as err:
            raise ValueError(f'Missing required parameter {err}') from err

    def stream_events(self, inputs: InputDefinition, ew: EventWriter):
        """
        Sending events to Splunk.

        Args:
            inputs (InputDefinition): The data inputs configurations.
            ew (EventWriter): The object that writes the events into Splunk
        """

        default_start_time = datetime.now().isoformat()

        session_key = self._input_definition.metadata['session_key']

        for input_name, input_item in inputs.inputs.items():
            logging.info('Executing stream events for %s', input_name)

            checkpoint_filename = self._get_checkpoint_filename(
                checkpoint_dir=inputs.metadata['checkpoint_dir'],
                input_name=input_name,
            )
            logging.debug('%s checkpoint filename: %s', input_name, checkpoint_filename)

            api_token = self._get_plain_api_token(session_key, input_item['api_token'])

            with CyberintRunner(base_url=input_item['api_url'],
                                access_token=api_token,
                                start_time=input_item.get('start_time', default_start_time),
                                checkpoint_filename=checkpoint_filename) as runner:
                for alert in runner.run():
                    ew.write_event(Event(stanza=input_name, data=json.dumps(alert)))

    @staticmethod
    def _get_checkpoint_filename(checkpoint_dir: str, input_name: str) -> str:
        filename = input_name[input_name.find('://') + 3:].lower().replace(' ', '_')
        filename = f'{filename}_{sha256(input_name.encode()).hexdigest()}'

        return os.path.join(checkpoint_dir, filename)

    def _get_plain_api_token(self, session_key: str, key: str) -> str:
        logging.info('Getting API token from secret storage: %s', key)

        service = connect(token=session_key, app=self.APP)
        for storage_item in service.storage_passwords:
            if storage_item.realm == key and storage_item.username == self.USERNAME:
                return storage_item.clear_password

        raise ValueError(f'API token {key} was not found in secret storage')


def main():
    log_filename = os.path.join(os.path.dirname(__file__), 'connector.log')
    handler = RotatingFileHandler(filename=log_filename, maxBytes=1 * 1024 * 1024)
    logging.basicConfig(level=logging.INFO, handlers=[handler])

    sys.exit(Script().run(sys.argv))


if __name__ == '__main__':
    main()
