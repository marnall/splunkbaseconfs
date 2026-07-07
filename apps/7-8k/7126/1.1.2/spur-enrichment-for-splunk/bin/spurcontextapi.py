import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "splunklib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spurlib"))
from spurlib.api import lookup
from spurlib.logging import setup_logging
from spurlib.formatting import format_for_enrichment, ENRICHMENT_FIELDS
from spurlib.notify import notify_low_balance

CACHE = {}

@Configuration(distributed=False)
class SpurContextAPI(StreamingCommand):
    """
    Enriches records with context from the Spur API.
    """
    ip_field = Option(require=True)
    def stream(self, records):
        logger = setup_logging()
        if len(self.ip_field) == 0:
            raise ValueError("No ip field specified")
        ipfield = self.ip_field
        logger.debug("ipfield: %s", ipfield)
        notified = False
        for record in records:
            if ipfield in record and record[ipfield] != "":
                if CACHE.get(record[ipfield]):
                    ctx = CACHE[record[ipfield]]
                else:
                    try:
                        ctx, balance_remaining, low_balance_threshold = lookup(
                            logger, self, record[ipfield]
                        )
                        if (
                            balance_remaining is not None
                            and low_balance_threshold
                            and balance_remaining < int(low_balance_threshold)
                            and not notified
                        ):
                            notify_low_balance(self, balance_remaining)
                            notified = True
                    except Exception as e:
                        error_msg = "Error looking up ip %s: %s" % (record[ipfield], e)
                        logger.error(error_msg)
                        ctx = {"spur_error": error_msg, "ip": record[ipfield]}
                if 'spur_ip' in ctx:
                    del ctx['spur_ip']
                CACHE[record[ipfield]] = ctx
                flattened = format_for_enrichment(ctx)
                for field in ENRICHMENT_FIELDS:
                    if field in flattened:
                        record[field] = flattened[field]
                    else:
                        record[field] = ""
            else:
                ctx = {"spur_error": "No ip address found in record"}
                flattened = format_for_enrichment(ctx)
                for field in ENRICHMENT_FIELDS:
                    if field in flattened:
                        record[field] = flattened[field]
                    else:
                        record[field] = ""
            try:
                yield record
            except StopIteration:
                return


dispatch(SpurContextAPI, sys.argv, sys.stdin, sys.stdout, __name__)
