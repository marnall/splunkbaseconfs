import os
import sys
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "splunklib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spurlib"))
from spurlib.api import lookup
from spurlib.logging import setup_logging
from spurlib.notify import notify_low_balance


@Configuration(distributed=False)
class SpurContextAPIGen(GeneratingCommand):
    """
    Generates a context record for a given IP address.
    """
    ip = Option(require=True)
    def generate(self):
        logger = setup_logging()
        if len(self.ip) == 0:
            raise ValueError("No ip specified")
        logger.debug("ip: %s", self.ip)

        # Split the ip address by a comma in case it's a list of ip addresses
        ips = self.ip.split(",")
        notified = False
        for ip in ips:
            try:
                ctx, balance_remaining, low_balance_threshold = lookup(logger, self, ip)
                if (
                    balance_remaining is not None
                    and low_balance_threshold
                    and balance_remaining < int(low_balance_threshold)
                    and not notified
                ):
                    notify_low_balance(self, balance_remaining)
                    notified = True
            except Exception as e:
                logger.error("Error for ip %s: %s", ip, e)
                error_msg = "Error looking up ip %s: %s" % (ip, e)
                ctx = {"spur_error": error_msg, "ip": ip}

            record = {"_time": time.time(), 'event_no': 1, "_raw": json.dumps(ctx)}
            record.update(ctx)
            try:
                yield record
            except StopIteration:
                return

dispatch(SpurContextAPIGen, sys.argv, sys.stdin, sys.stdout, __name__)
