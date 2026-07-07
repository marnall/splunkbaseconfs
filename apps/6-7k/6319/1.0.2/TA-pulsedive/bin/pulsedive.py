#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import, division, print_function, unicode_literals
import time
import sys
import os
import re
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.client import StoragePassword, Service
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

# Configurable values
API_KEY = None
PROXY = None
BATCHING = 30
CMD_TIMEOUT = -1

REPORT_TYPES = ["ioc"]

# Final (readonly) definitions:
ALL_OUTPUT_FIELDS = {"ioc": ["iid", "type", "indicator", "risk", "risk_recommended", "manualrisk", "retired", "stamp_added", "stamp_updated", "stamp_seen", "stamp_probed", "stamp_retired", "recent", "submissions", "schema", "riskfactors", "attributes", "properties", "threats"]}

class PulsediveRequestLimitExceededException(Exception):
    pass



class SplunkJobTerminatedException(Exception):
    def __init__(self, state):
        self.state = state


class CustomCommandTimeoutException(Exception):
    def __init__(self, runtime):
        self.runtime = runtime


class TerminationHelper:
    """
    This class is used to help detect Splunk job termination, and subsequently terminate this command.
    Due to the nature of this command, it can execute for a very long time. Splunk has difficulty terminating
    it prematurely. As such, this class was written to assist the  user with terminating this command.
    Before this was implemented, attempting to terminate a job running this command would force the job into a
    "FAILED" state while continuing to execute this command and the job.
    """

    def __init__(self, service, ctx, recheck_interval=30):
        self.last_check = time.time()
        self.service = service  # type: Service
        self.sid = ctx.metadata.searchinfo.sid
        self.splunk_ver = [int(x) for x in ctx.metadata.searchinfo.splunk_version.split('.')]
        self.recheck_interval = recheck_interval
        self.ctx = ctx
        self.start_time = time.time()
        # Versions of Splunk lower than 7.1.0 treat the job lifecycle differently
        # For those versions, this check will fail prematurely
        # As such, we only run  check_termination when splunk_version >= 7.1.0
        if self.splunk_ver[0] < 7 or (self.splunk_ver[0] == 7 and self.splunk_ver[1] < 1):
            if CMD_TIMEOUT < 1:
                ctx.write_warning("Pulsedive Command : Splunk version '%s'. "
                                  "Unable to detect user-initiated termination of custom command. "
                                  "This feature works in Splunk version 7.1.0 and later. "
                                  "It is recommended, in this case, that CMD_TIMEOUT be set to a value greater than 0."
                                  % ctx.metadata.searchinfo.splunk_version)
            self.enabled = False
        else:
            self.enabled = True

    def _check_termination(self):
        """
        Queries Splunk's service REST to get status of the job.
        If the job has been terminated, raises a SplunkJobTerminatedException
        """
        self.last_check = time.time()
        job = self.service.job(self.sid)
        state = job['dispatchState'].upper()
        if state == "FAILED" or state == "FINALIZING" or state == "FINALIZED":
            raise SplunkJobTerminatedException(state)

    def check_termination(self, now=False):
        """
        Check if the job was terminated.
        This method has a built-in timer to avoid querying the info too often.
        :param now: use True to force a re-check now, ignoring the timer.
        """

        if CMD_TIMEOUT > 0:
            runtime = time.time() - self.start_time
            if runtime > CMD_TIMEOUT:
                raise CustomCommandTimeoutException(runtime)

        if not self.enabled:
            return

        if now or (time.time() - self.last_check) > self.recheck_interval:
            self._check_termination()


def _query_pulsedive_iocs(self, iocs):
    # Keep track of how many hashes we are dealing with
    if not isinstance(iocs, list):
        raise Exception("Unrecognized object type passed to _query_pulsedive_ips")

    out = {}

    # Query each IOC via Pulsedive
    for ioc in iocs:
        o = out[ioc] = {}

        raw_result = _query_pulsedive(self, {"ioc": ioc}, 1)

        # ioc names are not case sensitive as per RFC1035 (2.3.1)
        o['resource'] = ioc.lower()

        for x in ["iid", "type", "indicator", "risk", "risk_recommended", "manualrisk", "retired", "stamp_added", "stamp_updated", "stamp_seen", "stamp_probed", "stamp_retired", "recent", "submissions", "schema", "riskfactors", "attributes", "properties", "threats"]:
            if x in raw_result.keys():
                o[x] = str(raw_result.get(x))
            else:
                o[x] = ""

        o['query_time'] = time.time()

    return out


def _query_pulsedive(self, params, expect_n_results):
    """
    Execute HTTPs queries against Pulsedive api to get reports about HASH
    :param hash: a string or list of strings. The strings should be hex representations of MD5 or SHA256 hashes
    :return: Information from Pulsedive concerning the hashes.
    """
    import requests

    # Prepare Pulsedive request
    parameters = {
        "key": API_KEY,
        "q": "ioc=" + str(params['ioc']),
        "schema": "1",
        "pretty": "1"
    }

    response = requests.get('https://pulsedive.com/api/explore.php',
                            params=parameters, proxies=PROXY)
    
    # Exceeded API key call rate
    if response.status_code == 204:
        raise PulsediveRequestLimitExceededException()
    # Invalid token used
    elif response.status_code == 403:
        raise Exception("Got status code 403 from Pulsedive API. "
                        "This may indicate that an invalid token is being used. "
                        "You may change the token in app setup. ")
    # Some unexpected error occurred
    elif response.status_code != 200:
        raise Exception("Got status code %d from Pulsedive API." % response.status_code)

    json_response = response.json()

    parameters = {
        "key": API_KEY,
        "iid": str(json_response['results'][0]['iid']),
        "schema": "1",
        "pretty": "1",
        "historical": "0"
    }

    response = requests.get('https://pulsedive.com/api/info.php',
                            params=parameters, proxies=PROXY)

    # Exceeded API key call rate
    if response.status_code == 204:
        raise PulsediveRequestLimitExceededException()
    # Invalid token used
    elif response.status_code == 403:
        raise Exception("Got status code 403 from Pulsedive API. "
                        "This may indicate that an invalid token is being used. "
                        "You may change the token in app setup. ")
    # Some unexpected error occurred
    elif response.status_code != 200:
        raise Exception("Got status code %d from Pulsedive API." % response.status_code)

    json_response = response.json()

    return json_response


def batch(gen, n=1):
    """
    Get several items from a generator
    :param gen: The generator
    :param n: The number of items to get
    :return: A list of items retrieved from the generator
    """
    records = []
    for record in gen:
        records.append(record)
        n = n - 1
        if n <= 0:
            break
    return records


@Configuration(local=True)
class PulsediveCommand(StreamingCommand):
    ioc = Option(
        doc='''
        **Syntax:** **ioc=***<fieldname>*
        **Description:** Name of the field which contains the ioc''',
        require=False, validate=validators.Fieldname())
  
    def correlate_pulsedive(self, records):
        """
        Incorporate Pulsedive information into the events provided in 'records'
        :param records: The records to be supplemented with added information
        :return: None
        """
        for record in records:
            for k in ALL_OUTPUT_FIELDS[self.report_type]:
                if k not in record.keys():
                    record[k] = ""

        expected_min_resource_len = 0

        already_warned = False
        # Put records into temporary dict, as cross-reference
        records_dict = {}
        resources = []

        for record in records:
            # The following are validation checks
            if self.matching_field in record.keys() and len(record[self.matching_field]) >= expected_min_resource_len:
                _resource = record[self.matching_field]
                records_dict[_resource] = record
                resources.append(_resource)
            elif not already_warned:
                self.write_warning("Pulsedive Command: Warning: \
                One or more events had bad data or no data in your input field. \
                Normalize the field in your data to correct this issue. Note: this \
                is often caused by empty values, mvfield values, or values with leading or trailing whitespaces. \
                Warning: Unaddressed data quality issues can additionally cause subsequent failures with lookups. "
                                   )
                already_warned = True

        # If there are no hashes to scan, exit.
        if len(resources) == 0:
            self.logger.debug("Not querying Pulsedive API with %d resources" % len(resources))
            return
        self.logger.debug("Querying Pulsedive API with %d resources (%s)" % (len(resources), self.report_type))

        attempts = 0
        # Query the API
        while True:
            try:
                attempts += 1
                if self.report_type == "ioc":
                    pulsedive_res = _query_pulsedive_iocs(self, resources)
                break
            except PulsediveRequestLimitExceededException:
                # Always log to the search.log file
                self.logger.warning("Pulsedive Request Limit Exceeded. Waiting 1 minute before resuming queries.")

                # End sleep in 60 seconds
                sleep_end_time = time.time() + 60
                while time.time() < sleep_end_time:
                    # Check if user terminated the job
                    self.termination_helper.check_termination(now=True)
                    # Sleep at most 5 seconds, and at least enough seconds to reach end of timeout period
                    time.sleep(max(0.0, min(5.0, sleep_end_time - time.time())))
            except Exception as e:
                self.error_exit(e, "Unexpected error when querying Pulsedive API: %s" % e)
            if attempts > 10:
                self.error_exit(None, "Failed to retrieve results from Pulsedive after 10 retries. Aborting.")

        # Verify that we got expected number of results
        if len(pulsedive_res) != len(records_dict):
            self.error_exit(None, "Pulsedive returned %d results, but %d were expected. "
                                  "Is the batch_size value set too high for this specific key (app setup)?"
                            % (len(pulsedive_res), len(records_dict)))

        # Place values from results into the rows we are processing.
        for k, v in pulsedive_res.items():
            # Fill with real values from response (at least as many as we have)
            for pdk, pdv in v.items():
                    records_dict[k][pdk] = pdv

    def prepare(self):
        """
        Called by splunkd before the command executes.
        Used to get configuration data for this command from splunk.
        :return: None
        """
        global API_KEY, BATCHING, CMD_TIMEOUT, PROXY

        self.logger.debug('PDCommand: %s', self)  # logs command line

        proxy_password = None

        # Get the API key from Splunkd's REST API
        # Also get proxy password if configured
        for passwd in self.service.storage_passwords:  # type: StoragePassword
            if (passwd.realm is None or passwd.realm.strip() == "") and passwd.username == "pulsedive":
                API_KEY = passwd.clear_password
            if (passwd.realm is None or passwd.realm.strip() == "") and passwd.username == "pulsedive_proxy":
                proxy_password = passwd.clear_password

        # Verify we got the key
        if API_KEY is None or API_KEY == "defaults_empty":
            self.error_exit(None, "No API key found for Pulsedive. Re-run the app setup for the TA.")


    def stream(self, records):
        """
        Hooking point for splunk.
        :param records: The generator function provided by Splunk which will provide all the events.
        :return: yields events one at a time
        """
        self.termination_helper = TerminationHelper(self.service, self)

        self.logger.debug("PDCommand: BATCHING = %d" % BATCHING)

        self.matching_field = None
        self.report_type = None
        for rt in REPORT_TYPES:
            if getattr(self, rt) is not None:
                if self.report_type is not None:
                    self.error_exit(None, "Pulsedive Command: Getting multiple types of reports in a single search is not supported. "
                                          "Specify 'ioc=' and try again.")
                    return
                self.report_type = rt
                self.matching_field = getattr(self, rt)
        if self.report_type is None:
            self.error_exit(None, "Pulsedive Command: No field specified for matching. "
                                  "Specify 'ioc=' and try again.")
            return

        # Process the events
        try:
            while True:
                _records = batch(records, n=BATCHING)
                if len(_records) == 0:
                    break
                self.termination_helper.check_termination()
                self.correlate_pulsedive(_records)
                for record in _records:
                    yield record
        except SplunkJobTerminatedException as sjt:
            warning = "Pulsedive Command: Forcing exit. Reason: Parent job termination detected. " \
                      "Parent job state: %s" % sjt.state
            self.write_warning(warning)
            self.logger.warning(warning)
            return
        except CustomCommandTimeoutException as cct:
            warning = "Pulsedive Command: Forcing exit. Reason: Internal timeout reached. " \
                      "If necessary, the timeout can be increased on the app setup page. " \
                      "Command has been running for: %d seconds" % cct.runtime
            self.write_warning(warning)
            self.logger.warning(warning)
            return


dispatch(PulsediveCommand, sys.argv, sys.stdin, sys.stdout, __name__)
