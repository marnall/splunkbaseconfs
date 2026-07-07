import sys
import os
import requests

# Add bin/ to path for shared helpers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splunk_helpers import get_session_key, splunk_rest, read_conf, APP_NAME


class Savedsearch:
    def __init__(self, session_key):
        self.session_key = session_key
        self.base_endpoint = f'/servicesNS/-/{APP_NAME}/saved/searches'

    def _get_searches(self, count=0):
        """Fetch all saved searches for this app via REST."""
        endpoint = f'{self.base_endpoint}?count={count}&output_mode=json'
        result = splunk_rest('GET', endpoint, self.session_key)
        return result.get('entry', [])

    def listDisabledQueries(self):
        listQueries = []
        print("Results")
        for entry in self._get_searches():
            name = entry['name']
            is_scheduled = entry.get('content', {}).get('is_scheduled', '0')
            if str(is_scheduled) == '0':
                listQueries.append(name)
                print(name)
        return listQueries

    def listallQueries(self):
        listQueries = []
        print("Result")
        for entry in self._get_searches():
            name = entry['name']
            is_scheduled = entry.get('content', {}).get('is_scheduled', '0')
            query_status = f"{name}: {is_scheduled}"
            print(query_status)
            listQueries.append(query_status)
        return listQueries

    def queriesStatus(self):
        total = 0
        enabled = 0
        for entry in self._get_searches():
            is_scheduled = entry.get('content', {}).get('is_scheduled', '0')
            if str(is_scheduled) == '1':
                enabled += 1
            total += 1
        print("Result")
        print(f"{total}:{enabled}")

    def disableQuery(self, section):
        try:
            endpoint = f'{self.base_endpoint}/{requests.utils.quote(section, safe="")}'
            splunk_rest('POST', endpoint, self.session_key,
                        data={'disabled': '1', 'output_mode': 'json'})
            print("Result")
            print("Updated!!!")
        except requests.exceptions.HTTPError:
            print("Result")
            print("Rule doesnt exist!!!")

    def enableQuery(self, section):
        try:
            endpoint = f'{self.base_endpoint}/{requests.utils.quote(section, safe="")}'
            splunk_rest('POST', endpoint, self.session_key,
                        data={'disabled': '0', 'output_mode': 'json'})
            print("Result")
            print("Updated!!!")
        except requests.exceptions.HTTPError:
            print("Result")
            print("Rule doesnt exist!!!")


def reportQuery(rule, session_key):
    try:
        conf = read_conf(session_key, 'avert', 'config')
        report_url = conf.get('report', '').strip('"')

        settings = read_conf(session_key, 'settings', 'profile')
        profile_id = settings.get('id', '')

        if report_url and profile_id:
            requests.post(report_url % profile_id, json={"rule": rule}, timeout=(3, 10))
    except Exception:
        pass


def options():
    print("savedsearch_list.py <options>\n")
    print("options:")
    print("\t/status              -    get total:disabled rules count")
    print("\t/listall             -    list all queries with status")
    print("\t/list-disabled       -    list all disabled queries")
    print("\t/disable <rulename>  -    disable a rule with rule name")
    print("\t/enable <rulename>   -    enable a rule with rule name")
    print("\t/report <rulename>   -    report a rule with rule name")


if __name__ == '__main__':
    session_key = get_session_key()
    queries = Savedsearch(session_key)

    if len(sys.argv) == 1:
        options()
    if len(sys.argv) > 1:
        if sys.argv[1].strip() in ['?', '/h', '-h', 'h', '-help', '--help', 'help', 'options']:
            options()
        elif sys.argv[1].strip() == "/listall":
            queries.listallQueries()
        elif sys.argv[1].strip() == "/list-disabled":
            queries.listDisabledQueries()
        elif sys.argv[1].strip() == "/status":
            queries.queriesStatus()
    if len(sys.argv) > 2:
        if sys.argv[1].strip() == "/disable":
            queries.disableQuery(sys.argv[2].strip())
        elif sys.argv[1].strip() == "/enable":
            queries.enableQuery(sys.argv[2].strip())
        elif sys.argv[1].strip() == "/report":
            reportQuery(sys.argv[2].strip(), session_key)
        else:
            options()
