import sys
import import_declare_test
import base64
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))  # nopep8

from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

def stream(streaming_command: StreamingCommand, events):

    for event in events:
        if streaming_command.action == "decode":
            new_field = f"{str(streaming_command.field)}_decoded"
            try:
                # Ensure the field content is a string before encoding to bytes for b64decode
                content_to_decode = event[str(streaming_command.field)]
                if isinstance(content_to_decode, str):
                    event[new_field] = base64.b64decode(content_to_decode).decode("utf-8")
                else:
                    # Handle cases where the content might not be a string (e.g., bytes already)
                    event[new_field] = base64.b64decode(content_to_decode).decode("utf-8")
            except Exception as e:
                event["error"] = f"Decoding error: {e}"
        elif streaming_command.action == "encode":
            new_field = f"{str(streaming_command.field)}_encoded"
            try:
                # Ensure the field content is a string before encoding to bytes for b64encode
                content_to_encode = event[str(streaming_command.field)]
                if isinstance(content_to_encode, str):
                    event[new_field] = base64.b64encode(content_to_encode.encode("utf-8")).decode("utf-8")
                elif isinstance(content_to_encode, bytes):
                    # If it's already bytes, just encode it
                    event[new_field] = base64.b64encode(content_to_encode).decode("utf-8")
                else:
                    # Convert other types to string before encoding
                    event[new_field] = base64.b64encode(str(content_to_encode).encode("utf-8")).decode("utf-8")
            except Exception as e:
                event["error"] = f"Encoding error: {e}"
        yield event
