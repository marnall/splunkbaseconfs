from connect import *
import requests
import json

all_ifs = '/nos/api/cfg/interface/'
stats = '/nos/api/info/statistics/interface/'

#Class with methods to get/set physical port properties
class Interfaces:
    #This API will get properties names of all interfaces
    def get_interfaces(self, conn):
        '''
        API's description: This API will get names of all ethernet interfaces
        Mandatory arguments: None
        Output: List or dictionary of interface properties
        '''
        tmp_url=form_url(conn, all_ifs)
        hdr = form_hdr(conn)
        (ret, report) = conn.get(all_ifs)
        interfaces = []
        if (report == None):
           return None
        for obj in report:
#           interfaces.append(obj.get('if_name'))
           interfaces.append(obj)
        return interfaces   

    #This API will get names of all link up ethernet interface
    def get_link_up_interfaces(self, conn):
        '''
        API's description: This API will get names of link up ethernet interfaces
        Mandatory arguments: None
        Output: List or dictionary of interface properties
        '''
        tmp_url=form_url(conn, all_ifs)
        hdr = form_hdr(conn)
        (ret, report) = conn.get(all_ifs)
        if (ret):
           interfaces = []
           for obj in report:
              if obj.get('oper_state') == 'up':
                  interfaces.append(obj)
           return interfaces   
        return None

class InterfaceStat:
     def __init__(self,params):
         self.name = params['name']
         self.last_stats = {'rx_pkts':0, 'rx_bcast':0, 'rx_ucast':0, 'rx_mcast':0, 'rx_errors':0,'tx_pkts':0,
                            'tx_bcast':0, 'tx_ucast':0, 'tx_mcast':0, 'tx_errors':0, 'rx_discards':0, 'tx_discards':0,
                            'tx_pkts_0_to_64_bytes':0, 'rx_pkts_0_to_64_bytes':0, 'tx_pkts_65_to_127_bytes':0,
                            'rx_pkts_65_to_127_bytes':0, 'tx_pkts_128_to_255_bytes':0, 'rx_pkts_128_to_255_bytes':0,
                            'rx_pkts_256_to_511_bytes':0, 'tx_pkts_256_to_511_bytes':0, 'rx_pkts_512_to_1023_bytes':0,
                            'tx_pkts_512_to_1023_bytes':0, 'rx_pkts_1024_to_1518_bytes':0, 'tx_pkts_1024_to_1518_bytes':0,
                            'rx_pkts_1519_to_1548_bytes':0, 'tx_pkts_1519_to_1548_bytes':0 ,'rx_bit_rate':0, 'tx_bit_rate':0}

     #This API will get interface statistical counters
     def get_all_stats(self, conn, if_name):
        '''
        API's description: This API will get all interface statisitics (rx and tx)
        Currently only support etherent interface
        Mandatory arguments:  if_name(Str)
        Optional arguments: None
        Output: Dictionary of interface statistical counters
        '''
        if if_name == None:
           return None
        name = if_name.replace("/", "%2F")

        (ret, report) = conn.get(stats + name)
        if (ret == 0):
            return None
        if_stats = dict()
        #Rx Stats
        if_stats['rx_pkts'] = report['rx_pkts']
        if_stats['rx_bcast'] = report['rx_bcast_pkts']
        if_stats['rx_ucast'] = report['rx_ucast_pkts']
        if_stats['rx_mcast'] = report['rx_mcast_pkts']
        if_stats['rx_errors'] = report['rx_errors'] 
        if_stats['rx_discards'] = report['rx_input_discards'] 
        if_stats['rx_pkts_0_to_64_bytes'] = report['rx_pkts_0_to_64_bytes']
        if_stats['rx_pkts_65_to_127_bytes'] = report['rx_pkts_65_to_127_bytes']
        if_stats['rx_pkts_128_to_255_bytes'] = report['rx_pkts_128_to_255_bytes']
        if_stats['rx_pkts_256_to_511_bytes'] = report['rx_pkts_256_to_511_bytes']
        if_stats['rx_pkts_512_to_1023_bytes'] = report['rx_pkts_512_to_1023_bytes']
        if_stats['rx_pkts_1024_to_1518_bytes'] = report['rx_pkts_1024_to_1518_bytes']
        if_stats['rx_pkts_1519_to_1548_bytes'] = report['rx_pkts_1519_to_1548_bytes']
        if_stats['rx_oversize'] = report['rx_oversize_pkts']
        if_stats['rx_bit_rate'] = report['rx_bit_rate']

        #Tx Stats
        if_stats['tx_pkts'] = report['tx_pkts']
        if_stats['tx_bcast'] = report['tx_bcast_pkts']
        if_stats['tx_ucast'] = report['tx_ucast_pkts']
        if_stats['tx_mcast'] = report['tx_mcast_pkts']
        if_stats['tx_errors'] = report['tx_errors'] 
        if_stats['tx_discards'] = report['tx_dropped']
        if_stats['tx_pkts_0_to_64_bytes'] = report['tx_pkts_0_to_64_bytes']
        if_stats['tx_pkts_65_to_127_bytes'] = report['tx_pkts_65_to_127_bytes']
        if_stats['tx_pkts_128_to_255_bytes'] = report['tx_pkts_128_to_255_bytes']
        if_stats['tx_pkts_256_to_511_bytes'] = report['tx_pkts_256_to_511_bytes']
        if_stats['tx_pkts_512_to_1023_bytes'] = report['tx_pkts_512_to_1023_bytes']
        if_stats['tx_pkts_1024_to_1518_bytes'] = report['tx_pkts_1024_to_1518_bytes']
        if_stats['tx_pkts_1519_to_1548_bytes'] = report['tx_pkts_1519_to_1548_bytes']
        if_stats['tx_oversize'] = report['tx_oversize_pkts']
        if_stats['tx_bit_rate'] = report['tx_bit_rate']
        return if_stats

     #This API will get rx interface statistics
     def get_rx_stats(self, conn, if_name):
        '''
        API's description: This API will get rx interface statisitics 
        Currently only support etherent interface
        Mandatory arguments:  if_name(Str)
        Optional arguments: None
        Output: Dictionary of interface statistical counters
        '''
        tmp_url=form_url(conn, stats)
        if if_name == None:
           return None
        name = if_name.replace("/", "%2F")

        tmp_url = tmp_url + name
        hdr = form_hdr(conn)
        ret = requests.get(tmp_url, headers=hdr, auth=(conn.user, conn.password), verify=False, timeout=10)
        report = ret.json()
        if_stats = dict()
        #Rx Stats
        if_stats['rx_pkts'] = report['rx_pkts']
        self.last_rx_stats['rx_pkts'] = report['rx_pkts']

        if_stats['rx_bcast'] = report['rx_bcast_pkts']
        self.last_rx_stats['rx_bcast'] = report['rx_bcast_pkts']

        if_stats['rx_ucast'] = report['rx_ucast_pkts']
        self.last_rx_stats['rx_ucast'] = report['rx_ucast_pkts']

        if_stats['rx_mcast'] = report['rx_mcast_pkts']
        self.last_rx_stats['rx_mcast'] = report['rx_mcast_pkts']

        if_stats['rx_errors'] = report['rx_errors'] 
        self.last_rx_stats['rx_errors'] = report['rx_errors']

        if_stats['rx_discards'] = report['rx_discards'] 
        self.last_rx_stats['rx_discards'] = report['rx_discards']

        if_stats['rx_pkts_0_to_64_bytes'] = report['rx_pkts_0_to_64_bytes'] 
        self.last_rx_stats['rx_pkts_0_to_64_bytes'] = report['rx_pkts_0_to_64_bytes']

        if_stats['rx_pkts_65_to_127_bytes'] = report['rx_pkts_65_to_127_bytes'] 
        self.last_rx_stats['rx_pkts_65_to_127_bytes'] = report['rx_pkts_65_to_127_bytes']

        if_stats['rx_pkts_128_to_255_bytes'] = report['rx_pkts_128_to_255_bytes'] 
        self.last_rx_stats['rx_pkts_128_to_255_bytes'] = report['rx_pkts_128_to_255_bytes']

        if_stats['rx_pkts_256_to_511_bytes'] = report['rx_pkts_256_to_511_bytes'] 
        self.last_rx_stats['rx_pkts_256_to_511_bytes'] = report['rx_pkts_256_to_511_bytes']

        if_stats['rx_pkts_512_to_1023_bytes'] = report['rx_pkts_512_to_1023_bytes'] 
        self.last_rx_stats['rx_pkts_512_to_1023_bytes'] = report['rx_pkts_512_to_1023_bytes']

        if_stats['rx_pkts_1024_to_1518_bytes'] = report['rx_pkts_1024_to_1518_bytes'] 
        self.last_rx_stats['rx_pkts_1024_to_1518_bytes'] = report['rx_pkts_1024_to_1518_bytes']

        if_stats['rx_pkts_1519_to_1548_bytes'] = report['rx_pkts_1519_to_1548_bytes'] 
        self.last_rx_stats['rx_pkts_1519_to_1548_bytes'] = report['rx_pkts_1519_to_1548_bytes']

        return if_stats

     #This API will get interface tx statistics 
     def get_tx_stats(self, conn, if_name):
        '''
        API's description: This API will get tx interface statisitics
        Currently only support etherent interface
        Mandatory arguments:  if_name(Str)
        Optional arguments: None
        Output: Dictionary of interface statistical counters
        '''
        tmp_url=form_url(conn, stats)
        if if_name == None:
           return None
        name = if_name.replace("/", "%2F")

        tmp_url = tmp_url + name
        hdr = form_hdr(conn)
        ret = requests.get(tmp_url, headers=hdr, auth=(conn.user, conn.password), verify=False, timeout=10)
        report = ret.json()
        if_stats = dict()

        #Tx Stats
        if_stats['tx_pkts'] = report['tx_pkts']
        self.last_tx_stats['tx_pkts'] = report['tx_pkts']

        if_stats['tx_bcast'] = report['tx_bcast_pkts']
        self.last_tx_stats['tx_bcast'] = report['tx_bcast_pkts']

        if_stats['tx_ucast'] = report['tx_ucast_pkts']
        self.last_tx_stats['tx_ucast'] = report['tx_ucast_pkts']

        if_stats['tx_mcast'] = report['tx_mcast_pkts']
        self.last_tx_stats['tx_mcast'] = report['tx_mcast_pkts']

        if_stats['tx_errors'] = report['tx_errors'] 
        self.last_tx_stats['tx_errors'] = report['tx_errors']

        if_stats['tx_discards'] = report['tx_discards'] 
        self.last_tx_stats['tx_discards'] = report['tx_discards']

        if_stats['tx_pkts_0_to_64_bytes'] = report['tx_pkts_0_to_64_bytes'] 
        self.last_tx_stats['tx_pkts_0_to_64_bytes'] = report['tx_pkts_0_to_64_bytes']

        if_stats['tx_pkts_65_to_127_bytes'] = report['tx_pkts_65_to_127_bytes'] 
        self.last_tx_stats['tx_pkts_65_to_127_bytes'] = report['tx_pkts_65_to_127_bytes']

        if_stats['tx_pkts_128_to_255_bytes'] = report['tx_pkts_128_to_255_bytes'] 
        self.last_tx_stats['tx_pkts_128_to_255_bytes'] = report['tx_pkts_128_to_255_bytes']

        if_stats['tx_pkts_256_to_511_bytes'] = report['tx_pkts_256_to_511_bytes'] 
        self.last_tx_stats['tx_pkts_256_to_511_bytes'] = report['tx_pkts_256_to_511_bytes']

        if_stats['tx_pkts_512_to_1023_bytes'] = report['tx_pkts_512_to_1023_bytes'] 
        self.last_tx_stats['tx_pkts_512_to_1023_bytes'] = report['tx_pkts_512_to_1023_bytes']

        if_stats['tx_pkts_1024_to_1518_bytes'] = report['tx_pkts_1024_to_1518_bytes'] 
        self.last_tx_stats['tx_pkts_1024_to_1518_bytes'] = report['tx_pkts_1024_to_1518_bytes']

        if_stats['tx_pkts_1519_to_1548_bytes'] = report['tx_pkts_1519_to_1548_bytes'] 
        self.last_tx_stats['tx_pkts_1519_to_1548_bytes'] = report['tx_pkts_1519_to_1548_bytes']
        return if_stats

     #This API will get interface statistical counters
     def get_rx_tx_traffic_rate(self, conn, if_name):
        '''
        API's description: This API will get interface traffic rate 
        Mandatory arguments:  if_name(Str)
        Optional arguments: None
        Output: Dictionary of interface statistical rate (every 30 seconds)
        '''
        tmp_url=form_url(conn, stats)
        if if_name == None:
           return None
        name = if_name.replace("/", "%2F")

        tmp_url = tmp_url + name
        hdr = form_hdr(conn)
        ret = requests.get(tmp_url, headers=hdr, auth=(conn.user, conn.password), verify=False, timeout=10)
        report = ret.json()
        if_stats = dict()
        #Rx Stats
        if_rate['rx_rate'] = report['rx_rate']
        if_rate['tx_rate'] = report['tx_rate']
        return if_rate
