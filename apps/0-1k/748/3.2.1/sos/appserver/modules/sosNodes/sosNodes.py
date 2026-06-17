import json
import logging
import os
import sys
from collections import Counter
import cherrypy
import controllers.module as module
import splunk
import splunk.search
import splunk.util
import lib.util as util
from splunk.appserver.mrsparkle.lib import jsonresponse

logger = logging.getLogger('splunk')

class sosNodes(module.ModuleHandler):

    def generateResults(self, host_app, client_app, sid, endpoint, internal, count=None):

        internal = splunk.util.normalizeBoolean(internal)
        job = splunk.search.JobLite(sid);
        rs = job.getResults(endpoint, count=100000)

        ''' 
        retrieve results from context search
        or from internal heatmap search 
        '''
        if internal is False:

            output = {'racks': {},'sym': {} }
            downed =  {} 
            tmp = {}
            symbol=""
            fullrack=[]
            for i in rs.results():
                fullrack.append(str(i['rack']))
            racktotals=Counter(fullrack)   
            shcount=1
            idxcount=1
            fwdcount=1
            for row in rs.results(): 

                host = str(row['host'])
                service = str(row['services'])
                racker=str(row['rack'])
                totalnode=racktotals[racker]

                
                if 'symbol' in row: 
                    symbol = str(row['symbol'])
                    if (symbol is not None) and (len(symbol)>0):
                         output['sym'][service]=symbol

                if racker=="SH":
                  if totalnode >100 and shcount<=100:
                     rack = str(row['rack'])+" - displaying 100 of "+str(totalnode)
                     status = int(str(row['status']))
                     if status != 1:
                         downed[host] = 1
                     if rack not in output['racks'].keys():
                         output['racks'][rack] = {}
                     if host not in output['racks'][rack].keys():
                         output['racks'][rack][host] = [{service: status}]
                     else:
                         output['racks'][rack][host].append({service: status})
                     output['downed'] = downed
                  elif totalnode <=1000:
                     rack = str(row['rack'])+" - displaying "+str(totalnode)+" of "+str(totalnode)
                     status = int(str(row['status']))
                     if status != 1:
                         downed[host] = 1
                     if rack not in output['racks'].keys():
                         output['racks'][rack] = {}
                     if host not in output['racks'][rack].keys():
                         output['racks'][rack][host] = [{service: status}]
                     else:
                         output['racks'][rack][host].append({service: status})
                     output['downed'] = downed
                  shcount=shcount+1
 
                  
                if racker=="IDX":
                  if totalnode >1000 and idxcount<=1000:
                     rack = str(row['rack'])+" - displaying 1000 of "+str(totalnode)
                     status = int(str(row['status']))
                     if status != 1:
                         downed[host] = 1
                     if rack not in output['racks'].keys():
                         output['racks'][rack] = {}
                     if host not in output['racks'][rack].keys():
                         output['racks'][rack][host] = [{service: status}]
                     else:
                         output['racks'][rack][host].append({service: status})
                     output['downed'] = downed
                  elif totalnode <=1000:
                     rack = str(row['rack'])+" - displaying "+str(totalnode)+" of "+str(totalnode)
                     status = int(str(row['status']))
                     if status != 1:
                         downed[host] = 1
                     if rack not in output['racks'].keys():
                         output['racks'][rack] = {}
                     if host not in output['racks'][rack].keys():
                         output['racks'][rack][host] = [{service: status}]
                     else:
                         output['racks'][rack][host].append({service: status})
                     output['downed'] = downed
                  idxcount=idxcount+1

                if racker=="FWD":
                  if totalnode >10000 and fwdcount<=10000:
                     rack = str(row['rack'])+" - displaying 10000 of "+str(totalnode)
                     status = int(str(row['status']))
                     if status != 1:
                         downed[host] = 1
                     if rack not in output['racks'].keys():
                         output['racks'][rack] = {}
                     if host not in output['racks'][rack].keys():
                         output['racks'][rack][host] = [{service: status}]
                     else:
                         output['racks'][rack][host].append({service: status})
                     output['downed'] = downed
                  elif totalnode <=10000:
                     rack = str(row['rack'])+" - displaying "+str(totalnode)+" of "+str(totalnode)
                     status = int(str(row['status']))
                     if status != 1:
                         downed[host] = 1
                     if rack not in output['racks'].keys():
                         output['racks'][rack] = {}
                     if host not in output['racks'][rack].keys():
                         output['racks'][rack][host] = [{service: status}]
                     else:
                         output['racks'][rack][host].append({service: status})
                     output['downed'] = downed
                  fwdcount=fwdcount+1




        else:

            output = {'heatmap': {}}

            for row in rs.results():

                host = str(row['host'])
                heatmap = str(row['heatmap'])

                output['heatmap'][host] = heatmap

        return self.render_json(output)

    def render_json(self, response_data, set_mime='text/json'):
        cherrypy.response.headers['Content-Type'] = set_mime
        if isinstance(response_data, jsonresponse.JsonResponse):
            response = response_data.toJson().replace("</", "<\\/")
        else:
            response = json.dumps(response_data).replace("</", "<\\/")
        return ' ' * 256  + '\n' + response
