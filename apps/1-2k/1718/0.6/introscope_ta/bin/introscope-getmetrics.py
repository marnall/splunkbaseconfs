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


# prints XML stream
def print_xml_stream(s):
    print "<stream><event unbroken=\"1\"><data>%s</data><done/></event></stream>" % encodeXMLText(s)
# prints XML stream
def print_xml_single_instance_mode(s):
    print "<stream><event><data>%s</data></event></stream>" % xml.sax.saxutils.escape(s)


def encodeXMLText(text):
    text = text.replace("&", "&amp;")
    text = text.replace("\"", "&quot;")
    text = text.replace("'", "&apos;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("\n", "")
    return text

def IntroscopeResponseHandler (raw_response_output):
    try : 
        xmldoc = xml.dom.minidom.parseString(raw_response_output)
        #print (raw_response_output + '\n')
        metricHeader=[]
        metricData=[]
        result=[]
        results=[]
        
        for m in xmldoc.getElementsByTagName('multiRef'):
            #print (m.attributes['id'].value)
            type=str(m.attributes['xsi:type'].value)
            #if  m.hasAttributes['xsi:type'].value == "ns3:TimesliceGroupedMetricData"  : 
            matchObj = re.search( r":(?P<node>\w+)", type)
            type = matchObj.group("node")
            #print('type =' + type)
            if  type =='TimesliceGroupedMetricData' :
                #print(str(m.getElementsByTagName('timesliceStartTime')[0].firstChild.data))
                ttime = time.strptime(str(m.getElementsByTagName('timesliceStartTime')[0].firstChild.data),'%Y-%m-%dT%H:%M:%S.000Z')
                ttime = time.mktime(ttime) 
                href=[]
                for md in m.getElementsByTagName('metricData')[0].getElementsByTagName('metricData') : 
                    href.append(md.attributes['href'].value[1:])
                metricHeader.append({'childs' : href , 'header' : str(m.attributes['id'].value) , 'time' : ttime})
            elif type == 'MetricData':
                agentName=str(m.getElementsByTagName('agentName')[0].firstChild.data)
                matchObj = re.search( r'(?P<node>\w*)\|(?P<application>\w*)\|(?P<cluster>\w+)\/(?P<hostname>\w+)', agentName)
                host=matchObj.group("cluster") + "_" + matchObj.group("hostname")
                metricData.append({'id' : str(m.attributes['id'].value) , 'host' : host, 'value' : str(m.getElementsByTagName('metricValue')[0].firstChild.data)})
                
        for h in metricHeader :
            result={'_time': h["time"]}
            for d in h["childs"] :
                dataList = [item    for item in metricData if item['id'] == d]
                #print(dataList[0])
                line=dataList[0]
                #to_do add alert if nb>1
                result[str(line["host"])]=str(line["value"])
            results.append(result)
        #print(results)
        si.outputResults(results)
        #sys.stdout.flush() 
        
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        #print("Error '%s'. %s" % (e, stack))
        si.generateErrorResults("Error '%s'. %s" % (e, stack))
        #si.generateErrorResults(str(e))
        
if __name__ == '__main__':
    try:
        SoapMessage=Template('<soapenv:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:met="http://metricsdata.webservicesimpl.server.introscope.wily.com">   <soapenv:Header/>   <soapenv:Body>      <met:getMetricData soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">         <agentRegex xsi:type="xsd:string">$agentRegex</agentRegex>         <metricRegex xsi:type="xsd:string">$metricRegex</metricRegex>         <startTime xsi:type="xsd:dateTime">$startTime</startTime>         <endTime xsi:type="xsd:dateTime">$endTime</endTime>         <dataFrequency xsi:type="xsd:int">$dataFrequency</dataFrequency>      </met:getMetricData>   </soapenv:Body></soapenv:Envelope>')
        #message='<soapenv:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:met="http://metricsdata.webservicesimpl.server.introscope.wily.com"> <soapenv:Header/> <soapenv:Body> <met:getMetricData soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"> <agentRegex xsi:type="xsd:string">(.*)kihub33_a_(.*)</agentRegex> <metricRegex xsi:type="xsd:string">CPU:Utilization % \(process\)</metricRegex> <startTime xsi:type="xsd:dateTime">2013-12-21T00:00:00Z</startTime> <endTime xsi:type="xsd:dateTime">2013-12-21T10:00:00Z</endTime> <dataFrequency xsi:type="xsd:int">60</dataFrequency> </met:getMetricData> </soapenv:Body></soapenv:Envelope>'
        message=str(SoapMessage.safe_substitute(agentRegex='(.*)kihub33_a_(.*)', metricRegex='CPU:Utilization % \(process\)', dataFrequency='60',startTime='2013-12-27T10:00:00Z', endTime='2013-12-27T10:30:00Z'))
        host = 'introscope.com:8080'
        url = '/introscope-web-services/services/MetricsDataService'
        username = 'test'
        password = 'test'
        #httplib.HTTPConnection.debuglevel = 1
        auth = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        webservice = httplib.HTTP(host)
        webservice.putrequest("POST", url)
        webservice.putheader("Host", host)
        webservice.putheader("User-Agent", "Python http auth")
        webservice.putheader("Content-type", "text/html; charset=\"UTF-8\"")
        webservice.putheader("Content-length", "%d" % len(message))
        webservice.putheader("Authorization", "Basic %s" % auth)
        webservice.putheader("Accept-Encoding" , 'gzip,deflate')
        webservice.putheader("Connection" , 'Keel-Alive')
        webservice.putheader("SOAPAction", "\"\"")
        webservice.endheaders()
        webservice.send(message)
        

        statuscode, statusmessage, header = webservice.getreply()
        #print('test:' + statusmessage + str(statuscode))
        #results.append({'_time' : now, '_raw' : statusmessage + str(statuscode) })        
        res = webservice.getfile().read()
        #results=[]
        #results.append({'_raw' : res })
        #si.outputResults(results)
        #print(res)
        IntroscopeResponseHandler (res)
 
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        #print("Error '%s'. %s" % (e, stack))
        si.generateErrorResults("Error '%s'. %s" % (e, stack))
        #si.generateErrorResults(str(e))

    
