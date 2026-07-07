# pylint: disable=import-error
"""
Splunk bindings to generate positive threatstream matches on disk
"""
import os
import time
import csv
import datetime
import sys
import copy

from random import randint, choice

from six import PY2, iteritems, iterkeys

import util.splunk_access
import util.kvs_manager
import ts.settings as settings

from splunklib.searchcommands import GeneratingCommand, Configuration, Option, validators, dispatch


cim_log_format = "%s %s"

cim_static_fields = {
    "vendor": "anomali",
    "product": "_test_logs",
    "src": "",
    "dest": "",
    "src_port": "",
    "dest_port": "",
    "log_format": "",
}

cim_log_network_traffic_format = {
    "action": "",
    "direction": "",
    "protocol": "",
    "src_ip": "",
    "dest_ip": "",
}

# Done
cim_log_dns_format = {
    "query": "",  # Indicator field
    "message_type": "QUERY",
    "query_type": "Query",
    "query_count": 1,
    "record_type": "A",
    "reply_code": "NoError",
}

# Done
cim_log_intrusion_detection_format = {
    "action": "",  # Allowed OR  Blocked
    "category": "",  # stuff like  spyware, ftp-attack, etc etc
    "signature": "",
    "user": "",
    "ids_type": "",  # network, host, application, wireless
}

# We only create AV logs here, dont care about web or email
cim_log_malware_attacks_format = {
    "action": "",  # Expecting allowed, blocked or deferred
    "category": "",  # e.g. keylogger, hacktool, ad-supported program
    "file_hash": "",
    "file_name": "",
    "user": "",
    "product_version": "1.0.0",
    "signature_version": "1.0.0"
}

cim_log_certificates_format = {
    "ssl_hash": "",
    "ssl_engine": "ssl",
    "ssl_is_valid": "false",
    "ssl_issuer": "Anomali Test Generator",
    "ssl_issuer_common_name": "AnomaliTestGenerator",
    "ssl_issuer_email": "test@anomalitest.test",
    "ssl_issuer_locality": "Outer Space",
    "ssl_issuer_organization": "Anomali",
    "ssl_name": "test_ssl.cer",
    "ssl_email": "test_issuer@test.test"
}

cim_log_web_format = {
    "action": "",  # allowed, blocked
    "http_content_type": "",
    "http_user_agent": "",
    "http_referrer": "",
    "status": "",  # 200 if allowed, 401 if blocked
    "url": "",
    "user": "",
}

cim_log_email_format = {
    "action": "",  # delivered, blocked, quarantined, deleted
    "message_id": "",
    "recipient": "",
    "src_user": "",
    "subject": "Anomali Test Event",
    "signature": "Anomali Test signature",
}


def random_ip():
    """str: return a semi-randomised internal ip address"""
    return "10.0.0.%s" % randint(1, 255)


def random_port():
    """int: return a randomised port"""
    return randint(1, 65535)


@Configuration(local=True)
class SplunkMatchGen(GeneratingCommand):
    """Splunk Generating command that allows a user to create matches on disk ready for ingestion"""
    event_fields = ['_time',
                    'file_name',
                    'http_refer',
                    'http_user_agent',
                    'user',
                    'src',
                    'action',
                    'dest',
                    'url',
                    'file_hash',
                    'dest_port',
                    'src_port',
                    'recipient',
                    'src_user',
                    'src_ip',
                    'dest_ip'
                   ]
    users = ["sam6543", "jbennett221", "abrown", "mjones"]
    datamodel_options = ["optic", "cim"]
    event_actions = ['detected', 'missed', 'allowed', 'alerted', 'blocked']
    IOC_TYPES = ['ip', 'domain', 'url', 'email', 'md5']
    threatmodels = ["actor", "tipreport"]

    event_count = Option(default=100, validate=validators.Integer())
    datamodel = Option(default="optic")

    cim_file_name = 'ts_cim_events.log'
    optic_file_name = 'ts_sample_events.csv'
    tm_iocs_only = Option(default=True, validate=validators.Boolean())
    query_limit = Option(default=5000, validate=validators.Integer())

    itype = Option(default=[], validate=validators.List())

    def prepare(self):
        """Quick and dirty validation of arguments"""
        if self.datamodel not in self.datamodel_options:
            raise ValueError("unable to determine datamodel to generate events for")

        if self.query_limit <0:
            raise ValueError("query_limit must be a positive integer")

    def generate(self):

        yield {
            "_raw": "Taking paramaters tm_iocs_only: %s, query_limit: %s, itype: %s, datamodel: %s, event_count: %s " %
                    (self.tm_iocs_only, self.query_limit, self.itype, self.datamodel, self.event_count),
            "_time": time.time()
        }

        python_version = "Python 2" if PY2 else "Python 3"
        yield {"_raw": 'Generating events under {}'.format(python_version), "_time": time.time()}

        self.splunkd = util.splunk_access.SplunkAccess(session_key=self.service.token, logger=self.logger)
        kvsm = self.splunkd.get_kvsm()

        if not os.path.exists(settings.get_samples_dir()):
            yield {"_time": time.time(), "_raw": "Didn't find Samples directory, creating"}
            try:
                os.mkdir(settings.get_samples_dir())
                yield {"_time": time.time(), "_raw": "Created Samples directory at %s" % settings.get_samples_dir()}
            except OSError:
                pass
        else:
            yield {"_time": time.time(), "_raw": "Found existing samples directory at %s" % settings.get_samples_dir()}

        t0 = time.time()
        # query the kvstore and bring back indicators
        self.ioc_store = {}
        kvstore_query = self.create_kvstore_query()
        yield {"_raw": "KVStore Query: %s" % kvstore_query, "_time": time.time()}
        for ioc_format in self.IOC_TYPES:
            self.ioc_store[ioc_format] = []
            collection_name = 'ts_%s' % ioc_format

            indicator_field = self.get_lookup_ioc_field(ioc_format)
            # Query only for threatmodel related items
            query = {
                "fields": '%s,tipreport,actor,itype' % indicator_field,
                "limit": self.query_limit,  # Used to prevent mem crashes in huge installs
                "query": kvstore_query
            }
            kvstore_entries = kvsm.get_kvs_with_query(collection_name, query)
            for kvstore_entry in kvstore_entries:
                kvstore_entry["value"] = kvstore_entry[indicator_field]
                self.ioc_store[ioc_format].append(kvstore_entry)

        t1 = time.time()
        yield {"_raw": 'ioc_store load time: %s ' % (t1 - t0), "_time": time.time()}
        #yield {"_raw": 'ioc_store: %s' % (self.ioc_store), "_time": time.time()}
        eventgen_metadata = None
        oneshot_sourcetype = None
        for ioc_type in self.IOC_TYPES:
            yield {"_raw": 'Found %s relevant ioc of type %s' % (len(self.ioc_store[ioc_type]), ioc_type), "_time": time.time()}

        if self.datamodel == "optic":
            yield {"_raw": "Generating sample event data to file %s" % self.optic_file_name,
                   "_time": time.time()}
            oneshot_sourcetype = "anomali_test"
            eventgen_metadata = self.gen_optic_logs()

        elif self.datamodel == "cim":
            yield {"_raw": "Generating sample event data to file %s" % self.cim_file_name,
                   "_time": time.time()}
            oneshot_sourcetype = "anomali_cim_test"
            eventgen_metadata = self.gen_cim_events()

        yield {"_raw": "Finished writing sample event data", "_time": time.time()}

        for metadata_entry in eventgen_metadata["messages"]:
            yield {"_raw": "%s" % metadata_entry, "_time": time.time()}

        yield {"_raw": "%s" % eventgen_metadata, "_time": time.time()}

        if eventgen_metadata:
            yield {"_raw": "Uploading file via oneshot api", "_time": time.time()}
            self.add_oneshot(sourcetype=oneshot_sourcetype, file_location=eventgen_metadata["file_location"])
            os.remove(eventgen_metadata["file_location"])

        yield {"_raw": "Finished running script %s" % os.path.basename(__file__), "_time": time.time()}

    def add_oneshot(self,  sourcetype="anomali", file_location=None, index="main"):
        """Attempt to add the events file directly to the Splunk instance via the oneshot command"""

        try:
            index = self.splunkd.service.indexes[index]
        except Exception:
            raise ValueError("Index %s does not exist on this host")

        index.upload(file_location, sourcetype=sourcetype)

    def gen_optic_logs(self):
        """Generate TS_Optic compliant events

        Yields:
            str: logging information, this is escalated to the splunk search interface as events
        """
        sample_file = os.path.join(settings.get_samples_dir(), self.optic_file_name)

        metadata = {
            "file_location": sample_file,
            "messages": []
        }

        with open(sample_file, 'w') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.event_fields)
            writer.writeheader()

            for ioc_format in self.IOC_TYPES:
                iocs = self.ioc_store[ioc_format]
                if self.tm_iocs_only and self.itype:
                    for threatmodel in self.threatmodels:
                        for itype in self.itype:
                            _iocs = copy.deepcopy(self.threatmodel_related_iocs(iocs, threatmodel))
                            _iocs = self.itype_related_iocs(_iocs, itype)
                            metadata["messages"].append(
                                "Found %s iocs relevant to format %s, itype %s, threatmodel %s" % (
                                len(_iocs), ioc_format, itype, threatmodel))
                            written_count = self.optic_log_writer(_iocs, writer, ioc_format)
                            metadata["messages"].append(
                                "Wrote %s logs to file with format %s itype %s and threatmodel %s" % (written_count, ioc_format, itype, threatmodel))
                elif self.tm_iocs_only:
                    for threatmodel in self.threatmodels:
                        _iocs = copy.deepcopy(self.threatmodel_related_iocs(iocs, threatmodel))
                        metadata["messages"].append(
                            "Found %s iocs relevant to format %s, threatmodel %s " % (len(_iocs), ioc_format, threatmodel))
                        written_count = self.optic_log_writer(_iocs, writer, ioc_format)
                        metadata["messages"].append(
                            "Wrote %s logs to file with format %s threatmodel %s" % (written_count, ioc_format, threatmodel))
                elif self.itype:
                    for itype in self.itype:
                        _iocs = copy.deepcopy(self.itype_related_iocs(iocs, itype))
                        metadata["messages"].append("Found %s iocs relevant to format %s, itype %s " % (len(_iocs), ioc_format, itype))
                        written_count = self.optic_log_writer(_iocs, writer, ioc_format)
                        metadata["messages"].append(
                            "Wrote %s logs to file with format %s itype %s" % (written_count, ioc_format, itype))
                else:
                    _iocs = copy.deepcopy(iocs)
                    metadata["messages"].append("Found %s iocs relevant to format %s " % (len(_iocs), ioc_format))
                    written_count = self.optic_log_writer(_iocs, writer, ioc_format)
                    metadata["messages"].append("Wrote %s logs to file with format %s" % (written_count, ioc_format))

        return metadata

    def optic_log_writer(self, iocs, csv_writer, ioc_format):
        """Writes the TS_Optic log to file"""

        counter = 0
        if not iocs:
            return 0
        else:
            for _ in range(0, int(self.event_count)):
                counter += 1
                csv_writer.writerow(self.gen_event(ioc_format, iocs))
            return counter

    def cim_log_writer(self, iocs, file_, ioc_format ):
        """Writes CIM logs to file"""

        counter = 0
        if not iocs:
            return 0
        else:
            for _ in range(0, int(self.event_count)):
                counter += 1
                indicator_row = iocs[randint(0, len(iocs) - 1)]
                ioc_val = indicator_row.get("value")
                ioc_itype = indicator_row.get("itype")
                file_.write("%s\n" % self.cim_event(ioc_format, ioc_val, ioc_itype))
            return counter

    def gen_cim_events(self):
        """Generate cim logs and send to the cim log file"""

        sample_file = os.path.join(settings.get_samples_dir(), self.cim_file_name)

        metadata = {
            "file_location": sample_file,
            "messages": []
        }
        with open(sample_file, 'w') as f:
            for ioc_format in self.IOC_TYPES:
                iocs = self.ioc_store[ioc_format]
                if self.tm_iocs_only and self.itype:
                    metadata["messages"].append("Found both TM and itype options specified")
                    for threatmodel in self.threatmodels:
                        for itype in self.itype:
                            _iocs = copy.deepcopy(self.threatmodel_related_iocs(iocs, threatmodel))
                            _iocs = self.itype_related_iocs(_iocs, itype)
                            written_count = self.cim_log_writer(_iocs, f, ioc_format)
                            metadata["messages"].append(
                                "Wrote %s logs to file with format %s itype %s and threatmodel %s" % (
                                written_count, ioc_format, itype, threatmodel))
                elif self.tm_iocs_only:
                    for threatmodel in self.threatmodels:
                        _iocs = copy.deepcopy(self.threatmodel_related_iocs(iocs, threatmodel))
                        written_count = self.cim_log_writer(_iocs, f, ioc_format)
                        metadata["messages"].append(
                            "Wrote %s logs to file with format %s threatmodel %s" % (
                            written_count, ioc_format, threatmodel))
                elif self.itype:
                    for itype in self.itype:
                        _iocs = copy.deepcopy(self.itype_related_iocs(iocs, itype))
                        written_count = self.cim_log_writer(_iocs, f, ioc_format)
                        metadata["messages"].append(
                            "Wrote %s logs to file with format %s itype %s" % (
                            written_count, ioc_format, itype))
                else:
                    _iocs = copy.deepcopy(iocs)
                    written_count = self.cim_log_writer(_iocs, f, ioc_format)
                    metadata["messages"].append(
                        "Wrote %s logs to file with format %s" % (written_count, ioc_format))

        return metadata

    def cim_event(self, ioc_format, indicator, itype):
        """Attempt to create an appropriate"""
        direction = choice(["inbound", "outbound"])

        static_fields = copy.deepcopy(cim_static_fields)
        static_fields["dest_port"] = random_port()
        static_fields["src_port"] = random_port()

        if ioc_format == "ip":
            log_format = choice(["network", "ids"])

            if log_format == "network":
                # Create Network Traffic logs
                static_fields["log_format"] = "anomali_test_cim_network_traffic"
                static_fields["src"] = indicator if direction == "inbound" else random_ip()
                static_fields["dest"] = indicator if direction == "outbound" else random_ip()

                network_format = copy.deepcopy(cim_log_network_traffic_format)
                network_format["direction"] = direction
                network_format["src_ip"] = static_fields["src"]
                network_format["dest_ip"] = static_fields["dest"]

                static_fields.update(network_format)

            else:
                # Create IDS logs
                static_fields["log_format"] = "anomali_test_cim_intrusion_detection"
                static_fields["src"] = indicator if direction == "inbound" else random_ip()
                static_fields["dest"] = indicator if direction == "outbound" else random_ip()

                ids_format = copy.deepcopy(cim_log_intrusion_detection_format)
                ids_format["action"] = choice(["allowed", "blocked"])
                ids_format["category"] = itype
                ids_format["signature"] = choice(["test_sig_1", "test_sig_2", "test_sig_3"])
                ids_format["user"] = choice(self.users)
                ids_format["ids_type"] = "network"

                static_fields.update(ids_format)

        elif ioc_format == "url":
            # Create Web logs
            action = choice(["allowed", "blocked"])
            static_fields["log_format"] = "anomali_test_cim_web"

            web_format = copy.deepcopy(cim_log_web_format)
            web_format["action"] = action
            web_format["url"] = indicator
            web_format["http_content_type"] = "application/json"
            web_format["http_referrer"] = "-"
            web_format["status"] = 200 if action == "allowed" else 401
            web_format["user"] = choice(self.users)

            static_fields.update(web_format)

        elif ioc_format == "domain":
            # Create DNS logs
            static_fields["log_format"] = "anomali_test_cim_dns"
            static_fields["src"] = random_ip()
            static_fields["dest"] = random_ip()

            dns_format = copy.deepcopy(cim_log_dns_format)
            dns_format["query"] = indicator

            static_fields.update(dns_format)

        elif ioc_format == "email":
            # Create Email logs

            static_fields["log_format"] = "anomali_test_cim_email"
            static_fields["src"] = random_ip()
            static_fields["dest"] = random_ip()

            email_format = copy.deepcopy(cim_log_email_format)
            email_format["action"] = choice(["delivered", "blocked", "quarantined", "deleted"])
            email_format["src_user"] = indicator if direction == "inbound" else \
                                        "%s@anomalitest.test" % choice(self.users)
            email_format["recipient"] = indicator if direction == "outbound" else \
                                        "%s@anomalitest.test" % choice(self.users)
            email_format["message_id"] = random_port()

            static_fields.update(email_format)

        elif ioc_format == "md5":
            if itype == "mal_sslcert_sha1":
                # Create Certificate logs
                static_fields["log_format"] = "anomali_test_cim_certificate"
                static_fields["src"] = random_ip()
                static_fields["dest"] = random_ip()

                certificate_format = copy.deepcopy(cim_log_certificates_format)
                certificate_format["ssl_hash"] = indicator
                static_fields.update(certificate_format)

            else:
                static_fields["log_format"] = "anomali_test_cim_malware"
                static_fields["src"] = random_ip()
                static_fields["dest"] = random_ip()

                # Create Malware logs
                malware_format = copy.deepcopy(cim_log_malware_attacks_format)
                malware_format["action"] = choice(["allowed", "blocked", "deferred"])
                malware_format["category"] = choice(["hack_tool", "heuristics", "cloud_detection", "EICAR", "spyware"])
                malware_format["signature"] = choice(["heuristics", "cloud", "eicar", "test_sig"])
                malware_format["file_hash"] = indicator
                malware_format["file_name"] = "test_hash_%s.txt" % randint(1, 10000)
                malware_format["user"] = choice(self.users)

                static_fields.update(malware_format)

        kv_values = ['%s="%s"' % (key, value) for key, value in iteritems(static_fields)]
        date = datetime.datetime.fromtimestamp(time.time()).isoformat()

        return cim_log_format % (date, ", ".join(kv_values))

    def get_lookup_ioc_field(self, ioc_format):
        """Change the ioc field mapping for IOC_TYPE = ip to srcip

        Args:
            ioc_format (str): the intelligence type

        Returns:
            ioc_type (str): transformed string
        """
        return ioc_format if ioc_format != 'ip' else 'srcip'

    def threatmodel_related_iocs(self, iocs, threatmodel):
        """Returns Indicators related to the specified ThreatModels"""

        threatmodel_indicators = []

        for ioc_ in iocs:
            if ioc_.get(threatmodel):
                threatmodel_indicators.append(ioc_)

        return threatmodel_indicators

    def itype_related_iocs(self, iocs, itype):

        itype_indicators = []

        for ioc_ in iocs:
            if ioc_.get("itype") == itype:
                itype_indicators.append(ioc_)

        return itype_indicators

    def create_kvstore_query(self):
        """Create a Query for the KVStore to bring back appropriate IOCs"""
        query=""

        tm_type_query = ",".join(['{"%s": {"$gte": "0"}}' % threatmodel for threatmodel in self.threatmodels])
        itype_item_query = ",".join(['{"itype": "%s"}' % itype for itype in self.itype])

        threatmodel_query = '{"$or": [%s]}' % tm_type_query if self.tm_iocs_only else None
        itype_query = '{"$or": [%s] }' % itype_item_query

        if self.tm_iocs_only and self.itype:
            query = '{ "$and": [%s, %s]}' % (itype_query, threatmodel_query)
        elif self.tm_iocs_only:
            query = threatmodel_query
        elif self.itype:
            query = itype_query

        return query

    def gen_event(self, ioc_format=None, iocs=None):
        """Creates a TS_Optic optimised log pattern

        Args:
            ioc_format (str): the ioc type (ip, url, email, md5, domain)
            iocs (dict): list of iocs to use to generate

        Returns:
            dict: event dict to write into the csv file
        """
        direction = choice(["inbound", "outbound"])

        if not iocs:
            raise ValueError("Unable to generate log for ioc format %s" % ioc_format)

        indicator_value = iocs[randint(0, len(iocs)-1)]["value"]
        event = {'_time': datetime.datetime.fromtimestamp(time.time())}

        event["src_port"] = random_port()
        event["dest_port"] = random_port()
        event["action"] = choice(self.event_actions)

        if ioc_format == "ip" or ioc_format == "domain":
            event["src"] = indicator_value if direction == "inbound" else random_ip()
            event["dest"] = indicator_value if direction == "outbound" else random_ip()
            event["src_ip"] = event["src"] if ioc_format == "ip" else random_ip()
            event["dest_ip"] = event["dest"] if ioc_format == "ip" else random_ip()

        elif ioc_format == "url":
            event["src"] = random_ip()
            event["dest"] = random_ip()
            event["url"] = indicator_value
            event["http_refer"] = ""
            event["http_user_agent"] = ""
            event["user"] = choice(self.users)

        elif ioc_format == "email":
            event["recipient"] = indicator_value if direction == "inbound" else "%s@test_anomali.test" % choice(self.users)
            event["src_user"] = indicator_value if direction == "outbound" else "%s@test_anomali.test" % choice(self.users)
            event["src"] = random_ip()
            event["dest"] = random_ip()

        elif ioc_format == "md5":
            event["file_name"] = "test_value_%s.txt" % randint(0, 9999)
            event["file_hash"] = indicator_value

        return event


dispatch(SplunkMatchGen, sys.argv, sys.stdin, sys.stdout, __name__)
