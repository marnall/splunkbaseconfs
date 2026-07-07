import re
import sys
import os

from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands.validators import Validator


def is_field_name(field_name):
    """
    Checks if match with a field name pattern
    """
    fieldname_pattern = re.compile("^[_.a-zA-Z-][_.a-zA-Z0-9-]*$")
    return fieldname_pattern.match(fieldname_pattern, field_name)


def is_hash_value(value):
    """
    Checks if match with a SHA-256, SHA-1, or MD5 hash
    """
    hash_pattern = re.compile(r"""^[a-f0-9]+$""")

    value_str = str(value).lower()
    size = len(value_str)

    valid_pattern = hash_pattern.match(value_str)
    valid_length = size == 32 or size == 40 or size == 64
    return valid_pattern and valid_length


def is_url(value):
    try:
        result = urlparse(value)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


class HashValidator(Validator):
    """
    Validates MD5 values.
    """

    pattern = re.compile(r"""^[a-f0-9]+$""")

    def __call__(self, value):
        if value is not None:
            value = str(value).lower()
            size = len(value)

            valid_pattern = HashValidator.pattern.match(value)
            valid_length = size == 32 or size == 40 or size == 64

            if not valid_pattern or not valid_length:
                raise ValueError(f"Expected SHA-256, SHA-1 or MD5 value: {value}")
        return value

    def format(self, value):
        return self.__call__(value)
