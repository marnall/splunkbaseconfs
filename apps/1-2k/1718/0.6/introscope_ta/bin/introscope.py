'''
v 0.6
(C) Copyright 2014 SBB AG (http://sbb.ch) and others.

All rights reserved. This program and the accompanying materials
are made available under the terms of the 
GNU Lesser General Public License (LGPL) version 2.1 
which accompanies this distribution, and is available at
http://www.gnu.org/licenses/lgpl-2.1.html
This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
Lesser General Public License for more details.

Contributors :
    Sebastien Brennion
'''
import splunk.Intersplunk as si
import sys,logging,time,datetime,re
import xml.dom.minidom,xml.sax.saxutils
import httplib,urllib
import base64
from string import Template

#set up logging
logging.root
logging.root.setLevel(logging.ERROR)
formatter = logging.Formatter('%(levelname)s %(message)s')
#with zero args , should go to STD ERR
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)


SCHEME = """<scheme>
    <title>Introscope</title>
    <description>Introscope Modular Input</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>   
            <arg name="name">
                <title>Introscope name</title>
                <description>Name of this input</description>
            </arg>
            <arg name="offset">
                <title>polling offset(m)</title>
                <description>The app alway polls data from now - x Minutes</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
                <arg name="polling_interval">
                <title>polling interval(m)</title>
                <description>The app alway polls x Minutes time frames</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="introscope_host">
                <title>Introscope host</title>
                <description>introscope host with port : introscope.com:8080>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="instroscope_path">
                <title>Introscope path</title>
                <description>introscope path to Soap Api : /introscope-web-services/services/MetricsDataService</description >
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="username">
                <title>username</title>
                <description></description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="password">
                <title>password</title>
                <description></description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="agentRegex">
                <title>agentRegex</title>
                <description></description>
                <value>test</value>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="metricRegex">
                <title>metricRegex</title>
                <description></description>
                <value>test</value>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="dataFrequency">
                <title>Data Frequency</title>
                <description></description>
                <value>test</value>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="outputElement">
                <title>outputElement</title>
                <description></description>
                <value>test</value>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="outputRegex">
                <title>outputRegex</title>
                <description></description>
                <value>test</value>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="soapTemplate">
                <title>Soap Template</title>
                <description></description>
                <value>test</value>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def do_validate():
    config = get_validation_config() 
    #TODO
    #if error , print_validation_error & sys.exit(2) 

def getKey (rawKey,outputRegex) :
    #build key, out of the passed string from agentName or metricName
    try :
        m= re.search(outputRegex, rawKey)
        outputText=""
        i=0
        
        
        # if no match
        if m == None : 
            outputText= "Could not match any value for the key with regex=%s and Element=%s" %(outputRegex,rawKey) 
        else :
            for group in m.groups() :
                if i!=0 :
                    outputText+= "_"
                outputText+=group
                i = i +1   
            return outputText
            #print outputText
    except RuntimeError,e:
        logging.error("Looks like an error: %s" % str(e))
        sys.exit(2)   
        
        
def IntroscopeResponseHandler (raw_response_output,config):
    try : 
        #print_xml_single_instance_mode(raw_response_output)
        #sys.stdout.flush()  
        xmldoc = xml.dom.minidom.parseString(raw_response_output)
        metricHeader=[]
        metricData=[]
        results=[]
        #logging.error("there is %s multiRef" % str(xmldoc.getElementsByTagName('multiRef').length))
        for m in xmldoc.getElementsByTagName('multiRef'):
            type=str(m.attributes['xsi:type'].value)
            matchObj = re.search( r":(?P<node>\w+)", type)
            type = matchObj.group("node")

            if  type =='TimesliceGroupedMetricData' :
                introTime=str(m.getElementsByTagName('timesliceStartTime')[0].firstChild.data)
                #print(str(m.getElementsByTagName('timesliceStartTime')[0].firstChild.data))
                #ttime = time.strptime(str(m.getElementsByTagName('timesliceStartTime')[0].firstChild.data),'%Y-%m-%dT%H:%M:%S.000Z')
                #ttime = time.mktime(ttime)
                ttime=str(int(time.mktime(datetime.datetime.strptime(str(m.getElementsByTagName('timesliceStartTime')[0].firstChild.data),'%Y-%m-%dT%H:%M:%S.000Z').timetuple())))
                href=[]
                for md in m.getElementsByTagName('metricData')[0].getElementsByTagName('metricData') : 
                    href.append(md.attributes['href'].value[1:])
                metricHeader.append({'childs' : href , 'header' : str(m.attributes['id'].value) , 'time' : introTime})
            elif type == 'MetricData':
                #define the ouput key (in _time key=value) out of agentName or metricName
                key_raw=str(m.getElementsByTagName(config["outputElement"])[0].firstChild.data)                
                metricData.append({'id' : str(m.attributes['id'].value) , 'key' : getKey(key_raw,config["outputRegex"]), 'value' : str(m.getElementsByTagName('metricValue')[0].firstChild.data)})

            
        for h in metricHeader :
            result =str(h["time"]) + ' '
            for d in h["childs"] :
                dataList = [item    for item in metricData if item['id'] == d]
                line=dataList[0]
                result += ' ' + str(line["key"]) + '=' + str(line["value"])
            #logging.error("time=: %s " % str(h["time"])  )
            print_xml_single_instance_mode( result )
            sys.stdout.flush()  

       
    except RuntimeError,e:
        logging.error("Looks like an error: %s" % str(e))
        sys.exit(2) 
        
def do_run() :
    try:
        config = get_input_config() 
        SoapMessage=Template(config['soapTemplate'])
        message=SoapMessage
        host = config['introscope_host']
        url = config['introscope_path']
        #httplib.HTTPConnection.debuglevel = 1
        auth = base64.encodestring('%s:%s' % (config['username'],  config['password'])).replace('\n', '')
        offset=datetime.timedelta(minutes=int(config['offset']))
        interval=datetime.timedelta(minutes=int(config['polling_interval']))
        t_now=datetime.datetime.utcnow()
      
        
        while True :
            try : 
                
                t_now=t_now - datetime.timedelta(seconds=t_now.second)  
                t_startTime=t_now - (offset + interval)
                t_endTime=t_startTime + interval
                t_nextStart = t_endTime  + offset + interval
                message=str(SoapMessage.safe_substitute(agentRegex=config['agentRegex'], metricRegex=config['metricRegex'], dataFrequency=config['dataFrequency'],startTime=t_startTime.strftime('%Y-%m-%dT%H:%M:%S.000Z'), endTime=t_endTime.strftime('%Y-%m-%dT%H:%M:%S.000Z')))
                


                #prepare request
                webservice = httplib.HTTP(host)
                webservice.putrequest("POST", url)
                webservice.putheader("Host", host)
                webservice.putheader("User-Agent", "Python http auth")
                webservice.putheader("Content-type", "text/html; charset=\"UTF-8\"")
                webservice.putheader("Content-length", "%d" % len(message))
                webservice.putheader("Authorization", "Basic %s" % auth)
                webservice.putheader("Accept-Encoding" , 'gzip,deflate')
                webservice.putheader("Connection" , 'Keep-Alive')
                webservice.putheader("SOAPAction", "\"\"")
                webservice.endheaders()
                webservice.send(message)
                statuscode, statusmessage, header = webservice.getreply()
                res = webservice.getfile().read()
                #print_xml_single_instance_mode(message )
                IntroscopeResponseHandler (res,config)
                #logging.error("before loop -> timenow=%s  nexstart=%s startTime=%s endTime=%s" % (t_now.strftime('%H:%M:%S.000Z')  ,  t_nextStart.strftime('%H:%M:%S.000Z'), t_startTime.strftime('%H:%M:%S.000Z'), t_endTime.strftime('%H:%M:%S.000Z') ))
                
                while t_now < t_nextStart :
                    time.sleep(10)
                    t_now=datetime.datetime.utcnow()
                    #logging.info("loop tnow=%s" % t_now.strftime('%H:%M:%S.000Z') )
                
            except RuntimeError,e:
                logging.error("Looks like an error: %s" % str(e))
                t_now=datetime.datetime.utcnow()


    except RuntimeError,e:
        logging.error("Looks like an error: %s" % str(e))
        sys.exit(2)       
# prints validation error data to be consumed by Splunk
def print_validation_error(s):
    print "<error><message>%s</message></error>" % xml.sax.saxutils.escape(s)
    
# prints XML stream
def print_xml_single_instance_mode(s):
    print "<stream><event><data>%s</data></event></stream>" % xml.sax.saxutils.escape(s)
    
# prints XML stream
def print_xml_multi_instance_mode(s,stanza):
    print "<stream><event stanza=""%s""><data>%s</data></event></stream>" % stanza,xml.sax.saxutils.escape(s)
    
# prints simple stream
def print_simple(s):
    print "%s\n" % s
    
def usage():
    print "usage: %s [--scheme|--validate-arguments]"
    logging.error("Incorrect Program Usage")
    sys.exit(2)

def do_scheme():
    print SCHEME

#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_input_config():
    config = {}

    try:
        # read everything from stdin
        config_str = sys.stdin.read()

        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            logging.debug("XML: found configuration")
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    logging.debug("XML: found stanza " + stanza_name)
                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        logging.debug("XML: found param '%s'" % param_name)
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            logging.debug("XML: '%s' -> '%s'" % (param_name, data))

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and \
           checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception, "Invalid configuration received from Splunk."

        
    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

    return config

#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_validation_config():
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
    doc = xml.dom.minidom.parseString(val_str)
    root = doc.documentElement

    logging.debug("XML: found items")
    item_node = root.getElementsByTagName("item")[0]
    if item_node:
        logging.debug("XML: found item")

        name = item_node.getAttribute("name")
        val_data["stanza"] = name

        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            logging.debug("Found param %s" % name)
            if name and param.firstChild and \
               param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                val_data[name] = param.firstChild.data

    return val_data

if __name__ == '__main__':
     
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":           
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            do_validate()
        else:
            usage()
    else:
        do_run()
        
    sys.exit(0)