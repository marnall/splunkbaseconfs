# required imports
import cherrypy
import controllers.module as module
import splunk.rest as rest
import splunk.searchhelp.searchhelper as sh
import urllib
import lxml.etree as etree
import collections
import splunk.appserver.mrsparkle.lib.util as util




# logging setup
import logging
logger = logging.getLogger('splunk.appserver.controllers.module.SimpleResultsTable')

class searchbuilderAnalyzer(module.ModuleHandler):
    '''
    The best controller for a module you have ever seen
    '''
    
    def generateResults(self, host_app, client_app, search):

        sessionKey=cherrypy.session['sessionKey']

        searchStr=urllib.quote(search)

        try:
            parserResponse, parserContent = rest.simpleRequest("/services/search/parser?output_mode=xml&parse_only=true&q="+searchStr, raiseAllErrors=True)
        except Exception, e:
            #return  '<p>%s</p><br>' % e
            return   e

        parserContentXML = etree.XML(parserContent)




        segments = collections.OrderedDict()
        searchString = ""
        output = []
        output.append('<table style="clear:both">')
        output.append('<span class="hider" style="float:right;clear:right">Toggle extended help</span>')
        for item in parserContentXML.find('list'):
            for d in item:
                segment = {}
                for key in d:
                          segment[ key.attrib["name"]] = key.text
                if searchString:
                    searchString += " | "
                segmentString = urllib.quote("%s %s" % (segment['command'],  segment['rawargs']))
                searchString += urllib.quote(segmentString)
                segment['fullSearch'] = searchString
                segments[segmentString] = segment
                output.append('<tr><td class="searcher" style="max-width:200px"><span class="%s miniSearch" data-search="%s">%s</span>' % (segment['pipeline'],urllib.unquote(searchString),urllib.unquote(segmentString)))
                help = sh.help(sessionKey, host_app, 'admin' ,segment['command'] ,useTypeahead=False, showCommandHelp=True, showCommandHistory=False, showFieldInfo=False)
                commander=help['command']
                output.append('</td><td class=commander style="display:table-cell">%s</td>' % (help['command']['details']))
                output.append('<td><a target="_blank" href="http://docs.splunk.com/Documentation/Splunk/5.0/SearchReference/%s">help</a></td></tr>' % ( segment['command']))
        output.append('</table>')
    
        return "".join(output)
