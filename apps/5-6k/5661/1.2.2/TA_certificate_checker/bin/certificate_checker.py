from __future__ import print_function
from builtins import str
import os
import sys
from time import localtime,strftime
import time
from datetime import datetime
import subprocess
from shutil import which
import json
import re


def is_available(command):
    return which(command) is not None


def cert_to_json(attributes, port):
    match = ''
    new_list = []
    d = dict()
    for attr in attributes:
        if 'subject=' in attr:
            match = re.search('(CN=\S+?)(\/|$)', attr)
            #print(match.group(1))
            new_list.append(match.group(1))
        else:
            new_list.append(attr)
    # Converting list to dict for json dump
    d = dict(a.split('=') for a in new_list)
    # Adding 'service_port'
    d['service_port'] = port
    convert_dates(d)
    print(json.dumps(d))


def convert_dates(d):
    # Replacing 'GMT' with '+0000' because strptime was not recognizing the timezone name
    if 'notBefore' in d:
        notBeforeEpoch = datetime.strptime(d.get('notBefore').replace('GMT', '+0000'), '%b %d %H:%M:%S %Y %z')
        d['notBeforeEpoch'] = notBeforeEpoch.timestamp()
    if 'notAfter' in d:
        notAfterEpoch = datetime.strptime(d.get('notAfter').replace('GMT', '+0000'), '%b %d %H:%M:%S %Y %z')
        d['notAfterEpoch'] = notAfterEpoch.timestamp()


def check_ports(ports_list):
    #print("Ports Sent => ", ports_list)
    ps = None
    output = None
    for port in ports_list:
        dest_ip = "127.0.0.1:" + str(port)
        if os.name == 'nt':
            try:
                ps = subprocess.Popen('openssl s_client -connect %s | openssl x509 -noout -subject -serial -startdate -enddate' %dest_ip, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True)
                # timeout needs to be long here due to openssl binaries on Windows systems ignoring the input to STDIN
                output = ps.communicate(timeout=90)[0].decode('utf-8')
            except subprocess.TimeoutExpired:
                print_error("timeout expired during openssl connection to %s" %dest_ip)
            if output:
                cert_to_json(output.splitlines(), port)
        else:
            try:
                ps = subprocess.Popen('echo "q" | openssl s_client -connect %s | openssl x509 -noout -subject -serial -startdate -enddate' %dest_ip, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True)
                output = ps.communicate(timeout=10)[0].decode('utf-8')
            except subprocess.TimeoutExpired:
                print_error("timeout expired during openssl connection to %s" %dest_ip)
            if output:
                cert_to_json(output.splitlines(), port)


def get_windows_process():
    ps = ''
    output = ''
    match = ''
    result = 0
    if (is_available('tasklist') and is_available('netstat')):
        try:
            ps = subprocess.Popen('tasklist /NH /FI "IMAGENAME eq %s"' %win_process_name, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            output = str(ps.communicate(timeout=10)[0])
            match = re.search(re.escape(win_process_name)+'\s+(\d+)', output)
        except subprocess.TimeoutExpired:
            print_error("timeout expired during tasklist process lookup")
        if match:
            result = match.group(1)
        return result


def print_error(message):
    error_dict = { 'error':''};
    error_dict['error'] = message
    print(json.dumps(error_dict))


# -------------------
# Script starts here
# -------------------
nix_process_name = 'splunkd'
win_process_name = 'splunkd.exe'
ports = []

if (is_available('openssl')):
    # Windows requires slightly different parameters for listening ports
    if os.name == 'nt':
        process_id = get_windows_process()
        if process_id:
            try:
                ps = subprocess.Popen('netstat -a -n -p tcp -o | findstr "LISTENING" | findstr %s' %process_id, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True)
                output = str(ps.communicate(timeout=10)[0])
            except subprocess.TimeoutExpired:
                print_error("timeout expired while running netstat to find listening ports")
            if output:
                for line in output.split('TCP'):
                    match = re.search(':([0-9]+)', line)
                    if match:
                        ports.append(match.group(1))
                check_ports(ports)
        else:
            print("[!] Unable to determine a process id for", win_process_name)
    else:
        # *nix will attempt to use 'ss' or 'netstat'
        if (is_available('ss')):
            try:
                ps = subprocess.Popen(['ss', '-ntlp'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                output = str(ps.communicate(timeout=10)[0])
            except subprocess.TimeoutExpired:
                print_error("timeout expired while running ss to find listening ports")
            if output:
                for line in output.split('LISTEN'):
                    if nix_process_name in line:
                        match = re.search(':([0-9]+)', line)
                        if match:
                            ports.append(match.group(1))
                check_ports(ports)
        elif (is_available('netstat')):
            try:
                ps = subprocess.Popen(['netstat', '-ntlp'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                output = str(ps.communicate(timeout=10)[0])
            except subprocess.TimeoutExpired:
                print_error("timeout expired while running netstat to find listening ports")
            if output:
                for line in output.split('tcp'):
                    if nix_process_name in line:
                        match = re.search(':([0-9]+)', line)
                        if match:
                            ports.append(match.group(1))
                check_ports(ports)
        else:
            print_error("Unable to find a suitable binary to determine listening ports")
else:
    print_error("Fatal error: openssl binary not found")

