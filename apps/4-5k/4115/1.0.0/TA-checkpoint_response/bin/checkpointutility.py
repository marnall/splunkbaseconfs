from threading import Timer
import subprocess
import platform
import os
import shlex
from smb.SMBConnection import SMBConnection
import socket
import re
import sys

TIMEOUT = 30

def validate_credentials(username=None, password=None, hostname=None, key_path=None, port='22', os_type=None,
                         auth_type=None,domain='',upload_path=None):
    """

    :param username:
    :param password:
    :param hostname:
    :param key_path:
    :param port:
    :param os_type:
    :param auth_type:
    :return:
    """
    FILENAME = 'splunk_test_file_transfer.txt'
    with open(FILENAME, 'wb') as test_file:
        test_file.write("Testing file transfer. If this file is present at the specified upload path, then the authentication is successful.")
    try:
        os.environ["LD_LIBRARY_PATH"]=""
        if os_type == "windows":
            try:
                shared_folder = upload_path.rstrip('/')
                upload_path = '/' + FILENAME
                if auth_type == "password":
                    conn = SMBConnection(username, password, socket.gethostname(), hostname,domain, use_ntlm_v2=True,is_direct_tcp=True)
                    connected = conn.connect(hostname, 445)
                    if not connected:
                        return False, "Failed to authenticate user %s on %s" % (username, hostname)
                    with open(FILENAME,'r') as fp:
                        conn.storeFile(shared_folder, upload_path, fp)
                    conn.close()
                    remove_file(FILENAME)
                    return True, "Authentication Successful"
                else:
                    remove_file(FILENAME)
                    return False, "Key based authentication is not allowed in this case"
            except Exception as e:
                remove_file(FILENAME)
                return False, "Failed to authenticate user %s on %s" % (username, hostname)
        elif platform.system().lower() == "windows":
            port = port or '22'
            key_path = key_path.replace('\\','/')
            upload_path = upload_path.rstrip('/') + "/"
            if auth_type == "password":
                cmd = "echo y | pscp -scp -q -P " + port + " -pw " + password + " " + FILENAME + " " +\
                      username + "@" + hostname + ":" + upload_path
            else:
                if password and key_path:
                    cmd = "echo y | pscp -scp -q -P " + port + " -i " + key_path + " -pw " + password + " " + FILENAME + " " + username + "@" + hostname + ":" + upload_path
                elif key_path:
                    cmd = "echo y | pscp -scp -q -P " + port + \
                          " -i " + key_path + " " + FILENAME + " " + username + "@" + hostname + ":" + upload_path
                else:
                    return False, "This type of Authentication not supported. Enter proper details."

            # Initiate the upload opening the process and wait for it to complete. Kill the process and return failure
            # if the process take more time than the TIMEOUT defined.
            process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            timer = Timer(TIMEOUT, process.kill)
            timer.start()
            process.wait()
            timer.cancel()
            remove_file(FILENAME)
            if process.returncode != 0:
                return False, "Failed to authenticate user %s on %s" % (username, hostname)
            return True, "Authentication Successful"
        else:
            os.environ["SSHPASS"] = password
            port = port or '22'
            upload_path = upload_path.rstrip('/') + "/"
            if auth_type == "password":
                cmd = "sshpass -e scp -o StrictHostKeyChecking=no -P " + port + " " + FILENAME + " " +\
                  username + "@" + hostname + ":" + upload_path
            else:
                if password and key_path:
                    cmd = "sshpass -Ppassphrase -e scp -o StrictHostKeyChecking=no -P " + port + " -i " + key_path + " " +\
                      FILENAME + " " + username + "@" + hostname + ":" + upload_path
                elif key_path:
                    cmd = "scp -o PasswordAuthentication=no -o StrictHostKeyChecking=no -i " + key_path + " " + "-P " + port +\
                      " " + FILENAME + " " + username + "@" + hostname + ":" + upload_path
                elif password:
                    cmd = "sshpass -Ppassphrase -e scp -o StrictHostKeyChecking=no -P " + port + " " +\
                      " " + FILENAME + " " + username + "@" + hostname + ":" + upload_path
                else:
                    cmd = "scp -o PasswordAuthentication=no StrictHostKeyChecking=no -P " + port + " " + FILENAME + " " +\
                      username + "@" + hostname + ":" + upload_path

            cmd = shlex.split(cmd)
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
            timer = Timer(TIMEOUT, process.kill)
            timer.start()
            process.wait()
            timer.cancel()
            remove_file(FILENAME)
            if process.returncode != 0:
                return False, "Failed to authenticate user %s on %s" % (username, hostname)
            return True, "Authentication Successful"
    except Exception as e:
        remove_file(FILENAME)
        print >> sys.stderr, "ERROR Unexpected error: %s" % e
        return False, "ERROR Unexpected error: %s" % e


def remove_file(FILENAME):
    if os.path.exists(FILENAME):
        os.remove(FILENAME)

def is_ip(ip_str):
    """ Validates if the provided value is ipv4 or not

    :param ip_str: input value
    :return: True/False
    """

    ip_rex = '^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(/\d+)?$'
    m = re.match(ip_rex, ip_str)
    if m is None:
        return False
    else:
        return True

def is_domain(hostname):
    """ Validates if the provided value is domain or not

    :param hostname: input value
    :return: True/False
    """

    invalid_values = ['"', ',', '\\n','\\r\\n','#','!']
    for invalid_value in invalid_values:
        if invalid_value in hostname:
            return False

    if len(hostname) > 255:
        return False
    if is_ip(hostname):
        return False
    if is_ipv6(hostname):
        return False
    if is_ip_range(hostname):
        return False
    if hostname[-1] == '.':
        hostname = hostname[:-1]
    allowed = re.compile('@', re.IGNORECASE | re.UNICODE)
    return not any((allowed.search(x) for x in hostname.split('.')))

def is_md5(input_str):
    """ Validates if the provided value is md5 or not

    :param input_str: input value
    :return: True/False
    """

    regex = '^[0-9a-fA-F]{32}$'
    m = re.match(regex, input_str)
    return True if m else False

def is_ipv6(ip_str):
    """ Validates if the provided value is ipv6 or not

    :param ip_str: input value
    :return: True/False
    """

    ip_rex = '^(?:(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}' \
             '|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|::(?:[0-9A-Fa-f]{1,4}:)' \
             '{5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}' \
             '(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){4}' \
             '(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}' \
             '(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4})?::' \
             '(?:[0-9A-Fa-f]{1,4}:){3}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}' \
             '|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:)' \
             '{,2}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|' \
             '(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}' \
             '|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,3}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}:(?:[0-9A-Fa-f]' \
             '{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]' \
             '|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,4}[0-9A-Fa-f]{1,4})?::' \
             '(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}' \
             '(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,5}[0-9A-Fa-f]{1,4})?::' \
             '[0-9A-Fa-f]{1,4}|(?:(?:[0-9A-Fa-f]{1,4}:){,6}[0-9A-Fa-f]{1,4})?::)$'

    m = re.match(ip_rex, ip_str)
    if m is None:
        return False
    else:
        return True

def is_url(input_str):

    invalid_values = ['"', ',', '\\n','\\r\\n','#','!']
    for invalid_value in invalid_values:
        if invalid_value in input_str:
            return False

    return True if 0 in (input_str.find('http://'), input_str.find('https://'), input_str.find('ftp://')) else False

def is_mail_subject(input_str):

    invalid_values = ['"', ',', '\\n','\\r\\n','#','!']
    for invalid_value in invalid_values:
        if invalid_value in input_str:
            return False
    return True

def is_email(email_str):
    """ Validates if the provided value is an email or not

    :param email_str:
    :return:
    """
    invalid_values = ['"', ',', '\\n','\\r\\n','#','!']
    for invalid_value in invalid_values:
        if invalid_value in email_str:
            return False

    if len(email_str) > 255:
        return False
    if is_ip(email_str):
        return False
    email_regex = '^\\S*?@?[^\\s@]+\\.\\S+$'
    m = re.match(email_regex, email_str)
    return True if m else False

def is_ip_range(ip_range_str):
    """ Validates if the provided value contains valid ipv4 or not

    :param ip_str: input value
    :return: True/False
    """
    ip_list = ip_range_str.split('-')
    return len(ip_list) == 2 and all((is_ip(ip) for ip in ip_list))
