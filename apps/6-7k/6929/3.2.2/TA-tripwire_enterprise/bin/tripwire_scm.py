#!/usr/bin/python

import configparser
import csv
import inspect
import logging
import os
import shutil
import subprocess  # nosec
import time
from datetime import datetime, timedelta
from functools import partial
from io import open
from multiprocessing.pool import ThreadPool
from urllib.parse import quote_plus

import requests
import splunk_helper
from tripwire import ReportData, is_windows, make_sure_path_exists, check_te_connection, pyDes_decrypt
from tripwire_logging import setup_logger
from tripwire_multiprocess import CompressedCache, LargeResults, get_pages
from tripwire_rest_api import TEV1RestAPI

scm_watermark_file = 'scm_timestamp.txt'
logger = logging.getLogger('tripwire')
test_cache = CompressedCache()
test_group_cache = CompressedCache()
waiver_cache = CompressedCache()
nodes_by_id = CompressedCache()


def get_waiver_key(policy_id, policy_test_id, node_id):
    return '%s:%s:%s' % (policy_id, policy_test_id, node_id)


def get_is_waivered(policy_id, policy_test_id, node_id, creation_time):
    key = get_waiver_key(policy_id, policy_test_id, node_id)
    creation_dt = ReportData.isodatetime_to_datetime(creation_time)
    waivers = waiver_cache.get(key, [])
    for waiver in waivers:
        end_dt = ReportData.isodatetime_to_datetime(waiver['expiration'])
        if not end_dt or creation_dt < end_dt:
            return True
    return False


def node_thread_func(report_data, node):
    # parentGroups may be scoped to a policy, rather than a node
    # an example being the CentOS 6 Smart Node Group
    parent_groups = []
    try:
        url = 'nodes/%s/parentGroups' % quote_plus(node['id'])
        parent_groups = report_data.api.get(url)
    except:
        logger.info('Unable to find parentGroups for node: %s', url)
    parent_group_ids = set()
    for parent_group in parent_groups:
        for path in parent_group['path']:
            parent_group_ids.add(path['id'])
    return node['id'], parent_group_ids


def scm_thread_func(
    policy_nodes, exclude_waivered, detailed_attributes, report_data, testresult
):
    api = report_data.api
    t = testresult
    node = nodes_by_id.get(t['nodeId'], {})

    # A new node might have appeared with test results that we didn't see
    # when this script first started
    if not node:
        logger.info('Found new node: %s' % t['nodeId'])
        try:
            node = api.get('nodes/%s' % quote_plus(t['nodeId']))
        except requests.exceptions.HTTPError:
            logger.error('Unable to find node: %s' % t['nodeId'])
            return []
        logger.info('Got node')
        node_id, parent_group_ids = node_thread_func(report_data, node)
        node['parent_group_ids'] = parent_group_ids
        nodes_by_id[node_id] = node

    if not t['policyTestId'] in test_cache:
        try:
            test_cache[t['policyTestId']] = api.get(
                'policytests/%s' % quote_plus(t['policyTestId'])
            )
        except requests.exceptions.HTTPError:
            test_cache[t['policyTestId']] = {}
    if not t['policyTestId'] in test_group_cache:
        try:
            test_group_cache[t['policyTestId']] = api.get(
                'policytests/%s/parentGroups' % quote_plus(t['policyTestId'])
            )
        except requests.exceptions.HTTPError:
            test_group_cache[t['policyTestId']] = []

    policy_test = test_cache.get(t['policyTestId'], {})
    test_group = test_group_cache.get(t['policyTestId'], [])
    policy_name = ''
    policy_id = -1
    parent_test_groups = []
    # A single policyTestResult can have multiple test groups
    # depending on which policies apply to the node
    for path in [p['path'] for p in test_group]:
        for group in path:
            if group.get('type') == 'Policy':
                policy_id = group.get('id')
                pn = policy_nodes.get(policy_id, {})
                node_id = node.get('id')
                parent_scope = [
                    scope_id
                    for scope_id in pn.get('nodeScope', [])
                    if scope_id in node['parent_group_ids']
                ]
                if parent_scope or node_id in pn.get('nodeScope', []):
                    policy_name = group.get('name', '')
                    break
        if policy_name:
            parent_test_group_name = path[-1].get('name', '')
            parent_test_groups.append((policy_id, policy_name, parent_test_group_name))
            policy_name = ''

    results = []
    for policy_id, policy_name, parent_test_group_name in parent_test_groups:
        is_waivered = get_is_waivered(
            policy_id, t['policyTestId'], t['nodeId'], t['creationTime']
        )
        if exclude_waivered and is_waivered:
            logger.debug(
                'Excluding waivered for policyTestId %s, nodeId %s, creationTime: %s',
                t['policyTestId'],
                t['nodeId'],
                t['creationTime'],
            )
            continue
        node_attributes = ''
        if detailed_attributes:
            # there are 3 different possible system tagsets in TE
            system_attributes = [
                'Operating System',
                'Virtual Infrastructure',
                'Database Server',
            ]
            for item in node.get('tags'):
                if item.get('tagset') in system_attributes and 'SYSTEM' in item.get(
                    'type'
                ):
                    node_attributes = item.get('tag')

        results_data = [
            u.encode('utf-8')
            for u in [
                node.get('name', ''),
                node.get('type', ''),
                policy_name,
                parent_test_group_name,
                t['policyTestName'],
                str(policy_test.get('severity', -1)),
                'Yes' if is_waivered else 'No',
                policy_test.get('description', ''),
                t['elementName'],
                report_data.isodatetime_to_visible(t['creationTime']),
                str(t['state'].lower()),
                t['actual'],
            ]
        ]
        if detailed_attributes:
            results_data.insert(2, node_attributes.encode('utf-8'))
        results.append(results_data)
    return results


class SCM(ReportData):
    def get_report_params_from_watermark(self, watermark_full_path):
        with open(watermark_full_path) as f:
            timestamp = f.readlines()[0].split(',')
            logger.info(timestamp)
        report_params = (
            'BooleanCriterion,lastTestResultsOnly,true'
            ',displayActualTestResults,true'
            ',displayRemediation,false'
            ',displayWeights,true'
            ',displayCriteriaAtEnd,true'
            ':AbsoluteTimeRangeCriterion'
            ',%s'
            ',"No earlier than %s"'
            
            %(
                timestamp[1],
                timestamp[0].replace(':', '-')
            )
            #
            #
            #%('1583107304','3/2/20 3-43 PM')
        )
        return report_params


    def get_report_params_without_watermark(self):
        time_interval = self.interval
        unit = self.unit
        units = self.units
        if self.first_run:
            unit = 'day'
            units = 'day'
            time_interval = self.hist_days
        report_params = (
            'BooleanCriterion,lastTestResultsOnly,true'
            ',displayActualTestResults,true'
            ',displayRemediation,false'
            ',displayWeights,true'
            ',displayCriteriaAtEnd,true'
            ':RelativeTimeRangeCriterion'
            ',%s,%s'
            ',"In the last %s %s"' % (time_interval, unit, units, time_interval)
        )
        return report_params
    
    def do_soap(self, file_name, save_dir):
        watermark_full_path = os.path.join(save_dir, scm_watermark_file)
        #logger.info(watermark_full_path)
        #logger.info(save_dir)
        #logger.info(scm_watermark_file)
        if os.path.exists(watermark_full_path):
            report_params = self.get_report_params_from_watermark(watermark_full_path)
        else:
            logger.info("no watermark")
            report_params = self.get_report_params_without_watermark()
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
            'DTR',
            '-t',
            'detailedtestresults_rpt',
            '-P',
            report_params,
            '-F',
            'CSV',
            '-o',
            file_name,
        ]
        subprocess.check_call([a for a in args if a], encoding="utf-8")  # nosec

    def do_rest(
        self,
        file_name,
        policy_names=None,
        exclude_waivered=False,
        detailed_attributes=False,
    ):
        api = TEV1RestAPI(self.ip_address, self.username, self.password, verify_ssl_cert=self.te_sslverify)
        since = self.get_since_datetime()
        now = datetime.utcnow()
        pool = ThreadPool(processes=self.num_threads)
        nodes = api.get_pages('nodes')
        logger.info('Got %d nodes', len(nodes))
        for node in nodes:
            nodes_by_id[node['id']] = node

        # Get all the parentGroups for these nodes, so we can determine which
        # policies apply to them later
        func = partial(node_thread_func, self)
        for node_id, parent_group_ids in pool.imap_unordered(func, nodes):
            node = nodes_by_id[node_id]
            node['parent_group_ids'] = parent_group_ids
            nodes_by_id[node_id] = node

        # Should this be a CompressedCache?
        policy_nodes = {}
        dupe_params = []
        if policy_names:
            dupe_params = [{'name': name} for name in policy_names]
        with LargeResults('policies', self.cachedir) as policies:
            get_pages(self, policies, pool, 'policies', {}, dupe_params)
            if not policies.num_results:
                return False
            for p in policies:
                policy_nodes[p['id']] = p

        with LargeResults('waivers', self.cachedir) as waivers:
            get_pages(self, waivers, pool, 'waivers', {'closed': False}, [])
            for waiver in waivers:
                for waived_test in waiver['waivedTests']:
                    key = get_waiver_key(
                        waiver['policyId'],
                        waived_test['policyTestId'],
                        waived_test['nodeId'],
                    )
                    if key not in waiver_cache:
                        waiver_cache[key] = []
                    w = waiver_cache[key]
                    w.append(
                        {
                            'startTime': waiver['startTime'],
                            'expiration': waiver.get('expiration', ''),
                        }
                    )
                    waiver_cache[key] = w

        # get list of policy ids
        # get list of policytests with policy ids
        # get list of policyTestResults based on policytest ids
        # NOTE: Wrapping keys() in list() is unnecessary. Doing it to silence Splunk warnings
        dupe_params = [{'policyId': policy_id} for policy_id in list(policy_nodes.keys())]
        with LargeResults('policytests', self.cachedir) as policytests:
            get_pages(self, policytests, pool, 'policytests', {}, dupe_params)
            if not policytests.num_results:
                return False
            # We're retrieving policy tests now, might as well cache them
            local_policy_test_ids = set()
            dupe_params = []
            for policy_test in policytests:
                test_cache[policy_test['id']] = policy_test
                if policy_test['id'] not in local_policy_test_ids:
                    dupe_params.append({'policyTestId': policy_test['id']})
                    local_policy_test_ids.add(policy_test['id'])

        with LargeResults(
            'testresults',
            self.cachedir,
            permanent=False,
            timestamp_field='creationTime',
            newer_only=not self.do_daily_reindex,
        ) as testresults:
            # If we have cached results, only retrieve newer results
            if (
                not self.do_daily_reindex
                and testresults.last_dt
                and testresults.last_dt > since
            ):
                since = testresults.last_dt + timedelta(seconds=1)
            # Time range extends 10 days into the future to ensure we grab
            # test results if new ones occur while this script is running
            time_received_range = self.api.make_date_range(
                since, now + timedelta(days=10)
            )
            params = {'creationTimeRange': time_received_range}
            get_pages(
                self, testresults, pool, 'policytestresults/latest', params, dupe_params
            )

            with open(file_name, 'w') as f:
                writer = csv.writer(f)
                field_labels = [
                    'Node Name',
                    'Node Type',
                    'Policy',
                    'Parent Test Group',
                    'Test Name',
                    'Severity',
                    'IsWaivered',
                    'Description',
                    'Element',
                    'Result Time',
                    'Result State',
                    'Actual Value',
                ]
                if detailed_attributes:
                    field_labels.insert(2, 'Node Attributes')
                writer.writerow(field_labels)
                if not testresults.num_results:
                    return
                with open(os.path.join(self.cachedir, 'scm.csv'), 'w') as fscm:
                    csv_writer = csv.writer(
                        fscm, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL
                    )
                    func = partial(
                        scm_thread_func,
                        policy_nodes,
                        exclude_waivered,
                        detailed_attributes,
                        self,
                    )
                    num_results = 0
                    curr_results = 0
                    started_time = time.time()
                    for result in pool.imap_unordered(func, testresults, 100):
                        for row in result:
                            writer.writerow([res.decode('utf-8') for res in row])
                        if logger.level >= logging.DEBUG:
                            num = len(result)
                            num_results += num
                            curr_results += num
                            if curr_results > 1000:
                                elapsed = time.time() - started_time
                                csv_writer.writerow(
                                    [num_results, elapsed, num_results / elapsed]
                                )
                                curr_results = 0
        return True


def main():
    setup_logger()
    logger.info('tripwire_scm.py starting')
    session_token = splunk_helper.token_from_stdin()

    # get path of app
    cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    addon_path = os.path.split(os.path.split(cwd)[0])
    app = addon_path[1]
    first_run_file = os.path.join(cwd, 'firstrun_scm.txt')

    # ensure there is access to working directory
    subprocess.check_output('cd .', shell=True)  # nosec

    cfg = configparser.ConfigParser()
    configpath = os.path.join(os.path.split(cwd)[0], 'local', 'te_setup.conf')
    cfg.read(configpath, encoding="utf-8-sig")

    # gather parameters for command line call to Tripwire
    username = cfg.get('te_parameters', 'te_username')
    ip_address = cfg.get('te_parameters', 'workflow_host', fallback='127.0.0.1')  # default/te_setup.conf uses 0.0.0.0
    directory = cfg.get('te_parameters', 'data_location', fallback='/opt/teexports')
    unit = cfg.get('te_parameters', 'scm_unit', fallback='day')
    interval = cfg.get('te_parameters', 'scm_int_saved', fallback='1')
    hist_days = cfg.get('te_parameters', 'hist_days', fallback='14')
    scm_use_rest = cfg.get('te_parameters', 'scm_use_rest', fallback='0') == '1'
    scm_daily_reindex = (
        cfg.get('te_parameters', 'scm_daily_reindex', fallback='0') == '1'
    )
    scm_exclude_waivered = (
        cfg.get('te_parameters', 'scm_exclude_waivered', fallback='0') == '1'
    )
    scm_detailed_attributes = (
        cfg.get('te_parameters', 'scm_detailed_attributes', fallback='0') == '1'
    )
    te_sslverify = cfg.get('te_parameters', 'te_sslverify', fallback='0') == '1'
    num_threads = int(cfg.get('te_parameters', 'scm_rest_threads', fallback=1))
    policy_names = cfg.get('te_parameters', 'scm_policy_names', fallback='').split(',')
    policy_names = [p for p in policy_names if p]
    reindex_policy_names = cfg.get(
        'te_parameters', 'scm_reindex_policy_names', fallback=''
    ).split(',')
    reindex_policy_names = [p for p in reindex_policy_names if p]
    if not reindex_policy_names:
        reindex_policy_names = policy_names

    # make sure data directory exists
    save_dir = os.path.join(directory, 'SCM')
    tmp_dir = os.path.join(save_dir, 'tmp')
    make_sure_path_exists(save_dir)
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    make_sure_path_exists(tmp_dir)
    cache_dir = os.path.join(save_dir, 'cache')
    make_sure_path_exists(cache_dir)

    # Daily reindexing (retrieve all results)
    daily_reindex_file = os.path.join(cache_dir, 'daily_reindex.txt')
    do_daily_reindex = False
    if scm_daily_reindex and scm_use_rest:
        do_daily_reindex = True
        if os.path.isfile(daily_reindex_file):
            with open(daily_reindex_file) as f:
                contents = f.read().strip()
                logger.info('Checking last daily reindex time of %s' % contents)
                last_dt = ReportData.isodatetime_to_datetime(contents)
                last_dt = last_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                do_daily_reindex = (now - last_dt).days >= 1
    if do_daily_reindex:
        logger.info('Doing daily reindex!')
        if os.path.isfile(first_run_file):
            os.remove(first_run_file)
            if reindex_policy_names:
                policy_names = reindex_policy_names

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
    file_append = '-hist' if first_run else ''
    file_name = os.path.join(tmp_dir, 'DTR%s.csv' % file_append)

    homepath = os.environ.get("SPLUNK_HOME")
    script_loc = os.path.join(homepath, 'etc', 'apps', app, 'bin', 'tripwire.py')
    script_start = 'splunk'
    if not is_windows():
        homepath = os.environ.get("SPLUNK_HOME")
        script_start = os.path.join(homepath, 'bin', 'splunk')

    scm = SCM(
        ip_address,
        username,
        password,
        script_loc=script_loc,
        unit=unit,
        first_run=first_run,
        hist_days=hist_days,
        interval=interval,
        script_start=script_start,
        python_cmd='cmd python',
        num_threads=num_threads,
        cachedir=cache_dir,
        do_daily_reindex=do_daily_reindex,
        daily_reindex_file=daily_reindex_file,
        te_sslverify=te_sslverify,
    )
    success = True
    if scm_use_rest and scm.te_version_check('8.5.2'):
        logger.info("Starting REST API retrieval with %d threads", num_threads)
        success = scm.do_rest(
            file_name, policy_names, scm_exclude_waivered, scm_detailed_attributes
        )
    else:
        if scm_use_rest:
            logger.info(
                "TE version must be at least 8.5.2 to use the REST API "
                "for SCM.  Falling back to SOAP."
            )
        logger.info("Starting SOAP API retrieval")
        scm.do_soap(file_name,save_dir)
    if success:
        scm.save(tmp_dir, save_dir, first_run_file, scm_watermark_file)
    logger.info("Retrieval complete.")


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logger.exception("Exception in tripwire_scm.py")
