# Copyright 2014-2015 ITrust SAS.  All rights reserved.

# This software is provided by ITrust on
# an "as is" basis and any express or implied warranties, including but
# not limited to the implied warranties of merchantability and fitness
# for a particular purpose, are disclaimed in all aspects.  In no event
# will ITrust be liable for any direct, indirect, special, incidental
# or consequential damages relating to the use of this software, even if
# advised of the possibility of such damage.

# Reveelium Splunkapps
# Author: Sebastin Aucouturier
# Support: support@itrust.fr
# Last updated: 2015-07-17

import sys
import os
import splunk
import splunk.search
import splunk.bundle
import splunk.auth
import socket
import StringIO
import iso8601
import traceback
# classes for interaction with API de itt_client to send chunks
from itt.models.chunk import Chunk
from itt.restapi.client import APIStore
from logger import Logger
# classes for interaction with API de itt_client to send chunks
from itt.storage.store import (
    StoreAuthenticationError, StoreConnectionError, StoreDataValidationError,
    StoreError, StoreInternalError, StoreTimeout
    )

# URL where to send chunks
API_URL = "http://127.0.0.1/api/v1"
MAX_PERIOD = 600
log = Logger("/log/logs.txt")
bin_dir = os.path.dirname(os.path.join(os.getcwd(), __file__))
local_dir = os.path.normpath(os.path.join(bin_dir, "..", "local"))


# method to convert result date from search in splunk to seconds
def iso8601_to_epoch(datestr):
    return str(iso8601.parse(datestr))


def epoch_to_iso8601(epoch):
    return iso8601.tostring(epoch)


# Method to send the log to the API of itt_client
def send_log(log_type, url, username, password, started_at, ended_at, content):
    with APIStore(url, username, password) as store:
        started_at = epoch_to_iso8601(started_at)
        ended_at = epoch_to_iso8601(ended_at)

        try:
            chunk = Chunk(logtype=log_type, started_at=started_at, ended_at=ended_at)
            store.save(chunk)
            socket.setdefaulttimeout(240)
            log.write_to_log(log.INFO, "Preparing to upload chunk: Type %s started at %s, ended at %s" % (log_type, started_at, ended_at))
            store.log_upload(content, chunk)
            log.write_to_log(log.INFO, "send_log: 'Done uploading chunk. Chunk state: %s Chunk Size: %i" % (chunk.state, chunk.size))
            del store
            del chunk

        except StoreAuthenticationError, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
            log.write_to_log(log.ERROR, "Authentication error trying to access API: %s %s"
                                        % (error, e.message, '\n'.join(traceback.format_exc().splitlines())))
        except StoreConnectionError, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
            log.write_to_log(log.ERROR, "Error with the Store Connection: %s %s"
                                        % (error, e.message, '\n'.join(traceback.format_exc().splitlines())))
        except StoreDataValidationError, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
            log.write_to_log(log.ERROR, "Store Data Validation Error: %s %s"
                                        % (error, e.message, '\n'.join(traceback.format_exc().splitlines())))
        except StoreTimeout, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
            log.write_to_log(log.ERROR, "Time out for store: %s %s"
                                        % (error, e.message, '\n'.join(traceback.format_exc().splitlines())))
        except StoreError, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
            log.write_to_log(log.ERROR, "Store Error: %s %s"
                                        % (error, e.message, '\n'.join(traceback.format_exc().splitlines())))
        except StoreInternalError, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
            log.write_to_log(log.ERROR, "Store Internal Error:  %s %s"
                                        % (error, e.message, '\n'.join(traceback.format_exc().splitlines())))
        except StoreTimeout, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
            log.write_to_log(log.ERROR, "Unknown Error:  %s %s"
                                        % (error, e.message, '\n'.join(traceback.format_exc().splitlines())))
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
            log.write_to_log(log.ERROR, "Error with the Store Connection:  %s %s %s"
                                        % (error, e.message, '\n'.join(traceback.format_exc().splitlines())))


# method to retrieve conf
def get_conf(conf):
    aTypeList = ['bind', 'ms', 'custom', 'proxy']
    sourcetypes_list = conf['sourcetypes_list']
    if not sourcetypes_list:
        return
    split = sourcetypes_list.split("**")
    conf_list = []
    for item in split:
        element = item.split("*")

        if len(element) == 3:
            aType = aTypeList[int(element[1])]
            aTypeNb = '_'.join([element[0], aType])

            index_time = 'indextime_' + aTypeNb
            index_type = 'sourcetype_' + aTypeNb
            index_index = 'index_' + aTypeNb

            conf_tuple = (aType, index_type, index_index, index_time)
            conf_list.append(conf_tuple)
    return conf_list


# method to get last stored value itime
def get_current_itime(source_type, index_name, last_itime, session_key):
    query = ('search index="%s" sourcetype="%s" _indextime >= %s | sort - _indextime | head 1') % (index_name, source_type, last_itime)
    job = splunk.search.dispatch(query, sessionKey=session_key)
    current_itime = None
    for result in job.results:
        try:
            current_itime = int(result["_indextime"][0].getValue())
        except:
            pass
        break
    return current_itime


# method to retrieve dns logs
def retrieve_dns_logs(conf, session_key, index_type, index_index, index_time):
    log.write_to_log(log.INFO, "Retrieve_dns_logs")
    try:
        source_type = conf.get(index_type, "")
        index_name = conf.get(index_index, "")
        last_itime = int(conf.get(index_time, "0"))

        current_itime = get_current_itime(source_type, index_name, last_itime, session_key)


        # last_itime - current itime: time period to process.
        # Don't process more than some reasonable amount
        if current_itime is not None:
            if current_itime - last_itime > MAX_PERIOD:
                last_itime = current_itime - MAX_PERIOD

            query = ('search index="%s" sourcetype="%s" _indextime>=%s _indextime<%s | fields + _time, src_ip,dest_host,query_type') % (index_name, source_type, last_itime, current_itime)
            log.write_to_log(log.INFO, "* query: %s" % (query))
            job = splunk.search.dispatch(query, sessionKey=session_key)

            try:
                output = StringIO.StringIO()
                count = 0
                for result in job.results:
                    try:
                        query_type = ""
                        ip = ""
                        dest_host = ""
                        date_iso8601 = result['_time'][0].getValue()
                        epoch_iso8601 = iso8601_to_epoch(date_iso8601)
                        query_type = result['query_type'][0].getValue().strip()
                        dest_host = result['dest_host'][0].getValue().strip()
                        ip = result['src_ip'][0].getValue().strip()
                    except Exception, e:
                        continue
                    if query_type and dest_host and ip:
                        count += 1
                        content = ','.join([epoch_iso8601, dest_host, query_type, ip])
                        content += '\n'
                        output.write(content)

                result_content = output.getvalue()
                output.close()
                if count > 0:
                    urlapi = conf.get('urlapi', 'http://127.0.0.1')
                    user = conf.get('user', '')
                    password = conf.get('password', '')
                    url = ''.join([urlapi, '/api/v1'])
                    send_log("dns", url, user, password, last_itime, current_itime, result_content.encode('utf8'))

            except Exception, e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
                log.write_to_log(log.ERROR, "Retrieve_dns_logs: " + error + " " + e.message + '\n'.join(traceback.format_exc().splitlines()))

            conf[index_time] = current_itime

    except Exception, e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
        log.write_to_log(log.ERROR, "Main code: " + error + "  " + e.message)


# method to retrieve proxy logs
def retrieve_proxy_logs(conf, session_key, index_type, index_index, index_time):
    log.write_to_log(log.INFO, "Retrieve_proxy_logs")
    try:
        source_type = conf.get(index_type, "")
        index_name = conf.get(index_index, "")
        last_itime = int(conf.get(index_time, "0"))
        current_itime = get_current_itime(source_type, index_name, last_itime, session_key)


        if current_itime is not None:
            # last_itime - current itime: time period to process.
            # Don't process more than some reasonable amount
            if current_itime - last_itime > MAX_PERIOD:
                last_itime = current_itime - MAX_PERIOD

            query = ('search index="%s" sourcetype="%s" _indextime>=%s _indextime<%s | fields + _time,time_taken,src,user,query,http_referer,http_user_agent,bytes_in,status,bytes_out') % (index_name, source_type, last_itime, current_itime)
            job = splunk.search.dispatch(query, sessionKey=session_key)
            count = 0

            try:
                output = StringIO.StringIO()
                for result in job.results:
                    try:
                        time_taken = "0"
                        c_ip = ""
                        cs_user = ""
                        cs_uri = ""
                        referer = ""
                        user_agent = ""
                        cs_bytes = "0"
                        sc_status = ""
                        sc_bytes = "0"

                        date_iso8601 = result['_time'][0].getValue()
                        epoch_iso8601 = iso8601_to_epoch(date_iso8601)
                        time_taken = result["time_taken"][0].getValue().strip()
                        c_ip = '"%s"' % result["src"][0].getValue().strip()
                        cs_user = '"%s"' % result["user"][0].getValue().strip()
                        cs_uri = '"%s"' % result["query"][0].getValue().strip()
                        referer = '"%s"' % result["http_referer"][0].getValue().strip()
                        user_agent = '"%s"' % result["http_user_agent"][0].getValue().strip()
                        cs_bytes = result["bytes_in"][0].getValue().strip()
                        sc_status = result["status"][0].getValue().strip()
                        sc_bytes = result["bytes_out"][0].getValue().strip()
                    except:
                        continue

                    if cs_uri and c_ip:
                        count += 1
                        content = ','.join([epoch_iso8601, time_taken, c_ip, cs_user, cs_uri, referer, user_agent, cs_bytes, sc_status, sc_bytes])
                        content += '\n'
                        output.write(content)

                result_content = output.getvalue()
                output.close()
                if count > 0:
                    urlapi = conf.get('urlapi', 'http://127.0.0.1')
                    user = conf.get('user', '')
                    password = conf.get('password', '')
                    url = ''.join([urlapi, '/api/v1'])
                    send_log("proxy", url, user, password, last_itime, current_itime, result_content.encode('utf8'))

            except Exception, ex:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
                    log.write_to_log(log.ERROR, "retrieve proxy logs" + error + " " + ex.message)

            conf[index_time] = current_itime

    except Exception, e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
        log.write_to_log(log.ERROR, "Main code: " + error + " " + e.message)


def main():
    # getting session key from splunk
    if len(sys.argv) > 1:
        session_key = splunk.auth.getSessionKey(sys.argv[1], sys.argv[2])
    else:

        # normally, the script is called by splunk and session key is passed
        # in stdin
        session_key = sys.stdin.readline()

    conf = splunk.bundle.getConf('it_tude', session_key, 'it_tude', owner='nobody')['config']

    # checking if credentials are present. If not we stop
    if (conf['user'] is None) or (not conf['user']) or (conf['password'] is None) or (not conf['password']):
        log.write_to_log(log.ERROR, "Invalid username and password. Impossible to process logs - %s %s" % (conf['user'], conf['password']))
        return

    conf_list = get_conf(conf)
    for item in conf_list:
            aType, index_type, index_index, index_time = item
            if aType == "proxy":
                retrieve_proxy_logs(conf, session_key, index_type, index_index, index_time)
            else:
                retrieve_dns_logs(conf, session_key, index_type, index_index, index_time)

# main stream
try:
    log.write_to_log(log.DEBUG, "start")
    main()
    log.write_to_log(log.DEBUG, "finish")

except Exception, e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    error = 'Type: %s FileName: %s Line: %s' % (exc_type, fname, exc_tb.tb_lineno)
    log.write_to_log(log.ERROR, "Main code: " + error + " " + e.message)
