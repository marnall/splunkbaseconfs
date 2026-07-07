#!/usr/bin/python

import configparser
import csv
import inspect
import logging
import os
import shutil
import subprocess  # nosec
import threading
import time
from datetime import datetime
from functools import partial
from io import open
from multiprocessing.pool import ThreadPool

import requests
import splunk_helper
from tripwire import ReportData, is_windows, make_sure_path_exists, check_te_connection, pyDes_decrypt
from tripwire_logging import setup_logger
from tripwire_multiprocess import CompressedCache, LargeResults, get_pages


logger = logging.getLogger('tripwire')
node_types_by_name = {}
attributes_by_version = CompressedCache()


class TimeoutException(Exception):
    pass


def fim_thread_func(report_data, version):
    api = report_data.api
    v = version
    attrs = attributes_by_version.get(v['id'])
    if not attrs:
        try:
            attrs = api.get('versions/%s/attributes' % v['id'])
        except requests.exceptions.HTTPError:
            attrs = {}
        attributes_by_version[v['id']] = attrs
    # This could be its own baseline,
    # so don't check the cache until now
    baseline_attrs = attributes_by_version.get(v['baselineVersion'], {})
    if v['baselineVersion'] and not baseline_attrs:
        try:
            baseline_attrs = api.get('versions/%s/attributes' % v['baselineVersion'])
        except requests.exceptions.HTTPError:
            baseline_attrs = {}
        attributes_by_version[v['baselineVersion']] = baseline_attrs
    attributes = []
    # NOTE: converting attrs.items() to list(attrs.items()) is unnecessary. Only making this change to silence
    # Splunk app readiness warnings
    for name, props in list(attrs.items()):
        attributes.append(
            'Name="%s",Expected="%s",Observed="%s"'
            % (name, baseline_attrs.get(name, {}).get('value', ''), props['value'])
        )
    audit = api.get('versions/%s/audit' % v['id'])
    username = ''
    if audit:
        username = audit[0].get('username', '')
    return [
        u.encode('utf-8')
        for u in [
            v['nodeName'],
            node_types_by_name.get(v['nodeName'], ''),
            v['ruleName'],
            v['elementName'],
            report_data.isodatetime_to_visible(v['timeReceived']),
            v['changeType'].title(),
            report_data.get_severity_range_name(v['severity']),
            str(v['severity']),
            str(v['approvalId']),
            username,
            ";\r\n".join(attributes),  # Attributes
            '',  # Content, this doesn't ever seem to actually be used
        ]
    ]


class FIM(ReportData):
    def __init__(self, *args, **kwargs):
        self.show_cont_diff = kwargs.pop('show_cont_diff', False)
        self.compare_prev_version = kwargs.pop('compare_prev_version', False)
        self.timeout = kwargs.pop('fim_timeout', 59)
        super().__init__(*args, **kwargs)

    def run_with_timeout(self, cmd):
        process = [None]

        def report_run():
            process[0] = subprocess.Popen(cmd)  # nosec
            process[0].communicate()

        thread = threading.Thread(target=report_run)
        thread.start()
        thread.join(self.timeout * 60)
        if thread.is_alive():
            process[0].terminate()
            thread.join()
            raise TimeoutException()

    def do_soap(self, file_name, timestamp_file):
        time_interval = self.interval
        show_content_param = ''
        compare_prev_version_param = ''
        unit = self.unit
        units = self.units
        if self.show_cont_diff:
            show_content_param = ',showContentDiff,true'
        if self.compare_prev_version:
            compare_prev_version_param = (
                ':SelectCriterion,versionCompare,versionCompare,all'
            )
        if not os.path.exists(timestamp_file):
            if self.first_run:
                unit = 'day'
                units = 'day'
                time_interval = self.hist_days
            report_params = (
                'BooleanCriterion,currentVersionsOnly,false'
                ',displayUsers,true'
                ',displayCriteriaAtEnd,true'
                '%s'
                '%s'
                ':RelativeTimeRangeCriterion'
                ',%s,%s'
                ',"In the last %s %s"'
                % (
                    show_content_param,
                    compare_prev_version_param,
                    time_interval,
                    unit,
                    units,
                    time_interval,
                )
            )
        elif os.path.exists(timestamp_file):
            with open(timestamp_file) as f:
                timestamp = f.readlines()[0].split(',')
            report_params = (
                'BooleanCriterion,currentVersionsOnly,false'
                ',displayUsers,true'
                ',displayCriteriaAtEnd,true'
                '%s'
                '%s'
                ':AbsoluteTimeRangeCriterion'
                ',%s'
                ',"No earlier than %s"'
                % (
                    show_content_param,
                    compare_prev_version_param,
                    timestamp[1],
                    timestamp[0].replace(':', '-'),
                )
            )
        args = [self.script_start] + self.python_cmd.split(' ') + [self.script_loc]
        if not self.te_sslverify:
            args.append('-k')  # insecure, don't validate TE certificates
        args += [
            '-s',
            self.ip_address,
            '-u',
            self.username,
            '-p',
            self.password,
            'report',
            '-T',
            'DCR',
            '-t',
            'detailedchanges_rpt',
            '-P',
            report_params,
            '-F',
            'CSV',
            '-o',
            file_name,
        ]
        self.run_with_timeout([a for a in args if a])

    def do_rest(self, file_name):
        pool = ThreadPool(processes=self.num_threads)
        since = self.get_since_datetime()
        now = datetime.utcnow()
        nodes = self.api.get_pages('nodes')
        for node in nodes:
            node_types_by_name[node['name']] = node['type']
        logger.info('Got %d nodes', len(nodes))

        with open(file_name, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    'Node Name',
                    'Node Type',
                    'Rule Name',
                    'Element Name',
                    'Version Time',
                    'Change Type',
                    'Severity Name',
                    'Severity',
                    'Approval ID',
                    'Users',
                    'Attributes',
                    'Content',
                ]
            )

            with LargeResults(
                'versions',
                self.cachedir,
                permanent=False,
                timestamp_field='timeReceived',
            ) as versions:
                # If we have cached results, only retrieve newer results
                if versions.last_dt and versions.last_dt > since:
                    since = versions.last_dt
                time_received_range = self.api.make_date_range(since, now)
                get_pages(
                    self,
                    versions,
                    pool,
                    'versions',
                    {'timeReceivedRange': time_received_range},
                    dupe_params=[
                        {'changeType': 'Added'},
                        {'changeType': 'Removed'},
                        {'changeType': 'Modified'},
                    ],
                    timestamp_field='timeReceived',
                    end_time=now,
                    range_param='timeReceivedRange',
                )
                if not versions.num_results:
                    return
                # The REST API only allows you to filter severity by
                # 1 severity at a time, I would have to add 10k severity params
                # just to exclude severity 0.  For now, I'll filter out in the
                # code, but lets hope there aren't a bunch of severity 0
                # changes in TE.
                # versions is a generator, it is important to use a
                # generator expression here so as to not blow up memory
                versions = (v for v in versions if v['severity'] != 0)
                with open(os.path.join(self.cachedir, 'fim.csv'), 'w') as ffim:
                    csv_writer = csv.writer(
                        ffim, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL
                    )
                    func = partial(fim_thread_func, self)
                    num_results = 0
                    curr_results = 0
                    started_time = time.time()
                    for result in pool.imap_unordered(func, versions, 100):
                        if result:
                            writer.writerow([res.decode('utf-8') for res in result])
                        if logger.level >= logging.DEBUG:
                            num_results += 1
                            curr_results += 1
                            if curr_results > 1000:
                                elapsed = time.time() - started_time
                                csv_writer.writerow(
                                    [num_results, elapsed, num_results / elapsed]
                                )
                                curr_results = 0


def main():
    setup_logger()
    logger.info('tripwire_fim.py starting')
    session_token = splunk_helper.token_from_stdin()

    # get path of app
    cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    addon_path = os.path.split(os.path.split(cwd)[0])
    app = addon_path[1]
    first_run_file = os.path.join(cwd, 'firstrun_fim.txt')

    # ensure there is access to working directory
    subprocess.check_output('cd .', shell=True)  # nosec

    cfg = configparser.ConfigParser()
    configpath = os.path.join(os.path.split(cwd)[0], 'local', 'te_setup.conf')
    cfg.read(configpath, encoding="utf-8-sig")

    # gather parameters for command line call to Tripwire
    username = cfg.get('te_parameters', 'te_username', fallback='')
    ip_address = cfg.get('te_parameters', 'workflow_host', fallback='127.0.0.1')  # default/te_setup.conf uses 0.0.0.0
    directory = cfg.get('te_parameters', 'data_location', fallback='/opt/teexports')
    unit = cfg.get('te_parameters', 'fim_unit', fallback='hour')
    interval = cfg.get('te_parameters', 'fim_int_saved', fallback='1')
    hist_days = cfg.get('te_parameters', 'hist_days', fallback='14')
    show_cont_diff = cfg.get('te_parameters', 'showContentDiff', fallback='1') == '1'
    compare_prev_version = (
        cfg.get('te_parameters', 'compare_prev_version', fallback='0') == '1'
    )
    fim_use_rest = cfg.get('te_parameters', 'fim_use_rest', fallback='0') == '1'
    fim_timeout = int(cfg.get('te_parameters', 'fim_timeout', fallback=59))
    te_sslverify = cfg.get('te_parameters', 'te_sslverify', fallback='0') == '1'
    num_threads = int(cfg.get('te_parameters', 'fim_rest_threads', fallback=1))

    # make sure data directory exists
    save_dir = os.path.join(directory, 'FIM')
    tmp_dir = os.path.join(save_dir, 'tmp')
    make_sure_path_exists(save_dir)
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    make_sure_path_exists(tmp_dir)
    cache_dir = os.path.join(save_dir, 'cache')
    make_sure_path_exists(cache_dir)
    timestamp_file = os.path.join(save_dir, 'fim_timestamp.txt')

    first_run = not os.path.exists(first_run_file)
    if first_run:
        logger.info('Doing first run')

    # Decrypt Password
    pm = splunk_helper.PasswordManager(auth_token=session_token)
    password = pm.get_password(username=username)
    if not password:  # if password is an empty string, fallback to DES password
        password = cfg.get("te_parameters", "te_pass", fallback="")
        password = pyDes_decrypt(password)

    check_te_connection(ip_address, username, password, te_sslverify, logger)

    # setup file names for command line call
    save_dir = os.path.join(directory, 'FIM')
    tmp_dir = os.path.join(save_dir, 'tmp')
    file_append = '-hist' if first_run else ''
    file_name = os.path.join(tmp_dir, 'DCR%s.csv' % file_append)

    homepath = os.environ.get("SPLUNK_HOME")
    script_loc = os.path.join(homepath, 'etc', 'apps', app, 'bin', 'tripwire.py')
    script_start = 'splunk'
    if not is_windows():
        homepath = os.environ.get("SPLUNK_HOME")
        script_start = os.path.join(homepath, 'bin', 'splunk')

    fim = FIM(
        ip_address,
        username,
        password,
        fim_timeout=fim_timeout,
        script_loc=script_loc,
        unit=unit,
        first_run=first_run,
        show_cont_diff=show_cont_diff,
        compare_prev_version=compare_prev_version,
        hist_days=hist_days,
        interval=interval,
        script_start=script_start,
        python_cmd='cmd python',
        num_threads=num_threads,
        cachedir=cache_dir,
        te_sslverify=te_sslverify,
    )

    # Only TE 8.5.1 supports a severityRange call we need to make.
    # Only TE 8.5.2 has a fixed versions/attributes API call fix
    # WARNING: There is no way to get content diffs via the REST API.
    if fim_use_rest and fim.te_version_check('8.5.2'):
        logger.info("Starting REST API retrieval with %d threads", num_threads)
        fim.do_rest(file_name)
    else:
        if fim_use_rest:
            logger.info(
                "TE version must be at least 8.5.2 to use the REST API "
                "for FIM.  Falling back to SOAP."
            )
        logger.info("Starting SOAP API retrieval")
        try:
            fim.do_soap(file_name, timestamp_file)
        except TimeoutException:
            logger.error("SOAP API retrieval timed out after %s minute(s)", fim_timeout)
    fim.save(tmp_dir, save_dir, first_run_file)
    logger.info("Retrieval complete.")


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logger.exception("Exception in tripwire_fim.py")
