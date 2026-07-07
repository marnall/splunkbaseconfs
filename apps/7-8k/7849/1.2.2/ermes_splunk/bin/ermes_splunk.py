import json
import logging
import os
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Dict, List

# NOTE: splunklib and other 3rd party dependencies must exist within ermes_splunk/lib/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import certifi  # noqa: E402
from splunklib.modularinput import (  # noqa: E402
    Argument,
    Event,
    EventWriter,
    InputDefinition,
    Scheme,
    Script,
    ValidationDefinition,
)

_PRODUCT_NAME = "Ermes Browser Security"

_DEFAULT_API_SERVER = "https://api.shield.ermessecurity.com"

_API_SERVER = "api_server"
_CLIENT_ID = "client_id"
_CLIENT_SECRET = "client_secret"

_DATETIME_STRPTIME_FORMAT_ISO_8601 = "%Y-%m-%dT%H:%M:%S.%f%z"

_CAT_GENERAL = "general"
_CAT_AUTHENTICATION = "dashboard_auth"
_CAT_DASHBOARD = "dashboard_audit"
_CAT_DEVICE_STATUS = "device_status"

_NO_LOG_DATA_CATEGORIES = {
    _CAT_GENERAL,
    _CAT_AUTHENTICATION,
    _CAT_DASHBOARD,
    _CAT_DEVICE_STATUS,
}


def _datetime_to_string(dt: datetime) -> str:
    # If the object is a datetime with no timezone info, we interpret it as an
    # unaware datetime object representing UTC date/time.
    if not dt.tzinfo:
        # Add timezone info to always return timezone-aware string representation
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat(timespec="microseconds")


def _string_to_datetime(dt_string: str) -> datetime:
    return datetime.strptime(dt_string, _DATETIME_STRPTIME_FORMAT_ISO_8601)


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def _get_token(
    ssl_ctx: ssl.SSLContext, api_server: str, client_id: str, client_secret: str
) -> str:
    body = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }
    data = urllib.parse.urlencode(body).encode("utf-8")
    request = urllib.request.Request(f"{api_server}/oauth/token", data=data)
    with urllib.request.urlopen(request, context=ssl_ctx) as response:
        return json.loads(response.read())["access_token"]


def _fetch_events_page(
    ssl_ctx: ssl.SSLContext,
    api_server: str,
    from_time: datetime,
    page: int,
    access_token: str,
) -> List[Dict]:
    params = urllib.parse.urlencode(
        {
            "page": page,
            "max_results": 100,
            "gt__created": _datetime_to_string(from_time),
            "sort": "_created",
        }
    )
    request = urllib.request.Request(
        f"{api_server}/public/v1/events?{params}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(request, context=ssl_ctx) as response:
        return json.loads(response.read())["_items"]


class ErmesForEnterprise(Script):
    """All modular inputs should inherit from the abstract base class Script
    from splunklib.modularinput.script.
    They must override the get_scheme and stream_events functions, and,
    if the scheme returned by get_scheme has Scheme.use_external_validation
    set to True, the validate_input function.
    """

    def get_scheme(self) -> Scheme:
        """When Splunk starts, it looks for all the modular inputs defined by
        its configuration, and tries to run them with the argument --scheme.
        Splunkd expects the modular inputs to print a description of the
        input in XML on stdout. The modular input framework takes care of all
        the details of formatting XML and printing it. The user need only
        override get_scheme and return a new Scheme object.

        :return: scheme, a Scheme object
        """
        # Splunk will display "Ermes Browser Security" to users for this input
        scheme = Scheme(_PRODUCT_NAME)

        scheme.description = f"Ingest events from {_PRODUCT_NAME}."

        # If you set external validation to True, without overriding validate_input,
        # the script will accept anything as valid. Generally you only need external
        # validation if there are relationships you must maintain among the
        # parameters, such as requiring min to be less than max in this example,
        # or you need to check that some resource is reachable or valid.
        # Otherwise, Splunk lets you specify a validation string for each argument
        # and will run validation internally using that string.
        # scheme.use_external_validation = True
        scheme.use_external_validation = True

        scheme.use_single_instance = False

        api_server_argument = Argument(_API_SERVER)
        api_server_argument.title = "API Server"
        api_server_argument.data_type = Argument.data_type_string
        api_server_argument.description = f"Ermes Events API Server (Optional. Default value is '{_DEFAULT_API_SERVER}')."
        # Optional, default to _DEFAULT_API_SERVER if missing
        api_server_argument.required_on_create = False
        scheme.add_argument(api_server_argument)

        client_id_argument = Argument(_CLIENT_ID)
        client_id_argument.title = "Client ID"
        client_id_argument.data_type = Argument.data_type_string
        client_id_argument.description = "OAuth Client ID."
        client_id_argument.required_on_create = True
        scheme.add_argument(client_id_argument)

        client_secret_argument = Argument(_CLIENT_SECRET)
        client_secret_argument.title = "Client Secret"
        client_secret_argument.data_type = Argument.data_type_string
        client_secret_argument.description = "OAuth Client Secret."
        client_secret_argument.required_on_create = True
        scheme.add_argument(client_secret_argument)

        return scheme

    def validate_input(self, validation_definition: ValidationDefinition) -> None:
        """
        When using external validation, after splunkd calls the modular input with
        --scheme to get a scheme, it calls it again with --validate-arguments for
        each instance of the modular input in its configuration files, feeding XML
        on stdin to the modular input to do validation. It is called the same way
        whenever a modular input's configuration is edited.

        If validate_input does not raise an Exception, the input
        is assumed to be valid. Otherwise it prints the exception as an error message
        when telling splunkd that the configuration is invalid.

        :param validation_definition: a ValidationDefinition object
        """

        # Get the values of the parameters
        api_server = (
            validation_definition.parameters.get(_API_SERVER) or _DEFAULT_API_SERVER
        )
        client_id = validation_definition.parameters[_CLIENT_ID]
        client_secret = validation_definition.parameters[_CLIENT_SECRET]

        ssl_ctx = _ssl_context()
        try:
            access_token = _get_token(ssl_ctx, api_server, client_id, client_secret)
        except Exception:
            raise ValueError(
                "Unable to retrieve access token. Please check your configuration parameters."
            )

        try:
            _fetch_events_page(
                ssl_ctx,
                api_server,
                from_time=datetime.now(tz=timezone.utc) - timedelta(seconds=10),
                page=1,
                access_token=access_token,
            )
        except Exception:
            raise ValueError(
                "Unable to fetch events sample. Please check your configuration parameters."
            )

    def stream_events(self, inputs: InputDefinition, event_writer: EventWriter) -> None:
        """This function handles all the action: splunk calls this modular input
        without arguments, streams XML describing the inputs to stdin, and waits
        for XML on stdout describing events.

        If you set use_single_instance to True on the scheme in get_scheme, it
        will pass all the instances of this input to a single instance of this
        script.

        :param inputs: an InputDefinition object
        :param event_writer: an EventWriter object
        """

        # Go through each input for this modular input
        for input_name, input_item in list(inputs.inputs.items()):
            # Get fields from the InputDefinition object
            api_server = input_item.get(_API_SERVER) or _DEFAULT_API_SERVER
            client_id = input_item[_CLIENT_ID]
            client_secret = input_item[_CLIENT_SECRET]

            logging.info(f"Input name: {input_name} (client_id: {client_id})")

            # Get the checkpoint directory out of the modular input's metadata
            checkpoint_dir = inputs.metadata["checkpoint_dir"]
            logging.info(f"Checkpoint dir: {checkpoint_dir}")

            checkpoint_file_path = os.path.join(checkpoint_dir, f"{client_id}.txt")

            try:
                # read sha values from file, if exist
                with open(checkpoint_file_path, "r") as file:
                    data = file.read()
            except:  # noqa: E722
                # If there's an exception, assume the file doesn't exist
                now = datetime.now(tz=timezone.utc)
                from_time = now - timedelta(days=3)
            else:
                from_time = _string_to_datetime(data)

            max_event_time = from_time

            ssl_ctx = _ssl_context()
            access_token = _get_token(ssl_ctx, api_server, client_id, client_secret)

            page = 1
            while True:
                entries = _fetch_events_page(
                    ssl_ctx, api_server, from_time, page, access_token
                )
                if not entries:
                    break

                for entry in entries:
                    # '_created' represents the moment the event object is created in database
                    entry_created = entry["_created"]
                    # 'timestamp' represents the actual moment when the event occurred
                    entry_timestamp = entry["timestamp"]

                    entry_created_datetime = _string_to_datetime(entry_created)
                    entry_timestamp_datetime = _string_to_datetime(entry_timestamp)

                    event_cat = entry["event_cat"]
                    # Extract and parse log_data only for events that are not related to dashboard login/activity
                    # and device status (in these cases, log_data includes mainly internal information)
                    log_data = (
                        entry.get("log_data", {})
                        if event_cat not in _NO_LOG_DATA_CATEGORIES
                        else {}
                    )

                    parsed_log_data = {}
                    for k, v in log_data.items():
                        if isinstance(v, dict):
                            # Flatten sub-dicts (e.g. 'dlp_details', 'extension_details')
                            parsed_log_data.update(v)
                        else:
                            parsed_log_data[k] = v

                    event_data = {
                        "message": entry["message"]["en"],
                        "username": entry["username"],
                        "client_ip": entry["client_ip"],
                        "severity": entry["level"],
                        "event_cat": event_cat,
                        "event_id": entry["event_id"],
                    }
                    if parsed_log_data:
                        event_data["log_data"] = parsed_log_data

                    # Create an Event object, and set its fields
                    event = Event(
                        data=json.dumps(event_data),
                        time="%.3f" % entry_timestamp_datetime.timestamp(),
                    )

                    # Tell the EventWriter to write this event
                    event_writer.write_event(event)

                    max_event_time = max(max_event_time, entry_created_datetime)

                page += 1

            with open(checkpoint_file_path, "w") as fp:
                fp.write(_datetime_to_string(max_event_time))


if __name__ == "__main__":
    logging.root
    logging.root.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(levelname)s %(message)s")
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(formatter)
    logging.root.addHandler(handler)

    sys.exit(ErmesForEnterprise().run(sys.argv))
