#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################################################################################
##
##          Script:         optiv_decept.py
##
##          Language:       Python
##
##          Version:        1.32
##
##          Original Date:  07-24-2016
##
##          Author:         Derek Arnold
##
##          Company:        Optiv Security
##
##          Purpose:        Listen on multiple network ports and write data to a file to detect indicators of compromise.
##
##          Syntax:         python ./optiv_decept.py
##
##          Copyright (C):  2016 Derek Arnold (ransomvik)
##
##          License:        This program is free software: you can redistribute it and/or modify
##                          it under the terms of the GNU General Public License as published by
##                          the Free Software Foundation, either version 3 of the License, or
##                          any later version.
##
##                          This program is distributed in the hope that it will be useful,
##                          but WITHOUT ANY WARRANTY; without even the implied warranty of
##                          MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##                          GNU General Public License for more details. See <http://www.gnu.org/licenses/>
##
##          Change Log:     07-24-2016 DPA      Created.
##                          09-29-2016 DPA      Fixed logging.
##                          01-23-2017 DPA      Changed file rotation and tcp connection timeout
##                          02-06-2017 DPA      Added a udp handler
##                          02-18-2017 DPA      Added an SSH/telnet username and password collector
##                          02-22-2017 DPA      Added CEF Logging as an option
##
##########################################################################################################################

import socket
import select
import time
import sys
import logging
import re
import threading
import subprocess
import os

#from logging.handlers import TimedRotatingFileHandler
from logging.handlers import RotatingFileHandler


AUTHOR = 'Derek Arnold'
VERSION = '1.32'
ORGANIZATION = 'Optiv Security'
PROGRAM_NAME = 'Optiv Decept'
YEAR = '2017'

enable_cef_logging = False

splunk_home = '/opt/splunk'
log_name = 'optiv_decept.log'
log_path = os.path.join(splunk_home, 'etc', 'apps', 'optiv_TA_decept', 'bin', log_name)

if enable_cef_logging == True:
    log_name_cef = 'optiv_decept_cef.log'
    log_path_cef = os.path.join(splunk_home, 'etc', 'apps', 'optiv_TA_decept', 'bin', log_name_cef)


tcp_port_list = [20,21,22,23,25,
                 53,69,80,110,118,
                 137,139,143,194,389,
                 443,445,465,514,587,636,
                 993,1080,1194,1433,1604,
                 1723,3128,3306,3389,5900,
                 6000,8080,8888]

udp_port_list = [53,115,118,123,137,139,143,389,514,
                 1080,1194,1433,1512,2049,3306]

num_tcp_connections = 0
num_udp_connections = 0
splunk_is_still_running = True

tcpservers = []
udpservers = []
logger = logging.getLogger('decept')
this_decept_system_ip_address = str(socket.gethostbyname(socket.gethostname()))

#Create a logger object and set rotation schedule
def create_decept_logger(path):

    handler = RotatingFileHandler(path, mode='a', maxBytes=955555, backupCount=5, encoding=None, delay=0)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return 0

#Create a cef logger object and set rotation schedule
def create_decept_cef_logger(path):

    handler_cef = RotatingFileHandler(path, mode='a', maxBytes=955555, backupCount=5, encoding=None, delay=0)

    formatter_cef = logging.Formatter('CEF:0|Optiv|Decept System|'+VERSION+'|100|%(message)s|4|')
    handler_cef.setFormatter(formatter_cef)

    logger.addHandler(handler_cef)

    return 0

#future use
def handle_port_22(conn,timeout=20):
    logger.info("in handle_port_22().")
    begin=time.time()
    first_level_response = False
    second_level_response = False
    third_level_response = False
    sent_challenge_message = False

    while True:
        if time.time()-begin>timeout:
            break
        try:
            if sent_challenge_message is False:
                sent_challenge_message = True

                #message = "SSH-2.0-OpenSSH_6.6.1\n"
                message = "login as: "

                conn.send(message)

                data2=conn.recv(1024)

                logger.info("data received: " + str(data2))

                #if correct_response in str(data2) and first_level_response is False:
                if data2 and first_level_response is False:
                    #logger.info("received SSH connection string")
                    logger.info("received username: " + str(data2))
                    first_level_response = True
                    #message = "login as: "
                    message = data2 + "@" + this_decept_system_ip_address + "'s password: "
                    conn.send(message)

                    data3=conn.recv(25)

                    logger.info("received password: " + data )
                    message = "Permission denied, please try again.\n"

                    conn.send(message)

        except:
            time.sleep(15)

    return 0


def handle_udp_accept(conn,dest_portnum,timeout=10):

    global num_udp_connections
    num_udp_connections+=1
    conn.setblocking(0)
    data=''
    begin=time.time()
    total_data=[]
    bytes_in = 0

    while True:
        if total_data and time.time()-begin>timeout:
            break
        elif time.time()-begin>timeout:
            break
        try:
            (client_data, client_address) = conn.recvfrom(1024)
            logger.info('UDP Connection #' + str(num_udp_connections) + " detected: Source: " + str(client_address[0]) + ":" + str(client_address[1]) +
                " Destination: " + this_decept_system_ip_address + ":" + str(dest_portnum) + " proto: udp Severity: medium")

            client_data = client_data.replace("\n", " ")
            bytes_in = len(client_data)
            logger.info("Bytes in: " + str(bytes_in) + " Data received: ^^^\'"+str(client_data)+"\'^^^")

            begin=time.time()

            break
        except:
            time.sleep(0.5)

    return 0


#Handle an incoming TCP connection and log the payload
def handle_tcp_accept(conn,dest_portnum,timeout=10):

    logger.info('Attempting to receive TCP data. Timeout=' + str(timeout))

    sleep_interval = int(0.5)

    conn.setblocking(0)
    bytes_in = int(0)
    total_data=[]
    data=''
    begin=time.time()
    wait_for_response = False
    first_level_response = False
    second_level_response = False

    while 1:
        #if you got some data, then break after wait sec
        if total_data and time.time()-begin>timeout:
            break
        #if you got no data at all, wait a little longer
        elif time.time()-begin>timeout:
            break
        try:
            if (int(dest_portnum)==22 or int(dest_portnum)==23) and wait_for_response is False:
                wait_for_response = True

                sleep_interval = int(15)
                timeout=60
                #handle_port_22(conn)

                message = "login as: "
                conn.send(message)
                time.sleep(15)
                data2 = conn.recv(25)
                data2 = data2.replace("\n", "")
                data += data2 + "\n"
                time.sleep(15)

                if data2 and first_level_response is False:
                    logger.info("received username: " + str(data2))
                    bytes_in += len(data2)
                    first_level_response = True
                    message = str(data2) + "@" + this_decept_system_ip_address + "'s password: "

                    conn.send(message)
                    time.sleep(15)
                    data3=conn.recv(25)
                    data3 = data3.replace("\n", "")
                    data += data3 + "\n"
                    time.sleep(15)

                    if data3 and second_level_response is False:
                        logger.info("received password: " + data3 )
                        bytes_in += len(data3)
                        second_level_response = True
                        message = "Permission denied, please try again.\n"

                        conn.send(message)


            else:
                data=conn.recv(1024)
                bytes_in = len(data)

            if (bytes_in>1):
                data = data.replace("\n", " ")
                logger.info("Bytes in: " +str(bytes_in)+ " Data received: ^^^\'"+str(data)+"\'^^^")
                total_data.append(data)
                begin=time.time()
        except:
            time.sleep(0.5)


    logger.info("Closing connection.")

    return 0

#Get the source, destination ports and IPs and adjust formatting
def parse_tcp_connection(addr,conn):

    global num_tcp_connections
    num_tcp_connections += 1

    src_ip = "0.0.0.0"
    dest_ip = "0.0.0.0"
    src_port = 0
    dest_port = 0
    address_str = str(addr)
    connection_str = str(conn)

    src_ip_search = re.search('\(\'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\'',address_str)

    if src_ip_search:
        src_ip = src_ip_search.group(1)

    src_port_search = re.search('\(\'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\',\s(\d{1,5})',address_str)
    if src_port_search:
        src_port = src_port_search.group(1)

    dest_ip_search = re.search('\(\'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\'',connection_str)
    if dest_ip_search:
        dest_ip = dest_ip_search.group(1)

    dest_port_search = re.search('\(\'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\',\s(\d{1,5})',connection_str)
    if dest_port_search:
        dest_port = dest_port_search.group(1)
    logger.info('TCP Connection #' + str(num_tcp_connections) + " detected: Source: " + src_ip + ":" + str(src_port) +
                " Destination: " + dest_ip + ":" + str(dest_port) + " proto: tcp Severity: medium")

    return 0

#Monitors the splunkd daemon, shuts down this program when splunk shuts down
def pendulum():

    global splunk_is_still_running
    threading.Timer(120.0, pendulum).start()

    pl = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE).communicate()[0]
    num_splunkd_processes = 0

    processes = pl.split('\n')
# this specifies the number of splits, so the splitted lines
# will have (nfields+1) elements
    nfields = len(processes[0].split()) - 1
    for row in processes[1:]:
        if len (row) > 2:
            process_string = str(row.split(None, nfields)[3])
            if "splunkd" == process_string:
                num_splunkd_processes += 1

    if num_splunkd_processes > 0:
        logger.info("Splunk is running.")
        splunk_is_still_running = True
        return 0
    else:
        logger.warn("Splunk is NOT running!")
        splunk_is_still_running = False
        close_program()
        return -1

#Closes this program
def close_program():
    global tcpservers
    global udpservers

    logger.warn('Program is shutting down NOW!')
    for close_socket in tcpservers:

        logger.info("closing a socket in close_program")

        close_socket.close()

    for close_socket in udpservers:
        logger.info("closing a socket in close_program")

        close_socket.close()

    tcpservers = []
    udpservers = []

    sys.exit(0)
    return 0

def main():

    global tcpservers
    global udpservers

    create_decept_logger(log_path)

    if enable_cef_logging == True:
        create_decept_cef_logger(log_path_cef)

    logger.setLevel(logging.INFO)

    logger.info('Starting program.')

    logger.info("\n"+
        "   *_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*\n"+
        "      "+PROGRAM_NAME+" Version " + str(VERSION)+ "\n"
        "      Author: "+AUTHOR+" Year " + str(YEAR) + "\n"
        "      "+ORGANIZATION +"\n"+
        "   *_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*_*")


    logger.info("Binding to ports in 30 seconds.")
    logger.info("This decept system IP address is: " + this_decept_system_ip_address + ".")
    time.sleep(30)
    pendulum()

    num_good_tcp_binds = 0
    num_bad_tcp_binds = 0
    num_good_udp_binds = 0
    num_bad_udp_binds = 0
    dest_portnum = '0'

    for port in tcp_port_list:
        time.sleep(1)

        ds = ("0.0.0.0", port)
        logger.info("Attempting to bind to tcp port: " + str(port))

        try:

            tcpservers.append(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            tcpservers[-1].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcpservers[-1].bind(ds)
            tcpservers[-1].listen(10)
            logger.info('Successfully bound to tcp port: ' + str(port))
            num_good_tcp_binds += 1

        except socket.error , msg:
            logger.warn( 'Could not bind to tcp port ' + str(port) + " Error Code : " + str(msg[0]) + " Message " + msg[1])
            num_bad_tcp_binds += 1
            if tcpservers[-1]:
                tcpservers[-1].close()
                tcpservers = tcpservers[:-1]

    logger.info("Successful tcp port binds: " + str(num_good_tcp_binds) + ", Unsuccessful tcp port binds: " + str(num_bad_tcp_binds))

    for port in udp_port_list:
        time.sleep(1)

        ds = ('',port)
        logger.info("Attempting to bind to udp port: " + str(port))

        try:
            udpservers.append(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
            udpservers[-1].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udpservers[-1].bind(ds)
            logger.info('Successfully bound to udp port: ' + str(port))
            num_good_udp_binds += 1

        except socket.error , msg:
            logger.warn( 'Could not bind to udp port ' + str(port) + " Error Code : " + str(msg[0]) + " Message " + msg[1])
            num_bad_udp_binds += 1
            if udpservers[-1]:
                udpservers[-1].close()
                udpservers = udpservers[:-1]

    logger.info("Successful udp port binds: " + str(num_good_udp_binds) + ", Unsuccessful udp port binds: " + str(num_bad_udp_binds))

    while splunk_is_still_running:
        try:
            inputready, outputready, exceptready = select.select(tcpservers, [], [],10)
        except select.error, e:
            logger.warn("Select error: " + e)

           #logger.info("done with select statement")

        for conn in inputready:
            for tcp_item in tcpservers:
                if conn == tcp_item:
                    #logger.info("in tcp try loop")
                    connection, address = conn.accept()
                    parse_tcp_connection(address,connection.getsockname())
                    if tcp_item.getsockname()[1]:
                        if len(str(tcp_item.getsockname()[1])) > 0:
                                dest_portnum = str(tcp_item.getsockname()[1])
                    handle_tcp_accept(connection,dest_portnum)
                    connection.close()

        try:
            inputready, outputready, exceptready = select.select(udpservers, [], [],10)
        except select.error, e:
            logger.warn("Select error: " + e)

        for conn in inputready:
            for udp_item in udpservers:
                if conn == udp_item:

                    if udp_item.getsockname()[1]:
                        if len(str(udp_item.getsockname()[1])) > 0:
                            dest_portnum = str(udp_item.getsockname()[1])
                    handle_udp_accept(conn,dest_portnum)

    return 0

if __name__ == '__main__':
   main()


#EOF
