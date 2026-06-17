import json
import logging
import os
import sys
import cherrypy
import controllers.module as module
import splunk
import splunk.search
import splunk.util
import lib.util as util
from splunk.appserver.mrsparkle.lib import jsonresponse

logger = logging.getLogger('splunk.appserver.controllers.module.sosnodes')

class sosnodes(module.ModuleHandler):

    def generateResults(self, host_app, client_app, sid, endpoint, internal, count=None):

        internal = splunk.util.normalizeBoolean(internal)
        job = splunk.search.JobLite(sid);
        rs = job.getResults(endpoint, count=count)

        ''' 
        retrieve results from context search
        or from internal heatmap search 
        '''
        if internal is False:

            output = {'racks': {}}
            downed =  {} 
            tmp = {}

            for row in rs.results(): 

                host = str(row['host'])
                service = str(row['services'])
                rack = str(row['rack'])
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
