'''
Alert action script to SFTP a splunk result as a CSV to a remote server
'''

from __future__ import print_function
import sys
import os
import logging
import io
import re
import gzip
import csv
import json
from helpers import check_known_hosts, load_paramiko

SSHClient,AutoAddPolicy = load_paramiko()
check_known_hosts()

def sftp_buffer(sftp, buf, csv_dict, fieldnames, destination):
    '''
    Write csv dictionary to buffer then send as file-object over SFTP
    '''
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(csv_dict)
    buf.seek(0)
    sftp.putfo(buf,destination)

def remote_command(payload):
    '''
    Exectute a command on remote host over SSH
    '''
    config = payload.get('configuration')
    server = config.get('sftp_host')
    username = config.get('sftp_username')
    password = config.get('sftp_password')
    autoadd = config.get('sftp_autoadd')
    results_file = payload.get('results_file')
    filename = config.get('sftp_filename')
    if filename == '' or filename is None:
        filename = re.sub(r'\.csv\.gz$','',os.path.basename(results_file))
    destdir = config.get(r'sftp_destdir')
    if destdir == '' or destdir is None:
        destdir = '.'
    destination = destdir + '/' + filename + '.csv'
    with SSHClient() as ssh:
        ssh.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        if autoadd == "1":
            ssh.set_missing_host_key_policy(AutoAddPolicy())
        if username=='':
            ssh.connect(server, password=password)
        else:
            ssh.connect(server, username=username, password=password)
        sftp = ssh.open_sftp()
        with gzip.open(results_file, 'rt') as unzipped_file:
            csv_dict = csv.DictReader(unzipped_file)
            fieldnames = csv_dict.fieldnames
            fieldnames = [name for name in fieldnames if '__mv_' not in name]
            if sys.version_info >= (3, 0):
                with io.StringIO() as buf:
                    sftp_buffer(sftp, buf, csv_dict, fieldnames, destination)
            else:
                with io.BytesIO() as buf:
                    sftp_buffer(sftp, buf, csv_dict, fieldnames, destination)

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.ERROR)
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:
            # retrieving message payload from splunk
            splunk_payload = json.loads(sys.stdin.read())
            remote_command(splunk_payload)
        except Exception as exc:
            logging.exception(exc)
            print('ERROR Unexpected error: %s' % exc, file=sys.stderr)
            sys.exit(3)
    else:
        print('FATAL Unsupported execution mode (expected --execute flag)', file=sys.stderr)
        sys.exit(1)
