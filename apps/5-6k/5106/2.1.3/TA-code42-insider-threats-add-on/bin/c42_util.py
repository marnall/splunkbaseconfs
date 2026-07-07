import dateutil.parser
import json
import re
import os
import traceback
from configparser import ConfigParser
from datetime import timezone, timedelta, datetime
from pathlib import Path

from incydr import Client
from kvstore import KVStoreClient


def get_app_version():
    current_path = Path(__file__)
    app_conf = current_path.parent.parent / "default" / "app.conf"
    parser = ConfigParser()
    parser.read(app_conf)
    return parser["launcher"]["version"]


class InvalidIntervalException(Exception):
    def __init__(self, input_name, limit):
        msg = f"Input {input_name} cannot use an interval of less than {limit} seconds."
        super().__init__(msg)


class Code42ModInput:
    """A Mixin to add custom shared functionality to the modinput_wrapper's `BaseModInput`"""

    def raise_interval_error_if_needed(self, limit, input_adjective):
        """Error for when user tries setting input < the given seconds.
        This is because we don't want to encourage too frequent of polling for our APIs.
        """
        if int(self.get_arg("interval")) < limit:
            key = self.get_input_stanza_names()
            msg = (
                f"Input {key} cannot use an interval of less than {limit} seconds."
                f" Aborting Code42 {input_adjective} event collection."
            )
            raise Exception(msg)

    def initialize_sdk(self):
        """Create the Incydr Client using the account set in the input settings."""
        account_cfg = self.get_arg("c42_account")
        api_client_id = account_cfg["api_client_id"]
        api_client_secret = account_cfg["api_client_secret"]
        domain = account_cfg["c42_domain"]
        if not domain[0:4] == "http":
            domain = f"https://{domain}"

        proxies = construct_proxies(
            account_cfg.get("proxy_address"), account_cfg.get("proxy_auth")
        )
        if proxies:
            os.environ["http_proxy"] = proxies["http"]
            os.environ["https_proxy"] = proxies["https"]
        version = get_app_version()
        user_agent_prefix = (
            f"Code42 - Splunk/{version} (Code42; code42.com) "
        )

        self.log_info(
            f"Initializing Code42 sdk with api_client_id: {api_client_id}, domain: {domain}, proxies: {proxies}"
        )
        sdk = Client(
            url=domain, api_client_id=api_client_id, api_client_secret=api_client_secret, user_agent_prefix = user_agent_prefix
        )
        self.log_info("Incydr sdk initialized successfully.")
        return sdk

    def get_checkpoint_data(self, checkpoint_key, initial_days_back):
        """Return a tuple of the checkpointed-timestamp float and a checkpointed list of events
        from the last poll that were at the end of the query result and all had the same timestamp.
        We do this because we want to de-duplicate the already-handled events at the
        beginning of the next poll.
        """
        checkpoint = self.get_check_point(checkpoint_key)
        if not checkpoint:
            # The initial implementation of get_checkpoint_data() used `self.input_type` as the checkpoint key, which
            # wasn't unique across multiple instances of the same input type. We now take it as an argument so it can
            # be unique to each configured input, but we need to check for the "old" one and use that.
            checkpoint = self.get_check_point(self.input_type) or {}
        timestamp = checkpoint.get("timestamp")
        # Use a default begin timestamp if polling for the first time.
        if not timestamp:
            timestamp = (get_now() - timedelta(days=initial_days_back)).timestamp()
        return timestamp, checkpoint.get("events", [])

    def write_event(self, ew, event_data):
        event_data = (
            event_data.json()
            if hasattr(event_data, "json") and callable(event_data.json)
            else json.dumps(event_data)
        )
        new_event = self.new_event(event_data)
        ew.write_event(new_event)

    def update_mod_input_config(self, **kwargs):
        """
        Updates currently executing modular input config with provided kwargs.
        """
        for i in self.service.inputs.list(kind=self.input_type):
            if i.name == self.get_input_stanza_names():
                if "interval" not in kwargs:
                    # since interval is a required arg, we need to always provide it here
                    kwargs["interval"] = i.content["interval"]
                i.update(**kwargs)

    def post_splunk_message(self, name, message, severity):
        """Posts a Splunk bulletin message for all users."""
        data = {"name": name, "value": message, "severity": severity}
        self.service.messages.create(**data)
        self.log_debug(f"Posted Slunk message: {data}")

    def notify_once_every_n_hours(self, checkpoint_key, hours, name, message, severity):
        """
        Send a notification only once per number of hours specified. Last notification time
        is stored in a checkpoint. Used for notifying a required change
        post-upgrade or other error state without spamming notifications.
        """
        notified = self.get_check_point(checkpoint_key)
        self.log_debug(
            f"Notification checkpoint key: {checkpoint_key}, value: {notified}"
        )
        try:
            notified = datetime.fromtimestamp(notified)
        except Exception:
            notified = datetime.fromtimestamp(0)
        now = datetime.now()
        if now - notified > timedelta(hours=hours):
            self.post_splunk_message(name, message, severity)
            self.save_check_point(checkpoint_key, now.timestamp())

    def notify_api_client_config_required(self):
        self.notify_once_every_n_hours(
            checkpoint_key="c42_api_client_config_required",
            hours=24,
            name="Configuration Update Required",
            message="The Code42 Insider Risk App now requires an API Client for authentication. To continue ingesting Code42 data, [https://code42.com/r/support/splunk-auth update your app configuration] to use API clients.",
            severity="warn",
        )

    def create_kv_store_client(self, collection_name):
        session_key = self.context_meta["session_key"]
        return KVStoreClient(collection_name, session_key)
    
    def log_error_with_traceback(self, err):
        # log the error at error and the traceback at debug.
        self.log_error(repr(err))
        self.log_debug("".join(traceback.format_tb(err.__traceback__)))


def parse_timestamp(date_str):
    """Parse a timestamp str to an unix epoch time."""
    try:
        date = dateutil.parser.parse(date_str).replace(tzinfo=timezone.utc)
        return date.timestamp()
    except:
        # Sometimes our API returns dates like `2021-08-11 18:10:26 (UTC)`.
        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S (UTC)").replace(
            tzinfo=timezone.utc
        )
        return date.timestamp()


def construct_proxies(proxy_address, proxy_auth):
    if not proxy_address:
        return
    if proxy_auth:
        proxy_address = re.sub(r"^(https?://)", rf"\1{proxy_auth}@", proxy_address)
    return {"http": proxy_address, "https": proxy_address}


def get_now():
    return datetime.now(tz=timezone.utc)
