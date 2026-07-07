import json
import sys
from time import sleep
from xml.etree import ElementTree as et

import splunklib.client as client
import splunklib.results as results


class splunkquery():

    def __init__(self, **kwargs):
        """
        The method is used to init an object of Splunk class
        :param host: Splunk Web (Search Head) hostname
        :param port: TCP port
        :param username: an account specified at Splunk
        :param password: a code phrase for the mentioned above account
        :param typeConnection: http or https
        """

        if 'sessionkey' in list(kwargs.keys()):
            #self.__service = client.Service(token=kwargs.get('sessionkey') )
            self.__service = client.Service(token=kwargs.get('sessionkey'), owner="nobody", app="TA-siemplify")
        if 'helper' in list(kwargs.keys()):
            self.helper = kwargs.get('helper')
        else:
            self.host = kwargs.get('host')
            self.port = kwargs.get('port')
            self.username = kwargs.get('username')
            self.password = kwargs.get('password')

            if 'type' in list(kwargs.keys()):
                self.type = kwargs.get('protocol')
            else:
                self.type = 'http'

            self.__service = client.connect(host=self.host,
                                            port=self.port,
                                            username=self.username,
                                            password=self.password,
                                            type=self.type)

    def _buildSplunkSettings(self, earliestTime, latestTime):
        """
        The private method
        :param earliestTime:
        :param latestTime:
        :return:
        """

        return {"earliest_time": earliestTime,
                "latest_time": latestTime,
                "search_mode": "normal",
                "exec_mode": "normal",
                "adhoc_search_level": "verbose"
                }

    def _buildSearchQuery(self, searchQuery, head):
        """
        We method is used to build search query to restrict time and a number of events.
        It might be helpful to limit searching time.
        :param searchQuery: Splunk query. Recommendation is not to used quotients.
        :param head: a value specified a number of events.
        :return: search query.
        """
        if not searchQuery.startswith('Search') or searchQuery.startswith('search'):
            searchQuery = 'search ' + searchQuery

        if head != 0:
            searchQuery += f' | head {head}'

        return searchQuery

    def connect(self):
        return self.__service

    def runExportSearch(self, searchQuery, head, earliestTime='-24h', latestTime='now'):
        """
        The method is used to run export search at Splunk. It uses an export REST API call.
        It means that Splunk doesn't save result on its side and directs found events to a client side.
        :param searchQuery: a query uses to run search
        :param head: a value specified a number of events.
        :param earliestTime: a value specified the earliest to get events.
        :param latestTime: a value specified the latest time to get events.
        Please check the article at Splunk.com to fully understand about time values.
        https://docs.splunk.com/Documentation/SplunkCloud/6.6.3/SearchReference/SearchTimeModifiers
        :return: JSON
        """

        service = self.connect()

        kwargs = self._buildSplunkSettings(earliestTime, latestTime)
        searchQuery = self._buildSearchQuery(searchQuery, head)

        self.helper.log_debug(f'Splunk Query Module: {searchQuery}')

        exportsearch_results = service.jobs.export(searchQuery, **kwargs)

        reader = results.ResultsReader(exportsearch_results)
        output = []

        for result in reader:
            if isinstance(result, dict):
                output.append(result)

        return json.dumps(output)

    def runSearchGetEvents(self, searchQuery, head, earliestTime='-24h', latestTime='now'):
        """
        The method is used to run a normal query at Splunk web.nnnn
        :param searchQuery: a query uses to run search
        :param head: a value specified a number of events.
        :param earliestTime: a value specified the earliest to get events.
        :param latestTime: a value specified the latest time to get events.
        Please check the article at Splunk.com to fully understand about time values.
        https://docs.splunk.com/Documentation/SplunkCloud/6.6.3/SearchReference/SearchTimeModifiers
        :return: JSON
        """

        service = self.connect()

        kwargs = self._buildSplunkSettings(earliestTime, latestTime)
        #searchQuery = self._buildSearchQuery(searchQuery, head)
        searchQuery = searchQuery + "| fields *" + f"|head {head}"
        self.helper.log_debug(f'Splunk Query Module: {searchQuery}')

        job = service.jobs.create(searchQuery, **kwargs)
        self.helper.log_debug(f"New submitted SID: {job.sid}")

        while True:
            while not job.is_done():
                pass
            stats = {"isDone": job["isDone"],
                     "doneProgress": float(job["doneProgress"]) * 100,
#                     "scanCount": int(job["scanCount"]),
                     "eventCount": int(job["eventCount"]),
                     "resultCount": int(job["resultCount"])}

            if stats["isDone"] == "1":
                break
        output = []
        for result in  results.ResultsReader(job.events()):
            if isinstance(result, dict):
                del result['_raw']
                output.append(result)

        sys.stdout.write('\n')
        job.cancel()
        return json.dumps(output)

    #@staticmethod
    def _parse_conf_xml(self, xml_content):
        """
        @xml_content: XML DOM from splunkd
        """
        xml_conf = et.fromstring(xml_content)
        result_dict = {}
        for child in xml_conf.iterfind('{http://www.w3.org/2005/Atom}content/{http://dev.splunk.com/ns/rest}dict/{http://dev.splunk.com/ns/rest}key'):
            try:
                if not child.text.startswith('\n'):
                    result_dict[child.attrib['name']] = child.text
            except Exception as e:
                pass

        for child in xml_conf.iterfind("{http://www.w3.org/2005/Atom}content/{http://dev.splunk.com/ns/rest}dict/{http://dev.splunk.com/ns/rest}key/[@name='fieldMetadataStatic']"):
            dict_key = None
            child_obj = {}
            for k in child.iter():
                if k.text.startswith('\n') and k.attrib != {} and k.attrib['name'] != 'fieldMetadataStatic':
                    dict_key = k.attrib['name']
                    child_obj[dict_key] = {}
                else:
                    if dict_key != None and k.attrib != {} and not k.text.startswith('\n'):
                        child_obj[dict_key][k.attrib['name']]  = k.text

            result_dict['fieldMetadataStatic'] = child_obj

        for child in xml_conf.iterfind("{http://www.w3.org/2005/Atom}content/{http://dev.splunk.com/ns/rest}dict/{http://dev.splunk.com/ns/rest}key/[@name='fieldMetadataResults']"):
            dict_key = None
            child_obj = {}
            for k in child.iter():
                if k.text.startswith('\n') and k.attrib != {} and k.attrib['name'] != 'fieldMetadataResults':

                    dict_key = k.attrib['name']
                    child_obj[dict_key] = {}
                else:
                    if dict_key != None and k.attrib != {}:
                        child_obj[dict_key][k.attrib['name']]  = k.text

            result_dict['fieldMetadataResults'] = child_obj
        return result_dict


    def getJobSummary(self, sid):
        try:
            output = []
            service = self.connect()
            res = service.get(f'/services/search/jobs/{sid}')
        #    self.helper.log_debug(res)
        #    self.helper.log_debug(res['body'])
            summary = self._parse_conf_xml(res['body'].read())
            #self.helper.log_debug(summary)
            self.helper.log_debug(f"got job summary for sid: {sid}")
            return summary
        except Exception as err:
            self.helper.log_error(f'Error getting job summary for sid: {sid}')
            raise


    def runNormalSearch(self, searchQuery, head, earliestTime='-24h', latestTime='now', search_mode='normal'):
        """
        The method is used to run a normal query at Splunk web.nnnn
        :param searchQuery: a query uses to run search
        :param head: a value specified a number of events.
        :param earliestTime: a value specified the earliest to get events.
        :param latestTime: a value specified the latest time to get events.
        Please check the article at Splunk.com to fully understand about time values.
        https://docs.splunk.com/Documentation/SplunkCloud/6.6.3/SearchReference/SearchTimeModifiers
        :return: JSON
        """

        service = self.connect()

        kwargs = self._buildSplunkSettings(earliestTime, latestTime, search_mode)
        #searchQuery = self._buildSearchQuery(searchQuery, head)
        searchQuery = searchQuery + "| fields *"
        self.helper.log_debug(f'Splunk Query Module: {searchQuery}')

        job = service.jobs.create(searchQuery, **kwargs)
        self.helper.log_debug(f"New submitted SID: {job.sid}")

        while True:
            while not job.is_ready():
                pass
            stats = {"isDone": job["isDone"],
                     "doneProgress": float(job["doneProgress"]) * 100,
#                     "scanCount": int(job["scanCount"]),
                     "eventCount": int(job["eventCount"]),
                     "resultCount": int(job["resultCount"])}

            if stats["isDone"] == "1":
                break

        output = []

        for result in results.ResultsReader(job.results()):
            if isinstance(result, dict):
                output.append(result)

        job.cancel()
        sys.stdout.write('\n')

        return json.dumps(output)


    def getEvents(self,sid):
        service = self.connect()
        output = []
        self.helper.log_debug(f"getting events for SID: {sid}")
        for result in  results.ResultsReader(service.job(sid).events()):
            if isinstance(result, dict):
                output.append(result)
        sys.stdout.write('\n')
        return json.dumps(output)

    def addToKVStore(self, collection, data):
        service = self.connect()
        if collection in service.kvstore:
            self.helper.log_debug(f'Found KV Store: {collection}')
            c  = service.kvstore[collection]
            result = c.data.insert(json.dumps(data))
        else:
            raise ValueError('KV Store not found')
        return result

    def updateKVStoreRecord(self, collection, id, data):
        service = self.connect()
        if collection in service.kvstore:
            c = service.kvstore[collection]
            res = c.data.update(id, json.dumps(data))
            return res
        else:
            raise ValueError('KV not found')

    def getKVStoreRecord(self, collection, id):
        service = self.connect()
        if collection in service.kvstore:
            c = service.kvstore[collection]
            res = c.data.query_by_id(id)
            return res
#            return json.dumps(res)

    def getKVStoreRecordbyKey(self, collection, key, value):
        service = self.connect()
        res = None
        if collection in service.kvstore:
            c = service.kvstore[collection]
            query = json.dumps({f"{key}": f"{value}"})
            res = c.data.query(query=query)
            return res
