#!/usr/bin/env python

import csv
import re
import sys
import ssl
import socket
import hashlib
from time import mktime
from datetime import datetime
from asn1crypto.x509 import Certificate


""" An adapter that takes CSV as input, executes a script that connects
    with the dest field and retrieves the values from the certificate
    if one existed. Can be used with ip or hostname. Defaults to using 
    port 443 but can be over written with dest_port field.
"""

def main():
    parameters = [
        'dest',
        'dest_port',
        'ssl_end_time',
        'ssl_hash',
        'ssl_is_valid',
        'ssl_issuer',
        'ssl_issuer_common_name',
        'ssl_issuer_email',
        'ssl_issuer_locality',
        'ssl_issuer_organization',
        'ssl_issuer_state',
        'ssl_issuer_country',
        'ssl_issuer_unit',
        'ssl_self_issued',
        'ssl_self_signed',
        'ssl_serial',
        'ssl_signature_algorithm',
        'ssl_start_time',
        'ssl_subject',
        'ssl_subject_alt_name',
        'ssl_subject_common_name',
        'ssl_subject_email',
        'ssl_subject_locality',
        'ssl_subject_organization',
        'ssl_subject_state',
        'ssl_subject_country',
        'ssl_subject_unit',
        'ssl_validity_window',
        'ssl_version'
        ]
    
    field_arguments = {}
    i = 1
    for p in parameters:
        field_arguments[p] = sys.argv[i]
        i += 1
        
    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()
    
    for result in r:
        # Change the dest_port if provided otherwise set to 443
        if re.match(r'^\d+$', result[field_arguments['dest_port']]): 
            port = int(result[field_arguments['dest_port']])
        else:
            port = 443
            result[field_arguments['dest_port']] = port
        hostname = result[field_arguments['dest']]
        try:
            # Use socket.create_connection with a short timeout (e.g., 1 second)
            with socket.create_connection((hostname, port), timeout=1) as conn:
                context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                # For SNI, if host value is IP address do not add server_hostname
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', hostname):
                    sock = context.wrap_socket(conn)
                else:
                    sock = context.wrap_socket(conn, server_hostname=hostname)
                cert_der = sock.getpeercert(True)
                x509 = Certificate.load(cert_der)
                cert = x509.native['tbs_certificate']
                result[field_arguments['ssl_hash']] = hashlib.sha256(cert_der).hexdigest()
                result[field_arguments['ssl_start_time']] = int(mktime(cert['validity'].get('not_before').timetuple()))
                result[field_arguments['ssl_end_time']] = int(mktime(cert['validity'].get('not_after').timetuple()))
                result[field_arguments['ssl_validity_window']] = result[field_arguments['ssl_end_time']] - int(mktime(datetime.now().timetuple()))
                if result[field_arguments['ssl_validity_window']] > 0:
                    result[field_arguments['ssl_is_valid']] = 'true'
                else:
                    result[field_arguments['ssl_is_valid']] = 'false'
                # Issuer
                result[field_arguments['ssl_issuer_common_name']] = cert['issuer'].get('common_name')
                result[field_arguments['ssl_issuer_unit']] = cert['issuer'].get('unit_name')
                result[field_arguments['ssl_issuer_organization']] = cert['issuer'].get('organization_name')
                result[field_arguments['ssl_issuer_locality']] = cert['issuer'].get('locality_name')
                result[field_arguments['ssl_issuer_state']] = cert['issuer'].get('state_or_province_name')
                result[field_arguments['ssl_issuer_country']] = cert['issuer'].get('country_name')
                result[field_arguments['ssl_issuer_email']] = cert['issuer'].get('email')
                result[field_arguments['ssl_self_issued']] = x509.self_issued
                result[field_arguments['ssl_self_signed']] = str(x509.self_signed)
                result[field_arguments['ssl_serial']] = cert.get('serial_number')
                result[field_arguments['ssl_signature_algorithm']] = cert['signature'].get('algorithm')
                # Subject
                # Subject Alternative Names
                for i in cert['extensions']:
                    if i['extn_id'] == 'subject_alt_name':
                        begin = True
                        for n in i['extn_value']:
                            if begin:
                                sub_alt_name = n
                                begin = False
                            else:
                                sub_alt_name += '|' + n
                        result[field_arguments['ssl_subject_alt_name']] = sub_alt_name
                result[field_arguments['ssl_subject_common_name']] = cert['subject'].get('common_name')
                result[field_arguments['ssl_subject_unit']] = cert['subject'].get('unit_name')
                result[field_arguments['ssl_subject_organization']] = cert['subject'].get('organization_name')
                result[field_arguments['ssl_subject_locality']] = cert['subject'].get('locality_name')
                result[field_arguments['ssl_subject_state']] = cert['subject'].get('state_or_province_name')
                result[field_arguments['ssl_subject_country']] = cert['subject'].get('country_name')
                result[field_arguments['ssl_subject_email']] = cert['subject'].get('email')
                result[field_arguments['ssl_version']] = cert.get('version')
                # return the values
                w.writerow(result)
        except:
            # return the values
            w.writerow(result)

main()
