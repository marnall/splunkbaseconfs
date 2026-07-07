#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: info@vuldb.com

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import json
import time
import calendar
import VulDBApi
import splunklib.modularinput as mi
import state_store as ss
import splunklib.client as client
import splunklib.results as results

class VulDBModinput(mi.Script):

    # all credentials and secrets that should use Splunk's secret storage mechanism
    credentials = {
        'api_key': {'label': 'vuldb_api_key', 'value': ''},
        'proxy_password': {'label': 'proxy_password', 'value': ''}
    }

    credentials_mask = 'xxxxxxxxxxxx' # must pass input validation rules

    def get_scheme(self):
        scheme = mi.Scheme("VulDB")

        scheme.description = "Get information from VulDB, the number one vulnerability database."
        scheme.use_external_validation = True
        scheme.use_single_instance = True
        
        scheme.add_argument(mi.Argument(name="vuldb_lang",
                                     title="VulDB Language",
                                     description="The language to be used for the VulDB data.",
                                     data_type=mi.Argument.data_type_string,
                                     required_on_create=True,
                                     required_on_edit=False))
        
        scheme.add_argument(mi.Argument(name="api_key",
                                     title="VulDB API Key",
                                     description="The key for accessing the VulDB API",
                                     data_type=mi.Argument.data_type_string,
                                     required_on_create=True,
                                     required_on_edit=False))
        
        scheme.add_argument(mi.Argument(name="details",
                                     title="VulDB Details",
                                     description="Choose if you wish to retrieve details for the individual vulnerabilities. Will consume more API credits.",
                                     data_type=mi.Argument.data_type_boolean,
                                     required_on_create=True,
                                     required_on_edit=False))
        
        scheme.add_argument(mi.Argument(name="reachback_date",
                                     title="Fetch VulDB entries starting from this date.",
                                     description="Choose the maximum age of VulDB entries to fetch. Date must be entered in the format 'YYYY-MM-DD'. Default is now - one month. Consider API credit consumption.",
                                     data_type=mi.Argument.data_type_string,
                                     required_on_create=False,
                                     required_on_edit=False))
        
        scheme.add_argument(mi.Argument(name="fetch_updates",
                                     title="Fetch updates to existing VulDB entries.",
                                     description="Choose if you wish to retrieve updates to existing VulDB entries. Consider API credit consumption.",
                                     data_type=mi.Argument.data_type_boolean,
                                     required_on_create=False,
                                     required_on_edit=False))
        
        scheme.add_argument(mi.Argument(name="update_reachback_date",
                                     title="Fetch VulDB updates starting from this date.",
                                     description="Choose the maximum age of VulDB updates to fetch. Date must be entered in the format 'YYYY-MM-DD'. Default is now - one month. Consider API credit consumption.",
                                     data_type=mi.Argument.data_type_string,
                                     required_on_create=False,
                                     required_on_edit=False))
        
        scheme.add_argument(mi.Argument(name="proxy_address",
                                     title="Proxy server address",
                                     description="The address or IP of the proxy server for outgoing connections (optional)",
                                     data_type=mi.Argument.data_type_string,
                                     required_on_create=False,
                                     required_on_edit=False))
        
        scheme.add_argument(mi.Argument(name="proxy_scheme",
                                     title="Proxy server scheme",
                                     description="The scheme of the proxy server for outgoing connections, http or https (required if proxy server address is specified)",
                                     data_type=mi.Argument.data_type_string,
                                     required_on_create=False,
                                     required_on_edit=False))
                
        scheme.add_argument(mi.Argument(name="proxy_port",
                                     title="Proxy server port",
                                     description="The port of the proxy server for outgoing connections, e.g. 8080 (optional)",
                                     data_type=mi.Argument.data_type_string,
                                     required_on_create=False,
                                     required_on_edit=False))
                        
        scheme.add_argument(mi.Argument(name="proxy_username",
                                     title="Proxy server username",
                                     description="The username for the proxy server for outgoing connections (optional)",
                                     data_type=mi.Argument.data_type_string,
                                     required_on_create=False,
                                     required_on_edit=False))
                                
        scheme.add_argument(mi.Argument(name="proxy_password",
                                     title="Proxy server password",
                                     description="The password for the proxy server for outgoing connections (optional)",
                                     data_type=mi.Argument.data_type_string,
                                     required_on_create=False,
                                     required_on_edit=False))
        
        scheme.add_argument(mi.Argument(name="fetch_single_ids",
                                     title="Fetch VulDB IDs",
                                     description="Fetch individual vulnerabilities by specifying their VulDB IDs. Separate multiple IDs by comma.",
                                     data_type=mi.Argument.data_type_string,
                                     required_on_create=False,
                                     required_on_edit=False))

        scheme.add_argument(mi.Argument(name="polling_interval",
                                     title="Polling Interval",
                                     description="Interval time in seconds to poll VulDB. Default is 1 hour (3600 seconds).",
                                     data_type=mi.Argument.data_type_number,
                                     required_on_create=False,
                                     required_on_edit=False))

        return scheme

    def validate_input(self, v):
        
        if 'vuldb_lang' in v.parameters:
            if v.parameters['vuldb_lang'] not in ['en', 'de', 'es', 'fr', 'it', 'pt', 'zh', 'ja', 'ko', 'ru', 'ar', 'sv', 'nl', 'da', 'no', 'fi', 'is', 'hr', 'bs', 'sr', 'mk', 'sq', 'sl', 'be', 'tr', 'ro', 'cs', 'uk', 'bg', 'pl', 'hu', 'et', 'lv', 'lt', 'he', 'fa', 'ku', 'ug', 'el', 'ka', 'kk', 'az', 'tg', 'hi', 'ne', 'si', 'ps', 'mn', 'vi', 'th', 'lo', 'km', 'my', 'id', 'ms', 'am', 'sw', 'zu', 'xh', 'ti', 'ig', 'yo', 'so', 'sd', 'uz', 'tl', 'ur', 'bn', 'tk', 'ht', 'ha', 'sn', 'qu', 'gn', 'pa', 'mr', 'ta', 'gu', 'kn', 'te', 'ml', 'ch', 'rm', 'fy', 'lb', 'mt', 'ga', 'cy', 'br', 'gv', 'rw', 'rn', 'ny', 'ff', 'bm', 'wo', 'tn', 'st', 'ay', 'mi', 'sm', 'or', 'ak', 'ln', 'kg', 'ee', 'hy', 'ky', 'ks', 'bo', 'co', 'oc', 'ca', 'gl', 'fj', 'to', 'bi', 'kr', 'ng', 'nd', 'nr', 'dz', 'mh', 'lg', 'nv', 'iu', 'kl', 'eo', 'xk']:
                raise ValueError('Invalid VulDB language')
        
        if 'api_key' in v.parameters:
            try:
                if not v.parameters['api_key'].isalnum():
                    raise ValueError('VulDB API key must be alphanumeric')
            except Exception as e:
                raise ValueError('VulDB API key must be alphanumeric')
        
        if 'reachback_date' in v.parameters:
            if v.parameters['reachback_date']:
                try:
                    time.strptime(v.parameters['reachback_date'], "%Y-%m-%d")
                except Exception as e:
                    raise ValueError('Max age must be specified as YYYY-MM-DD')
                
        if 'update_reachback_date' in v.parameters:
            if v.parameters['update_reachback_date']:
                try:
                    time.strptime(v.parameters['update_reachback_date'], "%Y-%m-%d")
                except Exception as e:
                    raise ValueError('Max age must be specified as YYYY-MM-DD')
                
        if 'proxy_address' in v.parameters:
            if v.parameters['proxy_scheme'] and v.parameters['proxy_scheme'] not in ('http', 'https'):
                raise ValueError('Proxy scheme must be http or https')
            
            if v.parameters['proxy_scheme'] == 'https':
                try:
                    import ipaddress
                    ip_object = ipaddress.ip_address(v.parameters['proxy_address'])
                    proxy_addr = 'ip'
                except ValueError:
                    proxy_addr = 'host'
                    
                if proxy_addr == 'ip':
                    raise ValueError('When using https as proxy scheme, the proxy must be specified as a name and not as IP address.')

            if v.parameters['proxy_address'] and not v.parameters['proxy_port']:
                raise ValueError('You must supply the proxy port if you specify a proxy address')
            
            if v.parameters['proxy_username'] and not v.parameters['proxy_password']:
                raise ValueError('You must supply a password if you specify a username')
            
        if 'fetch_single_ids' in v.parameters:
            if v.parameters['fetch_single_ids'] is not None:
                for id in [x.strip() for x in v.parameters['fetch_single_ids'].split(',')]:
                    if not id.isdigit():
                        raise ValueError('VulDB IDs must be numeric and comma separated')

        if 'polling_interval' in v.parameters:
            if v.parameters['polling_interval'] is not None:
                if not v.parameters['polling_interval'].isdigit() or not (int(v.parameters['polling_interval']) >= 600 and int(v.parameters['polling_interval']) <= 86400):
                    raise ValueError('Polling interval must be between 10 minutes (600) and one day (86400).')
    
    def id_exists(self, service, index, id):
        assert isinstance(service, client.Service)
        assert isinstance(id, list)

        id = ','.join(id)
        search = f'search index="{index}" sourcetype=VulDB | spath output=id path=entry.id | spath output=mdate path=entry.timestamp.change | where id in ({id}) | dedup id | table id'

        job = service.jobs.create(search, earliest_time='', latest_time='now')
        while not job.is_done():
            time.sleep(.2)

        res = [ r['id'] for r in results.ResultsReader(job.results()) ]
        return res
        
    def get_ts(self, service, index, oldest=True):
        assert isinstance(service, client.Service)
        if oldest:
            search = f'search index="{index}" sourcetype=VulDB | spath output=cdate path=entry.timestamp.create | sort cdate | head 1 | table cdate'
        else:
            search = f'search index="{index}" sourcetype=VulDB | spath output=cdate path=entry.timestamp.create | sort - cdate | head 1 | table cdate'
        
        job = service.jobs.create(search)
        while not job.is_done():
            time.sleep(.2)

        res = job.results(output_mode='json').read()
        res = json.loads(res)
        if res['results']:
            return int(res['results'][0].get('cdate', 0))
        else:
            return 0
    
    def del_by_id(self, service, index, ids):
        assert isinstance(service, client.Service)
                
        assert not isinstance(ids, str), 'Argument must be a list.'
        idstr = ' OR id='.join(map(str, ids))
        
        # note: this requires the can_delete privilege!
        search = f'search index="{index}" sourcetype=VulDB | spath output=id path=entry.id | where id={idstr} | delete'
        
        job = service.jobs.create(search)
        while not job.is_done():
            time.sleep(.2)

        return job['resultCount']
    
    def protect_key(self, key, label):
        try:
            for storage_password in self.service.storage_passwords:
                if storage_password.username == label:
                    self.service.storage_passwords.delete(username = label)
                    break

            self.service.storage_passwords.create(key, label)
        except Exception as e:
            raise Exception(f"An error occurred protecting key with label {label}: {e}")

    def get_protected_key(self, label):
        try:
            for storage_password in self.service.storage_passwords:
                if storage_password.username == label:
                    return storage_password.content.clear_password
        except Exception as e:
            raise Exception(f"An error occurred retrieving protected key with label {label}: {e}")
        
    def mkmsg(self, service='', message='', severity='info', state_store='', sleep=43200, msg_class='last_msg', immediate=False):
        if immediate:
            service.service.post('/services/messages', severity=severity, name='msg_' + str(time.time()), value=message)
        else:
            now = int(time.time())
            last_msg = state_store.get_state(msg_class) or 0
            last_msg = int(last_msg)
            if now - last_msg >= sleep:
                service.service.post('/services/messages', severity=severity, name='msg_' + str(time.time()), value=message)
                state_store.update_state(msg_class, now)
    
    def stream_events(self, inputs, ew):
        # parameters for displaying error messages in the Splunk Web UI if data retrieval from VulDB fails.
        fail_cnt = 0
        max_fail_cnt = 3

        try:
            # for input_name, input_item in inputs.inputs.iteritems():
            # it doesn't make sense to have more than one modular input defined for VulDB.
            # Therefore, just take one from the list (which should only contain one entry)
            input_name, input_item = next(iter(inputs.inputs.items()))
            index = input_item['index']
            ew.log("INFO", f"VulDB app is using index [{index}]")

            if input_item['polling_interval']:
                polling_interval = int(input_item['polling_interval'])
            else:
                polling_interval = 3600
            ew.log("INFO", f"VulDB polling interval is set to [{polling_interval}] seconds")
                
            # protect credentials
            for iname, cred in self.credentials.items():
                try:
                    if input_item[iname] != self.credentials_mask:
                        self.protect_key(input_item[iname], cred['label'])

                        kind, name = input_name.split("://")
                        input_obj = self.service.inputs.__getitem__((name, kind))
                        kwargs = {iname: self.credentials_mask}
                        input_obj.update(**kwargs).refresh()

                    cred['value'] = self.get_protected_key(cred['label'])

                except Exception as e:
                    ew.log("ERROR", f"Error handling credential with label {cred['label']}: {e}")

            if input_item['proxy_address']:
                if not input_item['proxy_scheme']:
                    proxy_scheme = 'http'
                else:
                    proxy_scheme = input_item['proxy_scheme']

                if input_item['proxy_username']:
                    proxy_string = f"{proxy_scheme}://{input_item['proxy_username']}:{self.credentials['proxy_password']['value']}@{input_item['proxy_address']}:{input_item['proxy_port']}"
                else:
                    proxy_string = f"{proxy_scheme}://{input_item['proxy_address']}:{input_item['proxy_port']}"
                
                proxy = {'http' : proxy_string,
                        'https' : proxy_string}
            else:
                proxy = {}

            # init state store
            state_store = ss.FileStateStore(inputs.metadata, input_name)
            # init vuldb client
            vuldb = VulDBApi.VulDBClient(self.credentials['api_key']['value'], proxy, vuldb_lang=input_item['vuldb_lang'], verify=True)

            while True:
                # strategy for fetching data from VulDB:
                #  - get the time stamp (create date) of the latest entry stored in splunk from the cursor file. 0 if cursor file missing or empty.
                #  - if the time stamp is 0 or is older than the configured time interval to look back,
                #    fetch data from "now minus the configured time interval" up to now
                #  - if the time stamp is younger, fetch data from the time stamp up to now
                # Updates are fetched after data is downloaded, but in the same run.
                # Updated entries are stored in Splunk in addition to the original entries (dedup is used for data analysis).

                now = int(time.time())

                cursor = state_store.get_state("cursor") or 0

                # get create date of oldest and youngest entry in local Splunk
                # used to only store updates to entries we already have in Splunk and to check for cursor plausibility
                # if local splunk doesnt contain any vulns, oldest_ts will be 0 and no updates will be fetched
                oldest_ts = self.get_ts(self.service, index, oldest=True)
                youngest_ts = self.get_ts(self.service, index, oldest=False)

                # retrieve defaults for how far from the past data should be fetched
                if not cursor:
                    if youngest_ts:
                        ew.log('WARN', 'No valid cursor found, but VulDB data exists in Splunk! Resetting cursor, data redundancy may occur.')
                        
                    if input_item['reachback_date']:
                        cursor = calendar.timegm(time.strptime(input_item['reachback_date'], "%Y-%m-%d"))
                    else:
                        try:
                            res = vuldb.get_cursorinit(mode='recent')
                            fail_cnt = 0
                            cursor = int(res.json()['result'][0]['entry']['timestamp']['create']) - 1
                            ew.log('INFO', f'Got cursor init from VulDB: [{cursor}].')
                        except (VulDBApi.APIError, VulDBApi.VulDBError) as e:
                            fail_cnt += 1
                            if fail_cnt >= max_fail_cnt:
                                self.mkmsg(service=self, message=f'Fetching data from VulDB failed {fail_cnt} times in a row. Please check logs and connectivity.',
                                           severity='error', msg_class='vuldb_error', sleep=300, state_store=state_store)
                            ew.log('ERROR', f'Failed to retrieve data from VulDB (fail count: {fail_cnt}): {e}')
                            return
                        
                cursor = int(cursor)

                # fetch vulns
                cnt = 1
                finished = False
                remaining = 1
                while not finished:
                    if cnt > 1: time.sleep(5) # sleep between iterations to reduce load on vuldb.com

                    ew.log('INFO', f'Fetching entries younger than time stamp [{cursor}] from VulDB (chunk #{cnt})...')
                    try:
                        res = vuldb.get_entries_by_date(date=cursor + 1, details=input_item['details'])
                        fail_cnt = 0
                        items = res.json()['response']['items']
                        remaining = int(res.json()['response']['remaining'])
                        querylimit = int(res.json()['response']['querylimit'])
                    except (VulDBApi.APIError, VulDBApi.VulDBError) as e:
                        items = None

                        fail_cnt += 1
                        if fail_cnt >= max_fail_cnt:
                            self.mkmsg(service=self, message=f'Fetching data from VulDB failed {fail_cnt} times in a row. Please check logs and connectivity.',
                                severity='error', msg_class='vuldb_error', sleep=300, state_store=state_store)
                        ew.log('ERROR', f'Failed to retrieve data from VulDB (fail count: {fail_cnt}): {e}')
                    
                    if items:
                        # latest time stamp from results; may differ from latest time stamp in VulDB
                        cursor = sorted([ int(x['entry']['timestamp']['create']) for x in res.json()['result'] ])[-1]
                        state_store.update_state("cursor", cursor)
                        ew.log('INFO', f'...got a response with {items} entries from VulDB. Remaining API credits: [{remaining}]')
                        
                        for v in res.json()['result']:
                            try:
                                event = mi.Event()
                                event.stanza = input_name
                                event.data = json.dumps(v)
                                ew.write_event(event)
                            except Exception as e:
                                ew.log('ERROR', f'An error has occurred writing data to splunk: {e}')
                            
                        ew.log('INFO', 'Events written to splunk.')
                        cnt += 1
                        
                        if items < querylimit: finished = True
                        
                        if remaining == 0:
                            ew.log('ERROR', 'No more API credits left!')
                            self.mkmsg(service=self, message='All VulDB API credits are used up! Visit [!https://vuldb.com/?pay VulDB] to get more.',
                                severity='error', state_store=state_store)
                            break
                        elif remaining <= 10:
                            self.mkmsg(service=self, message=f'Running low on VulDB API credits! [remaining: {remaining}]. Visit [!https://vuldb.com/?pay VulDB] to get more.',
                                severity='warn', state_store=state_store)
                            ew.log('WARN', f'Running low on VulDB API credits! [remaining: {remaining}]')
                    elif items == 0:
                        ew.log('INFO', f'...no new entries available from VulDB. Remaining API credits: [{remaining}]')
                        finished = True
                    else:
                        finished = True
                        ew.log('ERROR', 'An unknown error occurred when trying to fetch data from VulDB.')


                # fetch updates if configured
                if input_item['fetch_updates'] == '1':
                    if oldest_ts != 0:
                        # retrieve defaults for how far from the past updates should be fetched
                        upd_cursor = state_store.get_state('last_updated') or 0
                        
                        if not upd_cursor:
                            if input_item['update_reachback_date']:
                                upd_cursor = calendar.timegm(time.strptime(input_item['update_reachback_date'], "%Y-%m-%d"))
                            else:
                                try:
                                    res = vuldb.get_cursorinit(mode='updates')
                                    fail_cnt = 0
                                    upd_cursor = int(res.json()['result'][0]['entry']['timestamp']['change']) - 1
                                    ew.log('INFO', f'Got update cursor init from VulDB with time stamp [{upd_cursor}]')
                                except (VulDBApi.APIError, VulDBApi.VulDBError) as e:
                                    fail_cnt += 1
                                    if fail_cnt >= max_fail_cnt:
                                        self.mkmsg(service=self, message=f'Fetching data from VulDB failed {fail_cnt} times in a row. Please check logs and connectivity.',
                                                    severity='error', msg_class='vuldb_error', sleep=300, state_store=state_store)
                                    ew.log('ERROR', f'Failed to retrieve data from VulDB (fail count: {fail_cnt}): {e}')
                        
                        # upd_cursor of older Splunk App versions was YYYYMMDD, convert to new format if applicable
                        try:
                            upd_cursor = time.mktime(time.strptime(str(upd_cursor), '%Y%m%d'))
                        except Exception:
                            pass
                        
                        upd_cursor = int(upd_cursor)
                        
                        finished = False
                        if remaining > 0:
                            cnt = 1
                            while not finished:
                                if cnt > 1: time.sleep(5) # sleep between iterations to reduce load on vuldb.com

                                ew.log('INFO', f'Fetching updates younger than time stamp [{upd_cursor}] from VulDB (chunk #{cnt})...')
                                try:
                                    res = vuldb.get_entries_by_date(date=upd_cursor + 1, mdate=True, details=input_item['details'])
                                    fail_cnt = 0
                                    items = res.json()['response']['items']
                                    remaining = int(res.json()['response']['remaining'])
                                    querylimit = int(res.json()['response']['querylimit'])
                                except (VulDBApi.APIError, VulDBApi.VulDBError) as e:
                                    items = None

                                    fail_cnt += 1
                                    if fail_cnt >= max_fail_cnt:
                                        self.mkmsg(service=self, message=f'Fetching data from VulDB failed {fail_cnt} times in a row. Please check logs and connectivity.',
                                           severity='error', msg_class='vuldb_error', sleep=300, state_store=state_store)
                                    ew.log('ERROR', f'Failed to retrieve data from VulDB (fail count: {fail_cnt}): {e}')
                                    
                                    
                                if items:
                                    timestamps = [ int(x['entry']['timestamp']['create']) for x in res.json()['result'] ] + \
                                                [ int(x['entry']['timestamp'].get('change', 0)) for x in res.json()['result'] ]
                                    upd_cursor = sorted(timestamps)[-1]
                                    state_store.update_state('last_updated', upd_cursor)
                                    ew.log('INFO', f'...got a response with {items} entries from VulDB. Remaining API credits: [{remaining}]')

                                    i_updates = 0
                                    for v in res.json()['result']:
                                        if 'change' in v['entry']['timestamp'] and \
                                        int(v['entry']['timestamp']['change']) > int(v['entry']['timestamp']['create']) and \
                                        int(v['entry']['timestamp']['create']) >= oldest_ts:
                                            i_updates += 1
                                            try:
                                                event = mi.Event()
                                                event.stanza = input_name
                                                event.data = json.dumps(v)
                                                ew.write_event(event)
                                            except Exception as e:
                                                ew.log('ERROR', f'An error has occurred writing data to splunk: {e}')
                                                
                                    if i_updates:
                                        ew.log('INFO', f'[{i_updates}] VulDB updates written to splunk')
                                    else:
                                        ew.log('INFO', f'No applicable updates found in chunk #{cnt}.')
            
                                    cnt += 1
                                    
                                    if items < querylimit: finished = True
            
                                    if remaining == 0:
                                        ew.log('ERROR', 'No more API credits left! Aborting.')
                                        self.mkmsg(service=self, message='All VulDB API credits are used up! Visit [!https://vuldb.com/?pay VulDB] to get more.',
                                            severity='error', state_store=state_store)
                                        break       
                                    elif remaining <= 10:
                                        self.mkmsg(service=self, message=f'Running low on VulDB API credits! [remaining: {remaining}]. Visit [!https://vuldb.com/?pay VulDB] to get more.',
                                            severity='warn', state_store=state_store)
                                        ew.log('WARN', f'Running low on VulDB API credits! [remaining: {remaining}]')
                                elif items == 0:
                                    ew.log('INFO', f'...no new updates available from VulDB. Remaining API credits: [{remaining}]')
                                    finished = True
                                else:
                                    finished = True
                                    ew.log('ERROR', 'An error occurred when trying to fetch data from VulDB.')
                        else:
                            ew.log('ERROR', 'No API credits available, cannot fetch updates!')
                            self.mkmsg(service=self, message='All VulDB API credits are used up! Visit [!https://vuldb.com/?pay VulDB] to get more.',
                                severity='error', state_store=state_store)
                    
                # fetch single ids if configured
                if input_item['fetch_single_ids']:
                    ids = [x.strip() for x in input_item['fetch_single_ids'].split(',')]
                    if remaining > len(ids):
                        ew.log('INFO', f"'Fetching VulDB IDs {input_item['fetch_single_ids']} from VulDB...")
                        try:
                            res = vuldb.get_entry_by_id(ids=ids, details=input_item['details'])
                            fail_cnt = 0
                        except (VulDBApi.APIError, VulDBApi.VulDBError) as e:
                            fail_cnt += 1
                            if fail_cnt >= max_fail_cnt:
                                self.mkmsg(service=self, message=f'Fetching data from VulDB failed {fail_cnt} times in a row. Please check logs and connectivity.',
                                            severity='error', msg_class='vuldb_error', sleep=300, state_store=state_store)
                            ew.log('ERROR', f'Failed to retrieve data from VulDB (fail count: {fail_cnt}): {e}')
                            
                        try:
                            items = res.json()['response']['items']
                            remaining = int(res.json()['response']['remaining'])
                        except Exception as e:
                            items = None
                        
                        if remaining <= 10:
                            self.mkmsg(service=self, message=f'Running low on VulDB API credits! [remaining: {remaining}]. Visit [!https://vuldb.com/?pay VulDB] to get more.',
                                severity='warn', state_store=state_store)
                            ew.log('WARN', f'Running low on VulDB API credits! [remaining: {remaining}]')
                            
                        if items:
                            ew.log('INFO', f'...got [{items}] vulnerabilities from VulDB. Remaining API credits: [{remaining}]')
                            
                            for v in res.json()['result']:
                                if 'warning' in v['entry']:
                                    ew.log('WARN', f"Fetching vulnerability ID [{v['entry']['id']}] generated a warning: {v['entry']['warning']}")
                                
                                try:
                                    event = mi.Event()
                                    event.stanza = input_name
                                    event.data = json.dumps(v)
                                    ew.write_event(event)
                                except Exception as e:
                                    ew.log('ERROR', f'An error has occurred writing data to splunk: {e}')

                            ew.log('INFO', 'Data written to splunk.')
                            # remove IDs from input config after success
                            kind, name = input_name.split("://")
                            input_obj = self.service.inputs.__getitem__((name, kind))
                            input_obj.update(fetch_single_ids='')
                        else:
                            ew.log('ERROR', 'Unknown error, no data retrieved from VulDB.')
                    else:
                        ew.log('ERROR', 'Not enough API credits available, cannot fetch VulDB IDs from VulDB!')
                        self.mkmsg(service=self, message='Not enough API credits available! Visit [!https://vuldb.com/?pay VulDB] to get more.',
                                severity='error', state_store=state_store)

                ew.log('INFO', f'Sleeping [{polling_interval}] seconds until next polling interval is reached')
                time.sleep(polling_interval)

        except RuntimeError as e:
            ew.log('ERROR', f'An error has ocurred: {str(e)}')
            sys.exit(2)

if __name__ == "__main__":
    VulDBModinput().run(sys.argv)
    sys.exit(0)