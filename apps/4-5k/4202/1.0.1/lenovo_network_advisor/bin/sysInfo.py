from connect import *
import requests
import json
from random import randint


fans = '/nos/api/sysinfo/fans'
temperature = '/nos/api/sysinfo/temperatures'
power = '/nos/api/sysinfo/power'
health = '/nos/api/sysinfo/globalhealthstatus'
resources = '/nos/api/sysinfo/resources'
hostname = '/nos/api/cfg/hostname'

#Class to provide basic properties of the system
class SystemInfo:
    """ Class to provide basic properties of the system """
    def __init__(self):
	#self.logger = FieldLogHandler('/opt/splunkforwarder/etc/apps/lenovo_network_advisor/logs/lenovo_cnos_system_health.log', 10, 10, INFO, 'SYSTEM_HEALTH')
	self.logger = None
	
    def get_simul_power(self,conn,sev):
        rpt = {}
        power1 =  {}
        power1["Model"] = 'XXXXXXXXXX'
        power1["Manufacturer"] = 'DELTA'
        x = randint(0, 1)
        power1["State"] = 'Normal ON'
        if (x == 1):
           power1["State"] = 'OFF'
        
        power1["Name"] = 'Power Supply 1'
        rpt["Power 1"] = power1
        power2 = {}
        power2["Model"] = 'XXXXXXXXXX'
        power2["Manufacturer"] = 'DELTA'
        power2["State"] = 'Normal ON'
        x = randint(0, 1)
        if (x == 1):
           power2["State"] = 'OFF'
        power2["Name"] = 'Power Supply 2'
        rpt["Power 2"] = power2
        return rpt

    def get_env_power(self, conn):
        '''
            API's description: This API will get enviroment power details
            Mandatory arguments:  None
            Optional arguments: None
            Returns: Dictionary or None if error happens
            {
                "Power 1":
                {
                        "Name" : "Power Supply 1"
                        "Manufacturer" : " DELTA",
                        "Model" : "XXXXXXXXXX",
                        "State" : "Normal ON"
                },
                "Power 2":
                {
                        "Name" : "Power Supply 2"
                        "Manufacturer" : " DELTA",
                        "Model" : "XXXXXXXXXX",
                        "State" : "12V Output Fault"
                },
            }

        '''
        tmp_url=form_url(conn, power)
        hdr = form_hdr(conn)
#        ret = requests.get(tmp_url, headers=hdr, auth=(conn.user, conn.password), verify=False, timeout=10)
        (ret, report) = conn.get(power)
        
	return report

    def evn_fans_json2field(self, report):
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

	if report.has_key('Fan 1'):
	    if  report['Fan 1'].has_key('speed-percent') and report['Fan 1'].has_key('speed-rpm'):
		splunk_field = {}
		splunk_field['name'] = 'FAN1_SPEED_PERCENT'
		splunk_field['value'] = report['Fan 1']['speed-percent']
		field_list.append(splunk_field)

		splunk_field = {}
		splunk_field['name'] = 'FAN1_SPEED_RPM'
		splunk_field['value'] = report['Fan 1']['speed-rpm']
		field_list.append(splunk_field)

	if report.has_key('Fan 2'):
	    if  report['Fan 2'].has_key('speed-percent') and report['Fan 2'].has_key('speed-rpm'):
		splunk_field = {}
		splunk_field['name'] = 'FAN2_SPEED_PERCENT'
		splunk_field['value'] = report['Fan 2']['speed-percent']
		field_list.append(splunk_field)

		splunk_field = {}
		splunk_field['name'] = 'FAN2_SPEED_RPM'
		splunk_field['value'] = report['Fan 2']['speed-rpm']
		field_list.append(splunk_field)

	if report.has_key('Fan 3'):
	    if  report['Fan 3'].has_key('speed-percent') and report['Fan 3'].has_key('speed-rpm'):
		splunk_field = {}
		splunk_field['name'] = 'FAN3_SPEED_PERCENT'
		splunk_field['value'] = report['Fan 3']['speed-percent']
		field_list.append(splunk_field)

		splunk_field = {}
		splunk_field['name'] = 'FAN3_SPEED_RPM'
		splunk_field['value'] = report['Fan 3']['speed-rpm']
		field_list.append(splunk_field)


	if report.has_key('Fan 4'):
	    if  report['Fan 4'].has_key('speed-percent') and report['Fan 4'].has_key('speed-rpm'):
		splunk_field = {}
		splunk_field['name'] = 'FAN4_SPEED_PERCENT'
		splunk_field['value'] = report['Fan 4']['speed-percent']
		field_list.append(splunk_field)

		splunk_field = {}
		splunk_field['name'] = 'FAN4_SPEED_RPM'
		splunk_field['value'] = report['Fan 4']['speed-rpm']
		field_list.append(splunk_field)

	if report.has_key('Fan 5'):
	    if  report['Fan 5'].has_key('speed-percent') and report['Fan 5'].has_key('speed-rpm'):
		splunk_field = {}
		splunk_field['name'] = 'FAN5_SPEED_PERCENT'
		splunk_field['value'] = report['Fan 5']['speed-percent']
		field_list.append(splunk_field)

		splunk_field = {}
		splunk_field['name'] = 'FAN5_SPEED_RPM'
		splunk_field['value'] = report['Fan 5']['speed-rpm']
		field_list.append(splunk_field)


	if report.has_key('Fan 6'):
	    if  report['Fan 6'].has_key('speed-percent') and report['Fan 6'].has_key('speed-rpm'):
		splunk_field = {}
		splunk_field['name'] = 'FAN6_SPEED_PERCENT'
		splunk_field['value'] = report['Fan 6']['speed-percent']
		field_list.append(splunk_field)

		splunk_field = {}
		splunk_field['name'] = 'FAN6_SPEED_RPM'
		splunk_field['value'] = report['Fan 6']['speed-rpm']
		field_list.append(splunk_field)

	if report.has_key('Fan 7'):
	    if  report['Fan 7'].has_key('speed-percent') and report['Fan 7'].has_key('speed-rpm'):
		splunk_field = {}
		splunk_field['name'] = 'FAN7_SPEED_PERCENT'
		splunk_field['value'] = report['Fan 7']['speed-percent']
		field_list.append(splunk_field)

		splunk_field = {}
		splunk_field['name'] = 'FAN7_SPEED_RPM'
		splunk_field['value'] = report['Fan 7']['speed-rpm']
		field_list.append(splunk_field)


	if report.has_key('Fan 8'):
	    if  report['Fan 8'].has_key('speed-percent') and report['Fan 8'].has_key('speed-rpm'):
		splunk_field = {}
		splunk_field['name'] = 'FAN8_SPEED_PERCENT'
		splunk_field['value'] = report['Fan 8']['speed-percent']
		field_list.append(splunk_field)

		splunk_field = {}
		splunk_field['name'] = 'FAN8_SPEED_RPM'
		splunk_field['value'] = report['Fan 8']['speed-rpm']
		field_list.append(splunk_field)

	if report.has_key('Fan 9'):
	    if  report['Fan 9'].has_key('speed-percent') and report['Fan 9'].has_key('speed-rpm'):
		splunk_field = {}
		splunk_field['name'] = 'FAN9_SPEED_PERCENT'
		splunk_field['value'] = report['Fan 9']['speed-percent']
		field_list.append(splunk_field)

		splunk_field = {}
		splunk_field['name'] = 'FAN9_SPEED_RPM'
		splunk_field['value'] = report['Fan 9']['speed-rpm']

	if report.has_key('Fan 10'):
	    if  report['Fan 10'].has_key('speed-percent') and report['Fan 10'].has_key('speed-rpm'):
		splunk_field = {}
		splunk_field['name'] = 'FAN10_SPEED_PERCENT'
		splunk_field['value'] = report['Fan 10']['speed-percent']
		field_list.append(splunk_field)

		splunk_field = {}
		splunk_field['name'] = 'FAN10_SPEED_RPM'
		splunk_field['value'] = report['Fan 10']['speed-rpm']

	if report.has_key('Fan 11'):
	    if  report['Fan 11'].has_key('speed-percent') and report['Fan 11'].has_key('speed-rpm'):
		splunk_field = {}
		splunk_field['name'] = 'FAN11_SPEED_PERCENT'
		splunk_field['value'] = report['Fan 11']['speed-percent']
		field_list.append(splunk_field)

		splunk_field = {}
		splunk_field['name'] = 'FAN11_SPEED_RPM'
		splunk_field['value'] = report['Fan 11']['speed-rpm']

	if report.has_key('Fan 12'):
	    if  report['Fan 12'].has_key('speed-percent') and report['Fan 12'].has_key('speed-rpm'):
		splunk_field = {}
		splunk_field['name'] = 'FAN12_SPEED_PERCENT'
		splunk_field['value'] = report['Fan 12']['speed-percent']
		field_list.append(splunk_field)

		splunk_field = {}
		splunk_field['name'] = 'FAN12_SPEED_RPM'
		splunk_field['value'] = report['Fan 12']['speed-rpm']


	return field_list

    def get_simul_fans(self,conn, sev):
        rpt = {}
        fan1 = {}
        fan1['speed-percent'] =  20
        if (sev == "Warning"):
           fan1['speed-percent'] =  90
         
#        fan1['speed-percent'] = randint(1, 90)
        fan1['speed-rpm']= 4340
        fan1['name'] = 'Fan1'
        fan1['module'] = 1
        fan1['air-flow'] = 'Front-to-Back'
        fan2 = fan1.copy()
        fan2['name'] = 'Fan2'
        fan3 = fan1.copy()
        fan3['name'] = 'Fan3'
        fan4 = fan1.copy()
        fan4['name'] = 'Fan4'
        fan5 = fan1.copy()
        fan5['name'] = 'Fan5'
        fan6 = fan1.copy()
        fan6['name'] = 'Fan6'
        fan7 = fan1.copy()
        fan7['name'] = 'Fan7'
        fan8 = fan1.copy()
        fan8['name'] = 'Fan8'
        fan8['speed-percent'] = 76 
        rpt['Fan 1'] = fan1
        rpt['Fan 2'] = fan2
        rpt['Fan 3'] = fan3
        rpt['Fan 4'] = fan4
        rpt['Fan 5'] = fan5
        rpt['Fan 6'] = fan6
        rpt['Fan 7'] = fan7
        rpt['Fan 8'] = fan8
        return rpt

    def get_env_fans(self, conn):
        '''
        API's description: This API will get enviroment fan details
        Mandatory arguments:  None
        Optional arguments: None
        Returns: Dictionary or None if error happens
        {
            "Fan 1":
            {
                "module" : 1
                "air-flow" : " Front-to-Back",
                "speed-percent" : 0,
                "speed-rpm" : 4205
            },
            "Fan 2":
            {
                "module" : 1
                "air-flow" : " Front-to-Back",
                "speed-percent" : 24,
                "speed-rpm" : 4402
            }
        }
        '''
        tmp_url=form_url(conn, fans)
        hdr = form_hdr(conn)
        (ret, report) = conn.get(fans)
	return report

    def get_simul_temperature(self, conn, sev):
        rpt = {}
        hot_spot = {}
        hot_spot['State'] = 'OK'
        hot_spot['Temp'] = randint(1, 40)
        if (sev == "Warning"):
           hot_spot['Temp'] = randint(50,70) 
        if (sev == "Critical"):
           hot_spot['Temp'] = randint(80,99) 
        rpt['Hot Spot'] = hot_spot
        cpu = {}
        cpu['State'] = 'OK'
        cpu['Temp'] = randint(1, 90)
        rpt['CPU Local'] = cpu
        temp_thres = {}
        temp_thres['System Warning'] = 85
        temp_thres['System Shutdown'] = 95
        temp_thres['System Set Point'] = 70 
        rpt['Temperature threshold'] = temp_thres
        amb = {}
        amb['State'] = 'OK'
        amb['Temp'] = 45
        rpt['Ambient'] = amb       
        return rpt


    def get_env_temperature(self, conn):
        '''
            API's description: This API will get enviroment temperature details
            Mandatory arguments:  None
            Optional arguments: None
            Returns: Dictionary or None if error happens
            {
               "Cpu Local":
               {
                    "Temp" : "31"
                    "State" : "OK"
               },
               "Hot Spot" :
               {
                    "Temp" : "46",
                    "State": "OK"
               },
	       "Temperature threshold": {
    		    "System Warning": 85,
		    "System Shutdown": 95,
		    "System Set Point": 70
               },
	       "CPU Local": {
		    "State": "OK",
		    "Temp": 37 
               },
  	       "Ambient": {
		    "State": "OK",
		    "Temp": 36
               }
	     }
        '''
        tmp_url=form_url(conn, temperature)
        hdr = form_hdr(conn)
        (ret, report)  = conn.get(temperature)
	return report

    def get_simul_hostname(self, conn, hostn):
        rpt = {}
        rpt["hostname"] = hostn
        return rpt

    def get_hostname(self, conn):
        '''
            API's description: This API will get system hostname
            Mandatory arguments:  None
            Optional arguments: None
            Returns: Dictionary or None if error happens
	    {
		"hostname": "MARS-2-test"
	    }

        '''
        tmp_url=form_url(conn, hostname)
        hdr = form_hdr(conn)
        (ret, report) = conn.get(hostname)
	return report

    def get_env_resources(self, conn):
        '''
            API's description: This API will get resources details
            Mandatory arguments:  None
            Optional arguments: None
            Returns: Dictionary or None if error happens
            {
             "Cpu(s)": {
               "idle": "79.8",
               "hardware_interrupt": "0.0",
               "stolen_time": "0.0",
               "software_interrupt": "0.0",
               "io_wait": "0.1",
               "system": "5.5",
               "user_nice": "0.0",
               "user_un_nice": "14.7"
             },
             "Mem": {
               "total": "4081540",
               "buffers": "516848",
               "free": "3077280",
               "used": "487412"
             },
             "tasks": {
               "zombie": "0",
               "running": "1",
               "total": "100",
               "stopped": "0",
               "sleeping": "99"
             },
             "load average": {
               "5 min": "0.34",
               "15 min": "0.36",
               "1 min": "0.37"
             }
	    }
        '''
        tmp_url=form_url(conn, resources)
        hdr = form_hdr(conn)
        (ret, report) = conn.get(resources)
	return report

    def get_simul_resources(self, conn, sevcpu, sevmem):
        rpt = {}
        cpu = {}
        cpu['idle'] = "79.8"
        cpu['hardware_interrupt'] = "0.0"
        cpu["stolen_time"] = "0.0"
        cpu["software_interrupt"] = "0.0"
        cpu["io_wait"] = "0.1"
        cpu["system"] = "5.0"
        cpu["user_nice"] = "0.0"
        cpu["user_un_nice"] = "14,7"
        rpt['Cpu(s)'] = cpu
        mem = {}
        mem["total"] = "4000000"
        mem["buffers"] = "500000"
        mem["free"] = "3000000"
        mem["used"] = "500000"
        if (sevmem == "Critical"):
            mem["buffers"] = "900000"
            mem["free"] = "10000"
            mem["used"] = "3900000"
        if (sevmem == "Warning"):
            mem["buffers"] = "100000"
            mem["free"] = "600000"
            mem["used"] = "3300000"
        rpt['Mem'] = mem 
        tasks1 = {'zombie':'0','running':'1','total':'103','stopped':'0','sleeping':'102'}
        rpt['tasks'] = tasks1
        ldavg = {'5 min':'0.46','15 min':'0.53','1 min':'0.29'}
        rpt['load average'] = ldavg
        return rpt
