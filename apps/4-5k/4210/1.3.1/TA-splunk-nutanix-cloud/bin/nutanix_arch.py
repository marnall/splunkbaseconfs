from splunklib.modularinput import *
import requests
import json
import sys

requests.packages.urllib3.disable_warnings()

class NutanixARCH(Script):
    
    
    def get_scheme(self):
        """ Defining a scheme in plaintext which will provide Splunkd data about the modular input."""
        # About the Modular Input
        scheme = Scheme('Nutanix Prism API Architecture')
        scheme.description = 'Streams architecture data: Host, VMs, Disks.'
        scheme.use_external_validation = True
        
        # About the username located in inputs.conf.spec
        username_argument = Argument('username')
        username_argument.data_type = Argument.data_type_string
        username_argument.description = 'Username is necessary to authenticate with the Nutanix Prism Rest API.'
        username_argument.required_on_create = True
        scheme.add_argument(username_argument)
        
        # About the password located in inputs.conf.spec
        password_argument = Argument('password')
        password_argument.data_type = Argument.data_type_string
        password_argument.description = 'Password is necessary to authenticate with the Nutanix Prism Rest API'
        password_argument.required_on_create = True
        scheme.add_argument(password_argument)
        
        
        # About the IP/Hostname located in inputs.conf.spec
        ip_argument = Argument('ip')
        ip_argument.data_type = Argument.data_type_string
        ip_argument.description = 'IP or Hostname is necessary to access the Nutanix Prism Rest API.'
        ip_argument.required_on_create = True
        scheme.add_argument(ip_argument)
        
        
        # About the port located in inputs.conf.spec
        port_argument = Argument('port')
        port_argument.data_type = Argument.data_type_string
        port_argument.description = 'Port is necessary to access the Nutanix Prism Rest API.'
        port_argument.required_on_create = True
        scheme.add_argument(port_argument)
        return scheme
    

    def stream_events(self,inputs,ew):
         # Taken from Splunk's event writer module.
        
        """The method called to stream events into Splunk. It should do all of its output via
             EventWriter rather than assuming that there is a console attached.
             :param ew: An object with methods to write events and log messages to Splunk."""
        try:
            ew.log('INFO','Obtaining Username, Password, Console IP, and Port Number from inputs.conf.')
            for input_name, input_item in inputs.inputs.iteritems():
                Username = input_item['username']
                Password = input_item['password']
                IP = input_item['ip']
                Port = input_item['port']     
            ew.log('INFO', 'Accessing Nutanix Rest API for host data using Username:%s,Password:%s,IP:%s,Ports:%s' %(Username, Password, IP, Port))
                        
            # Creating a session
            endpoint = 'https://%s:%s/PrismGateway/services/rest/v1/' %(IP, Port)
            req = requests.Session()
            req.auth = (Username, Password)
            req.headers.update({'Content-Type': 'application/json; charset=utf-8'})

            # Obtaining data on Hosts and testing response.
           
            ew.log('INFO','Obtaining data about the hosts in a cluster.')
            datasource = req.get(endpoint+'hosts/',verify=False)
            if datasource.status_code == 200:
                for item in datasource.json()['entities']:
                    event = Event()
                    event.stanza = input_name
                    event.source = 'nutanix:hosts'
                    event.host = endpoint+'hosts/'
                    event.data = json.dumps(item)
                    event.sourcetype = 'nutanix_arch'
                    ew.write_event(event)
                
                # Obtaining data on VMs.
                ew.log('INFO','Obtaining data about the VMs in a cluster.')
                datasource = req.get(endpoint+'vms/',verify=False)
                for item in datasource.json()['entities']:
                    event = Event()
                    event.stanza = input_name
                    event.source = 'nutanix:vms'
                    event.host = endpoint+'vms/'
                    event.data = json.dumps(item)
                    event.sourcetype = 'nutanix_arch'
                    ew.write_event(event)
                        
                # Obtaining data on Disks.
                ew.log('INFO','Obtaining data about the Disks in a cluster.')
                datasource = req.get(endpoint+'disks/',verify=False)
                for item in datasource.json()['entities']:
                     event = Event()
                     event.stanza = input_name
                     event.source = 'nutanix:disks'
                     event.host = endpoint+'disks/'
                     event.data = json.dumps(item)
                     event.sourcetype = 'nutanix_arch'
                     ew.write_event(event)
                # Obtaining data on data resiliency
                ew.log('INFO','Obtaining the data resiliency status of a cluster.')
                datasource = req.get(endpoint+'cluster/domain_fault_tolerance_status/',verify=False)
                for item in datasource.json():
                    event = Event()
                    event.stanza = input_name
                    event.source = 'nutanix:resiliency'
                    event.host = endpoint+'cluster/domain_fault_tolerance_status/'
                    event.data = json.dumps(item)
                    event.sourcetype = 'nutanix_resiliency'
                    ew.write_event(event)


                        
            elif datasource.status_code == 401 or datasource.status_code == 403:
                ew.log('ERROR','The Nutanix Prism API username and/password is incorrect or unauthorized for API access. A status code of %s was returned.' %datasource.status_code)
                       
            else:
                ew.log('ERROR','A status code of %s was returned. Splunk was unable to retrieve data from the Nutanix Prism API.' %datasource.status_code)
                
        except Exception as e:
            ew.log('ERROR',' Splunk was unable to retrieve data from the Nutanix Prism API. The following error was encountered when accessing the Nutanix API Endpoint to obtain architecture data: %s' %e)
                 
                 
if __name__ == '__main__':
    sys.exit(NutanixARCH().run(sys.argv))
    
