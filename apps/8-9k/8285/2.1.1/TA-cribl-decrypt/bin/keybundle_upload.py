import base64
import io
from typing import Dict
import os
import sys
import json
import logging as logger
import gzip

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from splunk.persistconn.application import PersistentServerConnectionApplication  # type: ignore
from splunk.clilib.bundle_paths import make_splunkhome_path  # type: ignore

from key import Key
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

import handler_utils as utils
from secret_manager import SecretManager

logger.basicConfig(
    level=logger.DEBUG,
    format="%(asctime)s %(levelname)s  %(message)s",
    datefmt="%m-%d-%Y %H:%M:%S.000 %z",
    filename=make_splunkhome_path(["var", "log", "splunk", "ta-cribl-decrypt.log"]),
    filemode="a",
)

APP_NAME = "TA-cribl-decrypt"

logger.info("New persistent connection started for TA-Cribl-Decrypt (key uploader).")

# https://stackoverflow.com/questions/60207053/creating-a-rest-handler-for-any-of-splunks-rest-endpoints
if sys.platform == "win32":
    import msvcrt

    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


class Upload(PersistentServerConnectionApplication):
    """
    Received a Cribl keybundle and uploads the keys to the Splunk secret store.
    """

    def __init__(self, _command_line, _command_arg) -> None:
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string: bytes) -> str:
        """
        Handles the incoming request from the REST app server.

        Args:
            in_string (bytes): The request from the REST app server.

        Returns:
            str: JSON response from this endpoint.
        """
        try:
            request_data: Dict[str, str] = json.loads(in_string)
            session_key = utils.get_session_token(request_data)
            secret_manager = SecretManager(session_key)

            base64_content: bytes = ""
            for field in request_data["form"]:
                if field[0] == "file":
                    base64_content = field[1]

            content = base64.b64decode(base64_content)

            logger.info(f"Processing keybundle.")

            num_successful = 0

            with gzip.GzipFile(fileobj=io.BytesIO(content)) as gz:
                tar_content = gz.read()

                secret = self._extract_file(tar_content, "cribl.secret")

                if secret is None:
                    logger.error("No cribl.secret found in the uploaded file. Key bundle is invalid.")
                    return utils.wrap_response("No cribl.secret found in the uploaded file. Key bundle is invalid.",500,)
                
                secret_key = base64.b64decode(secret)      
                keys_file = self._extract_file(tar_content, "keys.json")

                if keys_file is None:
                    logger.error("No keys.json was found in the uploaded file. Key bundle is invalid.")
                    return utils.wrap_response("No keys.json was found in the uploaded file. Key bundle is invalid.",500,)

                keys = utils.get_keys(keys_file)

                for key in keys:
                    try:
                        logger.debug(f"Found key in file with description {key.description}.")
                        plainKey = base64.b64encode(self._decrypt(secret_key, key))
                        key.plain_key = plainKey

                        if secret_manager.key_exists(key.key_id):
                            response = secret_manager.update_key(key)
                        else:
                            response = secret_manager.add_key(key)
                        if response.status == 201:
                            logger.debug(f"Successfully stored secret for key with key ID {key.key_id}")
                            num_successful += 1
                        elif response.status == 200:
                            logger.debug(f"Successfully updated stored secret for key with key ID {key.key_id}")
                            num_successful += 1
                        else:
                            logger.warning(f"Failed to save secret for key ID {key.key_id}. Received response {response.status} with message {response.messages}.")
                    except Exception as e:
                        logger.exception(f"Failed to save secret for key ID {key.key_id}")
                        return utils.wrap_response("Internal error, see logs for details.",500,)

            if len(keys) > 0 and num_successful == 0:
                return utils.wrap_response("Internal error. No keys were processed. See logs for more details.",500,)

            resp = f"Successfully processed {num_successful} of {len(keys)} keys in the uploaded key bundle."
            logger.info(resp)
            return utils.wrap_response(resp, 200)

        except Exception:
            logger.exception("Exception uploading file")
            return utils.wrap_response("Internal error. No keys were processed. See logs for more details.",500,)

    def _extract_file(self, tar_bytes: bytes, filename: str) -> bytes:
        """
        Extract the file content from a tarball without using the tar library or file operations.

        Args:
            tar_bytes (bytes): the tarball content in bytes
            filename (str): the name of the file to pull from the tarball

        Returns:
            bytes: File content in bytes
        """
        offset = 0
        while offset < len(tar_bytes):
            # Read the header, break if it's empty and we're done reading.
            header = tar_bytes[offset : offset + utils.TAR_HEADER_SIZE]
            if not header:
                break

            # Extract filename from header (its first 100 bytes are filename) while stripping nulls.
            file_name = header[0:100].decode("utf-8").strip("\x00")

            # Gets the file size. Magic numbers here (124 -> 136) represent location of size info.
            # Then converts the string to an int (base 8, tar stores numeric values in octal).
            file_size = int(header[124:136].decode("utf-8").strip("\x00"), 8)

            # Read content for the passed file
            if file_name == filename:
                # How many bytes from the start?
                start_pointer = offset + utils.TAR_HEADER_SIZE
                # How many bytes from the end?
                end_pointer = offset + utils.TAR_HEADER_SIZE + file_size

                file_data = tar_bytes[start_pointer:end_pointer]
                return file_data

            # Progress the offset, move to next file header.
            # By adding utils.TAR_HEADER_SIZE - 1 we ensure rounding to the next block.
            offset += (
                utils.TAR_HEADER_SIZE
                + ((file_size + 511) // utils.TAR_HEADER_SIZE) * utils.TAR_HEADER_SIZE
            )

    def _decrypt(self, secret: bytes, key: Key) -> bytes:
        """
        Decrypt the AES-256-CBC encrypted keys to be stored in the Key object stored in Splunk

        Args:
            secret (bytes): The secret key from cribl.secret
            key (Key): The key object to pull the cipherKey from

        Returns:
            bytes: The decrypted key in bytes
        """
        # Extract the 256-bit (32 bytes) AES key
        aes_key = secret[:32]
        
        # Create a 16-byte IV (initialization vector) - all zeros
        iv = bytes(16)
        
        # Create the cipher object
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        
        # Create a decryptor and decrypt the data
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(key.cipher_key) + decryptor.finalize()

        # Remove PKCS7 padding added by default in the JS Crypto library used in Cribl
        unpadder = padding.PKCS7(128).unpadder()
        decrypted_data = unpadder.update(decrypted_data) + unpadder.finalize()
        
        return decrypted_data
