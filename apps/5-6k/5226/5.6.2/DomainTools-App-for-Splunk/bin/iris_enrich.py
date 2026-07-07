from __future__ import absolute_import
from urllib.parse import unquote

import os
import sys
import json
import time
import requests

from settings import APP_ID

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(os.path.join(splunkhome, "etc", "apps", APP_ID, "lib"))
from splunklib.searchcommands import (
    dispatch,
    EventingCommand,
    Configuration,
    Option,
    validators,
)
from domaintools.exceptions import (
    ServiceException,
    NotAuthorizedException,
    ServiceUnavailableException,
)

from dt_logger import DTLogger
from dt_api_wrapper import DtApiWrapper
import idna
from shared_enrich_formatters import update_row
import dt_exception_messages

MAX_DOMAINS_PER_QUERY = 100
MAX_REQUEST_SIZE = 1400


@Configuration()
class IrisEnrichCommand(EventingCommand):
    """This custom search command makes a request to the iris-enrich API endpoint and appends the data to given domains.

    Inherits from the EventingCommand custom search type. Override the `transform` method as the entrypoint to this script

    Example:
        | makeresults | eval domain="domaintools.com" | dtirisenrich domain=domain
    """

    domain = Option(require=True)

    inline_results = Option(
        doc="""
                    **Syntax:** **inline_results=***<boolean>*
                    **Description:** Enrich events inline""",
        default=False,
        require=False,
    )

    feature = Option(
        doc="""
                **Syntax:** **feature=***<feature>*
                **Description:** Feature in the app where this was called""",
        default="adhoc",
        require=False,
    )

    def get_token(self):
        """get session key used to decrpyt api credentials"""
        return self.metadata.searchinfo.session_key

    def get_user(self):
        """get current logged in user"""
        return self.metadata.searchinfo.username

    def get_key_from_domain(self, domain):
        if not domain:
            return

        consolidated_errors = ""

        # To avoid errors encountered for encoded domains, decode the domain first before processing further
        decoded_domain = unquote(domain)

        try:
            return decoded_domain.encode("idna").decode("utf-8").lower()
        except Exception as error1:
            consolidated_errors = f"error1: {error1}"

        try:
            return idna.encode(decoded_domain, uts46=True).decode("utf-8").lower()
        except Exception as error2:
            consolidated_errors += f", error2: {error2}"
            self.dt_log.error(consolidated_errors, {"domain": domain})

    def empty_row(self):
        row = {
            "key": None,
            "en_domain_name": None,
            "dt_unknown": True,
            "dt_event_seen": True,
            "dt_queued": None,
            "dt_retrieved": None,
            "dt_observed": None,
            "en_ip_1_asn": None,
            "en_ip_1_country_code": None,
            "en_ip_1_isp": None,
            "en_ip_1_address": None,
            "en_ip_2_asn": None,
            "en_ip_2_isp": None,
            "en_ip_2_country_code": "us",
            "en_ip_2_address": None,
            "en_additional_ips_raw": None,
            "en_website_response_code": None,
            "en_additional_whois_email": None,
            "en_ssl_email": None,
            "en_ssl_info_1_subject": None,
            "en_ssl_info_1_organization": None,
            "en_ssl_info_1_hash": None,
            "en_ssl_info_issuer_common_name": None,
            "en_ssl_info_common_name": None,
            "en_ssl_info_not_after": None,
            "en_ssl_info_not_before": None,
            "en_ssl_info_duration": None,
            "en_ssl_info_alt_names": None,
            "en_additional_ssl_raw": None,
            "en_mx_1_ip": None,
            "en_mx_1_priority": None,
            "en_mx_1_host": None,
            "en_mx_1_domain": None,
            "en_additional_mx_raw": None,
            "en_threat_profile_type": None,
            "en_domain_expiration_date": None,
            "en_popularity_rank": None,
            "en_threat_profile_spam": None,
            "en_additional_soa_email": None,
            "en_name_server_1_host": None,
            "en_name_server_1_ip": None,
            "en_name_server_1_domain": None,
            "en_name_server_2_host": None,
            "en_name_server_2_ip": None,
            "en_name_server_2_domain": None,
            "en_additional_name_servers_raw": None,
            "en_registrar": None,
            "en_spf_info": None,
            "en_adsense_code": None,
            "en_google_analytics_code": None,
            "en_tag_raw": None,
            "en_tag": None,
            "en_redirect_url": None,
            "en_risk_score": None,
            "en_threat_profile_phishing": None,
            "en_threat_profile_evidence": None,
            "en_threat_profile_malware": None,
            "en_proximity_score": None,
            "en_tld": None,
            "en_is_active": None,
            "en_domain_create_date": None,
            "en_domain_updated_timestamp": None,
            "en_registrant_org": None,
            "en_registrant_name": None,
            "en_first_seen": None,
            "en_server_type": None,
            "en_website_title": None,
            "en_ga4": None,
            "en_gtm_codes": None,
            "en_fb_codes": None,
            "en_hotjar_codes": None,
            "en_baidu_codes": None,
            "en_yandex_codes": None,
            "en_matomo_codes": None,
            "en_statcounter_project_codes": None,
            "en_statcounter_security_codes": None,
            "en_additional_codes_raw": None,
            "_raw": None,
        }
        for contact_type in ["registrant", "technical", "billing", "admin"]:
            row["en_{0}_contact_org".format(contact_type)] = None
            row["en_{0}_contact_email".format(contact_type)] = None
            row["en_{0}_contact_name".format(contact_type)] = None
            row["en_{0}_contact_country".format(contact_type)] = None
            row["en_{0}_contact_street".format(contact_type)] = None
            row["en_{0}_contact_state".format(contact_type)] = None
            row["en_{0}_contact_city".format(contact_type)] = None
            row["en_{0}_contact_fax".format(contact_type)] = None
            row["en_{0}_contact_phone".format(contact_type)] = None
            row["en_{0}_contact_postal".format(contact_type)] = None

        return row

    def format_row(self, response, queued_domains):
        """format Iris Enrich response to Splunk row"""
        output = {}
        missing_domains = response.get("missing_domains")
        if missing_domains:
            self.dt_log.warning(
                dt_exception_messages.missing_domains.format(",".join(missing_domains)),
                {"code": "EAL204"},
            )
            for domain in missing_domains:
                row = self.empty_row()
                key = self.get_key_from_domain(domain)
                row["key"] = key
                row["en_domain_name"] = domain
                row["dt_queued"] = queued_domains.get(key, {}).get("queued")
                row["dt_retrieved"] = time.time()
                row["dt_observed"] = queued_domains.get(key, {}).get("observed")

                output[key] = row

        for result in response.get("results"):
            try:
                key = self.get_key_from_domain(result["domain"])

                row = {
                    "dt_queued": queued_domains[key]["queued"],
                    "dt_retrieved": time.time(),
                    "dt_observed": queued_domains[key]["observed"],
                    "dt_unknown": False,
                    "dt_event_seen": True,
                    "_raw": json.dumps(result),
                }

                update_row(row, result)

                output[key] = row
            except Exception as e:
                self.dt_log.error(
                    "error mapping domain. exception type: {0}, exception message {1}, domain: {2}".format(
                        type(e).__name__, e, json.dumps(result)
                    )
                )

        return output

    def enrich(self, api, queued_domains):
        """query Iris Enrich API for batch of domains

        :param api: domaintools.API
        :param queued_domains: dict or domains to enrich {domainname: {'queued': timestamp, 'observed': timestamp}}
        :return: list formatted rows or iris data
        """
        rows = {}
        try:
            response = api.iris_enrich(*list(queued_domains.keys())).response()
            rows = self.format_row(response, queued_domains)
            self.dt_log.info("api status up", {"status": "up"})
        except NotAuthorizedException as e:
            self.dt_log.error(dt_exception_messages.not_autorized, {"status": "down"})
            raise Exception(dt_exception_messages.not_autorized)
        except ServiceUnavailableException as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.service_not_available)
        except requests.exceptions.ProxyError as e:
            self.dt_log.error(e, {"status": "down"})
        except requests.exceptions.SSLError as e:
            self.dt_log.error(e, {"status": "down"})
        except Exception as e:
            self.dt_log.error(e, {"status": "down"})

        return rows

    def should_batch_query(self, queued_domains):
        return (
            len(queued_domains) >= MAX_DOMAINS_PER_QUERY
            or len(",".join(list(queued_domains.keys()))) >= MAX_REQUEST_SIZE
        )

    def result_generator(self, records, enrichment):
        for record in records:
            domain = self.get_key_from_domain(record.get(self.domain))
            domain_enrichment = enrichment.get(domain, self.empty_row())

            if self.inline_results:
                record.update(domain_enrichment)
                yield record
            else:
                yield domain_enrichment

    def transform(self, records):
        """This is the entry point to an EventingCommand subclass. You must override this method

        :param records: generator iterator of rows from previous command of SPL search
        :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "iris_enrich", os.path.basename(__file__), self.get_user(), self.feature
        )
        self.dt_log.info("starting iris_enrich.py")

        api_wrapper = DtApiWrapper(self.service, self.dt_log)
        api = api_wrapper.create_dt_api()

        queued_domains = {}
        queued_records = []

        for record in records:
            if self.domain not in record:
                continue

            # always convert to list to avoid additional conditioning
            input_domains = (
                record[self.domain]
                if isinstance(record[self.domain], list)
                else [record[self.domain]]
            )

            # since we expect a list in every transform
            # we will iterate over the list and process it
            for d in input_domains:
                record_copy = record.copy()

                key = self.get_key_from_domain(d)
                if not key:
                    continue

                record_copy[self.domain] = key
                queued_records.append(record_copy)

                queued_domains[key] = {
                    "queued": record.get("queued", None),
                    "observed": record.get("observed", None),
                }

            if self.should_batch_query(queued_domains):
                iris_data = self.enrich(api, queued_domains)
                yield from self.result_generator(queued_records, iris_data)

                queued_domains = {}
                queued_records = []

        if not queued_domains:
            self.dt_log.info("nothing to enrich, exiting script", {"status": "up"})
            return

        iris_data = self.enrich(api, queued_domains)
        yield from self.result_generator(queued_records, iris_data)

        self.dt_log.info("completed iris_enrich.py successfully")


dispatch(IrisEnrichCommand, sys.argv, sys.stdin, sys.stdout, __name__)
