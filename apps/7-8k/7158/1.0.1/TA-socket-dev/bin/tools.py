import uuid
import hashlib


class Tools:
    @staticmethod
    def generate_uuid_from_string(string: str) -> str:
        hex_string = hashlib.md5(string.encode("UTF-8")).hexdigest()
        return str(uuid.UUID(hex=hex_string))
