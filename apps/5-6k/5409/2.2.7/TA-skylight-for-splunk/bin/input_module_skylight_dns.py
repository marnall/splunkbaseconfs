# encoding = utf-8
# encoding = utf-8
import os
import splunk.appserver.mrsparkle.lib.util as util
import os
import sys
import time
import datetime
import json


DNSTYPES = {
    0 : "RESERVED",
    1 : "A",
    2 : "NS",
    3 : "MD",
    4 : "MF",
    5 : "CNAME",
    6 : "SOA",
    7 : "MB",
    8 : "MG",
    9 : "MR",
    10 : "NULL",
    11 : "WKS",
    12 : "PTR",
    13 : "HINFO",
    14 : "MINFO",
    15 : "MX",
    16 : "TXT",
    17 : "RP",
    18 : "AFSDB",
    19 : "X25",
    20 : "ISDN",
    21 : "RT",
    22 : "NSAP",
    23 : "NSAP-PTR",
    24 : "SIG",
    25 : "KEY",
    26 : "PX",
    27 : "GPOS",
    28 : "AAAA",
    29 : "LOC",
    30 : "NXT",
    31 : "EID",
    32 : "NIMLOC/NB",
    33 : "SRV/NBSTAT",
    34 : "ATMA",
    35 : "NAPTR",
    36 : "KX",
    37 : "CERT",
    38 : "A6",
    39 : "DNAME",
    40 : "SINK",
    41 : "OPT",
    42 : "APL",
    43 : "DS",
    44 : "SSHFP",
    45 : "IPSECKEY",
    46 : "RRSIG",
    47 : "NSEC",
    48 : "DNSKEY",
    49 : "DHCID",
    50 : "NSEC3",
    51 : "NSEC3PARAM",
    55 : "HIP",
    56 : "NINFO",
    57 : "RKEY",
    58 : "TALINK",
    59 : "CDS",
    99 : "SPF",
    100 : "UINFO",
    101 : "UID",
    102 : "GID",
    103 : "UNSPEC",
    249 : "TKEY",
    250 : "TSIG",
    251 : "IXFR",
    252 : "AXFR",
    253 : "MAILB",
    254 : "MAILA",
    255 : "*",
    256 : "URI",
    257 : "CAA",
    32768 : "TA",
    32769 : "DLV",
}

DNSCODES = {
    -1: 'No DNS Response',
    0: 'No Error',
    1: 'Format Error',
    2: 'Server Failure',
    3: 'Non-Existent Domain',
    4: 'Not Implemented',
    5: 'Query Refused',
    6: 'Name Exists when it should not',
    7: 'RR Set Exists when it should not',
    8: 'RR Set that should exist does not',
    9: 'NotAuth',
    10: 'Name not contained in zone',
    16: 'TSIG Signature Failure/Bad OPT Version',
    17: 'Key not recognized',
    18: 'Signature out of time window',
    20: 'Duplicate key name',
    21: 'Algorithm not supported',
    22: 'Bad Truncation'
}

def validate_input(helper, definition):
    pass
def collect_events(helper, ew):
    pvx_ip_address = helper.get_global_setting('ip_address')
    verify = helper.get_arg('verify')
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)

    if pvx_ip_address == "none":
        return None

    pvx_api_key = ""
    try:
        cwd = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','pvx_api_key.txt')
        with open(cwd, 'r') as file:
            pvx_api_key = file.read().splitlines()[0]
    except:
        return None

    if verify == 'false':
        verify = False
    else:
        verify = True

    url = 'https://{}/api/query?expr=client.traffic, server.traffic, dns.rt, queries FROM dns BY time(), client.ip, server.ip, layer, query.type, response.code, response.type, server.mac, client.mac, query.name, capture.id SINCE @now-{} UNTIL @now-{}'.format(pvx_ip_address, 420, 360)
    headers = {'PVX-Authorization': pvx_api_key}
    method = 'GET'
    timeout = 45.0

    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=verify,
                                        timeout=timeout, use_proxy=True)
    r_json = response.json()
    if 'result' in r_json and 'data' in r_json['result']:
        query_types_to_change = ['A', 'MX', 'NS', 'PTR']
        for res in r_json['result']['data']:
            timestamp = int(float(res['key'][0]['value']))
            src_ip = res['key'][1].get('value')
            dest_ip = res['key'][2].get('value')
            layer = res['key'][3].get('value')
            query_type = DNSTYPES.get(res['key'][4].get('value'))
            if query_type not in query_types_to_change:
                query_type = 'Query'
            reply_code = DNSCODES.get(res['key'][5].get('value'))
            record_type = DNSTYPES.get(res['key'][6].get('value'))
            dest_mac = res['key'][7].get('value')
            src_mac = res['key'][8].get('value')
            query = res['key'][9].get('value')
            capture = res['key'][10].get('value')
            bytes_out = res['values'][0].get('value')
            bytes_in = res['values'][1].get('value')
            bytes_total = bytes_in + bytes_out
            dns_rt = res['values'][2].get('value')
            queries = res['values'][3].get('value')
            
            if dns_rt:
                dns_rt = round(dns_rt, 3)
            
            data = {
                'action': 'allowed',
                'time': timestamp,
                'src_ip': src_ip,
                'src_mac': src_mac.lower() if dest_mac else None,
                'dest_ip': dest_ip,
                'dest_mac': dest_mac.lower() if dest_mac else None,
                'query': query,
                'layer': layer,
                'dns_rt': dns_rt,
                'query_type': query_type,
                'reply_code': reply_code,
                'record_type': record_type,
                'bytes_out': bytes_out,
                'bytes_in': bytes_in,
                'bytes': bytes_total,
                'queries': queries,
                'capture': capture
            }
            event = helper.new_event(
                    time=timestamp,
                    source=helper.get_input_type(),
                    index=helper.get_output_index(),
                    sourcetype=helper.get_sourcetype(),
                    data=json.dumps(data),
                    done=True,
                    unbroken=True)
            ew.write_event(event)
