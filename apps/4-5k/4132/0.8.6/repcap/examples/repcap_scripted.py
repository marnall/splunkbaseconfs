#!/usr/bin/python
"""
    Report Capture - Scripted
    Version 0.4 (BETA)

    This script will trigger a report-capture and will download the report (if specified)
"""

import argparse
import os
import re
import ssl
import sys
import urllib2
import urllib

DELIVERY_OPTS = ['download', 'email']
HTTP_TIMEOUT_EXTRA = 30
PAGE_ORIENTS = ['landscape', 'portrait']
PAGE_SIZES = ['A1', 'A2', 'A3', 'A4', 'LTR', 'custom',
              '720P', '1080P', 'WUXGA', 'DCI2K', 'WQHD', 'QHDP', 'UWQHDP', 'UHD', '8K']
REPCAP_URL = '/en-GB/custom/repcap/repcapsvc/capture_scripted'
VERSION = "0.4"


def die(msg):
    """ Handle an error gracefully """
    print 'ERROR: %s' % str(msg)
    sys.exit(1)


def parse_args():
    """ Parse the CLI args """
    parser = argparse.ArgumentParser()
    parser.add_argument('--c_panel', type=str, required=False,
                        help='Dashboard panel')
    parser.add_argument('--c_url', type=str, required=True,
                        help='Dashboard/Report URL')
    parser.add_argument('--c_user', type=str, required=True,
                        help='Capture user')
    parser.add_argument('--c_wait', type=str, required=True,
                        help='Capture time')
    parser.add_argument('--d_method', type=str, required=True, choices=DELIVERY_OPTS,
                        help='Delivery method')
    parser.add_argument('--e_to', type=str, required=False,
                        help='Email addresses')
    parser.add_argument('--f_path', type=str, required=True,
                        help='Output file-path')
    parser.add_argument('--f_name', type=str, required=True,
                        help='Output file-name')
    parser.add_argument('--f_type', type=str, required=True,
                        help='Output file-type')
    parser.add_argument('--ignore_ssl', type=bool, required=False, default=False,
                        help='Ignore self-signed SSL certificates')
    parser.add_argument('--p_size', type=str, required=True, choices=PAGE_SIZES,
                        help='Page size')
    parser.add_argument('--p_orient', type=str, required=True, choices=PAGE_ORIENTS,
                        help='Page orientation')
    parser.add_argument('--s_height', type=int, required=False,
                        help='Screen height')
    parser.add_argument('--s_width', type=int, required=False,
                        help='Screen width')
    parser.add_argument('--spl_host', type=str, required=True,
                        help='Splunk hostname/IP')
    parser.add_argument('--spl_port', type=int, required=True,
                        help='Splunk port')
    parser.add_argument('--spl_proto', type=str, required=True, choices=['http', 'https'],
                        help='Splunk protocol')
    parser.add_argument('--spl_pass', type=str, required=True,
                        help='Splunk password')
    parser.add_argument('--spl_user', type=str, required=True,
                        help='Splunk username')
    # Perform the initial validation
    args = parser.parse_args()
    # Check the arg combinations
    if args.d_method == 'email' and not args.e_to:
        die('You must specify the e_to parameter if d_method is set to email')
    if args.p_size == 'custom' and not (args.s_height and args.s_width):
        die('You must specify both s_height and s_width if p_size is set to custom')
    # Check the specified file-path exists
    if not os.path.isdir(args.f_path):
        die('The specified f_path folder was not found')
    # Return the args (in dict form)
    return vars(args)


def spl_rest(script_args):
    """ Perform the REST call to Splunk """
    # Construct the URL
    splunk_url = '{proto}://{host}:{port}{url}'.format(
        proto=script_args['spl_proto'],
        host=script_args['spl_host'],
        port=script_args['spl_port'],
        url=REPCAP_URL)
    # Construct the output filename
    if script_args['d_method'] == 'download':
        outfile = '%s/%s.%s' % (
            script_args['f_path'], script_args['f_name'], script_args['f_type'])
    else:
        outfile = '%s/%s.html' % (
            script_args['f_path'], script_args['f_name'])
    # Construct the SSL context (if ignoring self-signed is enabled
    ssl_ctx = None
    if script_args['ignore_ssl']:
        try:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
        except:  # pylint: disable=bare-except
            print 'WARN: Failed to create SSL context, SSL validation may fail'
    # Create the args to encode
    script_args.pop('ignore_ssl', None)
    script_args.pop('f_path', None)
    script_args.pop('spl_host', None)
    script_args.pop('spl_port', None)
    script_args.pop('spl_proto', None)
    empty_keys = []
    for key in script_args.keys():
        if not script_args[key]:
            empty_keys.append(key)
    for key in empty_keys:
        script_args.pop(key, None)
    # Encode the request data
    splunk_data = urllib.urlencode(script_args)
    # Create the request
    http_req = urllib2.Request(splunk_url, splunk_data)
    # Perform the request
    if ssl_ctx:
        http_res = urllib2.urlopen(
            http_req,
            timeout=int(script_args['c_wait'])+HTTP_TIMEOUT_EXTRA,
            context=ssl_ctx)
    else:
        http_res = urllib2.urlopen(
            http_req,
            timeout=int(script_args['c_wait'])+HTTP_TIMEOUT_EXTRA)
    # Copy the data to a local var (as read() wipes the buffer once called
    html_buf = http_res.read()
    # Check if the download was successful
    if re.match('^<html>', html_buf):
        die('Failed to create report:\n%s' % str(html_buf))
    # Download the file contents
    with open(outfile, 'wb') as fileobj:
        fileobj.write(html_buf)


def main():
    """ Main execution """
    # Begin
    print 'Report Capture - Scripted (v%s)' % str(VERSION)
    # Parse the CLI args
    print 'Parsing script args'
    script_args = parse_args()
    # Perform the REST call
    print 'Performing REST call'
    spl_rest(script_args)
    # Capture complete
    print 'Capture complete'
    sys.exit(0)


if __name__ == '__main__':
    main()
