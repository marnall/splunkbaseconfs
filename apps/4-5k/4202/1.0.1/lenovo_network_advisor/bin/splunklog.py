from logger import *

def add_tlv_field(tlv_list, namestr, val):
    tlv_field = {}
    tlv_field['name'] = namestr
    tlv_field['value'] = val
    tlv_list.append(tlv_field)
    return tlv_list

def splunk_lldp_intf_stats(ip, rpt, logger):
    for obj in rpt:
       field_list = []
       for key in obj.keys():
          skey = key.replace(" ","_")
          add_tlv_field(field_list, skey, obj.get(key)) 
       logger.splunk_log(ip, 'LLDP_INTERFACE_STATS', field_list)

def env_resources_json2field(report):
    ''' 
        API's description: This API will translate enviroment resources JSON report 
        to splunk field dict list 
        Mandatory arguments:  None
        Optional arguments: None
        Returns: List with Dictionary elemetry or None if error happens
        [
    	{ 
    	 'name'  : 'CPU_USAGE', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'MEMORY_USAGE', 
    	 'value' : 'field_value'
    	}
        ]
    '''
    field_list = []

    if report.has_key('Cpu(s)'):
        if  report['Cpu(s)'].has_key('idle'):
    	    splunk_field = {}
    	    splunk_field['name'] = 'CPU_USAGE'
    	    splunk_field['value'] = float(100) - float(report['Cpu(s)']['idle'])
    	    field_list.append(splunk_field)

    if report.has_key('Mem'):
        if  report['Mem'].has_key('total') and report['Mem'].has_key('free'):
	    splunk_field = {}
    	    splunk_field['name'] = 'MEMORY_USAGE'
    	    splunk_field['value'] = 100 * round((float(report['Mem']['total']) - float(report['Mem']['free']))/float(report['Mem']['total']), 2)
    	    field_list.append(splunk_field)

    return field_list

def env_temperature_json2field(report):
    ''' 
        API's description: This API will translate enviroment temerature JSON report 
        to splunk field dict list 
        Mandatory arguments:  None
        Optional arguments: None
        Returns: List with Dictionary elemetry or None if error happens
        [
    	{ 
    	 'name'  : 'CPU_LOCAL_TEMP', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'CPU_LOCAL_STATE', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'HOT_SPOT_TEMP', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'HOT_SPOT_STATE', 
    	 'value' : 'field_value'
    	},
        ]
    '''
    field_list = []

    if report.has_key('CPU Local'):
        if  report['CPU Local'].has_key('Temp') and report['CPU Local'].has_key('State'):
    	    splunk_field = {}
    	    splunk_field['name'] = 'CPU_LOCAL_TEMP'
    	    splunk_field['value'] = report['CPU Local']['Temp']
    	    field_list.append(splunk_field)

    	    splunk_field = {}
    	    splunk_field['name'] = 'CPU_LOCAL_STATE'
    	    splunk_field['value'] = report['CPU Local']['State']
    	    field_list.append(splunk_field)

    if report.has_key('Hot Spot'):
        if report['Hot Spot'].has_key('Temp') and report['Hot Spot'].has_key('State'):
    	    splunk_field = {}
    	    splunk_field['name'] = 'HOT_SPOT_TEMP'
    	    splunk_field['value'] = report['Hot Spot']['Temp']
    	    field_list.append(splunk_field)

    	    splunk_field = {}
    	    splunk_field['name'] = 'HOT_SPOT_STATE'
    	    splunk_field['value'] = report['Hot Spot']['State']
    	    field_list.append(splunk_field)

    if report.has_key('Ambient'):
        if report['Ambient'].has_key('Temp') and report['Ambient'].has_key('State'):
    	    splunk_field = {}
    	    splunk_field['name'] = 'AMBIENT_TEMP'
    	    splunk_field['value'] = report['Ambient']['Temp']
    	    field_list.append(splunk_field)

    	    splunk_field = {}
    	    splunk_field['name'] = 'AMBIENT_STATE'
    	    splunk_field['value'] = report['Ambient']['State']
    	    field_list.append(splunk_field)

    if report.has_key('Temperature threshold'):
        if report['Temperature threshold'].has_key('System Warning') and report['Temperature threshold'].has_key('System Shutdown')and report['Temperature threshold'].has_key('System Set Point'):
    	    splunk_field = {}
    	    splunk_field['name'] = 'WARNING'
    	    splunk_field['value'] = report['Temperature threshold']['System Warning']
    	    field_list.append(splunk_field)

    	    splunk_field = {}
    	    splunk_field['name'] = 'SET_POINT'
    	    splunk_field['value'] = report['Temperature threshold']['System Set Point']
    	    field_list.append(splunk_field)

    	    splunk_field = {}
    	    splunk_field['name'] = 'SHUT_DOWN'
    	    splunk_field['value'] = report['Temperature threshold']['System Shutdown']
    	    field_list.append(splunk_field)

    return field_list

def env_fans_json2field(report):
    ''' 
        API's description: This API will translate enviroment fan JSON report 
        to splunk field dict list 
        Mandatory arguments:  None
        Optional arguments: None
        Returns: List with Dictionary elemetry or None if error happens
        [
    	{ 
    	 'name'  : 'FAN1_SPEED_PERCENT', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'FAN1_SPEED_RPM', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'FAN2_SPEED_PERCENT', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'FAN2_SPEED_RPM', 
    	 'value' : 'field_value'
    	},
        ]
    '''
    field_list = []
    
    num_of_fans = 0
    active_fans = 0
    sum_percent = 0

    if report.has_key('Fan 1'):
	num_of_fans = num_of_fans + 1
        if report['Fan 1'].has_key('speed-percent') and report['Fan 1'].has_key('speed-rpm'):
	    if int(report['Fan 1']['speed-percent']) > 0:
		sum_percent = sum_percent + int(report['Fan 1']['speed-percent'])
		active_fans = active_fans + 1
	    '''
    	    splunk_field = {}
    	    splunk_field['name'] = 'FAN1_SPEED_PERCENT'
    	    splunk_field['value'] = report['Fan 1']['speed-percent']
    	    field_list.append(splunk_field)
    	    splunk_field = {}
    	    splunk_field['name'] = 'FAN1_SPEED_RPM'
    	    splunk_field['value'] = report['Fan 1']['speed-rpm']
    	    field_list.append(splunk_field)
	    '''

    if report.has_key('Fan 2'):
	num_of_fans = num_of_fans + 1
        if report['Fan 2'].has_key('speed-percent') and report['Fan 2'].has_key('speed-rpm'):
	    if int(report['Fan 2']['speed-percent']) > 0:
		sum_percent = sum_percent + int(report['Fan 2']['speed-percent'])
		active_fans = active_fans + 1
	    '''
    	    splunk_field = {}
    	    splunk_field['name'] = 'FAN2_SPEED_PERCENT'
    	    splunk_field['value'] = report['Fan 2']['speed-percent']
    	    field_list.append(splunk_field)
    	    splunk_field = {}
    	    splunk_field['name'] = 'FAN2_SPEED_RPM'
    	    splunk_field['value'] = report['Fan 2']['speed-rpm']
    	    field_list.append(splunk_field)
	    '''

    if report.has_key('Fan 3'):
	num_of_fans = num_of_fans + 1
        if  report['Fan 3'].has_key('speed-percent') and report['Fan 3'].has_key('speed-rpm'):
	    if int(report['Fan 3']['speed-percent']) > 0:
		sum_percent = sum_percent + int(report['Fan 3']['speed-percent'])
		active_fans = active_fans + 1
	    '''
	    splunk_field = {}
	    splunk_field['name'] = 'FAN3_SPEED_PERCENT'
	    splunk_field['value'] = report['Fan 3']['speed-percent']
	    field_list.append(splunk_field)
	    splunk_field = {}
	    splunk_field['name'] = 'FAN2_SPEED_RPM'
	    splunk_field['value'] = report['Fan 2']['speed-rpm']
	    field_list.append(splunk_field)
	    '''

    if report.has_key('Fan 4'):
	num_of_fans = num_of_fans + 1
        if  report['Fan 4'].has_key('speed-percent') and report['Fan 4'].has_key('speed-rpm'):
	    if int(report['Fan 4']['speed-percent']) > 0:
		sum_percent = sum_percent + int(report['Fan 4']['speed-percent'])
		active_fans = active_fans + 1
	    '''
            splunk_field = {}
	    splunk_field['name'] = 'FAN4_SPEED_PERCENT'
	    splunk_field['value'] = report['Fan 4']['speed-percent']
	    field_list.append(splunk_field)
	    splunk_field = {}
	    splunk_field['name'] = 'FAN4_SPEED_RPM'
	    splunk_field['value'] = report['Fan 4']['speed-rpm']
	    field_list.append(splunk_field)
	    '''

    if report.has_key('Fan 5'):
	num_of_fans = num_of_fans + 1
   	if  report['Fan 5'].has_key('speed-percent') and report['Fan 5'].has_key('speed-rpm'):
	    if int(report['Fan 5']['speed-percent']) > 0:
		sum_percent = sum_percent + int(report['Fan 5']['speed-percent'])
		active_fans = active_fans + 1
	    '''
	    splunk_field = {}
	    splunk_field['name'] = 'FAN5_SPEED_PERCENT'
	    splunk_field['value'] = report['Fan 5']['speed-percent']
	    field_list.append(splunk_field)
	    splunk_field = {}
	    splunk_field['name'] = 'FAN5_SPEED_RPM'
	    splunk_field['value'] = report['Fan 5']['speed-rpm']
	    field_list.append(splunk_field)
	    '''

    if report.has_key('Fan 6'):
	num_of_fans = num_of_fans + 1
        if  report['Fan 6'].has_key('speed-percent') and report['Fan 6'].has_key('speed-rpm'):
	    if int(report['Fan 6']['speed-percent']) > 0:
		sum_percent = sum_percent + int(report['Fan 6']['speed-percent'])
		active_fans = active_fans + 1
	    '''
	    splunk_field = {}
	    splunk_field['name'] = 'FAN6_SPEED_PERCENT'
	    splunk_field['value'] = report['Fan 6']['speed-percent']
	    field_list.append(splunk_field)

	    splunk_field = {}
	    splunk_field['name'] = 'FAN6_SPEED_RPM'
	    splunk_field['value'] = report['Fan 6']['speed-rpm']
	    field_list.append(splunk_field)

	    '''

    if report.has_key('Fan 7'):
	num_of_fans = num_of_fans + 1
	if  report['Fan 7'].has_key('speed-percent') and report['Fan 7'].has_key('speed-rpm'):
	    if int(report['Fan 7']['speed-percent']) > 0:
		sum_percent = sum_percent + int(report['Fan 7']['speed-percent'])
		active_fans = active_fans + 1
	    '''
	    splunk_field = {}
	    splunk_field['name'] = 'FAN7_SPEED_PERCENT'
	    splunk_field['value'] = report['Fan 7']['speed-percent']
	    field_list.append(splunk_field)

	    splunk_field = {}
	    splunk_field['name'] = 'FAN7_SPEED_RPM'
	    splunk_field['value'] = report['Fan 7']['speed-rpm']
	    field_list.append(splunk_field)
	    '''

    if report.has_key('Fan 8'):
	num_of_fans = num_of_fans + 1
        if  report['Fan 8'].has_key('speed-percent') and report['Fan 8'].has_key('speed-rpm'):
	    if int(report['Fan 8']['speed-percent']) > 0:
		sum_percent = sum_percent + int(report['Fan 8']['speed-percent'])
		active_fans = active_fans + 1

    if report.has_key('Fan 9'):
	num_of_fans = num_of_fans + 1
        if  report['Fan 9'].has_key('speed-percent') and report['Fan 9'].has_key('speed-rpm'):
	    if int(report['Fan 9']['speed-percent']) > 0:
		sum_percent = sum_percent + int(report['Fan 9']['speed-percent'])
		active_fans = active_fans + 1

    if report.has_key('Fan 10'):
	num_of_fans = num_of_fans + 1
        if  report['Fan 10'].has_key('speed-percent') and report['Fan 10'].has_key('speed-rpm'):
	    if int(report['Fan 10']['speed-percent']) > 0:
		sum_percent = sum_percent + int(report['Fan 10']['speed-percent'])
		active_fans = active_fans + 1

    if report.has_key('Fan 11'):
	num_of_fans = num_of_fans + 1
        if  report['Fan 11'].has_key('speed-percent') and report['Fan 11'].has_key('speed-rpm'):
	    if int(report['Fan 11']['speed-percent']) > 0:
		sum_percent = sum_percent + int(report['Fan 11']['speed-percent'])
		active_fans = active_fans + 1

    if report.has_key('Fan 12'):
	num_of_fans = num_of_fans + 1
        if  report['Fan 12'].has_key('speed-percent') and report['Fan 12'].has_key('speed-rpm'):
	    if int(report['Fan 12']['speed-percent']) > 0:
		sum_percent = sum_percent + int(report['Fan 12']['speed-percent'])
		active_fans = active_fans + 1

    add_tlv_field(field_list, 'FAN_NUM',    num_of_fans)
    add_tlv_field(field_list, 'FAN_ACTIVE', active_fans)
    add_tlv_field(field_list, 'FAN_AVG_PERCENT', int(round(float(sum_percent)/float(active_fans),0)))

    return field_list


def env_power_json2field(report):
    ''' 
        API's description: This API will translate enviroment power JSON report 
        to splunk field dict list 
        Mandatory arguments:  None
        Optional arguments: None
        Returns: List with Dictionary elemetry or None if error happens
        [
    	{ 
    	 'name'  : 'POWER1_NAME', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'POWER1_MANUFACTURER', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'POWER1_MODEL', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'POWER1_STATE', 
    	 'value' : 'field_value'
    	},

    	{ 
    	 'name'  : 'POWER2_NAME', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'POWER2_MANUFACTURER', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'POWER2_MODEL', 
    	 'value' : 'field_value'
    	},
    	{ 
    	 'name'  : 'POWER2_STATE', 
    	 'value' : 'field_value'
    	},
        ]
        '''
    field_list = []

    if report.has_key('Power 1'):
        #print report['Power 1']
        if report['Power 1'].has_key('Name') and report['Power 1'].has_key('Manufacturer') and report['Power 1'].has_key('Model') and report['Power 1'].has_key('State'):
    	    splunk_field = {}
    	    splunk_field['name'] = 'POWER1_NAME'
    	    splunk_field['value'] = report['Power 1']['Name']
    	    field_list.append(splunk_field)

    	    splunk_field = {}
    	    splunk_field['name'] = 'POWER1_MANUFACTURER'
    	    splunk_field['value'] = report['Power 1']['Manufacturer']
    	    field_list.append(splunk_field)

    	    splunk_field = {}
    	    splunk_field['name'] = 'POWER1_MODEL'
    	    splunk_field['value'] = report['Power 1']['Model']
    	    field_list.append(splunk_field)

    	    splunk_field = {}
    	    splunk_field['name'] = 'POWER1_STATE'
    	    splunk_field['value'] = report['Power 1']['State']
    	    field_list.append(splunk_field)

    if report.has_key('Power 2'):
        if  report['Power 2'].has_key('Name') and report['Power 2'].has_key('Manufacturer') and report['Power 2'].has_key('Model') and report['Power 2'].has_key('State'):
    	    splunk_field = {}
    	    splunk_field['name'] = 'POWER2_NAME'
    	    splunk_field['value'] = report['Power 2']['Name']
    	    field_list.append(splunk_field)

    	    splunk_field = {}
    	    splunk_field['name'] = 'POWER2_MANUFACTURER'
    	    splunk_field['value'] = report['Power 2']['Manufacturer']
    	    field_list.append(splunk_field)

    	    splunk_field = {}
    	    splunk_field['name'] = 'POWER2_MODEL'
    	    splunk_field['value'] = report['Power 2']['Model']
    	    field_list.append(splunk_field)

    	    splunk_field = {}
    	    splunk_field['name'] = 'POWER2_STATE'
    	    splunk_field['value'] = report['Power 2']['State']
    	    field_list.append(splunk_field)

    return field_list
def env_hostname_json2field(report):
    '''
        API's description: This API will translate hostname JSON report
        to splunk field dict list
        Mandatory arguments:  None
        Optional arguments: None
        Returns: List with Dictionary elemet or None if error happens
        {
            "hostname": "MARS-2-test"
        }
    '''

    field_list = []

    if report.has_key('hostname'):
        splunk_field = {}
        splunk_field['name'] = 'HOSTNAME_NAME'
        splunk_field['value'] = report['hostname']
        field_list.append(splunk_field)

    return field_list

def splunk_health_hostname_log(ip, rpt, logger):
   '''
   API's description: This API will form and write splunk log message
   '''
   logger.splunk_log(ip, 'SYSTEM_STATUS', env_hostname_json2field(rpt))


def traffic_dict2field(traffic_dic):
    '''    
       API's description: This API will build splunk field dict list 
       Mandatory arguments:  None
       Optional arguments: None
       Returns: List with Dictionary elemetry or None if error happens
	[
	  { 
	   'name'  : 'RX_PKTS', 
	   'value' : 'field_value'
	  },
	  { 
	   'name'  : 'RX_BCAST', 
	   'value' : 'field_value'
	  },
	  { 
	   'name'  : 'RX_UCAST', 
	   'value' : 'field_value'
	  },
	  { 
	   'name'  : 'RX_MCAST', 
	   'value' : 'field_value'
	  },
	  { 
	   'name'  : 'RX_ERRORS', 
	   'value' : 'field_value'
	  },
	  { 
	   'name'  : 'TX_PKTS', 
	   'value' : 'field_value'
	  },
	  { 
	   'name'  : 'TX_BCAST', 
	   'value' : 'field_value'
	  },
	  { 
	   'name'  : 'TX_UCAST', 
	   'value' : 'field_value'
	  },
	  { 
	   'name'  : 'TX_MCAST', 
	   'value' : 'field_value'
	  },
	  { 
	   'name'  : 'TX_ERRORS', 
	   'value' : 'field_value'
	  },
        ]
    '''
    field_list = []

    field_list = add_tlv_field(field_list, 'RX_PKTS', traffic_dic['rx_pkts'])
    field_list = add_tlv_field(field_list, 'RX_BCAST', traffic_dic['rx_bcast'])
    field_list = add_tlv_field(field_list, 'RX_UCAST', traffic_dic['rx_ucast'])
    field_list = add_tlv_field(field_list, 'RX_MCAST', traffic_dic['rx_mcast'])
    field_list = add_tlv_field(field_list, 'RX_ERRORS', traffic_dic['rx_errors'])
    field_list = add_tlv_field(field_list, 'TX_PKTS', traffic_dic['tx_pkts'])
    field_list = add_tlv_field(field_list, 'TX_BCAST', traffic_dic['tx_bcast'])
    field_list = add_tlv_field(field_list, 'TX_UCAST', traffic_dic['tx_ucast'])
    field_list = add_tlv_field(field_list, 'TX_MCAST', traffic_dic['tx_mcast'])
    field_list = add_tlv_field(field_list, 'TX_ERRORS', traffic_dic['tx_errors'])
    field_list = add_tlv_field(field_list, 'TX_DISCARDS', traffic_dic['tx_discards'])
    field_list = add_tlv_field(field_list, 'RX_DISCARDS', traffic_dic['rx_discards'])
    field_list = add_tlv_field(field_list, 'RX_0_to_64', traffic_dic['rx_pkts_0_to_64_bytes'])
    field_list = add_tlv_field(field_list, 'TX_0_to_64', traffic_dic['tx_pkts_0_to_64_bytes'])
    field_list = add_tlv_field(field_list, 'RX_65_to_127', traffic_dic['rx_pkts_65_to_127_bytes'])
    field_list = add_tlv_field(field_list, 'TX_65_to_127', traffic_dic['tx_pkts_65_to_127_bytes'])
    field_list = add_tlv_field(field_list, 'RX_128_to_255', traffic_dic['rx_pkts_128_to_255_bytes'])
    field_list = add_tlv_field(field_list, 'TX_128_to_255', traffic_dic['tx_pkts_128_to_255_bytes'])
    field_list = add_tlv_field(field_list, 'RX_256_to_511', traffic_dic['rx_pkts_256_to_511_bytes'])
    field_list = add_tlv_field(field_list, 'TX_256_to_511', traffic_dic['tx_pkts_256_to_511_bytes'])
    field_list = add_tlv_field(field_list, 'RX_512_to_1023', traffic_dic['rx_pkts_512_to_1023_bytes'])
    field_list = add_tlv_field(field_list, 'TX_512_to_1023', traffic_dic['tx_pkts_512_to_1023_bytes'])
    field_list = add_tlv_field(field_list, 'RX_1024_to_1518', traffic_dic['rx_pkts_1024_to_1518_bytes'])
    field_list = add_tlv_field(field_list, 'TX_1024_to_1518', traffic_dic['tx_pkts_1024_to_1518_bytes'])
    field_list = add_tlv_field(field_list, 'RX_1519_to_1548', traffic_dic['rx_pkts_1519_to_1548_bytes'])
    field_list = add_tlv_field(field_list, 'TX_1519_to_1548', traffic_dic['tx_pkts_1519_to_1548_bytes'])
    field_list = add_tlv_field(field_list, 'RX_JUMBO', traffic_dic['rx_oversize'])
    field_list = add_tlv_field(field_list, 'TX_JUMBO', traffic_dic['tx_oversize'])
    field_list = add_tlv_field(field_list, 'TX_BIT_RATE', traffic_dic['tx_bit_rate'])
    field_list = add_tlv_field(field_list, 'RX_BIT_RATE', traffic_dic['rx_bit_rate'])

    return field_list

def splunk_device_traffic_log(ip, rpt, logger):
   '''
   API's description: This API will form and write splunk log message
   '''
   logger.splunk_log(ip, 'DEVICE_TRAFFIC', traffic_dict2field(rpt))
 
   #msg = json.dumps(switch_util)
   #splunk_msg = title_msg + msg
   #print(splunk_msg)
#   for metric_key in switch_util.keys():
#      splunk_msg = ''
#      splunk_msg = ' stat_type=' + metric_key + ','
#      splunk_msg = splunk_msg + ' stat_value=%s ' % (switch_util[metric_key])
#      splunk_msg = title_msg + splunk_msg
#      print(splunk_msg)

def splunk_device_iface_traffic_utilization(ip, rptlist, logger):
   '''
   API's description: This API will form and write splunk log message
   '''
   for x in range(0,len(rptlist)):
      rpt = rptlist[x]
      iface = traffic_dict2field(rpt["rpt"])
      splunk_field = {}
      splunk_field['name'] = 'interface'
      splunk_field['value'] = rpt["interface"]
      iface.append(splunk_field)
      splunk_field = {}
      splunk_field['name'] = 'speed'
      splunk_field['value'] = rpt["speed"]
      iface.append(splunk_field)
      splunk_field = {}
      splunk_field['name'] = 'Ctime'
      splunk_field['value'] = rpt["ctime"]
      iface.append(splunk_field)
      logger.splunk_log(ip, 'INTERFACE_TRAFFIC', iface)

    #title_msg = 'switch interface traffic utilization: switch_ip=%s, interface=%s,  ' % (conn.ip, ifname)

def splunk_congestion_log(ip, rpt, logger):
     intf_list = rpt['congestion-ctr']
     intf_len =  len(intf_list)
     total = 0
     any_loss = 0
     if (rpt["report-type"] == "port-drops"):
         field_list = []
         for x in range(0, intf_len):
              y = intf_list[x]
              if ( y['ctr'] > 0): 
                  intf = y['interface']
#                  intfs = intf.replace("/","_")
                  field_list = add_tlv_field(field_list, intfs, int(y['ctr']))
                  total = total + int(y['ctr'])
                  any_loss = 1
         if (any_loss == 1):
              field_list = add_tlv_field(field_list, "device_drops", total)
              logger.splunk_log(ip, 'DEVICE_CONGESTION_DROPS', field_list)
     elif (rpt["report-type"] == "port-queue-drops"):
         for x in range(0, intf_len):
              curr_y = intf_list[x]
              curr_qdc_list =  curr_y["queue-drop-ctr"]
              curr_qdc_list_len =  len(curr_qdc_list)
              for y in range(0, curr_qdc_list_len):
                   if (((int) (curr_qdc_list[y][1])) > 0):
                        field_list = []
                        intfs = curr_y['interface']
#                        intfs = intf.replace("/","_")
                        field_list = add_tlv_field(field_list, "interface", intfs)
                        field_list = add_tlv_field(field_list, "queue_type", curr_y["queue-type"])
                        intfs = "Queue " + str(y)
                        field_list = add_tlv_field(field_list, "queue_id", intfs)
#                        field_list = add_tlv_field(field_list, "queue_id", y)
                        field_list = add_tlv_field(field_list, "ctr", curr_qdc_list[y][1])
                        logger.splunk_log(ip, 'DEVICE_CONGESTION_QUEUE_DROPS', field_list)


def splunk_bst_log(ip, rpt, logger):
     realm_list = rpt['report']
     for i in range(len(realm_list)):
         realm =  realm_list[i]
         if not realm.has_key('realm'):
             break
         if realm['realm'] == 'egress-cpu-queue':
              data_list = realm['data']
              for j in range(len(data_list)):
                  data = data_list[j]
                  if (int(data[1]) > 0):
                      field_list = []
                      idxstr = 'Egr Cpu Queue ' + str(data[0])
                      field_list = add_tlv_field(field_list, 'queue', int(data[0]))
                      field_list = add_tlv_field(field_list, 'idx', idxstr)
                      field_list = add_tlv_field(field_list, 'data',  int(data[1]))
                      logger.splunk_log(ip, 'Cpu Queue', field_list)
         elif realm['realm'] == 'egress-rqe-queue':
              data_list = realm['data']
              for j in range(len(data_list)):
                  data = data_list[j]
                  if (int(data[1]) > 0):
                      field_list = []
                      idxstr = 'Egr Rqe Queue ' + str(data[0])
                      field_list = add_tlv_field(field_list, 'queue', int(data[0]))
                      field_list = add_tlv_field(field_list, 'idx', idxstr)
                      field_list = add_tlv_field(field_list, 'data',  int(data[1]))
                      logger.splunk_log(ip, 'Rqe Queue', field_list)
         elif realm['realm'] == 'device':
             field_list = []
             field_list = add_tlv_field(field_list, 'data', (int) (realm['data']))
             logger.splunk_log(ip, 'Device', field_list)
         elif realm['realm'] == 'ingress-port-priority-group':
             data_list = realm['data']
             for j in range(len(data_list)):
                 field_list = []
                 data = data_list[j]
                 arr = data['data']
                 field_list = add_tlv_field(field_list, 'interface', data['interface'])
                 field_list = add_tlv_field(field_list, 'pg', (int) (arr[0][0]))
                 idxstr = data['interface']
                 idxstr = 'Ing ' + idxstr + " Priority Group " + str(arr[0][0])
                 field_list = add_tlv_field(field_list, "idx", idxstr)
                 field_list = add_tlv_field(field_list, "umsharebuffer", (int) (arr[0][1]))
                 logger.splunk_log(ip, 'Ingress Port Priority Group', field_list)
         elif realm['realm'] == 'ingress-port-service-pool':
             data_list = realm['data']
             for j in range(len(data_list)):
                 field_list = []
                 data = data_list[j]
                 arr = data['data']
                 field_list = add_tlv_field(field_list, 'interface', data['interface'])
                 idxstr = data['interface']
                 field_list = add_tlv_field(field_list, 'servicepool', (int) (arr[0][0]))
                 idxstr = 'Ing ' + idxstr + " Service Pool " + str(arr[0][0])
                 field_list = add_tlv_field(field_list, "idx", idxstr)
                 field_list = add_tlv_field(field_list, "umsharebuffer", (int) (arr[0][1]))
                 logger.splunk_log(ip, 'Ingress Port Service Pool', field_list)
         elif realm['realm'] == 'egress-port-service-pool':
             data_list = realm['data']
             for j in range(len(data_list)):
                 data = data_list[j]
                 arr = data['data']
                 if (int(arr[0][2]) > 0):
                     field_list = []
                     field_list = add_tlv_field(field_list, 'interface', data['interface'])
                     idxstr = 'Egr ' + data['interface']
                     field_list = add_tlv_field(field_list, 'servicepool', (int) (arr[0][0]))
                     idxstr = idxstr + " Service Pool " + str(arr[0][0])
                     field_list = add_tlv_field(field_list, "idx", idxstr)
                     field_list = add_tlv_field(field_list, 'umsharebuffer', (int) (arr[0][2]))
                     logger.splunk_log(ip, 'Egress Port Service Pool', field_list)
                 if (int(arr[0][1]) > 0):
                     field_list = []
                     field_list = add_tlv_field(field_list, 'interface', data['interface'])
                     idxstr = 'Egr ' + data['interface']
                     field_list = add_tlv_field(field_list, 'servicepool', (int) (arr[0][0]))
                     idxstr = idxstr + " Service Pool " + str(arr[0][0]) + " uc"
                     field_list = add_tlv_field(field_list, "idx", idxstr)
                     field_list = add_tlv_field(field_list, 'ucsharebuffer', (int) (arr[0][1]))
                     logger.splunk_log(ip, 'Egress Port Service Pool', field_list)
                 if (int(arr[0][3]) > 0):
                     field_list = []
                     field_list = add_tlv_field(field_list, 'interface', data['interface'])
                     idxstr = 'Egr ' + data['interface']
                     field_list = add_tlv_field(field_list, 'servicepool', (int) (arr[0][0]))
                     idxstr = idxstr + " Service Pool " + str(arr[0][0]) + " mc"
                     field_list = add_tlv_field(field_list, "idx", idxstr)
                     field_list = add_tlv_field(field_list, 'mcsharebuffer', (int) (arr[0][3]))
                     logger.splunk_log(ip, 'Egress Port Service Pool', field_list)
         elif realm['realm'] == 'ingress-service-pool':
             data_list = realm['data']
             field_list = []
             field_list = add_tlv_field(field_list, 'servicepool', (int) (data_list[0][0]))
             idxstr = "Ing Service Pool " + str(data_list[0][0])
             field_list = add_tlv_field(field_list, "idx", idxstr)
             field_list = add_tlv_field(field_list, "umsharebuffer", (int) (data_list[0][1]))
             logger.splunk_log(ip, 'Ingress Service Pool', field_list)
         elif realm['realm'] == 'egress-service-pool':
             data_list = realm['data']
             if (int(data_list[0][1]) > 0):
                 field_list = []
                 field_list = add_tlv_field(field_list, 'servicepool', (int) (data_list[0][0]))
                 idxstr = "Egr Service Pool " + str(data_list[0][0])
                 field_list = add_tlv_field(field_list, "idx", idxstr)
                 field_list = add_tlv_field(field_list, 'umsharebuffer', (int) (data_list[0][1]))
                 logger.splunk_log(ip, 'Egress Service Pool', field_list)
             if (int(data_list[0][2]) > 0):
                 field_list = []
                 field_list = add_tlv_field(field_list, 'servicepool', (int) (data_list[0][0]))
                 idxstr = "Egr Service Pool " + str(data_list[0][0]) + " mc"
                 field_list = add_tlv_field(field_list, "idx", idxstr)
                 field_list = add_tlv_field(field_list, 'mcsharebuffer', (int) (data_list[0][2]))
                 logger.splunk_log(ip, 'Egress Service Pool', field_list)

def splunk_health_power_log(ip, rpt, logger):
   '''
   API's description: This API will form and write splunk log message
   '''
   logger.splunk_log(ip, 'POWER_STATUS', env_power_json2field(rpt))

def splunk_health_fans_log(ip, rpt, logger):
   '''
   API's description: This API will form and write splunk log message
   '''
   logger.splunk_log(ip, 'FANS_STATUS', env_fans_json2field(rpt))

def splunk_health_temperature_log(ip, rpt, logger):
   '''
   API's description: This API will form and write splunk log message
   '''
   logger.splunk_log(ip, 'TEMPERATURE_STATUS', env_temperature_json2field(rpt))

def splunk_health_resources_log(ip, rpt, logger):
   '''
   API's description: This API will form and write splunk log message
   '''
   logger.splunk_log(ip, 'RESOURCES_STATUS', env_resources_json2field(rpt))

