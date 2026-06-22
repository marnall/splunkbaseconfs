import sys
from datetime import datetime, timedelta, timezone

from connector import (
    AnyRun,
    CommonConfiguration,
    HttpProxy,
    Log,
    LogLevel,
    write_feeds_to_kv,
)
from connector.modules import (
    ANYRUN_API,
    FEEDS,
    KV,
    MODULAR_INPUT,
    PROXY,
    SECRET_STORAGE,
)
from connector.secreter import Secreter
from splunklib.client import Service
from splunklib.modularinput import Argument, Scheme, Script

NAME = "ti_feed"
MODULE = FEEDS


class TIFeed(Script):
    app: str

    logg: Log

    service: Service  # type: ignore

    def get_scheme(self):  # type: ignore
        scheme = Scheme("Ti Feed")
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        initial_ingesting_interval = Argument(
            "initial_ingesting_interval",
            title="Initial Ingesting Interval",
            required_on_edit=False,
        )
        initial_ingesting_interval.description = (
            "The initial ingesting interval for the input"
        )
        initial_ingesting_interval.required_on_create = False

        scheme.add_argument(initial_ingesting_interval)

        return scheme

    def stream_events(
        self, helper, ew, external_service=None, test: bool = False
    ):  # type: ignore
        if external_service:
            service = external_service
        else:
            service = self.service

        # Initialize log
        try:
            self.logg = Log(
                source=MODULE,
                threshold=CommonConfiguration().extract_log_threshold(service),
                service=service,
                test=test,
            )
            log = self.logg.log

        except Exception as e:
            raise Exception(f"Error initializing log: {e}", LogLevel.ERROR)

        # Get input info
        helper_dict = helper.__dict__

        input_params = helper_dict.get("inputs", {}).get(
            f"{NAME}://{NAME}", {}
        )

        # Get FEEDS token
        global_basic_token = Secreter(service=service, key="FEEDS").get(
            secure=False
        )

        if global_basic_token is None:
            log(
                message="Global FEEDS TOKEN not found",
                level=LogLevel.ERROR,
                object=SECRET_STORAGE,
            )
            return

        config = CommonConfiguration().get(service=service)

        try:
            proxy = HttpProxy(
                is_proxy=config.get("proxy_enable", 0) == 1,
                url=config.get("proxy_host", ""),
                port=config.get("proxy_port", ""),
                login=config.get("proxy_username", ""),
                password=config.get("proxy_password", ""),
            )
        except Exception as e:
            log(
                message=f"Error initializing proxy: {e}",
                level=LogLevel.ERROR,
                object=PROXY,
            )
            proxy = HttpProxy(is_proxy=False)

        # Get params
        try:
            ingesting_interval = int(
                input_params.get("initial_ingesting_interval", 30)
            )
            ingesting_interval = (
                ingesting_interval if ingesting_interval <= 90 else 90
            )
            load_from = datetime.now(timezone.utc) - timedelta(
                days=ingesting_interval
            )

        except Exception as e:
            log(
                message=f"Error getting initial ingesting interval: {e}",
                level=LogLevel.ERROR,
                object=MODULAR_INPUT,
            )
            return

        try:
            stores = AnyRun(
                api_key=global_basic_token,
                proxy=proxy,
                load_from=load_from,
            ).get_feeds()
        except Exception as e:
            log(
                message=f"No new feeds were received: {e}",
                level=LogLevel.INFO,
                object=ANYRUN_API,
            )

            return 0, 0, 0

        log(
            message="New feeds were successfully received. Writing to KV store...",
            level=LogLevel.DEBUG,
            object=FEEDS,
        )

        try:
            ip_count, domain_count, url_count = write_feeds_to_kv(
                feeds=stores,
                service=service,
            )
        except Exception as e:
            log(
                message=f"Error writing feeds to KV: {e}",
                level=LogLevel.ERROR,
                object=KV,
            )
            return

        log(
            message=f"KV Stores successfully updated with {ip_count} IPv4 addresses, {domain_count} Domain names and {url_count} URLs",
            object=KV,
            domain_count=domain_count,
            ip_count=ip_count,
            url_count=url_count,
            log_type="feed_updated",
        )

        if test:
            return ip_count, domain_count, url_count


if __name__ == "__main__":
    sys.exit(TIFeed().run(sys.argv))
