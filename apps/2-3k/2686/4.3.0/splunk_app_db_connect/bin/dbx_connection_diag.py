#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from urllib.parse import urlparse

import dbx_bootstrap_env
import argparse
import collections
import json
import os.path, subprocess
from subprocess import STDOUT, PIPE
import shutil
import os
import errno
import re
import datetime
import getpass
from splunklib.six.moves import input as input
import splunklib.client as client
import csv
import socket
import time
import jre_validator2
import java_home_detector2

# Set the correct classpath separator for the os
classpathSeparator = ";" if sys.platform == 'win32' else ":"

script_dir, _ = os.path.split(os.path.abspath(sys.argv[0]))

usage_message = """
This script invokes a java tool that tests your 'Splunk DB connect' connection to your database
"""

splunk_home = os.path.join(script_dir, "..", "..", "..", "..")
db_connect_home = os.path.join(script_dir, "..")

DB_CONNECT_APP_NAME = "splunk_app_db_connect"
verbose_logging = False


def _quit_with_description(description, code=-1):
    print(description)
    if code != 0:
        print("abort!")
    sys.exit(code)


def _yes_or_no(prompt):
    while True:
        ans = input(prompt)
        if ans == "y":
            return True
        else:
            return False


def _get_splunk_url(args):
    try:
        url = urlparse("https://localhost:8089")
        if args.scheme is not None:
            url = url._replace(scheme=args.scheme)
        if args.port is not None:
            url = url._replace(netloc="localhost:{}".format(args.port))

        return url
    except Exception as ex:
        _quit_with_description("invalid command line arguments, cause: %s" % str(ex))


def _create_service(username, password, url, app="-"):
    try:
        return client.connect(username=username, password=password, scheme=url.scheme, host=url.hostname, port=url.port,
                              app=app)
    except Exception as ex:
        _quit_with_description("failed to login to splunkd, cause={}".format(ex))


def _does_key_exist(entity, key):
    try:
        entity[key]
        return True
    except:
        return False


def read_rulebook(message, db, rulebook_path):
    with open(rulebook_path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['DB'] == db:
                err = row['Error']
                tokens = err.split()
                if message_match(message, tokens):
                    return row['Diagnosis'], row['Resolution']
        return "", ""


def message_match(message, tokens):
    """
    A function that tries to match the error message
    encountered with an error in the rulebook.
    message argument is the error issued while connecting.
    tokens are all the tokens of an error message in the rulebook
    """
    start = 0
    stop = len(message)
    for token in tokens:
        index = message.find(token, start, stop)
        if index == -1:
            return False
        else:
            start = index+len(token)
    return True


def _normalize_to_boolean(val):
    return True if val in ['1', 'true', 'True', 't', 'T', 'yes', 'Yes', 'y'] else False


def _normalize_to_boolean_string(val):
    return 'true' if val in ['1', 'true', 'True', 't', 'yes', 'Yes', 'y'] else 'false'


def _replace_token(source, lookup_table):
    source = re.sub(r"<(\w+?)>", r"{\1}", source)
    return source.format(**lookup_table)


def host_is_open(ip, port, timeout):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, int(port)))
        s.shutdown(socket.SHUT_RDWR)
        return True
    except:
        return False
    finally:
        s.close()


def check_host(ip, port, retry, delay, timeout):
    ipup = False
    for i in range(retry):
        if host_is_open(ip, port, timeout):
            ipup = True
            break
        else:
            time.sleep(delay)
    return ipup


def ping_host(connection):
    print("\nFirst trying to establish a simple socket connection to the DB server and port...\n")
    if check_host(connection['host'], connection['port'], retry=3, delay=10, timeout=3):
        print("Good news! " + connection['host'] + " server is up and running!\n")
    else:
        print("Could not establish connection to " + connection['host'] +
              ". Make sure the server is up, and you have access to it (not blocked by a firewall for example)\n")
        sys.exit()


def compile_java(java_compile, java_file):
    subprocess.check_call([java_compile, java_file])


def attempt_jdbc_connection(connection_field_values, selected_driver):
    cmd = "java -cp ." + classpathSeparator + "'" + selected_driver + "'" + " JDBCConnect " + " '" + connection_field_values['JDBC URL'] + "' '" + connection_field_values['Database user'] + "' '" + connection_field_values['Database password']+ "'"
    message = subprocess.check_output(cmd, shell=True).decode("utf-8")
    return message


def get_jdbc_drivers():
    files_in_dir = []
    location = '../drivers/'
    # r=>root, d=>directories, f=>files
    for r, d, f in os.walk(location):
        for item in f:
            if '.jar' in item:
                files_in_dir.append(os.path.join(r, item))
    if not files_in_dir:
        _quit_with_description("No drivers installed in '../drivers/' folder. Please upload at least one driver and try again.")
    return files_in_dir


def show_jdbc_drivers():
    print("Found the following JDBC drivers:")
    jdbc_drivers = get_jdbc_drivers()
    n = 0
    while n < len(jdbc_drivers):
        print(str(n) + ". ", jdbc_drivers[n])
        n += 1


def choose_jdbc_driver():
    show_jdbc_drivers()
    user_option = input("\nEnter the number of the driver to use: ")
    user_option = int(user_option)
    try:
        jdbc_drivers = get_jdbc_drivers()
        return jdbc_drivers[user_option]
    except Exception as ex:
        _quit_with_description("Not a valid selection: %s" % str(ex))


def choose_connection(db_connections_conf):
    if not db_connections_conf:
        _quit_with_description("Please create at least one DB connection thru DBX UI, and try it again.")
    n = 0
    db_connections = []
    print("\nFound the following connections:")
    for item in db_connections_conf:
        db_connections.append(item.name)
        print(str(n) + ". " + item.name)
        n += 1
    selection = input("\nSelect connection to test: ")
    try:
        connection = db_connections_conf[db_connections[int(selection)]]
    except Exception as ex:
        _quit_with_description("Not a valid selection: %s" % str(ex))
    return connection


def initialize_and_display_fields(use_ssl, connection, connection_type, identity, db_user, db_password):
    connection_ssl = connection['jdbcUseSSL']
    connection_properties = connection_type['connection_properties']
    connection_driver = connection_type['jdbcDriverClass']

    properties = dict(connection_type.content)
    properties.update(connection.content)
    properties.update(identity.content)
    url_template = properties['jdbcUrlFormat'] if not use_ssl else properties['jdbcUrlSSLFormat']
    jdbc_url = _replace_token(url_template, properties)

    print("\nThe following are your values of the fields for a JDBC connection:- \n")
    print("0. Using SSL = %s \n" % _normalize_to_boolean_string(connection_ssl))
    print("1. JDBC URL = %s\n" % jdbc_url)
    print("2. Database user = %s \n" % db_user)
    print("3. Database password = " + "*" * len(db_password) + "\n")
    print("4. Connection properties = %s \n" % connection_properties)

    connection_fields = ['Using SSL', 'JDBC URL', 'Database user', 'Database password',
                         'Connection properties', 'JDBC Driver']
    connection_field_values = {
        'Using SSL': _normalize_to_boolean_string(connection_ssl),
        'JDBC URL': jdbc_url,
        'Database user': db_user,
        'Database password': db_password,
        'Connection properties': connection_properties,
        'JDBC Driver': connection_driver
    }
    return properties, connection_fields, connection_field_values


def choose_connection_fields(properties, connection_fields, connection_field_values):
    user_change = True

    while user_change:
        print("Would you like to proceed with the connection diagnostics? \n ")
        user_change = not _yes_or_no("Press 'y' to proceed, 'n' to change the value of a connection field: ")

        if not user_change:
            break

        user_option = input("Enter the field number to be changed \n")
        user_option = int(user_option)
        while user_option > len(connection_fields) or user_option < 0:
            user_option = int(input("\nSpecified field number does not exist. Enter field number again \n"))
        if user_option == 3:
            print("\nCurrent value for field Database password = '****'")
        else:
            print("\nCurrent value for field {} = '{}' \n".format(connection_fields[user_option],
                                                              connection_field_values[connection_fields[user_option]]))
        new_value = input("Enter the new value for the field %s \n" % connection_fields[user_option])
        connection_field_values[connection_fields[user_option]] = new_value
        print("\nThe value for field {} has been changed to '{}' \n".format(connection_fields[user_option], new_value))

        if connection_fields[user_option] == 'Using SSL':
            use_ssl = _normalize_to_boolean(connection_field_values[connection_fields[user_option]])
            url_template = properties['jdbcUrlFormat'] if not use_ssl else properties['jdbcUrlSSLFormat']
            jdbc_url = _replace_token(url_template, properties)
            connection_field_values['JDBC URL'] = jdbc_url
            print("\nSince you changed the SSL type, your JDBC URL has been changed to conform to the SSL format: %s\n"
                  % jdbc_url)

    print("\nProceeding with the connection diagnostics... \n")


def java_home_selection(dbx_settings_conf):

    java_home = dbx_settings_conf["java"]["javaHome"]
    if not java_home:
        java_home = os.environ.get("JAVA_HOME")
    if not java_home:
        _quit_with_description("Cannot find JAVA_HOME defined in DBX or environment variables. Please input it thru DBX UI.")
    print("Your current Java Home in DB connect is set to: " + java_home + "\n")
    java_exec = java_home_detector2._get_java_executable(java_home)
    user_change_count = 0
    user_change = True

    while user_change:
        java_valid, java_details = jre_validator2.validateJRE(java_exec)
        java_compile = os.path.join(java_home, 'bin', 'javac')
        if not java_valid:
            print("Your Java Home is not valid. Please input a working Java Home directory \n")
            user_change = True
        else:
            if user_change_count < 1:
                print("Your Java Home is valid. Do you still wish to change it? \n")
                user_change = _yes_or_no("Enter 'y' to change it. 'n' to proceed without changing it: ")
            else:
                #allow the user to only modify the java home once, if correct.
                print("Your Java Home is valid. Proceeding...\n")
                user_change = False
            user_change_count += 1
            if not user_change:
                return java_home, java_compile, java_exec

        if user_change:
            java_home = input("Enter the new Java Home directory: ")
            java_exec = java_home_detector2._get_java_executable(java_home)
            java_valid = False


def main():
    parser = argparse.ArgumentParser(description="connection testing tool")
    parser.add_argument("-scheme", help="the splunk server uri's scheme, either http or https", required=False)
    parser.add_argument("-port", help="the splunk server's management port, by default it is 8089", required=False)
    parser.add_argument("-verbose", help="whether enable verbose logging, default is False", required=False,
                        action='store_true')
    args, unknown = parser.parse_known_args()

    verbose_logging = args.verbose
    url = _get_splunk_url(args)
    print(usage_message)

    username = input("\nSplunk username: ")
    password = getpass.getpass()
    # login logic
    service = _create_service(username, password, url, app=DB_CONNECT_APP_NAME)

    installed_apps = list(map(lambda service: service.name, service.apps))

    if DB_CONNECT_APP_NAME not in installed_apps:
        _quit_with_description("%s not installed on this Splunk instance?" % DB_CONNECT_APP_NAME)
    else:
        print("\n%s is installed on this Splunk instance" % DB_CONNECT_APP_NAME)

    if verbose_logging:
        print('Fetching connection configurations...\n')

    quit_code = ""
    while quit_code != "q":

        try:
            db_connections_conf = service.confs["db_connections"]
            db_connection_types_conf = service.confs["db_connection_types"]
            dbx_settings_conf = service.confs["dbx_settings"]
            connection = choose_connection(db_connections_conf)
        except Exception as ex:
            _quit_with_description(
                "Configurations not found for connection {}. Exception encountered: {}".format(connection.name, str(ex)))

        print("connection: " + connection.name + "\n")

        selected_driver = choose_jdbc_driver()

        java_home, java_compile, java_exec = java_home_selection(dbx_settings_conf)

        connection_type_name = connection['connection_type']
        connection_type = db_connection_types_conf[connection_type_name]
        print("connection type: " + connection_type.name + "\n")

        if verbose_logging:
            print("Fetching DBX identity associated with your connection...\n")
        db_identities_conf = service.confs["identities"]
        identity = db_identities_conf[connection['identity']]
        db_user = identity.content["username"]
        print("This connection is associated with username {}. Please enter your password for username {}".format(
            db_user, db_user))
        db_password = getpass.getpass()

        ping_host(connection)

        use_ssl = False
        if _does_key_exist(connection, "jdbcUseSSL"):
            use_ssl = _normalize_to_boolean(connection['jdbcUseSSL'])
        elif _does_key_exist(connection_type, "jdbcUseSSL"):
            use_ssl = _normalize_to_boolean(connection_type["jdbcUseSSL"])

        properties, connection_fields, connection_field_values = initialize_and_display_fields(use_ssl, connection, connection_type, identity, db_user, db_password)

        choose_connection_fields(properties, connection_fields, connection_field_values)

        compile_java(java_compile, "JDBCConnect.java")

        message = attempt_jdbc_connection(connection_field_values, selected_driver)

        if not message:
            print("\nThis connection appears to valid! If you are still having difficulty with this connection, check the database password")
        print(str(message) + "\n")

        if connection_type.name == "generic_mssql":
            diagnosis, resolution = read_rulebook(message, "mssql", 'rulebook.csv')
        else:
            diagnosis, resolution = read_rulebook(message, connection_type.name, 'rulebook.csv')

        if len(diagnosis) != 0:
            print('\nDiagnosis: '+diagnosis+'\n')
            print('\nResolution: '+resolution+'\n')
        quit_code = input("Hit return to start a new connection check, or q to quit this utility. If you wish to test with a different driver, you must quit and start a new test.\n")


if __name__ == '__main__':
    main()
