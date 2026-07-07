from __future__ import absolute_import
import os
import sys
import json
import requests
from six.moves import range
from datetime import datetime, timedelta
from settings import APP_ID

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(os.path.join(splunkhome, "etc", "apps", APP_ID, "lib"))
from splunklib import client
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)
from domaintools.exceptions import (
    NotAuthorizedException,
    ServiceUnavailableException,
    NotFoundException,
)

from dt_logger import DTLogger
from dt_api_wrapper import DtApiWrapper
import dt_exception_messages


@Configuration()
class ImportIrisDetectResultsCommand(StreamingCommand):
    """This custom search command takes in a list of terms, and makes a request to the Iris Detect API endpoint and outputs the current days results.

    Inherits from the StreamingCommand custom search type. Override the `stream` method as the entrypoint to this script

    Example:
        | from inputlookup:dt_iris_detect_monitors | dtimportirisdetectresults
    """

    feature = Option(
        doc="""
                **Syntax:** **feature=***<feature>*
                **Description:** Feature in the app where this was called""",
        default="adhoc",
        require=False,
    )

    lookup_type = Option(
        doc="""
                **Syntax:** **lookup_type=***<lookup_type>*
                **Description:** Results can either be new, ignored, watched or all""",
        default="all",
        require=False,
    )

    twenty_four_hours = str((datetime.now() - timedelta(days=1)).astimezone())
    monitor_id = Option(require=False, default=False)
    discovered_since = Option(require=False, default=twenty_four_hours)
    changed_since = Option(require=False, default=twenty_four_hours)
    ignored_since = Option(require=False, default=twenty_four_hours)

    def get_token(self):
        """get session key used to decrypt api credentials"""
        return self.metadata.searchinfo.session_key

    def get_user(self):
        """get current logged in user"""
        return self.metadata.searchinfo.username

    @staticmethod
    def format_common_fields(result):
        """format top level fields of Iris Detect response"""
        return {
            "dt_domain": result.get("domain"),
            "dt_state": result.get("state"),
            "dt_status": result.get("status"),
            "dt_discovered_date": datetime.fromisoformat(
                result.get("discovered_date")
            ).timestamp(),
            "dt_changed_date": (
                datetime.fromisoformat(result.get("changed_date")).timestamp()
                if result.get("changed_date")
                else datetime.fromisoformat(result.get("discovered_date")).timestamp()
            ),
            "dt_escalations": result.get("escalations"),
            "dt_risk_score": result.get("risk_score"),
            "dt_risk_status": result.get("risk_score_status"),
            "dt_mx_exists": result.get("mx_exists"),
            "dt_tld": result.get("tld"),
            "dt_domain_id": result.get("id"),
            "dt_monitor_ids": result.get("monitor_ids"),
            "dt_create_date": result.get("create_date"),
            "dt_registrar": result.get("registrar"),
            "dt_registrant_contact_email": result.get("registrant_contact_email"),
        }

    @staticmethod
    def format_ips(result):
        """map fields from Iris Detect ips to Splunk columns"""
        ips = result.get("ip", [])
        output = {"dt_ip_raw": json.dumps(ips) if ips else None}

        for count in range(1, 3):
            ip = ips.pop() if ips else {}
            output["dt_ip_address_{0}".format(count)] = ip.get("ip")

        return output

    @staticmethod
    def format_name_servers(result):
        """map fields from Iris Detect name servers to Splunk columns"""
        name_servers = result.get("name_server", [])
        output = {
            "dt_nameServer_raw": json.dumps(name_servers) if name_servers else None
        }

        for count in range(1, 3):
            ns = name_servers.pop() if name_servers else {}
            output["dt_nameServer_{0}".format(count)] = ns.get("host")

        return output

    @staticmethod
    def format_mail_servers(result):
        """map fields from Iris Detect mail servers to Splunk columns"""
        mail_servers = result.get("mx", [])
        output = {
            "dt_mailServer_raw": json.dumps(mail_servers) if mail_servers else None
        }

        for count in range(1, 3):
            mx = mail_servers.pop() if mail_servers else {}
            output["dt_mailServer_{0}".format(count)] = mx.get("host")

        return output

    @staticmethod
    def format_risk_score_components(result):
        """map fields from Iris Detect risk score components to Splunk columns"""
        components = result.get("risk_score_components", {})
        threat_profile = components.get("threat_profile", {})
        return {
            "dt_proximity_score": components.get("proximity"),
            "dt_threat_profile_malware": threat_profile.get("malware"),
            "dt_threat_profile_phishing": threat_profile.get("phishing"),
            "dt_threat_profile_spam": threat_profile.get("spam"),
            "dt_threat_profile_evidence": threat_profile.get("evidence"),
        }

    def get_new_results(self, api, kwargs):
        response = api.iris_detect_new_domains(**kwargs).response()
        results = response.get("watchlist_domains", [])
        count = response.get("count")
        while response.get("total_count") != count:
            kwargs["offset"] += response.get("limit")
            response = api.iris_detect_new_domains(**kwargs).response()
            count += response.get("count")
            results.extend(response.get("watchlist_domains"))

        return results

    def get_watched_results(self, api, kwargs):
        response = api.iris_detect_watched_domains(**kwargs).response()
        results = response.get("watchlist_domains", [])
        count = response.get("count")
        while response.get("total_count") != count:
            kwargs["offset"] += response.get("limit")
            response = api.iris_detect_watched_domains(**kwargs).response()
            count += response.get("count")
            results.extend(response.get("watchlist_domains"))

        return results

    def get_ignored_results(self, api, kwargs):
        response = api.iris_detect_ignored_domains(**kwargs).response()
        results = response.get("watchlist_domains", [])
        count = response.get("count")
        while response.get("total_count") != count:
            kwargs["offset"] += response.get("limit")
            response = api.iris_detect_ignored_domains(**kwargs).response()
            count += response.get("count")
            results.extend(response.get("watchlist_domains"))

        return results

    def get_splunk_detect_monitors(self, records):
        """get list of detect monitor Ids passed into this script

        :param records: search results piped into this script including column for monitor_ids
        :return: list of detect monitor IDs
        """
        monitors = []
        for record in records:
            if int(record["discover_new_domains"]) == 1:
                monitors.append(record["monitor_id"])
        return monitors

    def is_result_monitored_in_splunk(self, result, splunk_monitors):
        """determine if iris detect result is monitored in splunk

        :param result: iris detect result
        :param splunk_monitors: list of detect monitor IDs enabled for monitoring in splunk
        :return: boolean
        """
        return set(result.get("monitor_ids")) & set(splunk_monitors)

    def get_results(self, api, monitor_ids):
        """Query Iris Detect API for new or watched domains

        :param api: domaintools.API
        :param monitor_ids: list of detect monitor IDs enabled for monitoring in splunk
        :return: list formatted rows of Iris Detect results
        """
        rows = []
        try:
            kwargs = {"include_domain_data": True, "offset": 0}
            new_results = []
            watched_results = []
            ignored_results = []
            if self.monitor_id:
                kwargs["monitor_id"] = self.monitor_id
            if self.lookup_type == "new":
                if self.discovered_since:
                    kwargs["discovered_since"] = self.discovered_since
                new_results = self.get_new_results(api, kwargs)
            elif self.lookup_type == "watched":
                if self.changed_since:
                    kwargs["changed_since"] = self.changed_since
                watched_results = self.get_watched_results(api, kwargs)
            elif self.lookup_type == "ignored":
                if self.ignored_since:
                    kwargs["ignored_since"] = self.ignored_since
                ignored_results = self.get_ignored_results(api, kwargs)
            elif self.lookup_type == "all":
                if self.discovered_since:
                    kwargs["discovered_since"] = self.discovered_since
                new_results = self.get_new_results(api, kwargs)
                if "discovered_since" in kwargs:
                    del kwargs["discovered_since"]
                if self.changed_since:
                    kwargs["changed_since"] = self.changed_since
                kwargs["offset"] = 0
                watched_results = self.get_watched_results(api, kwargs)
                if self.ignored_since:
                    kwargs["ignored_since"] = self.ignored_since
                ignored_results = self.get_ignored_results(api, kwargs)

            for result in new_results:
                if not self.is_result_monitored_in_splunk(result, monitor_ids):
                    continue

                row = {}
                row.update(self.format_common_fields(result))
                row.update(self.format_ips(result))
                row.update(self.format_name_servers(result))
                row.update(self.format_mail_servers(result))
                row.update(self.format_risk_score_components(result))
                rows.append(row)
            for result in watched_results:
                if not self.is_result_monitored_in_splunk(result, monitor_ids):
                    continue

                row = {}
                row.update(self.format_common_fields(result))
                row.update(self.format_ips(result))
                row.update(self.format_name_servers(result))
                row.update(self.format_mail_servers(result))
                row.update(self.format_risk_score_components(result))
                rows.append(row)
            for result in ignored_results:
                if not self.is_result_monitored_in_splunk(result, monitor_ids):
                    continue

                row = {}
                row.update(self.format_common_fields(result))
                row.update(self.format_ips(result))
                row.update(self.format_name_servers(result))
                row.update(self.format_mail_servers(result))
                row.update(self.format_risk_score_components(result))
                rows.append(row)

        except NotAuthorizedException:
            self.dt_log.error(dt_exception_messages.not_autorized, {"status": "down"})
            raise Exception(dt_exception_messages.missing_iris_detect_access)
        except ServiceUnavailableException:
            self.dt_log.error(
                dt_exception_messages.service_not_available, {"status": "down"}
            )
            raise Exception(dt_exception_messages.service_not_available)
        except NotFoundException as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.not_found_error)
        except requests.exceptions.ProxyError as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.proxy_error)
        except requests.exceptions.SSLError as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.ssl_error)
        except Exception as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.generic.format(e)) from e

        self.dt_log.info("completed import_iris_detect_results.py")

        return rows

    def stream(self, records):
        """This is the entry point to an StreamCommand subclass. You must override this method

        :param records: generator iterator of rows from previous command of SPL search
        :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "iris_detect", os.path.basename(__file__), self.get_user(), self.feature
        )
        self.dt_log.info("starting import_iris_detect_results.py")

        api_wrapper = DtApiWrapper(self.service, self.dt_log)
        api = api_wrapper.create_dt_api()

        monitors = self.get_splunk_detect_monitors(records)

        yield from self.get_results(api, monitors)

        self.dt_log.info("api status up", {"status": "up"})
        self.dt_log.info("completed import_iris_detect_results.py successfully")


dispatch(ImportIrisDetectResultsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
