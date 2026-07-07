import argparse
import json
import os
import socket
import sys
import time
import logging, logging.handlers
import defusedxml.ElementTree as ET
from collections import OrderedDict

import nmap



# useful for debugging application, off by default
def setup_logger(level):
    logger = logging.getLogger('opd_search_command')
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(
        os.environ['SPLUNK_HOME'] + '/var/log/splunk/ta-opd.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger



def to_bool(val):
    return str(val).lower() in ("1", "true", "on")


APP_BIN_DIR = os.path.dirname(__file__)
BANNER_PLUS_NSE = os.path.join(APP_BIN_DIR, "banner-plus.nse")


class BaseScan(object):
    SCHEME = None

    def __init__(self, name, config):
        self.config = config
        self.target = self.get_target(name)
        self.logger = setup_logger(logging.INFO)

    @classmethod
    def parse_stanza(cls, stanza):
        config = {}
        for param in stanza.iterfind("param"):
            key = param.get("name")
            value = param.text

            try:
                if key in ("ping", "log_closed_ports"):
                    assert str(value).lower() in ("1", "0", "true", "false", "on", "off")
                elif key == "exclusions":
                    if value is not None:
                        items = [v.strip() for v in value.split(",") if v.strip() != ""]
                        for item in items:
                            cls.get_target(item)
                elif key == "interval":
                    if " " not in value:
                        # Should be a number of seconds
                        assert float(value) > 0
                    else:
                        # Cron schedule.... how validate make do?
                        pass
                elif key == "proto":
                    assert value.lower() in ("tcp", "udp", "icmp", "all")
                elif key == "ports":
                    if value is not None:
                        items = [v.strip() for v in value.split(",") if v.strip() != ""]
                        for item in items:
                            if ":" in item:
                                (proto, item) = item.split(":", 1)
                                assert proto in ("T", "U")

                            if "-" in item:
                                (start, end) = item.split("-", 1)
                                assert int(start) < int(end)
                            else:
                                assert int(item) > 0
                                assert int(item) < 65536
            except:
                raise ValueError("Invalid value for {0}: {1}".format(key, value))

            config[key] = value
        return config

    def get_arguments(self):
        args = list()

        if not to_bool(self.config["ping"]):
            args.append("-P0")

        if "exclusions" in self.config and self.config["exclusions"] != "":
            args.append("--exclude {0}".format(self.config["exclusions"]))

        proto = self.get_proto()
        if proto == "tcp":
            args.append("-sS")
        elif proto == "udp":
            args.append("-sU")
        elif proto == "icmp":
            args.append("-sP")

        return args

    def get_proto(self):
        if "proto" in self.config:
            return self.config["proto"].lower()
        return None

    @classmethod
    def get_scheme(cls):
        return cls.SCHEME

    @classmethod
    def get_target(cls, target):
        #try:
        if "://" in target:
            target = target.split("//", 1)[1]
        target = target.replace(",", "")
        return target

    def parse_host_result(self, host, host_result):
        proto = self.get_proto()

        if proto == "icmp":
            if host_result["status"]["state"].lower() == "up":
                state = "up"
            else:
                state = "down"

            print(json.dumps(OrderedDict([
                ("time", time.time()),
                ("dest_ip", host),
                ("dest_state", state),
            ])))


        for port in host_result.get(proto, []):
            port_result = host_result[proto][port]

            if port_result['state'].lower() == "open":
                state = "open"
            elif to_bool(self.config["log_closed_ports"]):
                state = "closed"
            else:
                continue

            dest_host = None
            if host_result.get("hostnames"):
                for hostname in host_result.get("hostnames"):
                    if hostname["type"] == "user":
                        dest_host = hostname["name"]
                
            yield OrderedDict([
                ("time", time.time()),
                ("dest_ip", host),
                ("dest_port", port),
                ("dest_state", "up"),
                ("dest_port_state", state),
                ("dest_host", dest_host),
                ("dest_svc", port_result["name"]),
                ("transport", proto)
            ])

    def run(self):
        nm = nmap.PortScanner()
        if self.get_proto() == "all":
            base_args = self.get_arguments()
            # TCP
            self.config["proto"] = "tcp"
            results = nm.scan(hosts=self.target, arguments=" ".join(base_args) + " -sS", sudo=True)
            for (host, host_result) in results["scan"].items():

                for result in self.parse_host_result(host, host_result):
                    for k in result.keys():
                        if result[k] is None:
                            del result[k]
                    result["label"] = self.config.get("label", "")
                    print(json.dumps(result))
            # UDP
            self.config["proto"] = "udp"
            results = nm.scan(hosts=self.target, arguments=" ".join(base_args) + " -sU", sudo=True)
            for (host, host_result) in results["scan"].items():

                for result in self.parse_host_result(host, host_result):
                    for k in result.keys():
                        if result[k] is None:
                            del result[k]
                    result["label"] = self.config.get("label", "")
                    print(json.dumps(result))
            # ICMP
            if type(self) is FullScan:
                self.config["proto"] = "icmp"
                results = nm.scan(hosts=self.target, arguments=" ".join(base_args) + " -sP", sudo=True)
                for (host, host_result) in results["scan"].items():

                    for result in self.parse_host_result(host, host_result):
                        for k in result.keys():
                            if result[k] is None:
                                del result[k]
                        result["label"] = self.config.get("label", "")
                        print(json.dumps(result))
        else:
            results = nm.scan(hosts=self.target, arguments=" ".join(self.get_arguments()), sudo=True)
            for (host, host_result) in results["scan"].items():

                for result in self.parse_host_result(host, host_result):
                    for k in result.keys():
                        if result[k] is None:
                            del result[k]
                    result["label"] = self.config.get("label", "")
                    print(json.dumps(result))


class FullScan(BaseScan):
    SCHEME = """<scheme>
        <title>OPD - Full Scan</title>
        <description>Scan for open ports.</description>
        <use_external_validation>true</use_external_validation>
        <streaming_mode>simple</streaming_mode>
        <endpoint>
            <args>
                <arg name="name">
                    <title>Subnet</title>
                    <description>Comma-separated list of subnets/hosts to scan</description>
                </arg>
                <arg name="label">
                    <title>Label</title>
                    <description>Input label</description>
                </arg>
                <arg name="exclusions">
                    <title>Excluded hosts</title>
                    <description>Comma-separated list of hosts to exclude from scan</description>
                    <required_on_create>false</required_on_create>
                    <required_on_edit>false</required_on_edit>
                </arg>
                <arg name="ping">
                    <title>Ping hosts before scanning</title>
                </arg>
                <arg name="proto">
                    <title>Protocol</title>
                    <required_on_create>false</required_on_create>
                    <required_on_edit>false</required_on_edit>
                </arg>
                <arg name="log_closed_ports">
                    <title>Log closed ports</title>
                </arg>
            </args>
        </endpoint>
    </scheme>"""

    def get_arguments(self):
        args = super(FullScan, self).get_arguments()

        args += [
            "--min-parallelism 100",
            "-T5",
        ]

        if self.get_proto() == "udp":
            # Configure minimum UDP ports
            args.append("--top-ports 500")

        return args


class QuickScan(BaseScan):
    SCHEME = """<scheme>
        <title>OPD - Quick Scan</title>
        <description>Quick scan for common open ports.</description>
        <use_external_validation>true</use_external_validation>
        <streaming_mode>simple</streaming_mode>
        <endpoint>
            <args>
                <arg name="name">
                    <title>Subnet</title>
                    <description>Comma-separated list of subnets/hosts to scan</description>
                </arg>
                <arg name="label">
                    <title>Label</title>
                    <description>Input label</description>
                </arg>
                <arg name="exclusions">
                    <title>Excluded hosts</title>
                    <description>Comma-separated list of hosts to exclude from scan</description>
                    <required_on_create>false</required_on_create>
                    <required_on_edit>false</required_on_edit>
                </arg>
                <arg name="ping">
                    <title>Ping hosts before scanning</title>
                </arg>
                <arg name="proto">
                    <title>Protocol</title>
                    <required_on_create>false</required_on_create>
                    <required_on_edit>false</required_on_edit>
                </arg>
                <arg name="log_closed_ports">
                    <title>Log closed ports</title>
                </arg>
                <arg name="ports">
                    <title>Ports</title>
                    <description>Comma-separated list of ports to scan</description>
                    <required_on_create>false</required_on_create>
                    <required_on_edit>false</required_on_edit>
                </arg>
            </args>
        </endpoint>
    </scheme>"""

    def get_arguments(self):
        args = super(QuickScan, self).get_arguments()

        ports = self.config.get("ports", "").replace(" ", "")

        if ports != "":
            args.append("-p {0}".format(ports))
        else:
            args.append("--top-ports 25")

        return args


class BannerScan(BaseScan):
    SCHEME = """<scheme>
        <title>OPD - Banner Scan</title>
        <description>Scan for banners on common open ports.</description>
        <use_external_validation>true</use_external_validation>
        <streaming_mode>simple</streaming_mode>
        <endpoint>
            <args>
                <arg name="name">
                    <title>Target</title>
                    <description>Comma-separated list of subnets/hosts to scan</description>
                </arg>
                <arg name="label">
                    <title>Label</title>
                    <description>Input label</description>
                </arg>
                <arg name="exclusions">
                    <title>Excluded hosts</title>
                    <description>Comma-separated list of hosts to exclude from scan</description>
                    <required_on_create>false</required_on_create>
                    <required_on_edit>false</required_on_edit>
                </arg>
                <arg name="ping">
                    <title>Ping hosts before scanning</title>
                </arg>
            </args>
        </endpoint>
    </scheme>"""

    def get_arguments(self):
        args = super(BannerScan, self).get_arguments()
        args.append("-p T:21-23,25,80,443,5060,8080,8443,U:5060")
        args.append("--script={0}".format(BANNER_PLUS_NSE))
        return args

    def parse_host_result(self, host, host_result):
        for proto in ("tcp", "udp"):
            if proto not in host_result:
                continue

            for (port, port_result) in host_result[proto].items():
                banner = port_result.get("script", {}).get("banner-plus", None)
                if banner is None:
                    continue
                yield OrderedDict([
                    ("time", time.time()),
                    ("dest_ip", host),
                    ("dest_port", port),
                    ("dest_host", host_result.get("hostname", None)),
                    ("banner", banner),
                ])


class VersionScan(QuickScan):
    SCHEME = """<scheme>
        <title>OPD - Version Scan</title>
        <description>Scan for software version on open ports.</description>
        <use_external_validation>true</use_external_validation>
        <streaming_mode>simple</streaming_mode>
        <endpoint>
            <args>
                <arg name="name">
                    <title>Target</title>
                    <description>Comma-separated list of subnets/hosts to scan</description>
                </arg>
                <arg name="label">
                    <title>Label</title>
                    <description>Input label</description>
                </arg>
                <arg name="exclusions">
                    <title>Excluded hosts</title>
                    <description>Comma-separated list of hosts to exclude from scan</description>
                    <required_on_create>false</required_on_create>
                    <required_on_edit>false</required_on_edit>
                </arg>
                <arg name="ping">
                    <title>Ping hosts before scanning</title>
                </arg>
                <arg name="proto">
                    <title>Protocol</title>
                    <required_on_create>false</required_on_create>
                    <required_on_edit>false</required_on_edit>
                </arg>
                <arg name="ports">
                    <title>Ports</title>
                    <description>Comma-separated list of ports to scan</description>
                    <required_on_create>false</required_on_create>
                    <required_on_edit>false</required_on_edit>
                </arg>
            </args>
        </endpoint>
    </scheme>"""

    def get_arguments(self):
        args = super(VersionScan, self).get_arguments()
        args.append("-sV")
        return args

    def parse_host_result(self, host, host_result):
        for proto in ("tcp", "udp"):
            if proto not in host_result:
                continue

            for (port, port_result) in host_result[proto].items():
                if port_result["state"] != "open" or port_result["version"] == "":
                    continue
                yield OrderedDict([
                    ("time", time.time()),
                    ("dest_ip", host),
                    ("dest_port", port),
                    ("dest_host", host_result.get("hostname", None)),
                    ("version", "{product} {version}".format(**port_result)),
                    ("cpe", port_result["cpe"])
                ])


ap = argparse.ArgumentParser()
scan_type = ap.add_mutually_exclusive_group()
scan_type.add_argument("--full", dest="scan_type", action="store_const", const=FullScan)
scan_type.add_argument("--quick", dest="scan_type", action="store_const", const=QuickScan)
scan_type.add_argument("--banners", dest="scan_type", action="store_const", const=BannerScan)
scan_type.add_argument("--versions", dest="scan_type", action="store_const", const=VersionScan)

run_mode = ap.add_mutually_exclusive_group()
run_mode.add_argument("--scheme", dest="run_mode", action="store_const", const="introspection")
run_mode.add_argument("--validate-arguments", dest="run_mode", action="store_const", const="validation")


def main():
    args = ap.parse_args()
    scanner = args.scan_type
    if args.run_mode == "introspection":
        print(scanner.get_scheme())
    elif args.run_mode == "validation":
        config_str = sys.stdin.read()
        doc = ET.fromstring(config_str)
        for item in doc.iterfind("./item"):
            try:
                scanner(item.get("name"), scanner.parse_stanza(item))
            except Exception as e:
                print("<error><message>{0}</message></error>".format(str(e)))
                sys.exit(1)
    else:
        config_str = sys.stdin.read()
        doc = ET.fromstring(config_str)
        for stanza in doc.iterfind("./configuration/stanza"):
            scanner(stanza.get("name"), scanner.parse_stanza(stanza)).run()

if __name__ == "__main__":
    main()

