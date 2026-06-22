import base64
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Dict


class Algorithm(Enum):
    """
    Valid decryption algorithms
    """    
    AES_256_CBC = "aes-256-cbc"
    AES_256_GCM = "aes-256-gcm"


class Key:
    """
    Object representation for the key JSON.
    """    
    def __init__(
        self,
        id: int,
        desc: str,
        alg: str,
        c_key: str,
        key_class: int,
        kms: str,
        created: int,
        expires: int,
        use_iv: bool = False,
        iv_size: int = 16,
    ) -> None:
        self.key_id: int = id
        self.description: str = desc
        self.algorithm: Algorithm = Algorithm(alg)
        self.cipher_key: bytes = c_key
        self.plain_key: bytes = None
        self.use_iv: bool = use_iv
        self.iv_size: int = iv_size
        self.key_class: int = key_class
        self.kms = kms
        self.created = created
        self.expires = expires
        self.last_updated: str = datetime.now(timezone.utc).isoformat() + 'Z'

    def to_dict(self) -> Dict[str, any]:
        """
        Turn this object to a dictionary

        Returns:
            Dict[str, any]: dictionary representation of this object
        """        
        return {
            "key_id": self.key_id,
            "description": self.description,
            "algorithm": self.algorithm.value,
            "cipherKey": base64.b64encode(self.cipher_key).decode(
                "utf-8"
            ),  # Encode bytes to base64 string
            "plainKey": (
                base64.b64encode(self.plain_key).decode("utf-8")
                if self.plain_key
                else None
            ),
            "useIV": self.use_iv,
            "ivSize": self.iv_size,
            "keyclass": self.key_class,
            "kms": self.kms,
            "created": self.created,
            "expires": self.expires,
            "lastUpdated": self.last_updated
        }

    def to_json(self) -> str:
        """
        Turn this object to a JSON string

        Returns:
            str: a JSON string representation of this object
        """        
        return json.dumps(self.to_dict())


class KeyBuilder:
    """
    Builder class to keep key intialization away from functional code
    """    
    def __init__(self) -> None:
        self.key_id: int = None
        self.description: str = None
        self.algorithm: str = None
        self.cipher_key: bytes = None
        self.use_iv = False
        self.iv_size: int = 16
        self.key_class: int = None
        self.kms: str = None
        self.created: int = None
        self.expires: int = None

    def set_id(self, id):
        self.key_id = id
        return self

    def set_description(self, description):
        self.description = description
        return self

    def set_algorithm(self, algorithm):
        self.algorithm = algorithm
        return self

    def set_cipher_key(self, cipher_key):
        self.cipher_key = cipher_key
        return self

    def set_use_iv(self, use_iv):
        self.use_iv = use_iv
        return self

    def set_iv_size(self, iv_size):
        self.iv_size = iv_size
        return self

    def set_key_class(self, key_class):
        self.key_class = key_class
        return self

    def set_kms(self, kms):
        self.kms = kms
        return self

    def set_created(self, created):
        self.created = created
        return self

    def set_expires(self, expires):
        self.expires = expires
        return self

    def build(self) -> Key:
        if self.key_id is None or self.algorithm is None or self.cipher_key is None:
            raise ValueError("Invalid key.")

        return Key(
            self.key_id,
            self.description,
            self.algorithm,
            self.cipher_key,
            self.key_class,
            self.kms,
            self.created,
            self.expires,
            self.use_iv,
            self.iv_size,
        )
