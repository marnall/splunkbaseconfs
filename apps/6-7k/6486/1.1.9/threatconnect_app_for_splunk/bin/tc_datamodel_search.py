# standard library
import json
import re
import sys
import time
from functools import lru_cache
from typing import Generator, List

# third-party
from base_search_command import BaseSearchCommand
from splunklib.client import Index
from splunklib.searchcommands import Configuration, Option, dispatch


@Configuration()
class DatamodelSearchCommand(BaseSearchCommand):
    """Playbook download command."""

    # args
    _key = Option(doc="The key for search settings.", require=False)
    _write_observations = Option(
        default="true", doc="Report observations.", require=False
    )
    _write_matches = Option(default="true", doc="Write matches.", require=False)

    # properties
    _command = "tcdatamodelsearch"
    execution_summary = {
        "count_events": 0,
        "count_ioc": 0,
        "count_matches": 0,
        "count_observations": 0,
    }
    log_data_default = {"search_name": None}

    @staticmethod
    def _csv_name(collection_name: str) -> str:
        csv_name = collection_name.lower().replace(" ", "-")
        # remove all non-alphanumeric characters and underscores
        csv_name = re.sub(r"[^a-zA-Z0-9_]", "", csv_name)
        return f"{csv_name}.csv.gz"

    @property
    def ioc_base_spl(self) -> str:
        """Return the base SPL to retrieve the indicators from the ioc collection csv files.

        Note: An owner can be in multiple collections, which means that the indicator from that
              specific owner can be in multiple csv files. Therefore, we need to dedup the results.
              Even though the end results will be added to a set (automatic dedup), testing
              proves that it is faster to let splunk dedup before returning the results. Each
              pagination of results takes .5 - .9 seconds. Saving time by lowering the number
              of results on the Splunk side seems to be more efficient.
        """
        collections = self.search_fields.ioc_collections.split(",")

        lookups = []
        for collection in collections:
            csv_name = self._csv_name(collection_name=collection.strip())
            lookups.append(f"| inputlookup {csv_name} append=true")
        return " ".join(lookups)

    def ioc_collections_download(self) -> set:
        """Return a unique set of indicators from the ioc collections.

        memory utilization estimate:
        - ~1.5MM iocs ~= 200MB RAM
        - ~20MM iocs ~= 2.6GB RAM
        """
        start_time = time.time()

        indicators = set()
        job = self.ioc_search_job(self.ioc_collections_spl())
        for result in self.iterate(job):
            summary = result["summary"].lower()
            if result["type"].lower() not in self.single_value_ioc_types:
                {indicators.add(ioc) for ioc in summary.split(" : ") if ioc}
            else:
                indicators.add(summary)

        self.log_execution_time(
            "collection-download", start_time, {"count": len(indicators)}
        )
        self.execution_summary["count_ioc"] = len(indicators)
        return indicators

    def ioc_collections_spl(self) -> str:
        """Return the SPL to retrieve the indicators from the ioc collection csv files."""
        spl = f"{self.ioc_base_spl} | dedup summary | fields summary type"
        self.log_data("INFO", "ioc-collections-spl", {"spl": spl})
        return spl

    def ioc_match_download(self, iocs: List[str]) -> dict:
        """Return a dict containing indicator data for the provides iocs.

        Note: The "inputlookup" command is not case sensitive, which means that the indicator
              being lower-case coming in will not be a problem.

        Returns:
        '1.1.1.1': {
            'data': [
                {
                    'id': '1',
                    'threatconnect_owner': 'owner',
                    'web_link': 'https://app.threatconnect.com/auth/...',
                }
            ],
            'type': 'Address'
        }
        """
        start_time = time.time()

        indicator_data = {}
        job = self.ioc_search_job(self.ioc_matches_spl(iocs))
        for result in self.iterate(job):
            indicator_data.setdefault(result["summary"], {})
            indicator_data[result["summary"]].setdefault("data", []).append(
                {
                    "id": result["id"],
                    "threatconnect_owner": result["ownerName"],
                    "web_link": result["webLink"],
                }
            )
            indicator_data[result["summary"]]["type"] = result["type"]

        self.log_execution_time(
            "match-download", start_time, {"count": len(indicator_data)}
        )
        return indicator_data

    def ioc_matches_spl(self, iocs: List[str]) -> str:
        """Return the SPL to retrieve the matched indicators from the ioc collection csv files.

        Note: The input list is chunked to ensure no more than 10k sub queries are executed.
        """
        search_part = " OR ".join([f'summary="{ioc}"' for ioc in iocs])
        spl = (
            f"{self.ioc_base_spl} | dedup id | search ({search_part}) "
            "| fields id, summary, ownerName, type, webLink"
        )
        self.log_data("INFO", "ioc-matches-spl", {"spl": f"{spl[:396]} ..."})
        return spl

    def ioc_search_job(self, spl: str):
        """Return the job for both ioc searches."""
        kwargs = {"exec_mode": "normal"}
        return self.tcs.search(spl, **kwargs)

    def generate(self) -> Generator:  # Entry Point
        """Implement the generate method execute datamodel search."""
        self.log_data(
            "INFO", "args", {"_key": self._key, "_write_matches": self._write_matches}
        )
        # download ioc collections from one or more csv file as defined in dm search config
        ioc_set = self.ioc_collections_download()

        # TODO explore yielding matches in process_events to reduce memory usage
        # process events and match them to the ioc_set
        matches = self.process_events(ioc_set)

        # iterate over matches and store them in the index
        yield from self.process_matches(matches)

    def match_builder(self, event: dict, ioc: str, match_ioc_data: dict) -> dict:
        """Return the a constructed matched event data."""
        return {
            "count": event["count"],
            "ioc": ioc,
            "ioc_type": match_ioc_data[ioc]["type"],
            "datamodel_search_name": self.search_fields.name,
            "datamodel": self.search_fields.data_model,
            "earliest": self.search_fields.earliest_epoch,
            "ioc_field": self.search_fields.ioc_field,
            "indicators": match_ioc_data[ioc]["data"],
            "labels": self.search_fields.labels,
            "latest": self.search_fields.latest_epoch,
            "spl": self.match_builder_spl(ioc, event["victim"]),
            "victim": event["victim"],
            "victim_field": self.search_fields.victim_field,
        }

    def match_builder_spl(self, ioc: str, victim: str) -> str:
        """Return the SPL to retrieve the matched events (stored with match event in index)."""
        return (
            f"""| datamodel {self.search_fields.data_model} search | """
            f'''search {self.search_fields.ioc_field}="{ioc}" AND '''
            f'''{self.search_fields.victim_field}="{victim}"'''
        )

    @property
    @lru_cache()
    def matched_event_index(self) -> Index:
        """Return the index to store matched events."""
        # get "tc_dm_search_events" index to store matched events
        try:
            return self.service.indexes[self.tcs.datamodel_index]
        except Exception as e:
            raise RuntimeError(
                f"{self.tcs.datamodel_index} index has not been created yet."
            ) from e

    def match_observation_builder(
        self, ioc: str, ioc_type: str, count: int, matched_observation: dict
    ):
        """Return the a constructed match event observation data."""
        if self.search_fields.report_observations is True:
            # consolidate observations count by day
            key_ = f"""{ioc}-{ioc_type}"""
            if key_ in matched_observation:
                matched_observation[key_]["observationCount"] += count
            else:
                matched_observation[key_] = {
                    "type": ioc_type,
                    "indicator": ioc,
                    "observationCount": count,
                }

    def match_observation_writer(self, matched_observation: dict):
        """Write matched observation data to the index."""
        self.execution_summary["count_observations"] = len(matched_observation)
        if (
            self._write_observations.lower() in ["t", "true"]
            and self.search_fields.report_observations is True
        ):
            self.tcs.collections.observations.batch_save(
                list(matched_observation.values())
            )

    def match_process_events(self, event_dict: dict, ioc_set: set, matches: dict):
        """Process the events and match them to the ioc_set.

        {
            '1.1.1.1': [
                {'count': '5', 'victim': '2.2.2.2'},
                {'count': '10', 'victim': '3.3.3.3'},
            ]
        }
        """
        start_time = time.time()
        # NOTE: using intersection is around 7x faster that doing matches in a for loop
        for _ioc in set(event_dict.keys()).intersection(ioc_set):
            for ed in event_dict[_ioc]:
                self.execution_summary["count_matches"] += 1
                matches.setdefault(_ioc, []).append(ed)
        self.log_execution_time("match-processing", start_time)

    def match_writer(self, event: dict):
        """Write matched data to the index."""
        if self._write_matches.lower() in ["t", "true"]:
            self.matched_event_index.submit(
                json.dumps(event),
                source="threatconnect-search-datamodel",
                sourcetype="threatconnect:event",
            )

    def process_events(self, ioc_set: set) -> dict:
        """Process events and match them to the ioc_set.

        Note:
        - when matching indicators the indicator value must be lower case in both sets
        - when matching indicators the indicator type does NOT matter

        Returns
        {
            '1.1.1.1': [
                {'count': '5', 'victim': '2.2.2.2'},
                {'count': '10', 'victim': '3.3.3.3'},
                (10, '3.3.3.3')
            ]
        }
        """
        event_dict = {}
        index = 0
        matches = {}
        page_size = 50_000
        for index, event in enumerate(
            self.iterate(self.tstat_search_job, count=page_size), start=1
        ):
            ioc_field = event["ioc_field"].lower()
            # TODO maybe instead of match_process_event, do an if ioc_field in ioc_set here?
            event_dict.setdefault(ioc_field, []).append(
                {
                    "count": int(event["count"]),
                    "victim": event["victim_field"],
                }
            )

            if index % page_size == 0:
                # process every page_size events in order to save memory
                self.log.info(f"Processing page {index} of tstats results")
                self.match_process_events(event_dict, ioc_set, matches)

                # reset event dict to save memory
                event_dict = {}
        self.execution_summary["count_events"] = index

        # process any remaining events
        self.match_process_events(event_dict, ioc_set, matches)

        return matches

    def process_matches(self, matches: dict) -> Generator:
        """Process matches to create matched event and observations."""
        # chunk the matched events because splunk only allows
        # 10k sub queries (e.g., summary=x OR summary==y OR ...)
        matched_observation = {}
        chunk_size = 10_000
        for i in range(0, len(matches), chunk_size):
            chunk = [ioc for ioc in list(matches.keys())[i : i + chunk_size]]
            match_ioc_data = self.ioc_match_download(chunk)
            self.log.info(f"Processing chunk {i} of matches {len(match_ioc_data)}")

            # for event in matches:
            for ioc in match_ioc_data:
                # get match event data: '1.1.1.1': [{'count': '5', 'victim': '2.2.2.2'}]
                for matched_event_data in matches[ioc.lower()]:
                    # generate "final" matched data to be stored in index
                    match_data = self.match_builder(
                        matched_event_data, ioc, match_ioc_data
                    )

                    # write matched data to index
                    self.match_writer(match_data)

                    # generate observation data to be stored in index
                    self.match_observation_builder(
                        ioc,
                        match_ioc_data[ioc]["type"],
                        matched_event_data["count"],
                        matched_observation,
                    )

                    # yield matches to Splunk UI
                    yield match_data

        self.match_observation_writer(matched_observation)

    def search_fields_time_spl(self, earliest: str, latest: str) -> str:
        """Return the SPL to convert the earliest and latest time fields"""
        spl = (
            "| makeresults "
            f'| eval _earliest="{earliest}" '
            "| eval _earliest_real=relative_time(now(), _earliest) "
            '| eval earliest_epoch=strftime(_earliest_real, "%s") '
            '| eval earliest_date=strftime(_earliest_real, "%m/%d/%Y:%H:%M:%S") '
            f'| eval _latest="{latest}" '
            "| eval _latest_real=relative_time(now(), _latest) "
            '| eval latest_epoch=strftime(_latest_real, "%s") '
            '| eval latest_date=strftime(_earliest_real, "%m/%d/%Y:%H:%M:%S") '
            "| fields earliest_epoch, earliest_date, latest_epoch, latest_date"
        )
        self.log_data("INFO", "search-field-time-convert-spl", {"spl": spl})
        return spl

    def search_fields_time_spl_job(self, spl: str):
        """Return the job for for the search fields time search."""
        kwargs = {"exec_mode": "normal"}
        return self.tcs.search(spl, **kwargs)

    @property
    @lru_cache()
    def search_fields(self):
        """Return the search fields from the datamodel search settings kvstore collection."""
        search_fields = self.tcs.collections.dm_search_settings.query_by_id(self._key)
        self.log_data_default["search_name"] = f'"{search_fields.name}"'

        # update labels to be a list
        labels = search_fields.get("labels", "").split(",")
        search_fields["labels"] = [label.strip() for label in labels if label.strip()]

        # ensure report_observations exists (raised attribute error if not defined)
        search_fields["report_observations"] = (
            search_fields.get("report_observations") or False
        )

        # TODO: this need more testing
        # convert time fields to epoch
        spl = self.search_fields_time_spl(
            search_fields["earliest"], search_fields["latest"]
        )
        job = self.search_fields_time_spl_job(spl)

        # NOTE: only one result should ever be returned
        for result in self.iterate(job):
            search_fields["earliest_epoch"] = result["earliest_epoch"]
            search_fields["earliest_date"] = result["earliest_date"]
            search_fields["latest_epoch"] = result["latest_epoch"]
            search_fields["latest_date"] = result["latest_date"]

        self.log_data("DEBUG", "search-fields", dict(sorted(search_fields.items())))
        return search_fields

    @property
    @lru_cache()
    def single_value_ioc_types(self):
        """Return the list of single value IOC types."""
        types = {
            "Address",
            "ASN",
            "CIDR",
            "EmailAddress",
            "Email Subject",
            "Hashtag",
            "Host",
            "Mutex",
            "URL",
            "User Agent",
        }
        return {type_.lower() for type_ in types}

    @property
    def tstat_search_job(self):
        """Process the results returned from tstats search"""
        kwargs = {
            "earliest_time": self.search_fields.earliest_epoch,
            "latest_time": self.search_fields.latest_epoch,
            "exec_mode": "normal",
        }
        return self.tcs.search(self.tstat_spl, **kwargs)

    @property
    def tstat_spl(self):
        """Return the SPL to retrieve the events from the datamodel."""
        where = f'{self.search_fields.ioc_field} != "unknown"'
        if self.search_fields.where:
            where = f"{self.search_fields.where} AND {where}"

        spl = (
            f"| tstats count FROM datamodel={self.search_fields.data_model} where "
            f"{where} BY {self.search_fields.ioc_field}, {self.search_fields.victim_field} "
            f"| rename {self.search_fields.ioc_field} as ioc_field "
            f"| rename {self.search_fields.victim_field} as victim_field"
        )
        self.log_data("INFO", "tstat-event-spl", {"spl": spl})
        return spl


if __name__ == "__main__":
    try:
        dispatch(DatamodelSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
