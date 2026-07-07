#!/usr/bin/env python

import argparse
import configparser
import inspect
import base64
import codecs
import csv
import email
import errno
import glob
import http.cookiejar
import logging
import os
import re
import shutil
import ssl
import sys
from six.moves import urllib
import xml.etree.ElementTree as ET  # nosec
from datetime import datetime, timedelta
from distutils.version import LooseVersion
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import open
from sys import platform as _platform

import pyDes
import requests
from tripwire_logging import setup_logger
from tripwire_rest_api import TEV1RestAPI
from six.moves import range


# uncomment to disable diffie-hellman ciphers
# (this is needed to resolve a "dh key too small" error on old versions of TE)
# ssl._DEFAULT_CIPHERS = 'HIGH:!DH:!aNULL'

logger = logging.getLogger('tripwire')

cfg = configparser.ConfigParser()
cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
configpath = os.path.join(os.path.split(cwd)[0], 'local', 'te_setup.conf')
cfg.read(configpath, encoding="utf-8-sig")

sslcontext = None
SSL_ABILITY = hasattr(ssl, '_create_unverified_context')
#logger.info(str(SSL_ABILITY))
if SSL_ABILITY:
    default_context = ssl.create_default_context()
    unverified_context = ssl._create_unverified_context()  # nosec

_nl = re.compile(r'(\r\n|\r|\n)')

DATE_FORMAT = '%m/%d/%y %H:%M'


def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def is_windows():
    return _platform == 'win32'


def check_te_connection(ip_address, username, password, verify_ssl_cert, c_logger):
    """Check the TE Connection by requesting the TE version"""

    # Check that TE Console is reachable with information available
    try:
        logger.info("Testing the REST API connection")
        TEV1RestAPI(ip_address, username, password, verify_ssl_cert=verify_ssl_cert)
    except requests.RequestException as exc:
        c_logger.error("Unable to connect to Tripwire Enterprise using credentials provided")
        if hasattr(exc, "response") and hasattr(exc.response, "status_code") and hasattr(exc.response, "text"):
            c_logger.error(f"HTTP status code {exc.response.status_code} . HTTP response text {exc.response.text}")
        else:
            c_logger.error(str(exc))
        sys.exit(1)


def pyDes_decrypt(encrypted_str):
    encryption = pyDes.des(
        "DESCRYPi", pyDes.CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=pyDes.PAD_PKCS5
    )
    encrypted_str = codecs.decode(encrypted_str, "hex")
    encrypted_str = encryption.decrypt(encrypted_str).decode("utf-8")
    return encrypted_str


def main():
    global sslcontext
    setup_logger()
    parser = argparse.ArgumentParser(description='TE API front-end')
    parser.add_argument('-s', help='TE server', dest='server', required=True)
    parser.add_argument('-u', help='username', dest='username', required=True)
    parser.add_argument('-p', help='password', dest='password', required=True)
    parser.add_argument('-k', help='insecure', dest='insecure', action='store_true')

    subparsers = parser.add_subparsers(dest='command')

    export_parser = subparsers.add_parser('export')
    export_parser.add_argument(
        '-S', help='export settings', dest='settings', action='store_true'
    )
    export_parser.add_argument(
        '-o',
        help='output file',
        dest='output',
        required=True,
        type=argparse.FileType('wb'),
    )

    report_parser = subparsers.add_parser('report')
    report_parser.add_argument('-T', help='title', dest='title', required=True)
    report_parser.add_argument('-t', help='type', dest='type', required=False)
    report_parser.add_argument(
        '-P', help='parameters', dest='parameters', required=False
    )
    report_parser.add_argument(
        '-F', help='format', dest='format', required=True, choices=['CSV', 'XML']
    )
    report_parser.add_argument(
        '-o',
        help='output file',
        dest='output',
        required=True,
        type=argparse.FileType('wb'),
    )
    report_parser.add_argument(
        '-E',
        help='Parse ECR SQL',
        dest='ecr_parse_sql',
        required=False,
        action='store_true',
        default=False,
    )

    args = parser.parse_args()
    if SSL_ABILITY:
        if args.insecure:
            # disable cert validation
            sslcontext = unverified_context
            logger.info("Certificate validation is disabled.  Please enable verification for increased security.")
        else:
            sslcontext = default_context
            logger.info("Enabling cert validatation")
            
            try:
                location = cfg.get('te_parameters','te_ssl_cert_path',fallback="")
                #logger.info('getting bad param')
                #location = cfg.get('te_parameters','doesnotexit')

                if (location != ""):
                    logger.info(f"Enabling cert validatation, looking in {location}")
                    default_context.load_verify_locations(location)
                else:
                    location = True
                    import certifi
                    logger.info(f"Cert validation in the default trust store is set: {certifi.where()}")
            except: 
                logger.warning("There was a problem setting the context.")


    with soap_client(args.server, args.username, args.password) as client:
        if args.command == 'export':
            if args.settings:
                exporttype = 'settings'
            else:
                raise Exception("No export type specified")
            args.output.write(client.export(exporttype))
        else:  # report
            params = None
            if args.parameters is not None:
                params = parse_report_params(args.parameters)
            xml = client.report(args.title, args.type, params)
            if args.format == 'XML':
                args.output.write(xml)
            else:
                write_report_csv(xml, args.output, args.ecr_parse_sql)


def write_report_csv(xml, outfile, ecr_parse_sql=False):
    report = ET.fromstring(xml)  # nosec

    type = report.find('ReportHead/Report').get('type')
    watermark_file = ""
    with open(outfile.name, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        basefile = csv_file.name.split('.')[0]
        writers = {}
        headers_written = set()

        if type == 'detailedchanges_rpt': watermark_file = 'fim_timestamp.txt'
        elif type == 'detailedtestresults_rpt': watermark_file = 'scm_timestamp.txt'

        if watermark_file != "" : save_report_timestamp(report, outfile.name, watermark_file)
        if type == 'detailedchanges_rpt':
            writer.writerow(
                [
                    'Node Name',
                    'Node Type',
                    'Rule Name',
                    'Element Name',
                    'Version Time',
                    'Change Type',
                    'Severity Name',
                    'Severity',
                    'Approval ID',
                    'Users',
                    'Attributes',
                    'Content',
                ]
            )
            for node in findall_category(report.find('ReportBody'), 'node'):
                for rule in findall_category(node, 'rule'):
                    for element in findall_category(rule, 'element'):
                        for version in findall_category(element, 'version'):
                            username = ""
                            for users in findall_category(version, 'users'):
                                for user in findall_category(users, 'user'):
                                    # XXX what if there is more than one user?
                                    username = user.get('name')
                            attributes = find_category(version, 'attributes')
                            content = find_category(version, 'content')

                            writer.writerow(
                                [
                                    node.get('name'),
                                    find_string(node, 'typeName'),
                                    rule.get('name'),
                                    element.get('name'),
                                    find_timestamp(version, 'changeTime'),
                                    find_string(version, 'changeTypeName'),
                                    find_string(version, 'severityName'),
                                    find_integer(version, 'severity'),
                                    find_string(version, 'approvalId'),
                                    username,
                                    _format_attributes(attributes),
                                    _format_content(content),
                                ]
                            )
        elif type == 'detailedtestresults_rpt':

            def create_actual_results(actual_result_dict):
                retval = ""
                for k,v in list(actual_result_dict.items()):
                    if v == "" and k == "":
                        return ""
                    elif k != "" and v !="":
                        retval = k + " = " + v + " "
                    else:
                        retval += k
                        retval += v
                        retval += " "
                return retval

            def find_nodes(writer, group, policy, policytest):
                for node in findall_category(policytest, 'node'):
                    for policytestresult in findall_category(node, 'policyTestResult'):
                        for versiontestresults in findall_category(
                            policytestresult, 'versionTestResults'
                        ):
                            actual_values = {}
                            for versiontestresult in findall_category(
                                versiontestresults, 'versionTestResult'
                            ):
                                actual_value = ""
                                actual_key = ""
                                line = ""
                                for actual in findall_category(
                                    versiontestresult, 'actual'
                                ):
                                    actual_key = find_string(actual, 'key') or ""
                                    actual_value = find_string(actual, 'value') or ""

                                    for value in findall_category(actual, 'value'):
                                        line += find_string(value, 'line') or ""

                                actual_value = actual_value + " " + line
                                actual_values [actual_key] = actual_value

 
                                policyname = ''
                                if policy is not None:
                                    policyname = policy.get('name')
                                groupname = ''
                                if group is not None:
                                    groupname = group.get('name')
                                actualval=create_actual_results(actual_values)    
                                writer.writerow(
                                    [
                                        node.get('name'),
                                        find_string(node, 'typeName'),
                                        policyname,
                                        groupname,
                                        policytest.get('name'),
                                        _nl.sub(
                                            "\r\n",
                                            find_string(policytest, 'description'),
                                        ),
                                        find_string(versiontestresult, 'elementName'),
                                        find_timestamp(versiontestresult, 'time'),
                                        find_string(versiontestresult, 'state'),
                                        actualval,
                                    ]
                                )

            def find_policytests(writer, group, policy, n):
                for child in n.findall('ReportSection'):
                    if child.get('category') == 'policytest':
                        find_nodes(writer, group, policy, child)
                    else:
                        if child.get('category') == 'policy':
                            policy = child
                        elif child.get('category') == 'policytestgroup':
                            group = child
                        find_policytests(writer, group, policy, child)

            writer.writerow(
                [
                    'Node Name',
                    'Node Type',
                    'Policy',
                    'Parent Test Group',
                    'Test Name',
                    'Description',
                    'Element',
                    'Result Time',
                    'Result State',
                    'Actual Value',
                ]
            )
            find_policytests(writer, None, None, report.find('ReportBody'))
        elif type == 'elementcontents_rpt':
            base_cols = [
                'Node Name',
                'Node Type',
                'Rule',
                'Rule Type',
                'Element',
                'Version Time',
            ]
            writer.writerow(base_cols + ['Content'])
            for node in findall_category(report.find('ReportBody'), 'node'):
                for rule in findall_category(node, 'rule'):
                    for element in findall_category(rule, 'element'):
                        for version in findall_category(element, 'version'):
                            for versionContent in findall_category(
                                version, 'versionContent'
                            ):
                                content = "\r\n".join(
                                    findall_string(versionContent, 'content')
                                )
                                element_name = element.get('name')
                                rule_type = find_string(rule, 'typeName')
                                items = [
                                    node.get('name'),
                                    find_string(node, 'typeName'),
                                    rule.get('name'),
                                    rule_type,
                                    element_name,
                                    find_timestamp(version, 'changeTime'),
                                ]
                                # Parse as SQL..
                                if ecr_parse_sql and rule_type == 'Query Rule':
                                    if element_name not in writers:
                                        en = element_name.replace(' ', '_')
                                        writers[element_name] = csv.writer(
                                            open('%s-%s.csv' % (basefile, en), 'w')
                                        )
                                    try:
                                        tree = ET.fromstring(content)  # nosec
                                        tree.find('ResultSetData')
                                        for row in tree.iter('Row'):
                                            row_data = []
                                            for col in row.iter('Column'):
                                                col_name = col.get('name')
                                                if col_name in base_cols:
                                                    col_name = 'query-' + col_name
                                                row_data.append((col_name, col.text))
                                            # Write out the CSV header
                                            if element_name not in headers_written:
                                                writers[element_name].writerow(
                                                    base_cols + [c[0] for c in row_data]
                                                )
                                                headers_written.add(element_name)
                                            # Add row data to our existing items
                                            # and then write the row to our csv
                                            writers[element_name].writerow(
                                                items + [c[1] for c in row_data]
                                            )
                                    except Exception:
                                        logger.exception(
                                            'Unable to parse Query content for %s',
                                            element_name,
                                        )
                                        continue
                                # Parse as regular ECR
                                # Sticking content into a single column
                                else:
                                    items.append(content)
                                    writer.writerow(items)
        else:
            raise Exception("Unknown report type")


def save_report_timestamp(report, outfile, watermark_filename):
    displayvalue = report.find('ReportHead/Criteria/TimestampCriterion/Timestamp').get(
        'displayvalue'
    )
    timestamp = report.find('ReportHead/Criteria/TimestampCriterion/Timestamp').text
    logger.info("writing timestamp")
    logger.info("outfile" + outfile)
    with open(os.path.join(os.path.dirname(outfile), watermark_filename), 'w') as f:
        f.write(displayvalue + ',')
        f.write(timestamp)


def _format_attributes(attributes):
    if attributes is None:
        return ""
    sections = []
    for section in attributes.findall('ReportSection'):
        # not sure what the point of this is, but tecommander does it
        if section.get('category') == 'removed':
            continue
        expected = _nl.sub("\r\n", find_string(section, "expected"))
        observed = _nl.sub("\r\n", find_string(section, "observed"))
        sections.append(
            'Name="%s",Expected="%s",Observed="%s"'
            % (section.get('name'), expected, observed)
        )
    return ";\r\n".join(sections)


def _format_content(content):
    if content is None:
        return ""
    removed = []
    added = []
    modified = []
    for section in content.findall('ReportSection'):
        if section.get('category') == 'removed':
            removed.append(
                _nl.sub("\r\n", find_string(section, "expected")).replace('"', '')
            )
        elif section.get('category') == 'added':
            added.append(
                _nl.sub("\r\n", find_string(section, "observed")).replace('"', '')
            )
        elif section.get('category') == 'modified':
            modified.append(
                _nl.sub("\r\n", find_string(section, "observed")).replace('"', '')
            )
    return 'added="%s";removed="%s";modified="%s"' % (
        "\r\n".join(added),
        "\r\n".join(removed),
        "\r\n".join(modified),
    )


def find_timestamp(node, name, displayname=False):
    for s in node.findall('Timestamp'):
        if s.get('name') == name:
            if displayname:
                return s.get('displayvalue')
            else:
                dt = datetime.fromtimestamp(int(s.text) / 1000)
                return dt.strftime(DATE_FORMAT)
    return ""


def find_string(node, name):
    for s in node.findall('String'):
        if s.get('name') == name:
            return "" if s.text is None else s.text
    return ""


def findall_string(node, name):
    r = []
    for s in node.findall('String'):
        if s.get('name') == name:
            r.append("" if s.text is None else s.text)
    return r


def find_integer(node, name):
    for s in node.findall('Integer'):
        if s.get('name') == name:
            return "" if s.text is None else s.text
    return ""


def findall_category(node, category):
    for c in node.findall('ReportSection'):
        if c.get('category') == category:
            yield c


def find_category(node, category):
    for c in node.findall('ReportSection'):
        if c.get('category') == category:
            return c
    return None


def find_attribute(node, name):
    for c in node.findall('ReportSection'):
        if c.get('name') != name:
            continue
        r = find_string(c, 'observed')
        if r:
            return r
    return None


def parse_report_params(arg):
    r = []
    for typevals in arg.split(':'):
        criterionvals = typevals.split(',')

        criterion = criterionvals[0]
        vals = criterionvals[1:]

        if criterion == 'BooleanCriterion':
            if (len(vals) % 2) != 0:
                raise Exception("Wrong number of parameters for BooleanCriterion")
            for i in range(0, len(vals), 2):
                c = ET.Element(
                    '{%s}BooleanCriterion' % soap_client.tw, {'name': vals[i]}
                )
                ET.SubElement(c, '{%s}Boolean' % soap_client.tw, {'value': vals[i + 1]})
                r.append(c)
        elif criterion == 'RelativeTimeRangeCriterion':
            if (len(vals) % 3) != 0:
                raise Exception(
                    "Wrong number of parameters for RelativeTimeRangeCriterion"
                )
            for i in range(0, len(vals), 3):
                val, unit, name = vals[i : i + 3]
                c = ET.Element(
                    '{%s}TimeRangeCriterion' % soap_client.tw,
                    {'name': 'timeRange', 'displayvalue': name},
                )
                ET.SubElement(
                    c,
                    '{%s}RelativeTimeRange' % soap_client.tw,
                    {
                        'period': unit,
                        'value': val,
                        'displayvalue': name,
                        'relativeOffset': 'none',
                    },
                )
                r.append(c)
        elif criterion == 'AbsoluteTimeRangeCriterion':
            if (len(vals) % 2) != 0:
                raise Exception(
                    "Wrong number of parameters for AbsoluteTimeRangeCriterion"
                )
            for i in range(0, len(vals), 2):
                timestamp, displayvalue = vals[i : i + 2]
                displayvalue.replace('-', ':')
                c = ET.Element(
                    '{%s}TimeRangeCriterion' % soap_client.tw,
                    {
                        'name': 'timeRange',
                        'displayvalue': 'No earlier than %s' % displayvalue,
                    },
                )
                d = ET.SubElement(
                    c,
                    '{%s}AbsoluteTimeRange' % soap_client.tw,
                    {'displayvalue': 'No earlier than %s' % displayvalue},
                )
                ET.SubElement(
                    d,
                    '{%s}Timestamp' % soap_client.tw,
                    {'name': 'start', 'displayvalue': displayvalue},
                ).text = timestamp
                r.append(c)
        elif criterion == 'SelectCriterion':
            if (len(vals) % 3) != 0:
                raise Exception("Wrong number of parameters for SelectCriterion")
            for i in range(0, len(vals), 3):
                name, display, val = vals[i : i + 3]
                c = ET.Element(
                    '{%s}SelectCriterion' % soap_client.tw,
                    {'name': name, 'displayvalue': display},
                )
                ET.SubElement(c, '{%s}String' % soap_client.tw).text = val
                r.append(c)
        else:
            raise Exception("Unknown criterion type: %s" % criterion)
    return r


def do_rest(req, username, password, parseresult=True):
    req.add_header(
        'Authorization',
        'Basic %s'
        % base64.encodestring('%s:%s' % (username, password)).replace('\n', ''),
    )
    req.add_header('Content-Type', 'application/xml')
    if SSL_ABILITY:
        s = urllib.request.urlopen(req, context=sslcontext).read()  # nosec
    else:
        s = urllib.request.urlopen(req).read()  # nosec
    if parseresult:
        return ET.fromstring(s)  # nosec
    else:
        return s


tagsetcache = {}
tagcache = {}


def get_tagset(server, username, password, tagsetname):
    if tagsetname in tagsetcache:
        return tagsetcache[tagsetname]
    tagsets = do_rest(
        urllib.request.Request('https://%s/assetview/api/tagsets' % server),
        username,
        password,
    )
    tagsetid = None
    for tagset in tagsets:
        if tagset.find('name').text == tagsetname:
            tagsetid = tagset.get('id')
            break
    if tagsetid is None:
        newtagset = ET.Element('tagset', {'id': '0'})
        ET.SubElement(newtagset, 'name').text = tagsetname
        ET.SubElement(newtagset, 'type').text = 'USER'

        tagset = do_rest(
            urllib.request.Request(
                'https://%s/assetview/api/tagsets' % server, ET.tostring(newtagset)
            ),
            username,
            password,
        )
        tagsetid = tagset.get('id')
    tagsetcache[tagsetname] = tagsetid
    return tagsetid


def get_tag(server, username, password, tagname, tagsetid):
    if tagname in tagcache:
        return tagcache[tagname]

    tagid = None
    tags = do_rest(
        urllib.request.Request('https://%s/assetview/api/tags' % server),
        username,
        password,
    )
    for tag in tags:
        if tag.find('name').text == tagname:
            tagid = tag.get('id')
            break

    if tagid is None:
        newtag = ET.Element('tag', {'id': '0'})
        ET.SubElement(newtag, 'name').text = tagname
        ET.SubElement(newtag, 'tagset-id').text = tagsetid

        tag = do_rest(
            urllib.request.Request(
                'https://%s/assetview/api/tags' % server, ET.tostring(newtag)
            ),
            username,
            password,
        )
        tagid = tag.get('id')

    tagcache[tagname] = tagid
    return tagid


def convert_oid(o):
    return str(int(o.split(':')[1], 36))


def get_assetid(server, username, password, nodeoid, cache):
    assetid = None
    if cache is not None:
        assetid = cache.get("assetid_%s" % nodeoid)
    if assetid is None:
        assets = do_rest(
            urllib.request.Request('https://%s/assetview/api/assets' % server),
            username,
            password,
        )
        for device in assets.findall(
            './/{http://scap.nist.gov/schema/asset-identification/1.1}computing-device'
        ):
            oid, id = None, None
            for synthetic in device.findall(
                '{http://scap.nist.gov/schema/asset-identification/1.1}synthetic-id'
            ):
                if synthetic.get('resource').endswith(':te-oid'):
                    oid = synthetic.get('id')
                elif synthetic.get('resource') == 'assetview:id':
                    id = synthetic.get('id')
            if oid is not None and id is not None:
                if oid == convert_oid(nodeoid):
                    assetid = id
                if cache is not None:
                    cache.set("assetid_%s" % nodeoid, id)
    if assetid is None:
        raise Exception("Asset ID not found for OID %s" % nodeoid)
    return assetid


def _has_tag(server, username, password, assetid, tagid):
    tags = do_rest(
        urllib.request.Request(
            'https://%s/assetview/api/assets/%s/tags' % (server, assetid)
        ),
        username,
        password,
    )
    for tag in tags:
        if int(tag.get('id')) == int(tagid):
            return True
    return False


def untag_asset(server, username, password, nodeoid, tagsetname, tagname, cache=None):
    tagsetid = get_tagset(server, username, password, tagsetname)
    tagid = get_tag(server, username, password, tagname, tagsetid)

    assetid = get_assetid(server, username, password, nodeoid, cache)

    if _has_tag(server, username, password, assetid, tagid):
        req = urllib.request.Request(
            'https://%s/assetview/api/assets/%s/tags/%s' % (server, assetid, tagid)
        )
        req.get_method = lambda: 'DELETE'
        do_rest(req, username, password, False)


def tag_asset(server, username, password, nodeoid, tagsetname, tagname, cache=None):
    tagsetid = get_tagset(server, username, password, tagsetname)
    tagid = get_tag(server, username, password, tagname, tagsetid)

    assetid = get_assetid(server, username, password, nodeoid, cache)

    if not _has_tag(server, username, password, assetid, tagid):
        do_rest(
            urllib.request.Request(
                'https://%s/assetview/api/assets/%s/tags/%s' % (server, assetid, tagid),
                "",
            ),
            username,
            password,
            False,
        )


class soap_client:

    soap_env = 'http://schemas.xmlsoap.org/soap/envelope/'
    tw = 'http://tripwire.com/twservice/wsdl/1'

    def __init__(self, server, username, password):
        self._server = server
        cj = http.cookiejar.CookieJar()
        if SSL_ABILITY:
            #logger.info("Setting SOAP SSL context")
            self._opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(cj),
                urllib.request.HTTPSHandler(context=sslcontext),
            )
        else:
            self._opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(cj)
            )
        # , urllib2.ProxyHandler({'https': 'localhost:8888'}))

        args = ET.Element('loginArgs')
        ET.SubElement(args, 'username').text = username
        ET.SubElement(args, 'password').text = password
        self._do_soap('login', args)

    def _do_soap(self, action, args, parseresult=True):
        env = ET.Element('{%s}Envelope' % soap_client.soap_env)
        body = ET.SubElement(env, '{%s}Body' % soap_client.soap_env)
        if args is not None:
            args.tag = "{%s}%s" % (soap_client.tw, args.tag)
            body.append(args)

        req = urllib.request.Request(
            'https://%s/twservice/soap' % self._server,
            '<?xml version="1.0" encoding="UTF-8"?>'.encode('utf-8')
            + ET.tostring(env, encoding='utf-8'),
        )
        req.add_header('Soapaction', action)
        req.add_header('Content-Type', 'text/xml; charset=utf-8')
        req.add_header(
            'Accept',
            'application/soap+xml, application/dime, multipart/related, text/*',
        )

        s = self._opener.open(req)

        if parseresult:
            env = ET.fromstring(s.read())  # nosec
            fault = env.find('.//{%s}Fault' % soap_client.soap_env)
            if fault is not None:
                raise Exception(ET.tostring(fault))
            return env.find('.//{%s}Body' % soap_client.soap_env)[0]
        else:
            return s

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.logout()

    def logout(self):
        self._do_soap('logout', None)

    def set_custom_property(self, oid, name, value, type='TextValue'):
        args = ET.Element(
            'setCustomPropertyArgs',
            {'name': name, 'targetType': 'element', 'useDefault': 'false'},
        )
        ET.SubElement(args, '{%s}%s' % (soap_client.tw, type)).text = value
        ET.SubElement(args, '{%s}OID' % soap_client.tw).text = oid

        r = self._do_soap('setCustomProperty', args)
        return (
            int(r.find('{%s}countResultResponse' % soap_client.tw).get('countSuccess'))
            == 1
        )

    def get_properties(self, oid):
        args = ET.Element('getPropertiesArgs')
        ET.SubElement(args, '{%s}OID' % soap_client.tw).text = oid

        r = self._do_soap('getProperties', args)
        return r[0]

    def describe_search(self, searchtype):
        args = ET.Element('describeSearchArgs', {'searchType': searchtype})

        return self._do_soap('describeSearch', args, False)

    def search_string(self, searchtype, name, value):
        args = ET.Element('searchArgs', {'searchType': searchtype})
        ET.SubElement(args, '{%s}String' % soap_client.tw, {'name': name}).text = value

        r = self._do_soap('search', args)
        return [o.text for o in r.findall('{%s}OID' % soap_client.tw)]

    def search_msm(self, searchtype, name, value):
        args = ET.Element('searchArgs', {'searchType': searchtype})
        msm = ET.SubElement(
            args,
            '{%s}MultiStringMatch' % soap_client.tw,
            {'name': name, 'operator': 'equals'},
        )
        ET.SubElement(msm, '{%s}String' % soap_client.tw).text = value

        r = self._do_soap('search', args)
        return [o.text for o in r.findall('{%s}OID' % soap_client.tw)]

    def search_custom_element(self, name, value, node=None):
        args = ET.Element('searchArgs', {'searchType': 'element'})

        if node is not None:
            msm = ET.SubElement(
                args,
                '{%s}MultiStringMatch' % soap_client.tw,
                {'name': 'search.element.nodeName', 'operator': 'equals'},
            )
            ET.SubElement(msm, '{%s}String' % soap_client.tw).text = node

        cvem = ET.SubElement(args, '{%s}CustomValueElementMatch' % soap_client.tw)
        tve = ET.SubElement(
            cvem,
            '{%s}TextValueExpression' % soap_client.tw,
            {'propertyName': name, 'operator': 'equal'},
        )
        ET.SubElement(tve, '{%s}TextValue' % soap_client.tw).text = value

        r = self._do_soap('search', args)
        return [o.text for o in r.findall('{%s}OID' % soap_client.tw)]

    def run_action(self, actionoid, oid):
        args = ET.Element(
            'runActionArgs', {'actionOid': actionoid, 'background': 'true'}
        )
        ET.SubElement(args, '{%s}OID' % soap_client.tw).text = oid

        r = self._do_soap('runAction', args)
        return (
            int(r.find('{%s}countResultResponse' % soap_client.tw).get('countSuccess'))
            == 1
        )

    def run_task(self, name):
        args = ET.Element(
            'runtask',
            {
                'xmlns:SOAP-ENC': 'http://schemas.xmlsoap.org/soap/encoding/',
                'SOAP-ENC:root': '1',
            },
        )
        ET.SubElement(
            args,
            'runtaskArgs',
            {
                'xmlns': 'http://www.w3.org/1999/XMLSchema',
                'background': 'true',
                'name': name,
            },
        )

        r = self._do_soap('runtask', args)
        return (
            int(r.find('{%s}countResultResponse' % soap_client.tw).get('countSuccess'))
            == 1
        )

    def _attachment(self, r):
        body = r.read()

        s = (
            "\r\n".join("%s: %s" % (k, r.info().get(k)[0]) for k in r.info()).encode(
                'utf-8'
            )
            + "\r\n\r\n".encode('utf-8')
            + body
        )

        msg = email.message_from_string(s.decode('utf-8'))
        for part in msg.walk():
            if part.get_content_type() == 'application/tripwireenterprise':
                return part.get_payload(decode=True)
        body = body.decode('utf-8')
        if 'faultstring' not in body:
            body = (
                '<ReportOutput>'
                + body.split('<ReportOutput>')[1].split('</ReportOutput>')[0]
                + '</ReportOutput>'
            )
        env = ET.fromstring(body)  # nosec
        fault = env.find('.//{%s}Fault' % soap_client.soap_env)
        if fault is not None:
            raise Exception(ET.tostring(fault))
        else:
            return body

    def export(self, exporttype, oidlist=None):
        args = ET.Element('exportArgs', {'exportType': exporttype})
        if oidlist is not None:
            for oid in oidlist:
                ET.SubElement(args, '{%s}OID' % soap_client.tw).text = oid
        return self._attachment(self._do_soap('export', args, parseresult=False))

    def report(self, title, type, params):
        args = ET.Element('reportArgs', {'reportName': title, 'outputFormat': 'xml'})
        if type is not None:
            args.set('type', type)
        if params is not None:
            criteria = ET.SubElement(args, '{%s}Criteria' % soap_client.tw)
            for param in params:
                criteria.append(param)
        return self._attachment(self._do_soap('report', args, parseresult=False))

    def import_(self, type, xml):
        id1 = 'AAAAAAAAAAAAAAA'
        id2 = 'BBBBBBBBBBBBBBB'

        env = ET.Element('{%s}Envelope' % soap_client.soap_env)
        body = ET.SubElement(env, '{%s}Body' % soap_client.soap_env)
        imp = ET.SubElement(body, "import")
        args = ET.SubElement(imp, '{%s}importArgs' % soap_client.tw, {'type': type})
        ET.SubElement(args, 'importContent', {'href': 'cid:%s' % id2})

        msg = MIMEMultipart('related; type="text/xml"; start="%s"' % id1)

        txt = MIMEText(ET.tostring(env, encoding='utf-8'), 'xml', 'utf-8')
        txt['Content-Id'] = id1
        msg.attach(txt)

        app = MIMEApplication(xml, 'octet-stream')
        app['Content-Id'] = id2
        msg.attach(app)

        s = msg.as_string(False)
        body = s.split('\n\n', 1)[1]

        req = urllib.request.Request('https://%s/twservice/soap' % self._server, body)
        req.add_header('Soapaction', 'import')
        req.add_header('Content-Type', msg['Content-Type'])
        req.add_header('MIME-Version', msg['MIME-Version'])

        s = self._opener.open(req)

        reply = ET.fromstring(s.read())  # nosec
        fault = reply.find('.//{%s}Fault' % soap_client.soap_env)
        if fault is not None:
            raise Exception(ET.tostring(fault))
        return int(
            reply.find('.//{%s}countResultResponse' % soap_client.tw).get(
                'countSuccess'
            )
        )


class ReportData:
    def __init__(
        self,
        ip_address,
        username,
        password,
        script_loc='tripwire.py',
        unit='day',
        first_run=False,
        script_start='',
        show_cont_diff=False,
        hist_days='30',
        interval=1,
        python_cmd='python',
        num_threads=1,
        cachedir='cache',
        do_daily_reindex=False,
        daily_reindex_file=None,
        te_sslverify=False,
    ):
        # SCM/FIM may be called manually from python interpretor for debugging
        setup_logger()
        self.ip_address = ip_address
        self.username = username
        self.password = password
        self.unit = unit
        self.interval = interval
        self.hist_days = hist_days
        self.show_cont_diff = show_cont_diff
        self.first_run = first_run
        self.script_loc = script_loc
        self.script_start = script_start
        self.python_cmd = python_cmd
        self.num_threads = num_threads
        self.cachedir = cachedir
        self.do_daily_reindex = do_daily_reindex
        self.daily_reindex_file = daily_reindex_file
        self.te_sslverify = te_sslverify
        if int(interval) == 1:
            self.units = unit
        else:
            self.units = unit + 's'
        self._api = None
        self.severity_ranges = None

    @property
    def api(self):
        if not self._api:
            self._api = TEV1RestAPI(self.ip_address, self.username, self.password, verify_ssl_cert=self.te_sslverify)
        return self._api

    @staticmethod
    def isodatetime_to_datetime(isodatetime):
        if not isodatetime:
            return None
        return datetime.strptime(isodatetime, '%Y-%m-%dT%H:%M:%S.%fZ')

    @staticmethod
    def datetime_to_isodatetime(dt):
        if not dt:
            return None
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    def isodatetime_to_visible(self, isodatetime):
        if not isodatetime:
            return ''
        dt = self.isodatetime_to_datetime(isodatetime)
        return dt.strftime(DATE_FORMAT)

    def get_severity_range_name(self, severity):
        if self.severity_ranges is None:
            # This call is supposedly only available in 8.5.1
            self.severity_ranges = self.api.get('settings/system/severityRange')
        severity = int(severity)
        for severity_range in self.severity_ranges:
            if (
                int(severity_range['minSeverity'])
                <= severity
                <= int(severity_range['maxSeverity'])
            ):
                return severity_range['name']
        return ''

    def save(self, tmp_dir, save_dir, first_run_file='first_run.txt', temp_file='fim_timestamp.txt'):
        logger.info("saving data")
        for file in glob.glob(os.path.join(tmp_dir, '*.csv')):
            file_name = os.path.basename(file)
            shutil.move(file, os.path.join(save_dir, file_name))
        if self.first_run:
            # create first run file
            with open(first_run_file, 'w') as f:
                f.write("First run completed\n" + "Hist days loaded:" + self.hist_days)
        if self.do_daily_reindex:
            with open(self.daily_reindex_file, 'w') as f:
                f.write(ReportData.datetime_to_isodatetime(datetime.now()))
        timestamp_tmp = os.path.join(tmp_dir, temp_file)
        if os.path.exists(timestamp_tmp):
            shutil.move(timestamp_tmp, os.path.join(save_dir, temp_file))

    def get_since_datetime(self):
        since = datetime.utcnow()
        if self.first_run:
            since -= timedelta(days=int(self.hist_days))
        elif self.unit.startswith('day'):
            since -= timedelta(days=int(self.interval))
        elif self.unit.startswith('hour'):
            since -= timedelta(hours=int(self.interval))
        return since

    def te_version_check(self, version):
        return LooseVersion(self.api.te_version) >= LooseVersion(version)

    def do_soap(self, file_name):
        raise NotImplementedError()

    def do_rest(self, file_name):
        raise NotImplementedError()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logger.exception('Exception in tripwire.py')
