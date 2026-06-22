#!/usr/bin/env python3
import sys, os
import json
import re
import base64
import struct
from urllib.parse import urlencode, urlparse
import urllib.request
import ssl
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from splunklib.searchcommands import StreamingCommand, Configuration

@Configuration(local=True)
class DecryptCommand(StreamingCommand):
    """
    Decrypts Cribl-encrypted values in Splunk events using the pattern:
    #<key_id>:<iv>:<encrypted_value>#
    """
    CRIBL_ENCRYPTED_DATA_REGEX = re.compile(r'#([a-zA-Z0-9]+):([a-zA-Z0-9+/]*):([a-zA-Z0-9+/]+)#')
    
    def __init__(self):
        super(DecryptCommand, self).__init__()
        self.keys = []
        self.default_iv = b'\x00' * 16
        self.auth_tag_length = 16

        self.logging_level = 'INFO'  # Set logging level to INFO    
    
    # Called before streaming starts to initialize crypto keys.
    def prepare(self):
        splunkd_uri = self.metadata.searchinfo.splunkd_uri
        session_key = self.metadata.searchinfo.session_key
        
        try:
            secrets = self._get_passwords(splunkd_uri, session_key)
            self._init_crypto(secrets)
        except Exception as e:
            self.write_error(f"Failed to get passwords: {str(e)}")
    
    def _get_passwords(self, splunkd_uri, session_key):
        # Retrieve encryption keys from Splunk storage/passwords endpoint.
        parsed_uri = urlparse(splunkd_uri)
        url = f"{parsed_uri.scheme}://{parsed_uri.netloc}/servicesNS/nobody/TA-cribl-decrypt/storage/passwords?output_mode=json"
        
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Splunk {session_key}')
        
        # Create SSL context that doesn't verify certificates - this is the default behavior in Splunk for localhost:8089
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        try:
            with urllib.request.urlopen(req, context=ctx) as response:
                if 200 <= response.status < 300:
                    data = response.read().decode('utf-8')
                    return json.loads(data)
                else:
                    raise Exception(f"Request failed with status code {response.status}")
        except Exception as e:
            raise Exception(f"Failed to retrieve passwords: {str(e)}")
    
    def _init_crypto(self, secrets):
        # Initialize encryption keys from password/secrets response.
        if 'entry' not in secrets:
            self.write_error(f"secrets.entry not found: {json.dumps(secrets)}")
            return
        
        for entry in secrets.get('entry', []):
            clear_password = entry.get('content', {}).get('clear_password')

            # Make sure we only load keys from our App!
            app = entry.get('acl', {}).get('app')
            if clear_password and app == 'TA-cribl-decrypt':
                try:
                    key = json.loads(clear_password)
                    self.keys.append(key)
                except Exception as e:
                    # Surface errors in the Splunk UI
                    self.write_error(f"Failed to parse key: {str(e)} {clear_password}")
                    self.write_error(f"Entry value: {entry}")
    
    def stream(self, records):
        # Process each record, decrypting encrypted fields - even when nested inside a field i.e. _raw.

        for record in records:
            # Decrypt all string fields in the record
            for field, value in list(record.items()):
                if isinstance(value, str):
                    record[field] = self._decrypt_value(field, value)
            yield record
    
    def _decrypt_value(self, field, value):
        # Decrypt a value by replacing all encrypted patterns in that value.
        # This means that all encrypted values inside of _raw and all indexed fields
        # will be decrypted.

        def replace_match(match):
            key_id = match.group(1)
            iv_b64 = match.group(2)
            encrypted_value = match.group(3)
            
            try:
                iv = base64.b64decode(iv_b64) if iv_b64 else None
                decrypted = self._decrypt_with_key(encrypted_value, key_id, iv)
                
                return decrypted
            except Exception as e:
                #
                # Note that this error will only be written once, but the search.log will contain the following 
                # for each subsequent occurrence: "Error adding inspector message: invalid level or message already exists"
                #
                self.write_info(f"Decryption error for keyId {key_id} on field {field}: {str(e)}")
                
                # If decryption fails, return original match
                return match.group(0)
        
        return self.CRIBL_ENCRYPTED_DATA_REGEX.sub(replace_match, value)
    
    def _decrypt_with_key(self, value, key_id, iv=None):
        # Decrypt a value using the specified key.
        
        # Find the key
        key = next((k for k in self.keys if k.get('key_id') == key_id), None)
        if not key:
            raise ValueError(f"keyId {key_id} not found")
        
        # Decode the plain key (double base64 encoded)
        plain_key = base64.b64decode(base64.b64decode(key['plainKey']).decode('utf-8'))
        
        # Use provided IV or default
        iv_bytes = iv if iv else self.default_iv
        
        algorithm_name = key.get('algorithm', 'aes-256-cbc')
        
        if algorithm_name == 'aes-256-gcm':
            # Handle GCM mode with authentication tag to match JS Crypto library
            
            # Ensure that the value is properly padded for base64 decoding - avoids an "incorrect padding" error
            buffer_value = base64.b64decode(value + '===')
            encrypted_data = buffer_value[:-self.auth_tag_length]
            auth_tag = buffer_value[-self.auth_tag_length:]
            
            cipher = Cipher(
                algorithms.AES(plain_key),
                modes.GCM(iv_bytes, auth_tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

            return decrypted_data.decode('utf-8')
        else:
            # Handle CBC mode (default)
            cipher = Cipher(
                algorithms.AES(plain_key),
                modes.CBC(iv_bytes),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            # Ensure that the value is properly padded for base64 decoding - avoids an "incorrect padding" error
            encrypted_data = base64.b64decode(value + '===')
            decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

            # Remove PKCS7 padding added by default in the JS Crypto library
            unpadder = padding.PKCS7(128).unpadder()
            decrypted_data = unpadder.update(decrypted_data) + unpadder.finalize()

            return decrypted_data.decode('utf-8')

if __name__ == '__main__':
    try:
        DecryptCommand().process()
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)