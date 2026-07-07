from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
import json
import sys
import logging
import base64


APP_NAME = Path(__file__).absolute().parts[-3]
APP_DIR = Path(environ['SPLUNK_HOME']).absolute() / 'etc' / 'apps' / APP_NAME
BIN_DIR = Path(APP_DIR / 'bin')
LOCAL_DIR = Path(APP_DIR / 'local')
DEFAULT_DIR = Path(APP_DIR / 'default')
LICENSE_FILE = Path(LOCAL_DIR / '.cmmc.license')
KEY_FILE = Path(DEFAULT_DIR / 'cmmc.key')
SLIM_DESIGNATOR_FILE = Path(DEFAULT_DIR / 'ascera.slim.json')


sys.path.append(
    str(BIN_DIR)
)


from helpers.logger import setup_logger
from helpers.licensing import (
    get_slim_license,
    check_for_slim_designator
)
import pendulum
from Crypto.Cipher import AES
from Crypto.Hash import SHA256


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_licensing_rest_endpoint'
)


class Licensing(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        self.log_start_message()

        # Load data submitted by browser (in bytes)
        data = json.loads(
            in_string.decode('utf-8')
        )


        # Assignments from submitted data
        for i in data['form']:
            key = i[0]
            value = i[1]

            if key == 'license':
                license_data = value

            elif key == 'action':
                action = value


        if action == 'add_new_license':
            logger.info(f'message="Received request to add new license: {license_data}."')

            self.save_new_license(
                license_data=license_data
            )

            license_status = self.get_license_status()

            self.log_stop_message()

            return {
                'payload': {
                    'license_status': license_status,
                    'status': 'success'
                },
                'status': 200
            }


        elif action == 'get_license_status':
            logger.info(f'message="Received request to retrieve license data."')
            license_status = self.get_license_status()

            if not license_status['license']:
                is_slim = check_for_slim_designator(SLIM_DESIGNATOR_FILE)

                if is_slim:
                    license_status = get_slim_license()

            self.log_stop_message()

            return {
                'payload': {
                    'license_status': license_status,
                    'status': 'success'
                },
                'status': 200
            }



    def read_license(self, license_data, secret_key):
        decoded_license_data = self.decode_license_data(
            license_data=license_data
        )

        decrypted_license_data = self.decrypt_license_data(
            key=secret_key,
            source=decoded_license_data
        )

        if decrypted_license_data:
            license_data_obj = json.loads(
                decrypted_license_data
            )

        else:
            license_data_obj = None

        return license_data_obj


    def load_license_file(self, path):
        logger.info(f'message="Loading saved license file from {path}."')

        with open(path, 'r') as license_file:
            return license_file.read().strip()


    def decode_license_data(self, license_data):
        logger.info(f'message="B64 decoding base 64 encoded license data."')

        try:
            bytes_b64 = license_data.encode('utf-8')
            bytes_decoded =  base64.b64decode(bytes_b64)
            decoded_string = bytes_decoded.decode('utf-8')
            return decoded_string

        except Exception as e:
            logger.error(f'status="ERROR", message="An error occurred while B64 decoding the license: {str(e)}"');
            return None


    def decrypt_license_data(self, key, source, decode=True):
        logger.info(f'message="Decrypting AES256 encrypted license data."')

        try:
            if decode:
                source = base64.b64decode(source.encode("utf-8"))

            key = SHA256.new(key.encode('utf-8')).digest()
            IV = source[:AES.block_size]
            decryptor = AES.new(key, AES.MODE_CBC, IV)
            data = decryptor.decrypt(source[AES.block_size:])
            padding = data[-1]

            if data[-padding:] != bytes([padding]) * padding:
                raise ValueError("Invalid padding...")

            return data[:-padding].decode('utf-8')

        except Exception as e:
            logger.error(f'status="ERROR", message="An error was encountered when decrypting the license data: {str(e)}"')
            return None


    def load_b64_secret_key(self, path):
        logger.info(f'message="Loading base 64 secret key from {path}."')

        with open(path, 'r') as key_file:
            return key_file.read().strip()


    def decode_secret_key(self, secret_key):
        logger.info(f'message="Decoding base 64 secret key."')

        return base64.b64decode(
            secret_key.encode('utf-8')
        ).decode('utf-8')


    def get_license_status(self):
        license_status = {
            'license': None,
            'valid_license': False,
            'message': None
        }
        

        try:
            b64_secret_key = self.load_b64_secret_key(str(KEY_FILE))
            logger.info(f'status="success", message="Successfully loaded base 64 secret key from {str(KEY_FILE)}."')

        except Exception as e:
            error = str(e)
            message = f'An error occurred while loading the base 64 secret key from {str(KEY_FILE)}: {error}'
            logger.error(f'status="ERROR", message="{message}", error="{error}"')
            license_status['message'] = message
            return license_status


        try:
            secret_key = self.decode_secret_key(b64_secret_key)
            logger.info(f'status="success", message="Successfully b64 decoded the base 64 secret key."')

        except Exception as e:
            error = str(e)

            if error == 'Incorrect padding':
                message = f'Invalid secret key. Restore the secret key to use your license.'

            else:
                message = f'An error occurred while b64 decoding the base 64 secret key: {error}'

            logger.error(f'status="ERROR", message="{message}", error="{error}"')
            license_status['message'] = message
            return license_status


        try:
            encrypted_license_data = self.load_license_file(str(LICENSE_FILE))
            logger.info(f'status="success", message="Successfully loaded saved license file from {str(LICENSE_FILE)}."')

        except FileNotFoundError:
            message = 'No license found.'
            license_status['message'] = message
            logger.info(f'status="not found", message="No saved license found at {str(LICENSE_FILE)}: {message}"')

        except Exception as e:
            error = str(e)
            message = f'An error occurred while loading the saved license file from {str(LICENSE_FILE)}: {error}'
            logger.error(f'status="ERROR", message="{message}", error="{error}"')
            license_status['message'] = message

        else:
            license_obj = self.read_license(
                license_data=encrypted_license_data,
                secret_key=secret_key
            )

            if license_obj:
                license_status['license'] = license_obj

                now_epoch_s = int(pendulum.now().format('X'))
                license_exp_epoch_s = license_obj['expires']

                if now_epoch_s < license_exp_epoch_s:
                    message = 'Valid license.'
                    license_status['valid_license'] = True
                    license_status['message'] = message
                    logger.info(f'status="success", message="License determined to be valid: {message}"')

                else:
                    message = 'License expired.'
                    license_status['message'] = message
                    logger.info(f'status="success", message="License determined to be invalid and expired: {message}", expired="{license_exp_epoch_s}"')

            else:
                message = 'Invalid license.'
                license_status['message'] = message
                logger.info(f'status="success", message="License determined to be invalid"')

        return license_status


    def save_new_license(self, license_data):
        logger.info(f'message="Creating /local directory if it does not exist."')

        LOCAL_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        logger.info(f'Saving license data ({license_data}) to {str(LICENSE_FILE)}.')

        with open(str(LICENSE_FILE), 'w+') as license_file:
            license_file.write(license_data)

        logger.info(f'status="success", message="Successfully saved license data ({license_data}) to {str(LICENSE_FILE)}."')

        return


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Licensing REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Licensing REST endpoint started at {timestamp}."')
        return


    def done(self):
        pass
