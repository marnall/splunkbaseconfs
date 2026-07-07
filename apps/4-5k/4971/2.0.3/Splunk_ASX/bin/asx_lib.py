import requests
import json
import splunk.mining.dcutils
import time
import re

class ASXLib:
    logger = splunk.mining.dcutils.getLogger()

    def __init__(self, service, api_url):
        self.service = service
        if api_url.endswith('/'):
            self.api_url = api_url[:-1]
        else:
            self.api_url = api_url

    def list_analytics_stories(self):
        url = self.api_url + '/stories?community=false'
        response = self.__call_security_content_api(url)
        self.logger.info("asx_lib.py - listing stories - {0}\n".format(response))
        return response['stories']


    def get_analytics_story(self, name):
        self.story = name

        url = self.api_url + '/stories/' + name  + '?community=false'
        story = self.__call_security_content_api(url)

        self.__generate_standard_macros(self.service)

        for detection in story['detections']:
            if 'macros' in detection:
                for macro in detection['macros']:
                    self.logger.info("asx_lib.py - generate macros.conf for: {0}".format(macro['name']))
                    self.__generate_macro(self.service, macro)

            self.logger.info("asx_lib.py - generate savedsearches.conf for detection: {0}".format(detection['name']))
            kwargs = self.__generate_detection(self.service, detection)

            if 'baselines' in detection:
                for baseline in detection['baselines']:
                    self.logger.info("asx_lib.py - generate savedsearches.conf for baseline: {0}".format(baseline['name']))
                    self.__generate_baseline(self.service, baseline)


        return 0


    def schedule_analytics_story(self, name, earliest_time, latest_time, cron_schedule):
        search_name = []

        for search in self.service.saved_searches:
            if 'action.escu.analytic_story' in search:
                if name in search['action.escu.analytic_story']:
                    if search['action.escu.search_type'] == "support":
                        query = search['search']
                        self.logger.info("asx_lib.py - schedule baseline - {} - {}\n".format(search['action.escu.full_search_name'], query))
                        self.logger.info("asx_lib.py - schedule baseline earliest_time latest_time - {} - {}\n".format(earliest_time, latest_time))
                        kwargs =    {"disabled": "false",
                                    "is_scheduled": True,
                                    "cron_schedule": cron_schedule,
                                    "dispatch.earliest_time": earliest_time,
                                    "dispatch.latest_time": latest_time,
                                    "search": search['search']
                                    }
                        search.update(**kwargs).refresh()
                        search_name.append(search['action.escu.full_search_name'])

                    if search['action.escu.search_type'] == "detection":
                        mappings = json.loads(search['action.escu.mappings'])
                        if "| collect" in search['search']:
                            query = search['search'].split("| collect",1)[0]
                        else:
                            query = search['search']

                        if "mitre_attack" in mappings:
                            query = query + ' | collect index=asx sourcetype=asx marker="mitre_id=' + mappings["mitre_attack"][0] + ', execution_type=scheduled"'
                        else:
                            query = query + ' | collect index=asx sourcetype=asx marker="execution_type=scheduled"'

                        self.logger.info("asx_lib.py - schedule detection - {} - {}\n".format(search['action.escu.full_search_name'], query))
                        self.logger.info("asx_lib.py - schedule detection earliest_time latest_time - {} - {}\n".format(earliest_time, latest_time))
                        kwargs =    {"disabled": "false",
                                    "is_scheduled": True,
                                    "cron_schedule": cron_schedule,
                                    "dispatch.earliest_time": earliest_time,
                                    "dispatch.latest_time": latest_time,
                                    "search": query
                                    }
                        search.update(**kwargs).refresh()
                        search_name.append(search['action.escu.full_search_name'])

        return search_name


    def run_analytics_story(self, name, earliest_time, latest_time):
        search_name = []
        execution_time = str(time.time())
        saved_searches = []

        for search in self.service.saved_searches:
            if 'action.escu.analytic_story' in search:
                if name in search['action.escu.analytic_story']:
                    if search['action.escu.search_type'] == "support":
                        saved_searches.insert(0,search)
                    else:
                        saved_searches.append(search)

        for search in saved_searches:
            if search['action.escu.search_type'] == "support":
                query = search['search']
                self.logger.info("asx_lib.py - run baseline - {} - {}\n".format(search['action.escu.full_search_name'],query))
                kwargs = {  "exec_mode": "blocking",
                            "disabled": False,
                            "dispatch.earliest_time": earliest_time,
                            "dispatch.latest_time": latest_time}
                jobs = self.service.jobs
                job = jobs.create(query, **kwargs)
                search_name.append(search['action.escu.full_search_name'])

            #Running Detections
            if search['action.escu.search_type'] == "detection":

                mappings = json.loads(search['action.escu.mappings'])
                if "| collect" in search['search']:
                    query = search['search'].split("| collect",1)[0]
                else:
                    query = search['search']

                if "mitre_attack" in mappings:
                    query = query + ' | collect index=asx sourcetype=asx marker="mitre_id=' + mappings["mitre_attack"][0] + ', execution_type=adhoc, execution_time=' + execution_time + '"'
                else:
                    query = query + ' | collect index=asx sourcetype=asx marker="execution_type=adhoc, execution_time=' + execution_time + '"'

                self.logger.info("asx_lib.py - run detection - {} - {}\n".format(search['action.escu.full_search_name'], query))

                kwargs = {  "disabled": False,
                            "dispatch.earliest_time": earliest_time,
                            "dispatch.latest_time": latest_time,
                            "search": query}

                search.update(**kwargs).refresh()
                job = search.dispatch()
                search_name.append(search['action.escu.full_search_name'])

        return search_name

    def __call_security_content_api(self, url):
        resp = requests.get(url)
        if resp.status_code != 200:
            # this is only temporary, needs to be fixed in API
            #raise requests.HTTPError('Error {} by calling {}'.format(resp.status_code, url))
            return 0
        else:
            # this is only temporary, needs to be fixed in API
            return resp.json()

    def __generate_macro(self, service, macro):
        if not (macro['name'] == 'security_content_ctime' or macro['name'] == 'security_content_summariesonly'):
            service.post('properties/macros', __stanza=macro['name'])
            service.post('properties/macros/' + macro['name'], definition=macro['definition'], description=macro['description'])

    def __generate_standard_macros(self, service):
        service.post('properties/macros', __stanza="security_content_ctime(1)")
        service.post('properties/macros/security_content_ctime(1)', definition='convert timeformat="%m/%d/%Y %H:%M:%S" ctime($field$)', description='convert epoch time to string', args='field')

        service.post('properties/macros', __stanza="security_content_summariesonly")
        service.post('properties/macros/security_content_summariesonly', definition='summariesonly=true allow_old_summaries=true', description="search data models summaries only", args='field')

    def __generate_baseline(self, service, baseline):
        full_search_name = str("ESCU - " + baseline['name'])
        resp = service.saved_searches.list()

        # if there are detections with the same name, don't override
        if not any(x.name == full_search_name for x in resp):
            kwargs = {}
            kwargs.update({"action.escu": "0"})
            kwargs.update({"action.escu.enabled": "1"})
            kwargs.update({"action.escu.search_type": "support"})
            kwargs.update({"action.escu.full_search_name": full_search_name})
            kwargs.update({"description": baseline['description']})
            kwargs.update({"action.escu.creation_date": baseline['date']})
            kwargs.update({"action.escu.modification_date": baseline['date']})

            if 'analytics_story' in baseline['tags']:
                kwargs.update({"action.escu.analytic_story": json.dumps(baseline['tags']['analytics_story'])})

            correlation_rule = baseline['search']

            kwargs.update({"cron_schedule":  "*/30 * * * *" })
            kwargs.update({"dispatch.earliest_time":  "-30m" })
            kwargs.update({"dispatch.latest_time":  "now" })
            kwargs.update({"action.escu.eli5":  baseline['description']})

            if 'how_to_implement' in baseline:
                kwargs.update({"action.escu.how_to_implement":  baseline['how_to_implement']})
            else:
                kwargs.update({"action.escu.how_to_implement": "none"})

            if 'known_false_positives' in baseline:
                kwargs.update({"action.escu.known_false_positives":  baseline['known_false_positives']})
            else:
                kwargs.update({"action.escu.known_false_positives": "None"})

            kwargs.update({"disabled": "true"})
            kwargs.update({"schedule_window": "auto"})
            kwargs.update({"is_visible": "false"})

            query = baseline['search']
            query = query.encode('ascii', 'ignore').decode('ascii')

            search = full_search_name
            search = search.encode('ascii', 'ignore').decode('ascii')

            # add try except here
            savedsearch = service.saved_searches.create(search, query, **kwargs)


    def __generate_detection(self, service, detection):

        full_search_name = str("ESCU - " + detection['name'] + " - Rule")
        resp = service.saved_searches.list()

        keys = ['mitre_attack', 'kill_chain_phases', 'cis20', 'nist']
        mappings = {}
        for key in keys:
            if key == 'mitre_attack':
                if 'mitre_attack_id' in detection['tags']:
                    mappings[key] = detection['tags']['mitre_attack_id']
            else:
                if key in detection['tags']:
                    mappings[key] = detection['tags'][key]
        detection['mappings'] = mappings

        data_model = self.parse_data_models_from_search(detection['search'])
        if data_model:
            detection['data_model'] = data_model

        nes_fields = self.get_nes_fields(detection['search'])
        if len(nes_fields) > 0:
            detection['nes_fields'] = nes_fields

        # if there are detections with the same name, don't override
        if not any(x.name == full_search_name for x in resp):
            kwargs = {}
            kwargs.update({"action.escu": "0"})
            kwargs.update({"action.escu.enabled": "1"})
            kwargs.update({"description":  detection['description'] })
            kwargs.update({"action.escu.mappings":  json.dumps(detection['mappings']) })
            if 'data_model' in detection:
                kwargs.update({"action.escu.data_models":  json.dumps(detection['data_model']) })
            kwargs.update({"action.escu.eli5":  detection['description'] })
            if 'how_to_implement' in detection:
                kwargs.update({"action.escu.how_to_implement":  detection['how_to_implement'] })
            else:
                kwargs.update({"action.escu.how_to_implement": "none"})
            if 'known_false_positives' in detection:
                kwargs.update({"action.escu.known_false_positives":  detection['known_false_positives'] })
            else:
                kwargs.update({"action.escu.known_false_positives": "None"})
            kwargs.update({"action.escu.creation_date":  detection['date'] })
            kwargs.update({"action.escu.modification_date":  detection['date'] })
            kwargs.update({"action.escu.confidence":  "high" })
            kwargs.update({"action.escu.full_search_name": full_search_name })
            kwargs.update({"action.escu.search_type": "detection"})
            kwargs.update({"action.escu.providing_technologies":  "[]" })

            if 'analytics_story' in detection['tags']:
                kwargs.update({"action.escu.analytic_story":  json.dumps(detection['tags']['analytics_story']) })

            kwargs.update({"cron_schedule":  "*/30 * * * *" })
            kwargs.update({"dispatch.earliest_time":  "-30m" })
            kwargs.update({"dispatch.latest_time":  "now" })
            kwargs.update({"action.correlationsearch": "1"})
            kwargs.update({"action.correlationsearch.enabled": "1"})
            kwargs.update({"action.correlationsearch.label":  full_search_name })
            kwargs.update({"schedule_window": "auto"})
            kwargs.update({"action.notable": "1"})
            if 'nes_fields' in detection:
                kwargs.update({"action.notable.param.nes_fields": detection['nes_fields'] })

            kwargs.update({"action.notable.param.rule_description": detection['description'] })
            kwargs.update({"action.notable.param.rule_title": full_search_name })
            kwargs.update({"action.notable.param.security_domain": detection['tags']['security_domain'] })
            kwargs.update({"action.notable.param.severity": "high" })
            kwargs.update({"alert.track": "1"})
            kwargs.update({"action.escu.earliest_time_offset": "3600"})
            kwargs.update({"action.escu.latest_time_offset": "86400"})
            kwargs.update({"is_scheduled": "1"})
            kwargs.update({"alert_type": "number of events"})
            kwargs.update({"alert_comparator": "greater than"})
            kwargs.update({"alert_threshold": "0"})
            #kwargs.update({"realtime_schedule": "0"})
            kwargs.update({"disabled": "true"})
            kwargs.update({"is_visible": "false"})

            query = detection['search']
            query = query.encode('ascii', 'ignore').decode('ascii')

            search = full_search_name
            search = search.encode('ascii', 'ignore').decode('ascii')

            try:
                savedsearch = service.saved_searches.create(search, query, **kwargs)
            except Exception as e:
                self.logger.error("Failed to store detection " + detection['name'] + " with error: " + str(e))



    def get_nes_fields(self, search):
        nes_fields_matches = []
        match_obj = ['user', 'dest', 'src']
        for field in match_obj:
            if (search.find(field + ' ') != -1):
                nes_fields_matches.append(field)

        return nes_fields_matches


    def parse_data_models_from_search(self, search):
        match = re.search(r'from\sdatamodel\s?=\s?([^\s.]*)', search)
        if match is not None:
            return match.group(1)
        return False
