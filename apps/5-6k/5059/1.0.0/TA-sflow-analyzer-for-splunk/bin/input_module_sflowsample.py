
# encoding = utf-8

import os
import sys
import time
import datetime
def validate_input(helper, definition):
    import subprocess
    interface = definition.parameters.get('interface', None)
    cmd=["sudo","tshark","-D"]
    check_interface=subprocess.check_output(cmd,stderr=subprocess.PIPE)
    check_interface=check_interface.decode("utf-8")
    if interface in check_interface:
        pass
    else:
        print("ERROR: Interface does not exist or does not support packet capture")
        sys.exit(0)

def collect_events(helper, ew):
    import sys
    import json
    import subprocess
    import datetime
    opt_interface = helper.get_arg('interface')
    cmd=["tshark","-i",opt_interface,"-n","-T","json","udp port 6343"]
    found_sflow_sample=False
    agent_string='"sflow_245.agent": "unknown",'
    vxlan=False
    stream=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    for line in iter(stream.stdout.readline,""):
        string=line.strip()
        if not found_sflow_sample:
            if "sflow_245.agent" in string:
               agent_string=string
            elif "Flow sample," in string:
              found_sflow_sample=True
              found_header=False
              unclosed=1
              sample_str='{'+"\"time\": \""+str(datetime.datetime.now())+'\",'+agent_string
        elif found_sflow_sample:
            if ("sflow.flow_sample.sampling_rate" in string) or ("sflow_245.header.frame_length" in string):
                sample_str+=string
            elif "sflow_245.header_tree" in string:
                sample_str+=string
                found_header=True
                unclosed+=1
            elif (found_header==True and unclosed>0):
                if '"vxlan": {' in string:
                    vxlan=True
                    sample_str+='"vxlan": {'
                elif ("eth.type" in string) or ("vlan.etype" in string):
                    ethertype=(string.split(': ')[1]).rstrip(',')
                elif ('"vlan": {') in string:
                    if '0x00008100' in ethertype:
                        string='"c-vlan": {'
                    elif '0x000088A8' in ethertype:
                        string='"s-vlan": {' 
                if ('{' in string) or ('[' in string):
                    unclosed+=1
                elif ('}' in string) or (']' in string):
                    unclosed-=1
                sample_str+=string
            elif unclosed==0:
                found_sflow_sample=False
                if vxlan:
                    vxlan=False
                    sample_str+='}'
                sample_str+='\n'
                data = sample_str
                event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
                ew.write_event(event)