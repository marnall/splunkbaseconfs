'''
Alert action script to issue command to a remote server over SSH
'''
from __future__ import print_function
import sys
import os
import logging
import json
from helpers import check_known_hosts, load_paramiko

SSHClient,AutoAddPolicy = load_paramiko()
check_known_hosts()

def remote_command(payload):
    '''
    Exectute a command on remote host over SSH
    '''
    config = payload.get('configuration')
    server = config.get('ssh_cmd_host')
    username = config.get('ssh_cmd_username')
    password = config.get('ssh_cmd_password')
    autoadd = config.get('ssh_cmd_autoadd')
    command = config.get('ssh_cmd_command')
    with SSHClient() as ssh:
        ssh.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        if autoadd == "1":
            ssh.set_missing_host_key_policy(AutoAddPolicy())
        if username=='':
            ssh.connect(server, password=password)
        else:
            ssh.connect(server, username=username, password=password)
        _ssh_stdin, _ssh_stdout, _ssh_stderr = ssh.exec_command(command)

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
