import sys
import json
from interface import *
import time
from logger import *


def get_device_iface_lldp_in_interval(conn, iface, interval):
   if iface == None:
      ifinfo = Interfaces()
      ifacelist = ifinfo.get_link_up_interfaces(conn)
   else:
      ifacelist = iface

   for obj in ifacelist:
      ifname = obj.get('if_name') 
      rpt = get_lldp_intf_stats_in_interval(conn, ifname, interval)

def get_device_traffic_utilization(conn, interval):
   '''
   API's description: This API will form and write splunk log message
   '''
   switch = TrafficUtilization(interval)
   switch_util = switch.get_device_traffic_utilization(conn)    
   return switch_util

def get_sim_device_traffic_instance(conn, traffic, traffic_prev):
   lentraffic = len(traffic) 
   if traffic_prev is None:
       traffic_prev = []
       for ilen in range(0, lentraffic):
           traffic_prev_rpt  = dict()
           traffic_prev_rpt['rpt'] = {'rx_pkts_256_to_511_bytes': '0', 'tx_discards': '0', 'rx_bcast': '0', 'rx_pkts': '0', 'tx_mcast': '0','rx_ucast': '0', 'rx_pkts_65_to_127_bytes': '0', 'rx_pkts_1519_to_1548_bytes': '0', 'rx_pkts_0_to_64_bytes': '0', 'tx_pkts_1519_to_1548_bytes': '0', 'tx_pkts_256_to_511_bytes': '0', 'rx_pkts_128_to_255_bytes': '0', 'rx_oversize': '0', 'tx_pkts_65_to_127_bytes': '0', 'rx_mcast': '0', 'tx_ucast': '0', 'tx_pkts_512_to_1023_bytes':'0', 'rx_discards': '0', 'tx_bcast': '0', 'tx_errors': '0', 'rx_pkts_1024_to_1518_bytes': '0', 'tx_pkts_128_to_255_bytes':'0', 'tx_oversize': '0', 'tx_pkts_1024_to_1518_bytes': '0', 'tx_pkts_0_to_64_bytes': '0', 'rx_pkts_512_to_1023_bytes': '0', 'rx_errors': '0', 'tx_pkts': '0'} 
           traffic_prev.append(traffic_prev_rpt)
   rptlist = []
   for ilen in range(0, lentraffic):
        rpt = dict()
        intf = traffic[ilen] 
        rprev = traffic_prev[ilen]
        prev = rprev['rpt']
        rpt['interface'] = intf['interface']
        rpt['speed'] = intf['speed']
        rx = intf['RxRate']
        tx = intf['TxRate']
        rxpkts = rx['pps']
        txpkts = tx['pps']
        rptd = dict()
        rptd['rx_pkts'] = str (rxpkts + int(prev['rx_pkts'])) 
        rptd['tx_pkts'] = str(txpkts + int(prev['rx_pkts']))
        rptd['rx_bcast'] = '0'
        rptd['tx_bcast'] = '0'
        if ('ucast' in rx):
            rptd['rx_ucast'] =  str (int(((rx['ucast'] * 0.01)) * rxpkts) + int(prev['rx_ucast']))
        else:
            rptd['rx_ucast'] = '0'
        if ('mcast' in rx):
            rptd['rx_mcast'] =  str (int(((rx['mcast'] * 0.01)) * rxpkts) + int(prev['rx_mcast']))
        else:
            rptd['rx_mcast'] = '0'
        if ('ucast' in tx):
            rptd['tx_ucast'] = str (int(((tx['ucast'] *  0.01)) * txpkts) + int(prev['tx_ucast']))
        else:
            rptd['tx_ucast'] = '0'
        if ('mcast' in tx):
            rptd['tx_mcast'] = str (int(((tx['mcast'] * 0.01)) * txpkts) + int(prev['tx_mcast']))
        else:
            rptd['tx_mcast'] = '0'
        if ('discards' in rx):
            rptd['rx_discards'] = str (int(((rx['discards'] * 0.01)) * rxpkts) + int(prev['rx_discards']))
        else:
            rptd['rx_discards'] = '0'
        if ('discards' in tx):
            rptd['tx_discards'] = str (int(((tx['discards'] * 0.01)) * txpkts) + int(prev['tx_discards']))
        else:
            rptd['tx_discards'] = 0
        if ('errors' in rx):
            rptd['rx_errors'] = str (int(((rx['errors'] * 0.01)) * rxpkts) + int(prev['rx_errors']))
        else:
            rptd['rx_errors'] = 0
        if ('errors' in tx):
            rptd['tx_errors'] = str (int(((tx['errors'] * 0.01)) * txpkts) + int(prev['tx_errors']))
        else:
            rptd['tx_errors'] = 0
        rptd['rx_oversize'] = 0
        rptd['tx_oversize'] = 0
        if ('0-64' in rx):
            rptd['rx_pkts_0_to_64_bytes'] = str (int(((rx['0-64'] * 0.01)) * rxpkts) + int(prev['rx_pkts_0_to_64_bytes']))
        else:
            rptd['rx_pkts_0_to_64_bytes'] = 0
        if ('0-64' in tx):
            rptd['tx_pkts_0_to_64_bytes'] = str (int(((tx['0-64'] * 0.01)) * txpkts) + int(prev['tx_pkts_0_to_64_bytes']))
        else:
            rptd['tx_pkts_0_to_64_bytes'] = 0
        if ('65-127' in rx):
            rptd['rx_pkts_65_to_127_bytes'] = str (int(((rx['65-127'] * 0.01)) * rxpkts) + int(prev['rx_pkts_65_to_127_bytes']))
        else:
            rptd['rx_pkts_65_to_127_bytes'] = 0
        if ('65-127' in tx):
            rptd['tx_pkts_65_to_127_bytes'] = str (int(((tx['65-127'] * 0.01)) * txpkts) + int(prev['tx_pkts_65_to_127_bytes']))
        else:
            rptd['65_to_127_bytes'] = 0
        if ('128-255' in rx):
            rptd['rx_pkts_128_to_255_bytes'] = str (int(((rx['128-255'] * 0.01)) * rxpkts) + int(prev['rx_pkts_128_to_255_bytes']))
        else:
            rptd['rx_pkts_128_to_255_bytes'] = 0
        if ('128-255' in tx):
            rptd['tx_pkts_128_to_255_bytes'] = str (int(((tx['128-255'] * 0.01)) * txpkts) + int(prev['tx_pkts_128_to_255_bytes']))
        else:
            rptd['tx_pkts_128_to_255_bytes'] = 0
        if ('256-511' in rx):
            rptd['rx_pkts_256_to_511_bytes'] = str (int(((rx['256-511'] * 0.01)) * rxpkts) + int(prev['rx_pkts_256_to_511_bytes']))
        else:
            rptd['rx_pkts_256_to_511_bytes'] = 0
        if ('256-511' in tx):
            rptd['tx_pkts_256_to_511_bytes'] = str (int(((tx['256-511'] * 0.01)) * txpkts) + int(prev['tx_pkts_256_to_511_bytes']))
        else:
            rptd['tx_pkts_256_to_511_bytes'] = 0
        if ('512-1023' in rx):
            rptd['rx_pkts_512_to_1023_bytes'] = str (int(((rx['512-1023'] * 0.01)) * rxpkts) + int(prev['rx_pkts_512_to_1023_bytes']))
        else:
            rptd['rx_pkts_512_to_1023_bytes'] = 0
        if ('512-1023' in tx):
            rptd['tx_pkts_512_to_1023_bytes'] = str (int(((tx['512-1023'] * 0.01)) * txpkts) + int(prev['tx_pkts_512_to_1023_bytes']))
        else:
            rptd['tx_pkts_512_to_1023_bytes'] = 0
        if ('1024-1518' in rx):
            rptd['rx_pkts_1024_to_1518_bytes'] = str (int(((rx['1024-1518'] * 0.01)) * rxpkts) + int(prev['rx_pkts_1024_to_1518_bytes']))
        else:
            rptd['rx_pkts_1024_to_1518_bytes'] = 0
        if ('1024-1518' in tx):
            rptd['tx_pkts_1024_to_1518_bytes'] = str (int(((tx['1024-1518'] * 0.01)) * txpkts) + int(prev['tx_pkts_1024_to_1518_bytes']))
        else:
            rptd['tx_pkts_1024_to_1518_bytes'] = 0
        if ('1519-1548' in rx):
            rptd['rx_pkts_1519_to_1548_bytes'] = str (int(((rx['1519-1548'] * 0.01)) * rxpkts) + int(prev['rx_pkts_1519_to_1548_bytes']))
        else:
            rptd['rx_pkts_1519_to_1548_bytes'] = 0
        if ('1519-1548' in tx):
            rptd['tx_pkts_1519_to_1548_bytes'] = str (int(((tx['1519-1548'] * 0.01)) * txpkts) + int(prev['tx_pkts_1519_to_1548_bytes']))
        else:
            rptd['tx_pkts_1519_to_1548_bytes'] = 0
        rpt['rpt'] = rptd
        rptlist.append(rpt)
   return rptlist 

def get_device_iface_traffic_instance(conn, iface):
   '''
   API's description: This API will form and write splunk log message
   '''
   if iface == None:
      ifinfo = Interfaces()
      ifacelist = ifinfo.get_link_up_interfaces(conn)
   else:
      ifacelist = iface

   if ifacelist is None:
      return None
   rpt_list = []
   time.sleep(1)
   switch = TrafficUtilization(1)
   for obj in ifacelist:
      ifname = obj.get('if_name')
      iface_util = switch.get_iface_traffic_instance(conn, ifname)
      if (iface_util is not None):
         rpt = {}
         rpt["interface"] =ifname
         rpt["rpt"] = iface_util
         rpt["speed"] = obj.get("speed")
         rpt["ctime"] = time.time()
         rpt_list.append(rpt)
         time.sleep(1)
   return rpt_list

def get_device_iface_traffic_utilization(conn, iface, interval):
   '''
   API's description: This API will form and write splunk log message
   '''
   if iface == None:
      ifinfo = Interfaces()
      ifacelist = ifinfo.get_link_up_interfaces(conn)
   else:
      ifacelist = iface

#   for ifname in ifacelist:
#      iface_util = switch.get_iface_traffic_utilization(conn, ifname)
   for obj in ifacelist:
      ifname = obj.get('if_name')
      iface_util = switch.get_iface_traffic_utilization(conn, ifname)
      rpt = {}
      rpt["interface"] =ifname
      rpt["rpt"] = iface_util
      rpt["speed"] = obj.get("speed")
      rpt_list.append(rpt)
   return rpt_list
      #title_msg = 'switch interface traffic utilization: switch_ip=%s, interface=%s,  ' % (conn.ip, ifname)

def init_stats(stats):
   #Rx Stats
   stats['rx_pkts'] = 0
   stats['rx_bcast'] = 0
   stats['rx_ucast'] = 0
   stats['rx_mcast'] = 0
   stats['rx_errors'] = 0
   stats['rx_pkts_0_to_64_bytes'] = 0
   stats['rx_pkts_65_to_127_bytes'] = 0
   stats['rx_pkts_128_to_255_bytes'] = 0
   stats['rx_pkts_256_to_511_bytes'] = 0
   stats['rx_pkts_512_to_1023_bytes'] = 0
   stats['rx_pkts_1024_to_1518_bytes'] = 0
   stats['rx_pkts_1519_to_1548_bytes'] = 0

   #Tx Stats
   stats['tx_pkts'] = 0
   stats['tx_bcast'] = 0
   stats['tx_ucast'] = 0
   stats['tx_mcast'] = 0
   stats['tx_errors'] = 0
   stats['tx_pkts_0_to_64_bytes'] = 0
   stats['tx_pkts_65_to_127_bytes'] = 0
   stats['tx_pkts_128_to_255_bytes'] = 0
   stats['tx_pkts_256_to_511_bytes'] = 0
   stats['tx_pkts_512_to_1023_bytes'] = 0
   stats['tx_pkts_1024_to_1518_bytes'] = 0
   stats['tx_pkts_1519_to_1548_bytes'] = 0

def calc_traffic_util(current, last, interval):
   #Rx Stats
   ret_stats = {'rx_pkts':0, 'rx_bcast':0, 'rx_ucast':0, 'rx_mcast':0, 'rx_errors':0, 'rx_discards':0,
                'rx_pkts_0_to_64_bytes':0, 'rx_pkts_65_to_127_bytes':0, 'rx_pkts_128_to_255_bytes':0,
                'rx_pkts_256_to_511_bytes':0, 'rx_pkts_512_to_1023_bytes':0, 'rx_pkts_1024_to_1518_bytes':0,
                'rx_pkts_1519_to_1548_bytes':0, 'tx_pkts_1519_to_1548_bytes':0,
                'tx_pkts_0_to_64_bytes':0, 'tx_pkts_65_to_127_bytes':0, 'tx_pkts_128_to_255_bytes':0,
                'tx_pkts_256_to_511_bytes':0, 'tx_pkts_512_to_1023_bytes':0, 'tx_pkts_1024_to_1518_bytes':0,
                'tx_pkts':0, 'tx_bcast':0, 'tx_ucast':0, 'tx_mcast':0, 'tx_errors':0, 'tx_discards':0}

   #Rx Stats
   ret_stats['rx_pkts'] = ((int) (current['rx_pkts']) - (int) (last['rx_pkts']))/interval
   ret_stats['rx_bcast'] = ((int)(current['rx_bcast']) - (int)(last['rx_bcast']))/interval
   ret_stats['rx_bcast'] = ((int)(current['rx_bcast']) - (int)(last['rx_bcast']))/interval
   ret_stats['rx_ucast'] = ((int)(current['rx_ucast']) - (int)(last['rx_ucast']))/interval
   ret_stats['rx_mcast'] = ((int)(current['rx_mcast']) - (int)(last['rx_mcast']))/interval
   ret_stats['rx_errors'] = ((int)(current['rx_errors']) - (int)(last['rx_errors']))/interval
   ret_stats['rx_discards'] = ((int)(current['rx_discards']) - (int)(last['rx_discards']))/interval
   ret_stats['rx_pkts_0_to_64_bytes'] = ((int)(current['rx_pkts_0_to_64_bytes']) - (int)(last['rx_pkts_0_to_64_bytes']))/interval
   ret_stats['rx_pkts_65_to_127_bytes'] = ((int)(current['rx_pkts_65_to_127_bytes']) - (int)(last['rx_pkts_65_to_127_bytes']))/interval
   ret_stats['rx_pkts_128_to_255_bytes'] = ((int)(current['rx_pkts_128_to_255_bytes']) - (int)(last['rx_pkts_128_to_255_bytes']))/interval
   ret_stats['rx_pkts_256_to_511_bytes'] = ((int)(current['rx_pkts_256_to_511_bytes']) - (int)(last['rx_pkts_256_to_511_bytes']))/interval
   ret_stats['rx_pkts_512_to_1023_bytes'] = ((int)(current['rx_pkts_512_to_1023_bytes']) - (int)(last['rx_pkts_512_to_1023_bytes']))/interval
   ret_stats['rx_pkts_1024_to_1518_bytes'] = ((int)(current['rx_pkts_1024_to_1518_bytes']) - (int)(last['rx_pkts_1024_to_1518_bytes']))/interval
   ret_stats['rx_pkts_1519_to_1548'] = ((int)(current['rx_pkts_1519_to_1548_bytes']) - (int)(last['rx_pkts_1519_to_1548_bytes']))/interval

   #Tx Stats
   ret_stats['tx_pkts'] = ((int) (current['tx_pkts']) - (int) (last['tx_pkts']))/interval
   ret_stats['tx_bcast'] = ((int) (current['tx_bcast']) - (int) (last['tx_bcast']))/interval
   ret_stats['tx_ucast'] = ((int) (current['tx_ucast']) - (int) (last['tx_ucast']))/interval
   ret_stats['tx_mcast'] = ((int) (current['tx_mcast']) - (int) (last['tx_mcast']))/interval
   ret_stats['tx_errors'] = ((int) (current['tx_errors']) - (int) (last['tx_errors']))/interval
   ret_stats['tx_discards'] = ((int)(current['tx_discards']) - (int)(last['tx_discards']))/interval
   ret_stats['tx_pkts_0_to_64_bytes'] = ((int)(current['tx_pkts_0_to_64_bytes']) - (int)(last['tx_pkts_0_to_64_bytes']))/interval
   ret_stats['tx_pkts_65_to_127_bytes'] = ((int)(current['tx_pkts_65_to_127_bytes']) - (int)(last['tx_pkts_65_to_127_bytes']))/interval
   ret_stats['tx_pkts_128_to_255_bytes'] = ((int)(current['tx_pkts_128_to_255_bytes']) - (int)(last['tx_pkts_128_to_255_bytes']))/interval
   ret_stats['tx_pkts_256_to_511_bytes'] = ((int)(current['tx_pkts_256_to_511_bytes']) - (int)(last['tx_pkts_256_to_511_bytes']))/interval
   ret_stats['tx_pkts_512_to_1023_bytes'] = ((int)(current['tx_pkts_512_to_1023_bytes']) - (int)(last['tx_pkts_512_to_1023_bytes']))/interval
   ret_stats['tx_pkts_1024_to_1518_bytes'] = ((int)(current['tx_pkts_1024_to_1518_bytes']) - (int)(last['tx_pkts_1024_to_1518_bytes']))/interval
   ret_stats['tx_pkts_1519_to_1548_bytes'] = ((int)(current['tx_pkts_1519_to_1548_bytes']) - (int)(last['tx_pkts_1519_to_1548_bytes']))/interval
   return ret_stats

def update_last_stats(node, current):
   #Rx Stats
   node.last_stats['rx_pkts'] = current['rx_pkts']
   node.last_stats['rx_bcast'] = current['rx_bcast']
   node.last_stats['rx_mcast'] = current['rx_mcast']
   node.last_stats['rx_ucast'] = current['rx_ucast']
   node.last_stats['rx_errors'] = current['rx_errors']
   node.last_stats['rx_discards'] = current['rx_discards']
   node.last_stats['rx_pkts_0_to_64_bytes'] = current['rx_pkts_0_to_64_bytes']
   node.last_stats['rx_pkts_65_to_127_bytes'] = current['rx_pkts_65_to_127_bytes']
   node.last_stats['rx_pkts_128_to_255_bytes'] = current['rx_pkts_128_to_255_bytes']
   node.last_stats['rx_pkts_256_to_511_bytes'] = current['rx_pkts_256_to_511_bytes']
   node.last_stats['rx_pkts_512_to_1023_bytes'] = current['rx_pkts_512_to_1023_bytes']
   node.last_stats['rx_pkts_1024_to_1518_bytes'] = current['rx_pkts_1024_to_1518_bytes']
   node.last_stats['rx_pkts_1519_to_1548_bytes'] = current['rx_pkts_1519_to_1548_bytes']

   #Tx Stats
   node.last_stats['tx_pkts'] = current['tx_pkts']
   node.last_stats['tx_bcast'] = current['tx_bcast']
   node.last_stats['tx_mcast'] = current['tx_mcast']
   node.last_stats['tx_ucast'] = current['tx_ucast']
   node.last_stats['tx_errors'] = current['tx_errors']
   node.last_stats['tx_discards'] = current['tx_discards']
   node.last_stats['tx_pkts_0_to_64_bytes'] = current['tx_pkts_0_to_64_bytes']
   node.last_stats['tx_pkts_65_to_127_bytes'] = current['tx_pkts_65_to_127_bytes']
   node.last_stats['tx_pkts_128_to_255_bytes'] = current['tx_pkts_128_to_255_bytes']
   node.last_stats['tx_pkts_256_to_511_bytes'] = current['tx_pkts_256_to_511_bytes']
   node.last_stats['tx_pkts_512_to_1023_bytes'] = current['tx_pkts_512_to_1023_bytes']
   node.last_stats['tx_pkts_1024_to_1518_bytes'] = current['tx_pkts_1024_to_1518_bytes']
   node.last_stats['tx_pkts_1519_to_1548_bytes'] = current['tx_pkts_1519_to_1548_bytes']

class TrafficUtilization:
     def __init__(self,  interval):
         self.interval = interval
         self.last_stats = {'rx_pkts':0, 'rx_bcast':0, 'rx_ucast':0, 'rx_mcast':0, 'rx_errors':0, 'rx_discards':0,
                            'rx_pkts_0_to_64_bytes':0, 'rx_pkts_65_to_127_bytes':0, 'rx_pkts_128_to_255_bytes':0,
                            'rx_pkts_256_to_511_bytes':0, 'rx_pkts_512_to_1023_bytes':0, 'rx_pkts_1024_to_1518_bytes':0,
                            'rx_pkts_1519_to_1548_bytes':0, 'tx_pkts_1519_to_1548_bytes':0,
                            'tx_pkts_0_to_64_bytes':0, 'tx_pkts_65_to_127_bytes':0, 'tx_pkts_128_to_255_bytes':0,
                            'tx_pkts_256_to_511_bytes':0, 'tx_pkts_512_to_1023_bytes':0, 'tx_pkts_1024_to_1518_bytes':0,
                            'tx_pkts':0, 'tx_bcast':0, 'tx_ucast':0, 'tx_mcast':0, 'tx_errors':0, 'tx_discards':0}

     def get_iface_traffic_instance(self, conn, if_name):
        iface = dict()
        iface['name'] = if_name
        stats = InterfaceStat(iface)
        ifstats = stats.get_all_stats(conn,if_name)
        return ifstats

     def get_iface_traffic_utilization(self, conn, if_name):
        '''
        API's description: This API will get interface traffic utilization based on the query interval,
        Mandatory arguments:  if_name(Str)
        Optional arguments: 0
        Output: Dictionary of interface statistical counters
        '''
        iface = dict()
        iface['name'] = if_name
        stats = InterfaceStat(iface)
        last_stats = dict()
        last_stats = stats.last_stats
        ifstats = stats.get_all_stats(conn,if_name)

        update_last_stats(stats, ifstats)
	time.sleep(self.interval)

        ifstats_fresh = stats.get_all_stats(conn,if_name)
        ifstats_util = calc_traffic_util(ifstats_fresh, last_stats, self.interval)
        #update_last_stats(stats, ifstats_util)

        return ifstats_util

     def get_device_traffic_utilization(self, conn):
        '''
        API's description: This API will get device traffic utilization based on the query interval,
        Optional arguments: 0
        Output: Dictionary of device statistical utilization
        '''
        last_stats = dict()
        last_stats = self.last_stats

        ifinfo = Interfaces()
        ifacelist = ifinfo.get_link_up_interfaces(conn)

        switch_stats = dict()
        switch_stats = {'rx_pkts':0, 'rx_bcast':0, 'rx_ucast':0, 'rx_mcast':0, 'rx_errors':0,'rx_discards':0,
                        'rx_pkts_0_to_64_bytes':0, 'rx_pkts_65_to_127_bytes':0, 'rx_pkts_128_to_255_bytes':0,
                        'rx_pkts_256_to_511_bytes':0, 'rx_pkts_512_to_1023_bytes':0, 'rx_pkts_1024_to_1518_bytes':0,
                        'rx_pkts_1519_to_1548_bytes':0, 'tx_pkts_1519_to_1548_bytes':0,
                        'tx_pkts_0_to_64_bytes':0, 'tx_pkts_65_to_127_bytes':0, 'tx_pkts_128_to_255_bytes':0,
                        'tx_pkts_256_to_511_bytes':0, 'tx_pkts_512_to_1023_bytes':0, 'tx_pkts_1024_to_1518_bytes':0,
                        'tx_pkts':0, 'tx_bcast':0, 'tx_ucast':0, 'tx_mcast':0, 'tx_errors':0, 'tx_discards':0}
        for ifname in ifacelist:
          iface = dict()
          iface['name'] = ifname
          stats = InterfaceStat(iface)
          if_stats = stats.get_all_stats(conn, ifname)
          
          switch_stats['rx_pkts'] += (int) (switch_stats['rx_pkts']) + (int) (if_stats['rx_pkts'])
          switch_stats['rx_bcast'] += (int)(switch_stats['rx_bcast']) + (int) (if_stats['rx_bcast'])
          switch_stats['rx_mcast'] += (int)(switch_stats['rx_mcast']) + (int) (if_stats['rx_mcast'])
          switch_stats['rx_ucast'] += (int)(switch_stats['rx_ucast']) + (int) (if_stats['rx_ucast'])
          switch_stats['rx_errors'] += (int)(switch_stats['rx_errors']) + (int) (if_stats['rx_errors'])
          switch_stats['rx_discards'] += (int)(switch_stats['rx_discards']) + (int) (if_stats['rx_discards'])
          switch_stats['rx_pkts_0_to_64_bytes'] += (int)(switch_stats['rx_pkts_0_to_64_bytes']) + (int) (if_stats['rx_pkts_0_to_64_bytes'])
          switch_stats['rx_pkts_65_to_127_bytes'] += (int)(switch_stats['rx_pkts_65_to_127_bytes']) + (int) (if_stats['rx_pkts_65_to_127_bytes'])
          switch_stats['rx_pkts_127_to_255_bytes'] += (int)(switch_stats['rx_pkts_127_to_255_bytes']) + (int) (if_stats['rx_pkts_127_to_255_bytes'])
          switch_stats['rx_pkts_256_to_511_bytes'] += (int)(switch_stats['rx_pkts_256_to_511_bytes']) + (int) (if_stats['rx_pkts_256_to_511_bytes'])
          switch_stats['rx_pkts_512_to_1023_bytes'] += (int)(switch_stats['rx_pkts_512_to_1023_bytes']) + (int) (if_stats['rx_pkts_512_to_1023_bytes'])
          switch_stats['rx_pkts_1024_to_1518_bytes'] += (int)(switch_stats['rx_pkts_1024_to_1518_bytes']) + (int) (if_stats['rx_pkts_1024_to_1518_bytes'])
          switch_stats['rx_pkts_1519_to_1548_bytes'] += (int)(switch_stats['rx_pkts_1519_to_1548_bytes']) + (int) (if_stats['rx_pkts_1519_to_1548_bytes'])

          switch_stats['tx_pkts'] += (int) (switch_stats['tx_pkts']) + (int) (if_stats['tx_pkts'])
          switch_stats['tx_bcast'] += (int)(switch_stats['tx_bcast']) + (int) (if_stats['tx_bcast'])
          switch_stats['tx_mcast'] += (int)(switch_stats['tx_mcast']) + (int) (if_stats['tx_mcast'])
          switch_stats['tx_ucast'] += (int)(switch_stats['tx_ucast']) + (int) (if_stats['tx_ucast'])
          switch_stats['tx_errors'] += (int)(switch_stats['tx_errors']) + (int) (if_stats['tx_errors'])
          switch_stats['tx_discards'] += (int)(switch_stats['tx_discards']) + (int) (if_stats['tx_discards'])
          switch_stats['tx_pkts_0_to_64_bytes'] += (int)(switch_stats['tx_pkts_0_to_64_bytes']) + (int) (if_stats['tx_pkts_0_to_64_bytes'])
          switch_stats['tx_pkts_65_to_127_bytes'] += (int)(switch_stats['tx_pkts_65_to_127_bytes']) + (int) (if_stats['tx_pkts_65_to_127_bytes'])
          switch_stats['tx_pkts_127_to_255_bytes'] += (int)(switch_stats['tx_pkts_127_to_255_bytes']) + (int) (if_stats['tx_pkts_127_to_255_bytes'])
          switch_stats['tx_pkts_256_to_511_bytes'] += (int)(switch_stats['tx_pkts_256_to_511_bytes']) + (int) (if_stats['tx_pkts_256_to_511_bytes'])
          switch_stats['tx_pkts_512_to_1023_bytes'] += (int)(switch_stats['tx_pkts_512_to_1023_bytes']) + (int) (if_stats['tx_pkts_512_to_1023_bytes'])
          switch_stats['tx_pkts_1024_to_1518_bytes'] += (int)(switch_stats['tx_pkts_1024_to_1518_bytes']) + (int) (if_stats['tx_pkts_1024_to_1518_bytes'])
          switch_stats['tx_pkts_1519_to_1548_bytes'] += (int)(switch_stats['tx_pkts_1519_to_1548_bytes']) + (int) (if_stats['tx_pkts_1519_to_1548_bytes'])

	time.sleep(self.interval)

        switch_stats_fresh = dict()
        switch_stats_fresh = {'rx_pkts':0, 'rx_bcast':0, 'rx_ucast':0, 'rx_mcast':0, 'rx_errors':0,'rx_discards':0,
                              'rx_pkts_0_to_64_bytes':0, 'rx_pkts_65_to_127_bytes':0, 'rx_pkts_128_to_255_bytes':0,
                              'rx_pkts_256_to_511_bytes':0, 'rx_pkts_512_to_1023_bytes':0, 'rx_pkts_1024_to_1518_bytes':0,
                              'rx_pkts_1519_to_1548_bytes':0, 'tx_pkts_1519_to_1548_bytes':0,
                              'tx_pkts_0_to_64_bytes':0, 'tx_pkts_65_to_127_bytes':0, 'tx_pkts_128_to_255_bytes':0,
                              'tx_pkts_256_to_511_bytes':0, 'tx_pkts_512_to_1023_bytes':0, 'tx_pkts_1024_to_1518_bytes':0,
                              'tx_pkts':0, 'tx_bcast':0, 'tx_ucast':0, 'tx_mcast':0, 'tx_errors':0, 'tx_discards':0}
        for ifname in ifacelist:
          iface = dict()
          iface['name'] = ifname
          stats = InterfaceStat(iface)
          if_stats = stats.get_all_stats(conn, ifname)
          
          switch_stats_fresh['rx_pkts'] += (int) (switch_stats_fresh['rx_pkts']) + (int) (if_stats['rx_pkts'])
          switch_stats_fresh['rx_bcast'] += (int)(switch_stats_fresh['rx_bcast']) + (int) (if_stats['rx_bcast'])
          switch_stats_fresh['rx_mcast'] += (int)(switch_stats_fresh['rx_mcast']) + (int) (if_stats['rx_mcast'])
          switch_stats_fresh['rx_ucast'] += (int)(switch_stats_fresh['rx_ucast']) + (int) (if_stats['rx_ucast'])
	  switch_stats_fresh['rx_errors'] += (int)(switch_stats_fresh['rx_errors']) + (int) (if_stats['rx_errors'])
          switch_stats_fresh['rx_discards'] += (int)(switch_stats_fresh['rx_discards']) + (int) (if_stats['rx_discards'])
          switch_stats_fresh['rx_pkts_0_to_64_bytes'] += (int)(switch_stats_fresh['rx_pkts_0_to_64_bytes']) + (int) (if_stats['rx_pkts_0_to_64_bytes'])
          switch_stats_fresh['rx_pkts_65_to_127_bytes'] += (int)(switch_stats_fresh['rx_pkts_65_to_127_bytes']) + (int) (if_stats['rx_pkts_65_to_127_bytes'])
          switch_stats_fresh['rx_pkts_128_to_255_bytes'] += (int)(switch_stats_fresh['rx_pkts_128_to_255_bytes']) + (int) (if_stats['rx_pkts_128_to_255_bytes'])
          switch_stats_fresh['rx_pkts_256_to_511_bytes'] += (int)(switch_stats_fresh['rx_pkts_256_to_511_bytes']) + (int) (if_stats['rx_pkts_256_to_511_bytes'])
          switch_stats_fresh['rx_pkts_512_to_1023_bytes'] += (int)(switch_stats_fresh['rx_pkts_512_to_1023_bytes']) + (int) (if_stats['rx_pkts_512_to_1023_bytes'])
          switch_stats_fresh['rx_pkts_1024_to_1518_bytes'] += (int)(switch_stats_fresh['rx_pkts_1024_to_1518_bytes']) + (int) (if_stats['rx_pkts_1024_to_1518_bytes'])
          switch_stats_fresh['rx_pkts_1519_to_1548_bytes'] += (int)(switch_stats_fresh['rx_pkts_1519_to_1548_bytes']) + (int) (if_stats['rx_pkts_1519_to_1548_bytes'])

          switch_stats_fresh['tx_pkts'] += (int) (switch_stats_fresh['tx_pkts']) + (int) (if_stats['tx_pkts'])
          switch_stats_fresh['tx_bcast'] += (int)(switch_stats_fresh['tx_bcast']) + (int) (if_stats['tx_bcast'])
          switch_stats_fresh['tx_mcast'] += (int)(switch_stats_fresh['tx_mcast']) + (int) (if_stats['tx_mcast'])
          switch_stats_fresh['tx_ucast'] += (int)(switch_stats_fresh['tx_ucast']) + (int) (if_stats['tx_ucast'])
          switch_stats_fresh['tx_errors'] += (int)(switch_stats_fresh['tx_errors']) + (int) (if_stats['tx_errors'])
          switch_stats_fresh['tx_discards'] += (int)(switch_stats_fresh['tx_discards']) + (int) (if_stats['tx_discards'])
          switch_stats_fresh['tx_pkts_0_to_64_bytes'] += (int)(switch_stats_fresh['tx_pkts_0_to_64_bytes']) + (int) (if_stats['tx_pkts_0_to_64_bytes'])
          switch_stats_fresh['tx_pkts_65_to_127_bytes'] += (int)(switch_stats_fresh['tx_pkts_65_to_127_bytes']) + (int) (if_stats['tx_pkts_65_to_127_bytes'])
          switch_stats_fresh['tx_pkts_128_to_255_bytes'] += (int)(switch_stats_fresh['tx_pkts_128_to_255_bytes']) + (int) (if_stats['tx_pkts_128_to_255_bytes'])
          switch_stats_fresh['tx_pkts_256_to_511_bytes'] += (int)(switch_stats_fresh['tx_pkts_256_to_511_bytes']) + (int) (if_stats['tx_pkts_256_to_511_bytes'])
          switch_stats_fresh['tx_pkts_512_to_1023_bytes'] += (int)(switch_stats_fresh['tx_pkts_512_to_1023_bytes']) + (int) (if_stats['tx_pkts_512_to_1023_bytes'])
          switch_stats_fresh['tx_pkts_1024_to_1518_bytes'] += (int)(switch_stats_fresh['tx_pkts_1024_to_1518_bytes']) + (int) (if_stats['tx_pkts_1024_to_1518_bytes'])
          switch_stats_fresh['tx_pkts_1519_to_1548_bytes'] += (int)(switch_stats_fresh['tx_pkts_1519_to_1548_bytes']) + (int) (if_stats['tx_pkts_1519_to_1548_bytes'])

        switch_util = calc_traffic_util(switch_stats_fresh, switch_stats, self.interval)
        #update_last_stats(self, switch_stats)
        return switch_util
