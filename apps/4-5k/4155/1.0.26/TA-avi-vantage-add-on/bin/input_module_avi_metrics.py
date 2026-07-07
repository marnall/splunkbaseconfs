# encoding = utf-8

import traceback
import requests
#import ConfigParser
import xml.dom.minidom, xml.sax.saxutils
import json
import time
import base64
import sys
import logging
import os
import _pickle as pickle
import datetime

if os.name == 'nt':
    from threading import Thread as Process
else:
    from multiprocessing import Process

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # avi_controller = definition.parameters.get('avi_controller', None)
    # avi_user = definition.parameters.get('avi_user', None)
    # avi_pass = definition.parameters.get('avi_pass', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_avi_controller = helper.get_arg('avi_controller')
    opt_avi_user = helper.get_arg('avi_user')
    opt_avi_pass = helper.get_arg('avi_pass')
    # In single instance mode, to get arguments of a particular input, use
    opt_avi_controller = helper.get_arg('avi_controller', stanza_name)
    opt_avi_user = helper.get_arg('avi_user', stanza_name)
    opt_avi_pass = helper.get_arg('avi_pass', stanza_name)
    """
    avi_user = helper.get_arg('avi_user')
    avi_pass = helper.get_arg('avi_pass')
    avi_controller = helper.get_arg('avi_controller')
    req_option = helper.get_arg('req_options')
    logging.error('Accessing Avi API for metrics data')


    #----- This class is where all the test methods/functions exist and are executed
    class avi_metrics_splunk():
        def __init__(self,avi_controller, avi_user, avi_pass):
            self.avi_cluster_ip = avi_controller
            self.avi_controller = avi_controller
            self.avi_user = avi_user
            self.avi_pass = avi_pass
            #------
            self.vs_metric_list  = [
                'l4_client.apdexc',
                'l4_client.avg_bandwidth',
                'l4_client.avg_application_dos_attacks',
                'l4_client.avg_complete_conns',
                'l4_client.avg_connections_dropped',
                'l4_client.avg_new_established_conns',
                'l4_client.avg_policy_drops',
                'l4_client.avg_rx_pkts',
                'l4_client.avg_tx_pkts',
                'l4_client.avg_rx_bytes',
                'l4_client.avg_tx_bytes',
                'l4_client.max_open_conns',
                'l4_client.avg_lossy_connections',
                'l7_client.avg_complete_responses',
                'l7_client.avg_client_data_transfer_time',
                'l7_client.avg_client_txn_latency',
                'l7_client.sum_application_response_time',
                'l7_client.avg_resp_4xx_avi_errors',
                'l7_client.avg_resp_5xx_avi_errors',
                'l7_client.avg_resp_2xx',
                'l7_client.avg_resp_4xx',
                'l7_client.avg_resp_5xx',
                'l4_client.avg_total_rtt',
                'l7_client.avg_page_load_time',
                'l7_client.apdexr',
                'l7_client.avg_ssl_handshakes_new',
                'l7_client.avg_ssl_connections',
                'l7_client.sum_get_reqs',
                'l7_client.sum_post_reqs',
                'l7_client.sum_other_reqs',
                'l7_client.avg_frustrated_responses',
                'l7_client.avg_waf_attacks',
                'l7_client.pct_waf_attacks',
                'l7_client.sum_total_responses',
                'l7_client.avg_waf_rejected',
                'l7_client.avg_waf_evaluated',
                'l7_client.avg_waf_matched',
                'l7_client.avg_waf_disabled',
                'l7_client.pct_waf_disabled',
                'l7_client.avg_http_headers_count',
                'l7_client.avg_http_headers_bytes',
                'l7_client.pct_get_reqs',
                'l7_client.pct_post_reqs',
                'l7_client.avg_http_params_count',
                'l7_client.avg_uri_length',
                'l7_client.avg_post_bytes',
                'dns_client.avg_complete_queries',
                'dns_client.avg_domain_lookup_failures',
                'dns_client.avg_tcp_queries',
                'dns_client.avg_udp_queries',
                'dns_client.avg_udp_passthrough_resp_time',
                'dns_client.avg_unsupported_queries',
                'dns_client.pct_errored_queries',
                'dns_client.avg_domain_lookup_failures',
                'dns_client.avg_avi_errors',
                'dns_server.avg_complete_queries',
                'dns_server.avg_errored_queries',
                'dns_server.avg_tcp_queries',
                'dns_server.avg_udp_queries',
                'l4_server.avg_rx_pkts',
                'l4_server.avg_tx_pkts',
                'l4_server.avg_rx_bytes',
                'l4_server.avg_tx_bytes',
                'l4_server.avg_bandwidth',
                'l7_server.avg_complete_responses',
                'l4_server.avg_new_established_conns',
                'l4_server.avg_pool_open_conns',
                'l4_server.avg_pool_complete_conns',
                'l4_server.avg_open_conns',
                'l4_server.max_open_conns',
                'l4_server.avg_errored_connections',
                'l4_server.apdexc',
                'l4_server.avg_total_rtt',
                'l7_server.avg_resp_latency',
                'l7_server.apdexr',
                'l7_server.avg_application_response_time',
                'l7_server.pct_response_errors',
                'l7_server.avg_frustrated_responses',
                'l7_server.avg_total_requests'            
                ]
            self.se_metric_list = [
                'se_if.avg_bandwidth',
                'se_stats.avg_connection_mem_usage',
                'se_stats.avg_connections',
                'se_stats.avg_connections_dropped',
                'se_stats.avg_cpu_usage',
                'se_stats.avg_disk1_usage',
                'se_stats.avg_mem_usage',
                'se_stats.avg_persistent_table_usage',
                'se_stats.avg_rx_bandwidth',
                'se_if.avg_rx_bytes',
                'se_if.avg_rx_pkts',
                'se_if.avg_rx_pkts_dropped_non_vs',
                'se_if.avg_tx_pkts',
                'se_if.avg_tx_bytes',
                'se_stats.avg_ssl_session_cache_usage',
                'se_if.avg_connection_table_usage',
                'se_stats.max_se_bandwidth',
                'se_stats.avg_eth0_bandwidth',
                'se_stats.pct_syn_cache_usage',
                'se_stats.avg_packet_buffer_usage',
                'se_stats.avg_packet_buffer_header_usage',
                'se_stats.avg_packet_buffer_large_usage',
                'se_stats.avg_packet_buffer_small_usage']
            self.controller_metric_list  = [
                'controller_stats.avg_cpu_usage',
                'controller_stats.avg_disk_usage',
                'controller_stats.avg_mem_usage']
            #----
            self.pool_server_metric_list = [
                'l4_server.avg_rx_pkts',
                'l4_server.avg_tx_pkts',
                'l4_server.avg_rx_bytes',
                'l4_server.avg_tx_bytes',
                'l4_server.avg_bandwidth',
                'l7_server.avg_complete_responses',
                'l4_server.avg_new_established_conns',
                'l4_server.avg_pool_open_conns',
                'l4_server.avg_pool_complete_conns',
                'l4_server.avg_open_conns',
                'l4_server.max_open_conns',
                'l4_server.avg_errored_connections',
                'l4_server.apdexc',
                'l4_server.avg_total_rtt',
                'l7_server.avg_resp_latency',
                'l7_server.apdexr',
                'l7_server.avg_application_response_time',
                'l7_server.pct_response_errors',
                'l7_server.avg_frustrated_responses',
                'l7_server.avg_total_requests'
                ]




        def avi_login(self):
            try:
                login = pickle.load(open((os.path.join(fdir,self.avi_cluster_ip)),'rb'))
                cookies=dict()
                for c in login.cookies:
                    expires = c.expires
                if 'avi-sessionid' in login.cookies.keys():
                    cookies['avi-sessionid'] = login.cookies['avi-sessionid']
                else:
                    cookies['sessionid'] = login.cookies['sessionid']
                headers = ({"X-Avi-Tenant": "admin", 'content-type': 'application/json'})
                resp = requests.get('https://%s/api/cluster' %self.avi_cluster_ip, verify=req_option, headers = headers,cookies=cookies,timeout=5)
                #if expires > time.time():
                if resp.status_code == 200:
                    return login
                else:
                    login = requests.post('https://%s/login' %self.avi_cluster_ip, verify=req_option, data={'username': self.avi_user, 'password': self.avi_pass},timeout=15)
                    pickle.dump(login, open((os.path.join(fdir,self.avi_cluster_ip)),'wb'))
                    return login
            except:
                try:
                    login = requests.post('https://%s/login' %self.avi_cluster_ip, verify=req_option, data={'username': self.avi_user, 'password': self.avi_pass},timeout=15)
                    pickle.dump(login, open((os.path.join(fdir,self.avi_cluster_ip)),'wb'))
                    return login
                except requests.exceptions.Timeout:
                    class timedout:pass
                    login = timedout()
                    login.status_code = 'timedout'
                    return login



        def return_tenants(self):
            try:
                admin_access = False
                for t in self.login.json()['tenants']:
                    if t['name'] == 'admin':
                        admin_access = True
                if admin_access == True:
                    resp = self.avi_request('tenant?page_size=200','admin')
                    if resp.status_code == 200:
                        tenants_resp = resp.json()
                        resp = tenants_resp
                        page_number = 1
                        while 'next' in resp:
                            page_number += 1
                            resp = self.avi_request('tenant?page_size=200&page='+str(page_number),'admin').json()
                            for r in resp['results']:
                                tenants_resp['results'].append(r)
                        return tenants_resp['results']
                    else:
                        return self.login.json()['tenants']
    
                else:
                    return self.login.json()['tenants']
            except:
                exception_text = traceback.format_exc()
                print(str(datetime.now())+' '+self.avi_cluster_ip+': '+exception_text)
                return self.login.json()['tenants'] 



        def avi_request(self,avi_api,tenant,api_version=None):
            cookies=dict()
            if api_version == None:
                major,minor = self.login.json()['version']['Version'].rsplit('.',1)
                api_version = '%s.%s' %(major,minor)                
            if 'avi-sessionid' in self.login.cookies.keys():
                cookies['avi-sessionid'] = self.login.cookies['avi-sessionid']
            else:
                cookies['sessionid'] = self.login.cookies['sessionid']
            headers = ({"X-Avi-Tenant": "%s" %tenant, 'content-type': 'application/json','X-Avi-Version': '%s' %api_version})
            return requests.get('https://%s/api/%s' %(self.avi_controller,avi_api), verify=req_option, headers = headers,cookies=cookies,timeout=50)


        def avi_post(self,api_url,tenant,payload,api_version=None):
            cookies=dict()
            if api_version == None:
                major,minor = self.login.json()['version']['Version'].rsplit('.',1)
                api_version = '%s.%s' %(major,minor)            
            if 'avi-sessionid' in self.login.cookies.keys():
                cookies['avi-sessionid'] = self.login.cookies['avi-sessionid']
            else:
                cookies['sessionid'] = self.login.cookies['sessionid']
            headers = ({"X-Avi-Tenant": "%s" %tenant, 'content-type': 'application/json','referer': 'https://%s' %self.avi_controller, 'X-CSRFToken': dict(self.login.cookies)['csrftoken'],'X-Avi-Version':'%s' %api_version})
            cookies['csrftoken'] = self.login.cookies['csrftoken']
            return requests.post('https://%s/api/%s' %(self.avi_controller,api_url), verify=req_option, headers = headers,cookies=cookies, data=json.dumps(payload),timeout=50)





        #----- Tries to determine a follower controller to poll
        def controller_to_poll(self):
            cookies=dict()
            if 'avi-sessionid' in self.login.cookies.keys():
                cookies['avi-sessionid'] = self.login.cookies['avi-sessionid']
            else:
                cookies['sessionid'] = self.login.cookies['sessionid']
            headers = ({"X-Avi-Tenant": "admin", 'content-type': 'application/json'})
            resp = (requests.get('https://%s/api/%s' %(self.avi_cluster_ip,'cluster/runtime'), verify=req_option, headers = headers,cookies=cookies,timeout=50)).json()
            follower_list = []
            if len(resp['node_states']) > 1:
                for c in resp['node_states']:
                    if c['state'] == 'CLUSTER_ACTIVE' and c['role']  == 'CLUSTER_FOLLOWER':
                        follower_list.append(c['mgmt_ip'])
                if len(follower_list) == 0:
                    return self.avi_cluster_ip
                else:
                    return sorted(follower_list)[0]
            else:
                return self.avi_cluster_ip




        #----- Creates inventory dicts to be used by other methods
        def gen_inventory_dict(self):
                start_time = time.time()
                vs_dict = {'tenants':{},'admin_vs':[]}
                se_dict={'tenants':{},'admin_se':[]}
                pool_dict={'tenants':{}}
                seg_dict = {'tenants':{}}
                cloud_mapping = {}
                cloud_dict={}
                if self.login.json()['user']['is_superuser'] == True: #----if SU, use wildcard tenant
                    vs_inv = self.avi_request('virtualservice-inventory?page_size=200','*').json()
                    resp = vs_inv
                    page_number = 1
                    while 'next' in resp:
                        page_number += 1
                        resp = self.avi_request('virtualservice-inventory?page_size=200&page='+str(page_number),'*').json()
                        for v in resp['results']:
                            vs_inv['results'].append(v)
                    #------------------
                    se_inv = self.avi_request('serviceengine-inventory?page_size=200','*').json()
                    resp = se_inv
                    page_number = 1
                    while 'next' in resp:
                        page_number += 1
                        resp = self.avi_request('serviceengine-inventory?page_size=200&page='+str(page_number),'*').json()
                        for s in resp['results']:
                            se_inv['results'].append(s)
                    #------------------
                    pool_inv = self.avi_request('pool-inventory?page_size=200','*').json()
                    resp = pool_inv
                    page_number = 1
                    while 'next' in resp:
                        page_number += 1
                        resp = self.avi_request('pool-inventory?page_size=200&page='+str(page_number),'*').json()
                        for p in resp['results']:
                            pool_inv['results'].append(p)
                    #------------------
                    seg_inv = self.avi_request('serviceenginegroup-inventory?page_size=200','*').json()
                    #------------------
                    cloud_inv = self.avi_request('cloud-inventory?page_size=200','*').json()
                    #------------------
                    if cloud_inv['count'] > 0:
                        for c in cloud_inv['results']:
                            cloud_dict[c['uuid']] = c['config']['name']
                    #------------------
                    if vs_inv['count'] > 0:
                        for v in vs_inv['results']:
                            for t in self.tenants:
                                if t['url'].split('/tenant/')[1] == v['config']['tenant_ref'].split('/tenant/')[1]:
                                    temp_tenant = t['name']
                            if temp_tenant not in vs_dict['tenants']:
                                vs_dict['tenants'][temp_tenant] = {'count':1,'results':[v]}
                            else:
                                vs_dict['tenants'][temp_tenant]['count']+=1
                                vs_dict['tenants'][temp_tenant]['results'].append(v)
                            vs_dict[v['uuid']] = v['config']['name']
                            cloud_mapping[v['uuid']] = cloud_dict[v['config']['cloud_ref'].split('/cloud/')[1]]
                            if temp_tenant == 'admin':
                                vs_dict['admin_vs'].append(v['uuid'])
                    #------------------
                    if se_inv['count'] > 0:
                        for s in se_inv['results']:
                            for t in self.tenants:
                                if t['url'].split('/tenant/')[1] == s['config']['tenant_ref'].split('/tenant/')[1]:
                                    temp_tenant = t['name']
                            if temp_tenant not in se_dict['tenants']:
                                se_dict['tenants'][temp_tenant] = {'count':1,'results':[s]}
                            else:
                                se_dict['tenants'][temp_tenant]['count']+=1
                                se_dict['tenants'][temp_tenant]['results'].append(s)
                            se_dict[s['uuid']] = s['config']['name']
                            cloud_mapping[s['uuid']] = cloud_dict[s['config']['cloud_ref'].split('/cloud/')[1]]
                            if temp_tenant == 'admin':
                                se_dict['admin_se'].append(s['uuid'])
                    #------------------
                    if pool_inv['count'] > 0:
                        for p in pool_inv['results']:
                            for t in self.tenants:
                                if t['url'].split('/tenant/')[1] == p['config']['tenant_ref'].split('/tenant/')[1]:
                                    temp_tenant = t['name']
                            if temp_tenant not in pool_dict['tenants']:
                                pool_dict['tenants'][temp_tenant] = {'count':1,'results':[p]}
                            else:
                                pool_dict['tenants'][temp_tenant]['count']+=1
                                pool_dict['tenants'][temp_tenant]['results'].append(p)
                            pool_dict[p['uuid']] = p['config']['name']
                            cloud_mapping[p['uuid']] = cloud_dict[p['config']['cloud_ref'].split('/cloud/')[1]]
                    #------------------
                    if seg_inv['count'] > 0:
                        for seg in seg_inv['results']:
                            for t in self.tenants:
                                if t['url'].split('/tenant/')[1] == seg['config']['tenant_ref'].split('/tenant/')[1]:
                                    temp_tenant = t['name']
                            if temp_tenant not in seg_dict['tenants']:
                                seg_dict['tenants'][temp_tenant] = {'count':1,'results':[seg]}
                            else:
                                seg_dict['tenants'][temp_tenant]['count']+=1
                                seg_dict['tenants'][temp_tenant]['results'].append(seg)
                            seg_dict[seg['uuid']] = seg['config']['name']
                            cloud_mapping[seg['uuid']] = cloud_dict[seg['config']['cloud_ref'].split('/cloud/')[1]]
                    #------------------
                else:
                    for t in self.tenants:
                        vs_inv = self.avi_request('virtualservice-inventory?page_size=200',t['name']).json()
                        resp = vs_inv
                        page_number = 1
                        while 'next' in resp:
                            page_number += 1
                            resp = self.avi_request('virtualservice-inventory?page_size=200&page='+str(page_number),t['name']).json()
                            for v in resp['results']:
                                vs_inv['results'].append(v)
                        #------------------
                        se_inv = self.avi_request('serviceengine-inventory?page_size=200',t['name']).json()
                        resp = se_inv
                        page_number = 1
                        while 'next' in resp:
                            page_number += 1
                            resp = self.avi_request('serviceengine-inventory?page_size=200&page='+str(page_number),t['name']).json()
                            for s in resp['results']:
                                se_inv['results'].append(s)
                        #------------------
                        pool_inv = self.avi_request('pool-inventory?page_size=200',t['name']).json()
                        resp = pool_inv
                        page_number = 1
                        while 'next' in resp:
                            page_number += 1
                            resp = self.avi_request('pool-inventory?page_size=200&page='+str(page_number),t['name']).json()
                            for p in resp['results']:
                                pool_inv['results'].append(p)
                        #------------------
                        seg_inv = self.avi_request('serviceenginegroup-inventory?page_size=200',t['name']).json()
                        #------------------
                        cloud_inv = self.avi_request('cloud-inventory?page_size=200',t['name']).json()
                        #------------------
                        for c in cloud_inv['results']:
                            cloud_dict[c['uuid']] = c['config']['name']
                        if vs_inv['count'] > 0:
                            vs_dict['tenants'][t['name']]=vs_inv
                        for v in vs_inv['results']:
                            vs_dict[v['uuid']] = v['config']['name']
                            cloud_mapping[v['uuid']] = cloud_dict[v['config']['cloud_ref'].split('/cloud/')[1]]
                            if t['name'] == 'admin':
                                vs_dict['admin_vs'].append(v['uuid'])
                        if se_inv['count'] > 0:
                            se_dict['tenants'][t['name']] = se_inv
                        for s in se_inv['results']:
                            se_dict[s['uuid']] = s['config']['name']
                            cloud_mapping[s['uuid']] = cloud_dict[s['config']['cloud_ref'].split('/cloud/')[1]]
                            if t['name'] == 'admin':
                                se_dict['admin_se'].append(s['uuid'])
                        if pool_inv['count'] > 0:
                            pool_dict['tenants'][t['name']] = pool_inv
                        for p in pool_inv['results']:
                            pool_dict[p['uuid']] = s['config']['name']
                            cloud_mapping[p['uuid']] = cloud_dict[p['config']['cloud_ref'].split('/cloud/')[1]]
                        if seg_inv['count'] > 0:
                            seg_dict['tenants'][t['name']] = seg_inv
                        for seg in seg_inv['results']:
                            seg_dict[seg['uuid']] = seg['config']['name']
                            cloud_mapping[seg['uuid']] = cloud_dict[seg['config']['cloud_ref'].split('/cloud/')[1]]
                temp_total_time = str(time.time()-start_time)
                logging.info(self.avi_cluster_ip+': func gen_inventory_dict completed, executed in '+temp_total_time+' seconds')
                return vs_dict, se_dict, pool_dict, seg_dict, cloud_mapping




        #-----------------------------------
        #----- Remove unavailable metrics for current version
        def remove_version_specific_metrics(self):
            #try:
            #----- Generate List of Available Metrics
                available_metrics = {}
                resp = self.avi_request('analytics/metric_id',self.tenants[0]['name']).json()
                vs_metrics = []
                se_metrics = []
                pool_server_metrics = []
                controller_metrics = []
                for m in resp['results']:
                    #available_metrics.append(m['name'])
                    available_metrics[m['name']]=m['entity_types']
                for vm in self.vs_metric_list:
                    if vm in available_metrics:
                        if 'virtualservice' in available_metrics[vm]:
                            vs_metrics.append(vm)
                for sm in self.se_metric_list:
                    if sm in available_metrics:
                        if 'serviceengine' in available_metrics[sm]:
                            se_metrics.append(sm)
                for cm in self.controller_metric_list:                
                    if cm in available_metrics:
                        if 'cluster' in available_metrics[cm]:
                            controller_metrics.append(cm)
                for pm in self.pool_server_metric_list:
                    if pm in available_metrics:
                        if 'pool' in available_metrics[pm]:
                            pool_server_metrics.append(pm)
                vs_metric_list = ','.join(vs_metrics)          
                se_metric_list = ','.join(se_metrics)
                controller_metric_list = ','.join(controller_metrics)
                pool_server_metric_list = ','.join(pool_server_metrics)
                return vs_metric_list, se_metric_list, controller_metric_list, pool_server_metric_list
            #except:
            #    print(str(datetime.now())+' '+self.avi_cluster_ip+': remove_version_specific_metrics encountered an error')
            #    exception_text = traceback.format_exc()
            #    print(str(datetime.now())+' '+self.avi_cluster_ip+': '+exception_text)




        #-----------------------------------


        def srvc_engn_stats(self):
            #try:
                temp_start_time = time.time()
                discovered_ses = []  #--- this is used b/c se in admin show up in other tenants
                discovered_health = []
                for t in self.tenants:
                    if t['name'] in self.se_dict['tenants'] and self.se_dict['tenants'][t['name']]['count'] > 0:
                        payload = {
                            "metric_requests": [
                                {
                                    "step": 300,
                                    "limit": 1,
                                    "aggregate_entity": False,
                                    "entity_uuid": "*",
                                    "se_uuid": "*",
                                    "id": "collItemRequest:AllSEs",
                                    "metric_id": self.se_metric_list
                                }
                                ]}
                        se_stat = self.avi_post('analytics/metrics/collection?pad_missing_data=false', t['name'], payload).json()
                        payload = {
                            "metric_requests": [
                                {
                                    "step": 5,
                                    "limit": 1,
                                    "aggregate_entity": False,
                                    "entity_uuid": "*",
                                    "se_uuid": "*",
                                    "id": "collItemRequest:AllSEs",
                                    "metric_id": self.se_metric_list
                                }
                                ]}
                        realtime_stat = self.avi_post('analytics/metrics/collection?pad_missing_data=false', t['name'], payload).json()
                        if 'series' in realtime_stat:
                            se_stat['series']['collItemRequest:AllSEs'].update(realtime_stat['series']['collItemRequest:AllSEs'])
                        for s in se_stat['series']['collItemRequest:AllSEs']:
                            if s in self.se_dict:
                                if t['name'] == 'admin' and s not in self.se_dict['admin_se']:
                                    continue
                                elif t['name'] != 'admin' and s in self.se_dict['admin_se']:
                                    continue
                                #if tenant != 'admin' and v in vs_dict['admin_vs']:
                                #    pass
                                #else:
                                else:
                                    se_name = self.se_dict[s]
                                    if se_name not in discovered_ses:
                                        discovered_ses.append(se_name)
                                        for entry in se_stat['series']['collItemRequest:AllSEs'][s]:
                                            if 'data' in entry:
                                                temp = {}
                                                temp['timestamp']=int(time.time())
                                                temp['se_name'] = se_name
                                                temp['tenant'] = t['name']
                                                temp['cloud'] = self.cloud_mapping[s]
                                                temp['avi_controller'] = self.avi_cluster_ip
                                                temp['metric_type'] = 'serviceengine_metrics'
                                                temp['metric_name'] = entry['header']['name']
                                                temp['metric_value'] = entry['data'][0]['value']
                                                event = helper.new_event(json.dumps(temp)+'\n')
                                                event.write_to(sys.stdout)
                temp_total_time = str(time.time()-temp_start_time)
                logging.info(self.avi_cluster_ip+': func srvc_engn_stats completed, executed in '+temp_total_time+' seconds')
            #except:
            #    pass




        #-----------------------------------
        #-----------------------------------
        #--- This function will loop through all tenants pulling the following statistics
        #--- for all Virtual Services.
        def virtual_service_stats_threaded(self):
            proc = []
            for t in self.tenants:
                t_name = t['name']
                p = Process(target = self.virtual_service_stats, args = (t_name,))
                p.start()
                proc.append(p)
            for p in proc:
                p.join()



        def virtual_service_stats(self,tenant):
                temp_start_time = time.time()
                #-----
                if tenant in self.vs_dict['tenants'] and self.vs_dict['tenants'][tenant]['count'] > 0:
                    endpoint_payload_list = []
                    payload =  {'metric_requests': [{'step' : 300, 'limit': 1, 'id': 'allvs', 'entity_uuid' : '*', 'metric_id': self.vs_metric_list}]}
                    vs_stats = self.avi_post('analytics/metrics/collection?pad_missing_data=false', tenant, payload).json()
                    #----- this pulls 1 min avg stats for vs that have realtime stats enabled
                    payload =  {'metric_requests': [{'step' : 5, 'limit': 1, 'id': 'allvs', 'entity_uuid' : '*', 'metric_id': self.vs_metric_list}]}
                    realtime_stats = self.avi_post('analytics/metrics/collection?pad_missing_data=false', tenant, payload).json()
                    #----- overwrites real time vs' 5 min avg with the 1 min avg
                    if 'series' in realtime_stats:
                        vs_stats['series']['allvs'].update(realtime_stats['series']['allvs'])
                    #----- THIS IS NEW
                    for v in vs_stats['series']['allvs']:
                        if v in self.vs_dict:
                            if tenant == 'admin' and v not in self.vs_dict['admin_vs']:
                                continue
                            elif tenant != 'admin' and v in self.vs_dict['admin_vs']:
                                continue
                            #if tenant != 'admin' and v in vs_dict['admin_vs']:
                            #    pass
                            #else:
                            else:
                                vs_uuid = v
                                vs_name = self.vs_dict[vs_uuid]
                                for m in vs_stats['series']['allvs'][v]:
                                    metric_name = m['header']['name']
                                    if 'data' in m:
                                        temp = {}
                                        temp['timestamp']=int(time.time())
                                        temp['tenant'] = tenant
                                        temp['cloud'] = self.cloud_mapping[vs_uuid]
                                        temp['vs_name'] = vs_name
                                        temp['avi_controller'] = self.avi_cluster_ip
                                        temp['metric_name'] = metric_name
                                        temp['metric_type'] = 'virtualservice_metrics'
                                        temp['metric_value'] = m['data'][0]['value']
                                        event = helper.new_event(json.dumps(temp)+'\n')
                                        event.write_to(sys.stdout)
                #-----------------------------------
                #----- SEND SUM OF VS_COUNT LIST - TOTAL NUMBER OF VS
                temp_total_time = str(time.time()-temp_start_time)
                logging.info(self.avi_cluster_ip+': func virtual_service_stats completed for tenant: '+tenant+', executed in '+temp_total_time+' seconds')





        def vs_metrics_per_se_threaded(self):
                temp_start_time = time.time()
                major,minor = self.login.json()['version']['Version'].rsplit('.',1)
                if (float(major) >= 17.2 and float(minor) >= 8) or float(major) >= 18.1: #----- controller metrics api introduced in 17.2.5
                    proc = []
                    for t in self.tenants:
                        if t['name'] in self.se_dict['tenants'] and self.se_dict['tenants'][t['name']]['count'] > 0:
                            p = Process(target = self.vs_metrics_per_se, args = (t['name'],))
                            p.start()
                            proc.append(p)
                        elif 'admin' in self.se_dict['tenants'] and self.se_dict['tenants']['admin']['count'] > 0:
                            p = Process(target = self.vs_metrics_per_se, args = (t['name'],))
                            p.start()
                            proc.append(p)
                    for p in proc:
                            p.join()
                    temp_total_time = str(time.time()-temp_start_time)
                    logging.info(self.avi_cluster_ip+': func vs_metrics_per_se_threaded completed, executed in '+temp_total_time+' seconds')




        def vs_metrics_per_se(self,tenant):
                temp_start_time = time.time()
                endpoint_payload_list = []
                payload =  {'metric_requests': [{'step' : 300, 'limit': 1, 'id': 'vs_metrics_by_se', 'entity_uuid' : '*', 'serviceengine_uuid': '*', 'include_refs': True, 'metric_id': self.vs_metric_list}]}
                vs_stats = self.avi_post('analytics/metrics/collection?pad_missing_data=false', tenant, payload).json()
                #----- this will pull 1 min stats for vs that have realtime stat enabled
                payload =  {'metric_requests': [{'step' : 5, 'limit': 1, 'id': 'vs_metrics_by_se', 'entity_uuid' : '*', 'serviceengine_uuid': '*', 'include_refs': True, 'metric_id': self.vs_metric_list}]}
                realtime_stats = self.avi_post('analytics/metrics/collection?pad_missing_data=false', tenant, payload).json()
                #----- overwrite 5 min avg stats with 1 min avg stats for vs that have realtime stats enabled
                if 'series' in realtime_stats:
                    vs_stats['series']['vs_metrics_by_se'].update(realtime_stats['series']['vs_metrics_by_se'])
                if len(vs_stats['series']['vs_metrics_by_se']) > 0:
                    for entry in vs_stats['series']['vs_metrics_by_se']:
                        if tenant == 'admin' and entry not in self.vs_dict['admin_vs']:
                            continue
                        elif tenant != 'admin' and entry in self.vs_dict['admin_vs']:
                            continue
                        else:
                            if entry in self.vs_dict:
                                vs_name = self.vs_dict[entry]
                                for d in vs_stats['series']['vs_metrics_by_se'][entry]:
                                    if 'data' in d:
                                        se_name = self.se_dict[d['header']['serviceengine_ref'].split('serviceengine/')[1]]
                                        temp = {}
                                        temp['timestamp']=int(time.time())
                                        temp['tenant'] = tenant
                                        temp['vs_name'] = vs_name
                                        temp['cloud'] = self.cloud_mapping[entry]
                                        temp['avi_controller'] = self.avi_cluster_ip
                                        temp['se_name'] = se_name
                                        temp['metric_type'] = 'virtualservice_metrics_per_serviceengine'
                                        temp['metric_name'] = d['header']['name']
                                        temp['metric_value'] = d['data'][0]['value']
                                        event = helper.new_event(json.dumps(temp)+'\n')
                                        event.write_to(sys.stdout)
                    temp_total_time = str(time.time()-temp_start_time)
                    logging.info(self.avi_cluster_ip+': func vs_metrics_per_se_threaded completed, executed in '+temp_total_time+' seconds')





        def vs_oper_status(self):
            temp_start_time = time.time()
            endpoint_payload_list = []
            vs_up_count = 0
            vs_down_count = 0
            vs_disabled_count = 0
            vs_count = 0
            for t in self.tenants:
                if t['name'] in self.vs_dict['tenants'] and self.vs_dict['tenants'][t['name']]['count'] > 0:
                    for v in self.vs_dict['tenants'][t['name']]['results']:
                        vs_name = v['config']['name']
                        metric_name = 'oper_status'
                        if v['runtime']['oper_status']['state'] == 'OPER_UP':
                            metric_value = 1
                            vs_up_count += 1
                        elif v['runtime']['oper_status']['state'] == 'OPER_DISABLED':
                            metric_value = 0
                            vs_down_count += 1
                            vs_disabled_count += 1
                        else:
                            metric_value = 0
                            vs_down_count += 1
                        temp = {}
                        temp['timestamp']=int(time.time())
                        temp['vs_name'] = vs_name
                        temp['tenant'] = t['name']
                        temp['avi_controller'] = self.avi_cluster_ip
                        temp['cloud'] = self.cloud_mapping[v['uuid']]
                        temp['metric_type'] = 'virtualservice_operstatus'
                        temp['metric_name'] = 'oper_status'
                        temp['metric_value'] = metric_value
                        event = helper.new_event(json.dumps(temp)+'\n')
                        event.write_to(sys.stdout)            
            #----- Starting here sending VS operstatus summary info
            temp = {}
            temp['timestamp']=int(time.time())
            temp['avi_controller'] = self.avi_cluster_ip
            #----- Total VS
            a = temp.copy()
            a['metric_name'] = 'count'
            a['metric_value'] = len(self.vs_dict) - 2
            a['metric_type'] = 'virtualservice_count'
            event = helper.new_event(json.dumps(a)+'\n')
            event.write_to(sys.stdout)       
            #----- Total VS UP
            b = temp.copy()
            b['metric_type'] = 'virtualservice_up'
            b['metric_name'] = 'status_up'
            b['metric_value'] = vs_up_count
            event = helper.new_event(json.dumps(b)+'\n')
            event.write_to(sys.stdout)  
            #----- Total VS Down
            c = temp.copy()
            c['metric_type'] = 'virtualservice_down'
            c['metric_name'] = 'status_down'
            c['metric_value'] = vs_down_count
            event = helper.new_event(json.dumps(c)+'\n')
            event.write_to(sys.stdout)  
            #----- Total VS Disabled
            d = temp.copy()
            d['metric_type'] = 'virtualservice_disabled'
            d['metric_name'] = 'status_disabled'
            d['metric_value'] = vs_disabled_count
            event = helper.new_event(json.dumps(d)+'\n')
            event.write_to(sys.stdout)  
            temp_total_time = str(time.time()-temp_start_time)
            if args.debug == True:
                print(str(datetime.now())+' '+self.avi_cluster_ip+': func vs_oper_status completed, executed in '+temp_total_time+' seconds')






        #----- PULL VS HEALTHSCORES
        def vs_se_healthscores(self):
            #----- PULL VS HEALTHSCORES
            #try:
                temp_start_time = time.time()
                discovered_vs = []
                discovered_se = []
                for t in self.tenants:
                    if t['name'] in self.vs_dict['tenants'] and self.vs_dict['tenants'][t['name']]['count'] > 0:
                        for v in self.vs_dict['tenants'][t['name']]['results']:
                            if v['uuid'] not in discovered_vs:
                                discovered_vs.append(v['uuid'])
                                vs_name = v['config']['name']
                                temp_dict = {}
                                temp_dict['healthscore'] = v['health_score']['health_score']
                                temp_dict['resources_penalty'] = v['health_score']['resources_penalty']
                                temp_dict['anomaly_penalty'] = v['health_score']['anomaly_penalty']
                                temp_dict['performance_score'] = v['health_score']['performance_score']
                                temp_dict['security_penalty'] = v['health_score']['security_penalty']
                                for h in temp_dict:
                                    vs_healthscore = v['health_score']['health_score']
                                    temp = {}
                                    temp['timestamp']=int(time.time())
                                    temp['tenant'] = t['name']
                                    temp['cloud'] = self.cloud_mapping[v['uuid']]
                                    temp['metric_name'] = h
                                    temp['avi_controller'] = self.avi_cluster_ip
                                    temp['vs_name'] = vs_name
                                    temp['metric_type'] = 'virtualservice_healthscore'
                                    temp['metric_value'] = temp_dict[h]
                                    event = helper.new_event(json.dumps(temp)+'\n')
                                    #ew.write_event(event)
                                    event.write_to(sys.stdout)
                    if t['name'] in self.se_dict['tenants'] and self.se_dict['tenants'][t['name']]['count'] > 0:
                        for s in self.se_dict['tenants'][t['name']]['results']:
                            if s['uuid'] not in discovered_se:
                                discovered_se.append(s['uuid'])
                                se_healthscore = s['health_score']['health_score']
                                temp1_dict = {}
                                temp1_dict['healthscore'] = s['health_score']['health_score']
                                temp1_dict['resources_penalty'] = s['health_score']['resources_penalty']
                                temp1_dict['anomaly_penalty'] = s['health_score']['anomaly_penalty']
                                temp1_dict['performance_score'] = s['health_score']['performance_score']
                                temp1_dict['security_penalty'] = s['health_score']['security_penalty']
                                for h in temp1_dict:
                                    temp = {}
                                    temp['timestamp']=int(time.time())
                                    temp['tenant'] = t['name']
                                    temp['cloud'] = self.cloud_mapping[s['uuid']]
                                    temp['metric_name'] = h
                                    temp['avi_controller'] = self.avi_cluster_ip
                                    temp['se_name'] = self.se_dict[s['uuid']]
                                    temp['metric_type'] = 'serviceengine_healthscore'
                                    temp['metric_value'] = temp1_dict[h]
                                    event = helper.new_event(json.dumps(temp)+'\n')
                                    event.write_to(sys.stdout)
                temp_total_time = str(time.time()-temp_start_time)
                logging.info(self.avi_cluster_ip+': func vs_healthscores completed, executed in '+temp_total_time+' seconds')
            #except:
            #    pass







        #-----------------------------------
        #----- GET Pool Member specific statistics
        def pool_server_stats_threaded(self):
            #try:
                temp_start_time = time.time()
                proc = []
                for t in self.tenants:
                    if t['name'] in self.pool_dict['tenants'] and self.pool_dict['tenants'][t['name']]['count'] > 0:
                        p = Process(target = self.pool_server_stats, args = (t['name'],))
                        p.start()
                        proc.append(p)
                    elif 'admin' in self.pool_dict['tenants'] and self.pool_dict['tenants']['admin']['count'] > 0:
                        p = Process(target = self.pool_server_stats, args = (t['name'],))
                        p.start()
                        proc.append(p)
                for p in proc:
                        p.join()
                temp_total_time = str(time.time()-temp_start_time)
                logging.info(self.avi_cluster_ip+': func pool_server_stats_threaded completed, executed in '+temp_total_time+' seconds')
            #except:
            #    exception_text = traceback.format_exc()
            #    print(str(datetime.now())+' '+self.avi_cluster_ip+': '+exception_text)





        #-----------------------------------
        #----- GET Pool Member specific statistics
        def pool_server_stats(self,tenant):
            #try:
                temp_start_time = time.time()
                endpoint_payload_list = []
                discovered_servers = []
                payload = {
                    "metric_requests": [
                        {
                            "step": 300,
                            "limit": 1,
                            "aggregate_entity": False,
                            "entity_uuid": "*",
                            "obj_id": "*",
                            "pool_uuid": "*",
                            "id": "collItemRequest:AllServers",
                            "metric_id": self.pool_server_metric_list
                        }
                        ]}
                dimension_limit = str(len(self.pool_dict)*len(self.pool_server_metric_list))
                api_url = 'analytics/metrics/collection?pad_missing_data=false&dimension_limit=%s&include_name=true&include_refs=true' %dimension_limit
                resp = self.avi_post(api_url,tenant,payload).json()
                if 'series' in resp:
                    if len(resp['series']['collItemRequest:AllServers']) != 0:
                        for p in resp['series']['collItemRequest:AllServers']:
                            if p not in discovered_servers:
                                discovered_servers.append(p)
                                server_object = p.split(',')[2]
                                for d in resp['series']['collItemRequest:AllServers'][p]:
                                    if 'data' in d:
                                        pool_name = d['header']['pool_ref'].rsplit('#',1)[1]
                                        metric_name = d['header']['name']
                                        temp_payload = {}
                                        temp_payload['timestamp']=int(time.time())
                                        temp_payload['avi_controller'] = self.avi_cluster_ip
                                        temp_payload['pool_name'] = pool_name
                                        temp_payload['tenant'] = tenant
                                        temp_payload['cloud'] = self.cloud_mapping[d['header']['pool_ref'].split('/pool/')[1].split('#')[0]]
                                        temp_payload['pool_member'] = server_object
                                        temp_payload['metric_type'] = 'pool_member_metrics'
                                        temp_payload['metric_name'] = metric_name
                                        temp_payload['metric_value'] = d['data'][0]['value']
                                        if 'entity_ref' in d['header']:
                                            vs_name = d['header']['entity_ref'].rsplit('#',1)[1]
                                            temp_payload['vs_name'] = vs_name
                                            event = helper.new_event(json.dumps(temp_payload)+'\n')
                                            event.write_to(sys.stdout)
                                        else:
                                            if tenant in self.pool_dict['tenants']:
                                                for x in self.pool_dict['tenants'][tenant]['results']:
                                                    if x['config']['name'] == pool_name:
                                                        for v in x['virtualservices']:
                                                            vs_name = self.vs_dict[v.split('/api/virtualservice/')[1]]
                                                            temp_payload1 = temp_payload.copy()
                                                            temp_payload1['vs_name'] = vs_name
                                                            event = helper.new_event(json.dumps(temp_payload1)+'\n')
                                                            event.write_to(sys.stdout)
                temp_total_time = str(time.time()-temp_start_time)
                logging.info(self.avi_cluster_ip+': func pool_server_stats for tenant '+tenant+', executed in '+temp_total_time+' seconds')
            #except:
                    #print(str(datetime.now())+' '+self.avi_cluster_ip+': func pool_server_stats  encountered an error for tenant '+tenant)
                    #exception_text = traceback.format_exc()
                    #print(str(datetime.now())+' '+self.avi_cluster_ip+': '+exception_text)










        #-----------------------------------
        #----- GET controller member statistics
        def controller_cluster_metrics(self):
            #try:
                temp_start_time = time.time()
                major,minor = self.login.json()['version']['Version'].rsplit('.',1)
                if (float(major) >= 17.2 and float(minor) >= 6) or float(major) >= 18.1: #----- controller metrics api introduced in 17.2.6
                    cluster= self.avi_request('cluster','admin').json()
                    cluster_nodes = {}
                    cluster_labels = {}
                    temp_list=[]
                    endpoint_payload_list = []
                    for c in cluster['nodes']:
                        cluster_nodes[c['vm_uuid']]=c['ip']['addr']
                        cluster_labels[c['vm_uuid']]=c['name']
                        #cluster_nodes[c['vm_uuid']]=c['vm_hostname']
                        resp = self.avi_request('analytics/metrics/controller/%s/?metric_id=%s&limit=1&step=300&?aggregate_entity=False' %(c['vm_uuid'],self.controller_metric_list),'admin').json()
                        temp_list.append(resp)
                    for n in temp_list:
                        node = cluster_nodes[n['entity_uuid']]
                        for m in n['series']:
                            temp = {}
                            temp['timestamp']=int(time.time())
                            temp['metric_name'] = m['header']['name']
                            temp['controller_name'] = node
                            temp['controller_label'] = cluster_labels[n['entity_uuid']]
                            temp['avi_controller'] = self.avi_cluster_ip
                            temp['metric_type'] = 'controller_metrics'
                            temp['metric_value'] = m['data'][0]['value']
                            event = helper.new_event(json.dumps(temp)+'\n')
                            event.write_to(sys.stdout)
                temp_total_time = str(time.time()-temp_start_time)
                logging.info(self.avi_cluster_ip+': func controller_cluster_metrics completed, executed in '+temp_total_time+' seconds')
            #except:
            #    pass





        #-----------------------------------
        def license_usage(self):
            temp_start_time = time.time()
            licensing = self.avi_request('licenseusage?limit=1&step=300','admin').json()
            lic_cores = None
            lic_sockets = None
            if 'licensed_cores' in licensing:    
                lic_cores = licensing['licensed_cores']
            if 'licensed_sockets' in licensing:    
                lic_sockets = licensing['licensed_sockets']
            if lic_cores != None and lic_cores > 0:
                cores_used = licensing['num_se_vcpus']
                percentage_used = (cores_used / float(lic_cores))*100
                temp = {}
                temp['timestamp']=int(time.time())
                temp['metric_type'] = 'licensing'
                temp['avi_controller'] = self.avi_cluster_ip
                temp['metric_name'] = 'licensed_cores'
                temp['metric_value'] = lic_cores
                event = helper.new_event(json.dumps(temp)+'\n')
                event.write_to(sys.stdout)
                #-----
                temp1 = {}
                temp1['timestamp']=int(time.time())
                temp1['metric_type'] = 'licensing'
                temp1['avi_controller'] = self.avi_cluster_ip
                temp1['metric_name'] = 'used_cores'
                temp1['metric_value'] = cores_used
                event = helper.new_event(json.dumps(temp1)+'\n')
                event.write_to(sys.stdout)
                #-----
                temp2 = {}
                temp2['timestamp']=int(time.time())
                temp2['metric_type'] = 'licensing'
                temp2['avi_controller'] = self.avi_cluster_ip
                temp2['metric_name'] = 'percentage_cores_used'
                temp2['metric_value'] = percentage_used
                event = helper.new_event(json.dumps(temp2)+'\n')
                event.write_to(sys.stdout)
            if lic_sockets != None and lic_sockets > 0:
                sockets_used = licensing['num_sockets']
                percentage_used = (sockets_used / float(lic_sockets))*100
                temp = {}
                temp['timestamp']=int(time.time())
                temp['metric_type'] = 'licensing'
                temp['avi_controller'] = self.avi_cluster_ip
                temp['metric_name'] = 'licensed_sockets'
                temp['metric_value'] = lic_sockets
                event = helper.new_event(json.dumps(temp)+'\n')
                event.write_to(sys.stdout)
                #-----
                temp1 = {}
                temp1['timestamp']=int(time.time())
                temp1['metric_type'] = 'licensing'
                temp1['avi_controller'] = self.avi_cluster_ip
                temp1['metric_name'] = 'used_sockets'
                temp1['metric_value'] = sockets_used
                event = helper.new_event(json.dumps(temp1)+'\n')
                event.write_to(sys.stdout)
                #-----
                temp2 = {}
                temp2['timestamp']=int(time.time())
                temp2['metric_type'] = 'licensing'
                temp2['avi_controller'] = self.avi_cluster_ip
                temp2['metric_name'] = 'percentage_sockets_used'
                temp2['metric_value'] = percentage_used
                event = helper.new_event(json.dumps(temp2)+'\n')
                event.write_to(sys.stdout)
            temp_total_time = str(time.time()-temp_start_time)
            logging.info(self.avi_cluster_ip+': func license_usage completed, executed in '+temp_total_time+' seconds')








        def gather_metrics(self):
            #try:
                logging.info(self.avi_cluster_ip+': Starting Avi Metrics Data Input Script')
                start_time = time.time()
                self.login = self.avi_login()
                if self.login.status_code == 200:
                    #self.avi_controller = self.controller_to_poll()
                    self.avi_controller = self.avi_cluster_ip
                    self.tenants = self.return_tenants()
                    self.vs_dict, self.se_dict, self.pool_dict, self.seg_dict, self.cloud_mapping = self.gen_inventory_dict()
                    #self.vs_dict, self.se_dict = self.gen_inventory_dict()
                    #---- remove metrics that are not available in the current version
                    self.vs_metric_list, self.se_metric_list, self.controller_metric_list, self.pool_server_metric_list = self.remove_version_specific_metrics()
                    #----- Do not remove
                    event = helper.new_event('Avi metric script starting\n')
                    ew.write_event(event)
                    #-----------------------------------
                    #----- Add Test functions to list for threaded execution
                    #-----------------------------------
                    test_functions = []
                    test_functions.append(self.srvc_engn_stats)
                    test_functions.append(self.virtual_service_stats_threaded)
                    test_functions.append(self.vs_metrics_per_se_threaded)
                    test_functions.append(self.vs_se_healthscores)
                    test_functions.append(self.controller_cluster_metrics)
                    test_functions.append(self.pool_server_stats_threaded)
                    test_functions.append(self.license_usage)
                    #-----------------------------------
                    #-----------------------------------
                    #-----
                    #-----------------------------------
                    #----- BEGIN Running Test Functions
                    #-----------------------------------
                    proc = []
                    for f in test_functions:
                        p = Process(target = f, args = ())
                        p.start()
                        proc.append(p)
                    for p in proc:
                        p.join()
                    #-----------------------------------
                    #-----
                    #-----------------------------------
                    #----- Log time it took to execute script
                    #-----------------------------------
                    total_time = str(time.time()-start_time)
                    logging.info(self.avi_cluster_ip+': Finished Avi Metrics Data Input Script, executed in '+total_time+' seconds')
                elif self.login.status_code == 'timedout':
                    logging.error(self.avi_cluster_ip+': AVI ERROR: timeout trying to access '+self.avi_cluster_ip)
                elif self.login.status_code == '401':
                    logging.error(self.avi_cluster_ip+': AVI ERROR: unable to login to '+self.avi_cluster_ip+' : '+self.login.text)
                else:
                    logging.error(self.avi_cluster_ip+': AVI ERROR: unknown login error to '+self.avi_cluster_ip)
            #except:
            #    pass


        def run(self):
            self.gather_metrics()


    fdir = os.path.abspath(os.path.dirname(__file__))
    c = avi_metrics_splunk(avi_controller, avi_user, avi_pass)
    c.run()
    sys.exit(0)


