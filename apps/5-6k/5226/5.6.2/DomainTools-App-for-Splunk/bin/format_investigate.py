from __future__ import absolute_import
import os, sys
import json
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
from dt_logger import DTLogger
import dt_exception_messages

from utils import convert_to_iso_format_date


@Configuration()
class FormatInvestigateCommand(EventingCommand):
    """This custom search command formats iris-investigate response for the domain profile dashboard

    Inherits from the EventingCommand custom search type. Override the `transform` method as the entrypoint to this script

    Attributes:
        output (str): The section of the iris-investigate response you want to format and output

    Example:
        | dtirisinvestigate domain=domaintools.com | dtformatinvestigate output=risk
    """

    output = Option(
        doc="""
            **Syntax:** **section=***<section>*
            **Description:** Name of the section to flatten [summary, admin_contact, technical_contact, billing_contact, ip, mx, ns, risk, ssl, email, tags]""",
        require=True,
        validate=validators.Set(
            "domain",
            "summary",
            "admin_contact",
            "technical_contact",
            "billing_contact",
            "registrant_contact",
            "ip",
            "mx",
            "ns",
            "risk",
            "ssl",
            "email",
            "tags",
            "codes",
            "pivot_summary",
            "all",
        ),
    )
    feature = Option(
        doc="""
                **Syntax:** **feature=***<feature>*
                **Description:** Feature in the app where this was called""",
        default="adhoc",
        require=False,
    )

    def get_user(self):
        """get current logged in user"""
        return self.metadata.searchinfo.username

    def format_pivots(self, value, count, field):
        """Makes value and count one value so we can render guided pivots"""
        return "{}%:%{}%:%{}".format(value, count, field) if count else value

    def check_no_results(
        self, output, field="field", message="No search results returned"
    ):
        if len(output) == 0:
            return [{field: message}]

        return output

    def output_domain(self, result):
        if result.get("message"):
            return [{"domain": result.get("message")}]

        return [{"domain": result.get("domain")}]

    def output_summary(self, result):
        """format top level data to Splunk row"""
        if result.get("message"):
            return []

        output = []
        registrar_status = []
        for status in result.get("registrar_status", []):
            registrar_status.append(status)
        output.append(
            {"field": "registrar_status", "value_count": ",".join(registrar_status)}
        )

        for field in [
            "domain",
            "active",
            "popularity_rank",
            "spf_info",
            "tld",
            "website_response",
            "data_updated_timestamp",
            "create_date",
            "adsense",
            "google_analytics",
            "expiration_date",
            "first_seen",
            "server_type",
            "website_title",
            "redirect_domain",
            "registrant_name",
            "registrant_org",
            "registrar",
        ]:
            field_name = field
            if field == "popularity_rank" and field not in result:
                field = "alexa"
                field_name = "popularity_rank"

            # some api responses use an empty string instead of an object for domains with missing values
            value = (
                result.get(field, {}).get("value", "")
                if isinstance(result.get(field), dict)
                else result.get(field)
            )

            count = (
                result.get(field, {}).get("count", 0)
                if isinstance(result.get(field), dict)
                else 0
            )
            pivot_field = field
            if field == "registrant_name":
                pivot_field = "registrant"

            value_count = self.format_pivots(value, count, pivot_field)
            output_dict = {"field": field_name, "value_count": value_count}
            output.append(output_dict)

        return output

    def output_contact(self, type, result):
        """format contact data to Splunk row"""
        output = []
        contact = result[type]
        for email in contact["email"]:
            email_value = email["value"]
            email_count = email["count"]
            output.append(
                {
                    "field": "email",
                    "value_count": self.format_pivots(
                        email_value, email_count, "email"
                    ),
                }
            )

        for field in [
            "name",
            "org",
            "street",
            "city",
            "state",
            "postal",
            "country",
            "phone",
            "fax",
        ]:
            value = contact[field]["value"]
            count = contact[field]["count"]
            output.append(
                {"field": field, "value_count": self.format_pivots(value, count, field)}
            )
        return output

    def output_mx(self, result):
        """format mx data to Splunk row"""
        output = []
        for mx_record in result["mx"]:
            ips = []
            for ip in mx_record["ip"]:
                ip_value = ip["value"]
                ip_count = ip["count"]
                ips.append(self.format_pivots(ip_value, ip_count, "mailserver_ip"))
            domain_value = mx_record["domain"]["value"]
            domain_count = mx_record["domain"]["count"]
            host_value = mx_record["host"]["value"]
            host_count = mx_record["host"]["count"]

            output.append(
                {
                    "id": result["domain"],
                    "domain": self.format_pivots(
                        domain_value, domain_count, "mailserver_domain"
                    ),
                    "host": self.format_pivots(
                        host_value, host_count, "mailserver_host"
                    ),
                    "ips": ",".join(ips),
                    "priority": mx_record["priority"],
                }
            )

        return output

    def output_ns(self, result):
        """format ns data to Splunk row"""
        output = []
        for ns_record in result["name_server"]:
            ips = []
            for ip in ns_record["ip"]:
                ip_value = ip["value"]
                ip_count = ip["count"]
                ips.append(self.format_pivots(ip_value, ip_count, "nameserver_ip"))

            domain_value = ns_record["domain"]["value"]
            domain_count = ns_record["domain"]["count"]
            host_value = ns_record["host"]["value"]
            host_count = ns_record["host"]["count"]

            output.append(
                {
                    "id": result["domain"],
                    "domain": self.format_pivots(
                        domain_value, domain_count, "nameserver_domain"
                    ),
                    "host": self.format_pivots(
                        host_value, host_count, "nameserver_host"
                    ),
                    "ips": ",".join(ips),
                }
            )

        return output

    def output_ip(self, result):
        """format ip data to Splunk row"""
        output = []
        for ip in result["ip"]:
            asns = []
            for asn in ip.get("asn", {}):
                asn_value = asn["value"]
                asn_count = asn["count"]
                asns.append(self.format_pivots(asn_value, asn_count, "asn"))

            address_value = ip["address"]["value"]
            address_count = ip["address"]["count"]

            output.append(
                {
                    "id": result["domain"],
                    "address": self.format_pivots(address_value, address_count, "ip"),
                    "asn": ",".join(asns),
                    "country_code": ip["country_code"]["value"],
                    "isp": ip["isp"]["value"],
                }
            )

        return output

    def output_risk(self, result):
        """format risk data to Splunk row"""
        if result.get("message"):
            return [{"risk_score": "Error", "type": "domain_risk"}]

        # overall risk score
        output = [
            {
                "id": result["domain"],
                "type": "domain_risk",
                "risk_score": (
                    result["domain_risk"].get("risk_score", "")
                    if isinstance(result["domain_risk"], dict)
                    else ""
                ),
                "evidence": "",
                "threats": "",
            }
        ]

        # component risk scores
        component_types = [
            "threat_profile_phishing",
            "threat_profile_malware",
            "threat_profile_spam",
            "proximity",
            "threat_profile",
        ]
        for component_type in component_types:
            component = next(
                (
                    d
                    for d in result["domain_risk"]["components"]
                    if d["name"] == component_type
                ),
                {},
            )

            threats = []
            if "threats" in component:
                for threat in component["threats"]:
                    threats.append(threat)

            evidence = []
            if "evidence" in component:
                for item in component["evidence"]:
                    evidence.append(item)

            output_dict = {
                "id": result["domain"],
                "type": component_type,
                "risk_score": component.get("risk_score") or "N/A",
                "threats": ",".join(threats) or "N/A",
                "evidence": ",".join(evidence) or "N/A",
            }

            output.append(output_dict)

        return output

    def output_ssl(self, result):
        """format ssl data to Splunk row"""
        output = []
        for cert in result["ssl_info"]:
            email = []
            for item in cert["email"]:
                email.append(item["value"])

            alt_names = []
            for item in cert["alt_names"]:
                alt_names.append(item["value"])

            output.append(
                {
                    "id": result["domain"],
                    "hash": self.format_pivots(
                        cert["hash"]["value"], cert["hash"]["count"], "ssl_hash"
                    ),
                    "subject": self.format_pivots(
                        cert["subject"]["value"],
                        cert["subject"]["count"],
                        "ssl_subject",
                    ),
                    "organization": self.format_pivots(
                        cert["organization"]["value"],
                        cert["organization"]["count"],
                        "ssl_org",
                    ),
                    "issuer_common_name": self.format_pivots(
                        cert["issuer_common_name"]["value"],
                        cert["issuer_common_name"]["count"],
                        "issuer_common_name",
                    ),
                    "common_name": self.format_pivots(
                        cert["common_name"]["value"],
                        cert["common_name"]["count"],
                        "common_name",
                    ),
                    "not_after": self.format_pivots(
                        convert_to_iso_format_date(cert["not_after"]["value"]),
                        cert["not_after"]["count"],
                        "not_after",
                    ),
                    "not_before": self.format_pivots(
                        convert_to_iso_format_date(cert["not_before"]["value"]),
                        cert["not_before"]["count"],
                        "not_before",
                    ),
                    "duration": self.format_pivots(
                        cert["duration"]["value"],
                        cert["duration"]["count"],
                        "duration",
                    ),
                    "alt_names": ",".join(alt_names),
                    "email": ",".join(email),
                }
            )

        return output

    def output_email(self, result):
        """format email data to Splunk row"""
        output = []
        for soa in result["soa_email"]:
            output.append(
                {
                    "id": result["domain"],
                    "type": "soa_email",
                    "email": self.format_pivots(soa["value"], soa["count"], "email"),
                }
            )

        for ssl in result["ssl_email"]:
            output.append(
                {
                    "id": result["domain"],
                    "type": "ssl_email",
                    "email": self.format_pivots(ssl["value"], ssl["count"], "email"),
                }
            )

        for whois in result["additional_whois_email"]:
            output.append(
                {
                    "id": result["domain"],
                    "type": "whois_email",
                    "email": self.format_pivots(
                        whois["value"], whois["count"], "email"
                    ),
                }
            )

        return output

    def output_tags(self, result):
        """format tags data to Splunk row"""
        output = []
        for tag in result["tags"]:
            output.append(
                {
                    "id": result["domain"],
                    "label": tag["label"],
                    # Everything is going to be scoped as Iris for now
                    # 'scope': tag['scope'],
                    "scope": "Iris",
                    "tagged_at": tag["tagged_at"],
                }
            )

        return self.check_no_results(output, "label")

    def output_codes(self, result):
        """format codes data to Splunk row"""
        output = []
        for field in [
            "ga4",
            "gtm_codes",
            "fb_codes",
            "hotjar_codes",
            "baidu_codes",
            "yandex_codes",
            "matomo_codes",
            "statcounter_project_codes",
            "statcounter_security_codes",
        ]:
            codes = []
            for code in result.get(field, []):
                code_value = code["value"]
                code_count = code["count"]
                codes.append(self.format_pivots(code_value, code_count, field))

            output.append(
                {
                    "id": result["domain"],
                    "field": field,
                    "code_value": ",".join(codes),
                }
            )

        return output

    def output_pivot_summary(self, result):
        output_dict = {
            "domain": result["domain"],
            "risk": result["domain_risk"].get("risk_score"),
            "create_date": result["create_date"].get("value"),
            "zerolist": None,
            "proximity": None,
            "threat_profile": None,
            "threat_profile_malware": None,
            "threat_profile_phishing": None,
            "threat_profile_spam": None,
        }
        for score in result["domain_risk"]["components"]:
            output_dict[score["name"]] = score["risk_score"]
        return [output_dict]

    def output_all(self, result):
        """format all iris-investigate data into a _raw column"""
        return [{"domain": result["domain"], "_raw": json.dumps(result)}]

    def transform(self, records):
        """This is the entry point to an EventingCommand subclass. You must override this method

        :param records: generator iterator of rows from previous command of SPL search
        :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "iris_investigate",
            os.path.basename(__file__),
            self.get_user(),
            self.feature,
        )

        for record in records:
            try:
                if "message" not in record:
                    record = json.loads(record.get("_raw"))

                if self.output == "domain":
                    output = self.output_domain(record)
                elif self.output == "summary":
                    output = self.output_summary(record)
                elif self.output in [
                    "admin_contact",
                    "billing_contact",
                    "registrant_contact",
                    "technical_contact",
                ]:
                    output = self.output_contact(self.output, record)
                elif self.output == "mx":
                    output = self.output_mx(record)
                elif self.output == "ns":
                    output = self.output_ns(record)
                elif self.output == "ip":
                    output = self.output_ip(record)
                elif self.output == "risk":
                    output = self.output_risk(record)
                elif self.output == "ssl":
                    output = self.output_ssl(record)
                elif self.output == "email":
                    output = self.output_email(record)
                elif self.output == "tags":
                    output = self.output_tags(record)
                elif self.output == "codes":
                    output = self.output_codes(record)
                elif self.output == "pivot_summary":
                    output = self.output_pivot_summary(record)
                else:
                    output = self.output_all(record)
                for row in output:
                    yield row
            except Exception as e:
                self.dt_log.error(
                    "error formatting domain: {0}, exception type: {1}, exception message: {2}".format(
                        json.dumps(record), type(e).__name__, e
                    )
                )
                raise Exception(dt_exception_messages.generic.format(e))


dispatch(FormatInvestigateCommand, sys.argv, sys.stdin, sys.stdout, __name__)
