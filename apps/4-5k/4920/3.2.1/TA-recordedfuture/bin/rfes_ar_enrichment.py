# encoding = utf-8
"""Implement enrichment. DO NOT MOVE THIS FILE"""

from __future__ import print_function
from requests import RequestException
import copy
import json
import os
import re
import sys


sys.path.insert(0, os.path.dirname(__file__))
from recordedfuture.core.utils import get_instance_guid  # noqa
from recordedfuture.es.adaptive_response import (  # noqa
    AdaptiveModularAction,
    ModularAction,
    mktimegm,
    ModularActionTimer,
    main_execution,
)
from recordedfuture.core.utils import format_evidence_details, get_category  # noqa
from recordedfuture.core.constants import REALTIME, CACHED, CACHED_NO_SHARE  # noqa


SUCCESS_MESSAGE = "Successfully queried for rfes_ar_enrichment"


class RecordedFutureEnrichmentModularAction(AdaptiveModularAction):
    """Recorded Future Modular Action."""

    def _format(self, data):
        return format_evidence_details(data)

    def _intelligence_sharing(self, category, ioc, event):
        """Method of sharing intelligence data

        Args:
            category: category of the IOC being enriched
            ioc: indicator being enriched
            event: splunk event where ioc is extracted from
        """
        tracking_payload = []
        data = {
            "iocs": {category: [ioc]},
            "use_case": event.get("threat_key"),
            "source_type": event.get("orig_sourcetype", ""),
            "field": event.get("threat_match_field", ""),
            "integration_instance_id": get_instance_guid(self.app_env),
        }

        if event.get("rf_multiorg_org", None):
            data["rf_multiorg_org"] = event.get("rf_multiorg_org")

        tracking_payload.append(data)
        try:
            self.rfclient.realtime_es.track(tracking_payload)
        except RequestException:
            self.logger.debug("Data sharing call failed")

    def dowork(self, result):
        """Do the actual enrichment for events."""

        if result.get("threat_description") == "RBA":
            # RBA feeds has threat_description == RBA, we do not
            # enrich these, so continue to next result.
            self.RBA_canary()
            return

        # get parameter value
        field = self.configuration.get("field")
        if not field:
            self.logger.error("Field: {} is missing".format(field))
            return

        parameter = result.get(field)
        if not parameter:
            self.logger.error("No value to lookup for field: {}".format(field))
            return

        # get category
        category_conf = self.configuration.get("category", "auto")
        category = self._get_category(category_conf, parameter, self.logger)
        self.logger.debug(
            "Call info: %s %s (%s)",
            category,
            parameter,
            "Python %d.%d.%d"
            % (sys.version_info.major, sys.version_info.minor, sys.version_info.micro),
        )

        threat_key = result.get("threat_key", "")
        entity_dict = {category: [parameter]}
        enrichment_mode = self.app_env.enrichment_mode
        event = copy.deepcopy(result)
        # See RFPD-68832, not popping source field and it will be a list and not a string
        # due to multiple source fields in event.
        event.pop("source", None)

        if event.get("threat_description") == "RBA":
            # RBA feed description is set to RBA, drop if present.
            self.logger.info("Result is from RBA feed, dropping enrichment.")
            self.RBA_canary()
            return

        summary = {}
        try:
            if enrichment_mode not in [CACHED, REALTIME, CACHED_NO_SHARE]:
                self.message("No lookup done due to missing configuration")
                return

            if "_raw" in event:
                event["orig_raw"] = event["_raw"]
                del event["_raw"]
            if enrichment_mode == REALTIME:
                self.logger.info("Will do live reputation lookup")
                # Make the API call
                enr = self.rfclient.lookup.reputation(
                    entity_dict=entity_dict, use_case="ar_reputation", timeout=20
                )
                summary = enr.get("data")[0].get("entry")
                if self.app_env.privacy.share_intelligence:
                    self._intelligence_sharing(category, parameter, event)

            if self.app_env.privacy.share_intelligence and enrichment_mode == CACHED:
                self.logger.info("Tracking cached lookup")
                raw = event.get("orig_raw")
                if raw:
                    all_matches = re.findall(r'orig_sourcetype="([^"]*)', raw)
                    sourcetype = all_matches[0] if all_matches else ""
                    extra_data = {
                        "sourcetype": sourcetype,
                        "integration_instance_id": get_instance_guid(self.app_env),
                    }
                    # This handles multi-org clients that wants to explicitly mark a detection
                    # with one org.
                    #
                    # To tag a detection with one specified org, the correlation search must be
                    # customized to add a field "rf_multiorg_org" which contains the org id
                    # (ie the entity id from RFs platform).
                    #
                    all_matches = re.findall(r'rf_multiorg_org="([^"]*)', raw)
                    rf_multiorg_org = all_matches[0] if all_matches else ""
                    extra_data["rf_multiorg_org"] = rf_multiorg_org
                    extra_data["field"] = field
                else:
                    extra_data = {}

                self.logger.info(extra_data)
                self.rfclient.correlation.track(entity_dict, extra_data)
                self.canary()

            if enrichment_mode in [CACHED, CACHED_NO_SHARE]:
                self.logger.info("Will do cached lookup")
                rldata = self.client.searches.search(
                    """
                        | localop
                        | inputlookup {}
                        | search Name="{}"
                    """.format(threat_key, parameter),
                    timeout=299,
                )
                try:
                    data = rldata.get("results", [])
                    if not data:
                        self.message("Search returned empty results")
                        return

                    data = data[0]
                    data["EvidenceDetails"] = json.loads(data["EvidenceDetails"]).get(
                        "EvidenceDetails"
                    )
                    summary = self._format(data)
                except ValueError:
                    self.logger.error("Failed to parse evidence details: %s" % rldata)
                    return

            event.update(**summary)

            # Finally - add title and description
            prefix = self.get_param("prefix")
            if not prefix:
                prefix = "Threat Activity Enriched"
            event["rule_title"] = "{prefix} ({parameter})".format(
                prefix=prefix, parameter=parameter
            )
            event["rule_description"] = (
                'Threat activity ({}) was enriched in the "{}" field based on threat '
                "intelligence available from Recorded Future.".format(parameter, field)
            )
            # also inject query_parameter
            event["query_parameter"] = parameter
            if event.get("threat_description") != "RBA":
                # Index in finding / notable data cause incident review load to fail
                # see RFPD-6216. Pop to remove.
                event.pop("index", None)
                # ad-hoc event inherits urgency from whichever event it is spawned from. Removing cause it to regen.
                event.pop("urgency", None)
                self.logger.info("Event final: %s", event)
                parsed_event = self.result2stash(event)
                self.logger.info("parsed_event: %s", parsed_event)
                self.addevent(parsed_event, sourcetype="stash")

        # process unsuccessful requests
        except Exception as err:
            self.logger.error(
                "Failed to query for rfes_ar_enrichment: %s", err, exc_info=True
            )
            self.message(
                "Failed to query for rfes_ar_enrichment: %s" % err, status="failure"
            )
        else:
            self.message(SUCCESS_MESSAGE, status="success")

    def _get_category(self, category, value, logger=None):
        """Return the category to enrich (ip, domain...).

        category - either the category or auto which activates
                   pattern based detection.
        value    - the value used in the patterns.

        >>> self._get_category('auto', '10.20.30.40')
        'ip'

        >>> self._get_category('auto', 'www.example.com')
        'domain'

        >>> self._get_category('auto', 'http://www.example.com/index.html')
        'url'

        >>> self._get_category('ip', 'apa.bepa.cepa')
        'ip'
        """
        try:
            return get_category(category, value)
        except Exception:
            logger.error('Failed to automatically detect category for "%s"', value)
            raise Exception('Failed to automatically detect category for "%s"' % value)

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
        if field not in result:
            self.logger.error("the event does not have the specified field '%s'", field)
            raise Exception('The event does not have the specified field "%s"' % field)

    def get_param(self, param_name):
        """Get parameter from configuration."""
        return self.configuration.get(param_name)


def main_callback(modaction):
    modaction.writeevents(index="notable", source="rfes_ar_enrichment")


if __name__ == "__main__":
    main_execution(
        RecordedFutureEnrichmentModularAction,
        name="rfes_ar_enrichment",
        execution_callback=main_callback,
    )
