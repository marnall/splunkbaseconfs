# encoding = utf-8
"""Implement Links Threat Hunt - More details can be found in Technical_docs/readme.adoc. DO NOT MOVE THIS FILE"""

from __future__ import print_function
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from recordedfuture.core.constants import REALTIME  # noqa
from recordedfuture.core.exceptions import CategoryParseException  # noqa
from recordedfuture.es.adaptive_response import (  # noqa
    AdaptiveModularAction,
    ModularAction,
    mktimegm,
    ModularActionTimer,
    main_execution,
)
from recordedfuture.enrichment.links import correlate_on_links  # noqa
from recordedfuture.core.utils import get_category  # noqa

SUCCESS_MESSAGE = "Successfully queried for rfes_ar_links"


class RecordedFutureLinksAction(AdaptiveModularAction):
    """Recorded Future Modular Action."""

    def dowork(self, result):
        """Do the actual enrichment for events."""
        # Read hunt parameters
        field = self.configuration.get("field")
        ioc = result[field]
        # get category
        category_conf = self.configuration.get("category", "auto")
        earliest = self.configuration.get("earliest")
        index_string = self.configuration.get("index")
        try:
            category = get_category(category_conf, ioc)
        except (CategoryParseException, TypeError):
            # TypeError can get thrown inside the except of get_category.
            msg = "Failed to automatically parse the category from '{field}'.".format(
                field=field
            )
            self.logger.error(msg)
            self.message(msg)
            return

        msg = "Call info: {category} {ioc} search in {index} w {earliest} ({version})".format(
            category=category,
            ioc=ioc,
            index=index_string,
            earliest=earliest,
            version="Python %d.%d.%d"
            % (sys.version_info.major, sys.version_info.minor, sys.version_info.micro),
        )

        self.logger.debug(msg)

        # DEV OVERRIDES
        threat_key = result.get("threat_key", "")
        enrichment_mode = self.app_env.enrichment_mode
        # Event contains the origin event of the hunt.
        try:
            if enrichment_mode != REALTIME:
                self.message(
                    "No lookup done, Links AR is currently only supported in Realtime mode.",
                    status="Requires real-time mode",
                )
                return

            in_dict = {
                "query": {
                    "ioc": ioc,
                    "category": category,
                    "use_case": threat_key,
                    "earliest": earliest,
                    "index_string": index_string,
                }
            }

            status, payload = correlate_on_links(in_dict, self.app_env)
            if status == 204:
                self.message(payload, status="success")
                return

            if status != 200:
                self.message(payload, status="failure")
                return

            self.logger.info(
                "Found {count} correlations on links data.".format(count=len(payload))
            )
            for entry in payload:
                # Format each entry we received to make sense for ES.

                if "_raw" in entry:
                    entry["orig_raw"] = entry["_raw"]
                entry["rule_title"] = (
                    "Recorded Future threat hunt ({source_ioc} > {dest_ioc})".format(
                        source_ioc=ioc, dest_ioc=entry.get("threat_match_value", None)
                    )
                )

                category = (
                    category.upper() if category in ["ip", "url"] else category.lower()
                )
                linked_category = (
                    entry.get("threat_object_type", "").upper()
                    if entry.get("threat_object_type", "") in ["ip", "url"]
                    else entry.get("threat_object_type", "").lower()
                )

                entry["rule_description"] = (
                    "Finding triggered by a Recorded Future Threat Hunt for the "
                    "{orig_cat} {orig_ioc}. "
                    "The hunt detected a linked "
                    "{linked_cat}: {linked_ioc}".format(
                        orig_cat=(
                            category.upper()
                            if category in ["ip", "url"]
                            else category.lower()
                        ),
                        orig_ioc=ioc,
                        linked_cat=linked_category,
                        linked_ioc=entry.get("threat_match_value", ""),
                    )
                )

                if entry.get("threat_match_value") == "unknown":
                    entry["rule_description"] += (
                        "The Unknown 'Risk Object' indicates that the exact field where the entity was"
                        "present could not be found. Check raw log snippet. "
                    )

                # Risk fields
                if self.configuration.get("risk") == "1":
                    entry["risk_score"] = entry.get("rf_a_risk", None)
                    entry["threat_object"] = entry.get("threat_match_value", None)
                    for key in ["src_ip", "src", "src_host"]:
                        if key in entry:
                            entry["risk_object"] = entry[key]
                            break
                    entry["risk_object_type"] = "system"
                    entry["risk_message"] = (
                        "Threat hunt: {source_ioc} > {dest_ioc}".format(
                            source_ioc=ioc,
                            dest_ioc=entry.get("threat_match_value", None),
                        )
                    )
                # See RFPD-68832, not popping source field and it will be a list and not a string
                # due to multiple source fields in event.
                entry.pop("source", None)
                # set time to current time, otherwise notable / finding will inherit from correlated event.
                entry["_time"] = str(time.time())
                for drop_key in ["index", "urgency", "_raw"]:
                    # index in event cause the notable / finding generation search to fail.
                    # ad-hoc event inherits urgency from whichever event it is spawned from. Removing cause it to regen.
                    entry.pop(drop_key, None)
                # DO MORE STUFF HERE

                parsed_event = self.result2stash(entry)
                self.addevent(parsed_event, sourcetype="stash")

            self.message(SUCCESS_MESSAGE, status="success")
            return
        # process unsuccessful requests
        except Exception as err:
            self.logger.exception(
                "Failed to query for rfes_ar_links: %s", err, exc_info=True
            )
            self.message(
                "Failed to query for rfes_ar_links: %s" % err,
                status="failure",
            )

    def validate(self, result):
        """Validate params. Both category and field are required."""
        if not self.get_param("category"):
            self.logger.error(
                "category is a mandatory parameter, but its value is None."
            )
            raise Exception("Category is a mandatory parameter, but its value is None.")
        field = self.get_param("field")
        if not field:
            self.logger.error("field is a mandatory parameter, but its value is None.")
            raise Exception("Field is a mandatory parameter, but its value is None.")

        index = self.get_param("index")
        if not index:
            self.logger.error("index is a mandatory parameter, but its value is None.")
            raise Exception("Index is a mandatory parameter, but its value is None.")

        earliest = self.get_param("earliest")
        if not earliest:
            self.logger.error(
                "earliest is a mandatory parameter, but its value is None."
            )
            raise Exception("earliest is a mandatory parameter, but its value is None.")

    def get_param(self, param_name):
        """Get parameter from configuration."""
        return self.configuration.get(param_name)


def main_callback(modaction):
    # Once we're done iterating the result set and making
    # the appropriate API calls we will write out the events
    if modaction.configuration.get("notable") == "1":
        modaction.logger.info("Writing results to 'notable' index.")
        modaction.writeevents(index="notable", source="Recorded Future Threat Hunt")

    if modaction.configuration.get("risk") == "1":
        modaction.logger.info("Writing results to 'risk' index.")
        modaction.writeevents(index="risk", source="Recorded Future Threat Hunt")


if __name__ == "__main__":
    main_execution(
        RecordedFutureLinksAction,
        name="rfes_ar_links",
        execution_callback=main_callback,
    )
