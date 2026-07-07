from connect import *
from logger import *
from  interface import *
import requests
import json
import time

def get_bst_report(conn):
     bst_report = BST_Report(conn)
     (ret, rpt) = bst_report.send_report()
     if (ret == 1):
         return rpt
     return None

def get_bst_congestion_queues_intf_up_instance(conn):
     ifacelist = []
     ifinfo = Interfaces()
     iflist = ifinfo.get_link_up_interfaces(conn)
     if (iflist == None):
         return None
     for obj in iflist:
        ifname = obj.get('if_name') 
        ifacelist.append(ifname) 
     bst = BST_Cgsn(conn)
     bst.configure_report('port-queue-drops', 5444, ifacelist, None, None)
     (ret, rpt) = bst.get_report()
     if (ret):
        return rpt
     return None
   
def get_bst_congestion_queues_intf_up(conn, interval):
     ifacelist = []
     ifinfo = Interfaces()
     iflist = ifinfo.get_link_up_interfaces(conn)
     for obj in iflist:
        ifname = obj.get('if_name') 
        ifacelist.append(ifname) 
     bst = BST_Cgsn(conn)
     bst.configure_report('port-queue-drops', 5444, ifacelist, None, None)
     (ret, l_rpt) = bst.get_report()
     time.sleep(interval)
     bst.configure_report('port-queue-drops', 5444, ifacelist, None, None)
     (ret, c_rpt) = bst.get_report()
     if (ret == 1):
         rpt = bst.calculate_pkt_loss(c_rpt, l_rpt, interval, 'port-queue-drops')
         return rpt

def get_bst_congestion_intf_up(conn, interval):
     ifacelist = []
     ifinfo = Interfaces()
     iflist = ifinfo.get_link_up_interfaces(conn)
     for obj in iflist:
        ifname = obj.get('if_name') 
        ifacelist.append(ifname) 
     bst = BST_Cgsn(conn)
     bst.configure_report('port-drops', 5444, ifacelist, 0)
     (ret, l_rpt) = bst.get_report()
     time.sleep(interval)
     bst.configure_report('port-drops', 5444, ifacelist, 0)
     (ret, c_rpt) = bst.get_report()
     if (ret == 1):
         c_rpt = bst.calculate_pkt_loss(c_rpt, l_rpt, interval, 'port-drops')
         return c_rpt
     return None
     
class BST_Feature():
     def __init__(self,conn):
         self.conn = conn
         self.url = '/nos/api/cfg/telemetry/bst/feature'
         self.inp_json = {'collection-interval': 60, 'send-async-reports': 0, 'send-snapshot-on-trigger': 1, 'trigger-rate-limit': 1, 'async-full-report': 0, 'trigger-rate-limit-interval': 10, 'bst-enable': 1}

     def get_report(self):
         (ret, rpt)  = self.conn.get(self.url)
         return (ret, rpt)
     def put_report(self):
         ret  = self.conn.put(self.url, self.inp_json)
         return (ret)

def set_bst_feature(conn):
     bst_feature = BST_Feature(conn)
     ret = bst_feature.put_report()
     return ret

     
class BST_Report():
     def __init__(self,conn):
         self.conn = conn
         self.url = '/nos/api/info/telemetry/bst/report'
         self.inp_json = { 'include-ingress-port-priority-group':1, 'include-ingress-port-service-pool':1, 'include-device':1, 'include-ingress-service-pool':1, 'include-egress-port-service-pool':1, 'include-egress-service-pool':1, 'include-egress-cpu-queue':1,'include-egress-rqe-queue':1}

     def send_report(self):
         (ret, rpt)  = self.conn.post(self.url, self.inp_json)
         return (ret, rpt)

class BST_Cgsn():
     def __init__(self,conn):
         self.conn = conn
         self.url = '/nos/api/info/telemetry/bst/congestion-drop-counters'
         self.inp_json = dict()

     def configure_report(self, req_type, req_id, arg1, arg2, arg3=0):
         req_params = dict()
         self.inp_json['request-type'] = req_type
         self.inp_json['req-id'] = int(req_id)
         if (req_type == 'top-drops'):
             req_params['count'] = int(arg1)
         elif (req_type == 'top-port-queue-drops'):
             req_params['count'] = int(arg1)
             req_params['queue-type'] = arg2
         elif (req_type == 'port-drops'):
             req_params['interface-list'] = arg1 
         elif (req_type == 'port-queue-drops'):
             req_params['interface-list'] = arg1
             if (arg2 is None):
                 req_params['queue-type'] = "all"
             else:
                 req_params['queue-type'] = arg2
             if (arg3 is None):
                 req_params['queue-list'] = [0,1,2,3,4,5,6,7]
             else:
                 l = [int(x) for x in arg3.split(',')]
                 req_params['queue-list'] = l
         self.inp_json['request-params'] = req_params.copy()
         return self.inp_json

     def get_report(self):
         (ret, rpt)  = self.conn.post(self.url, self.inp_json)
         return (ret, rpt)

     def calculate_pkt_loss(self, curr, last, interval, req_type):
         c_intflist = curr['congestion-ctr']
         l_intflist = last['congestion-ctr']
         c_intflen =  len(c_intflist)
         if (req_type == 'port-drops'):
             for x in range(0, c_intflen):
                 curr_y = c_intflist[x]
                 last_y = l_intflist[x]
                 curr_y['ctr'] = (((int) (curr_y['ctr']) - (int) (last_y['ctr']))/interval)
             return curr
         elif (req_type == 'port-queue-drops'):
             for x in range(0, c_intflen):
                 curr_y = c_intflist[x]
                 last_y = l_intflist[x]
                 last_qdc_list =  last_y["queue-drop-ctr"]
                 curr_qdc_list =  curr_y["queue-drop-ctr"]
                 curr_qdc_list_len =  len(curr_qdc_list)
                 for y in range(0, curr_qdc_list_len):
                      if (((int) (curr_qdc_list[y][1])) != 0):
                          curr_qdc_list[y][1] = (((int) (curr_qdc_list[y][1]) - (int) (last_qdc_list[y][1]))/interval) 
             return curr

