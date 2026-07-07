import requests
import os
import sys

# Add bin/ to path for shared helpers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splunk_helpers import get_session_key, splunk_rest, read_conf, write_conf, APP_NAME


def getdata(session_key):
    settings = read_conf(session_key, 'settings', 'profile')
    search_settings = read_conf(session_key, 'settings', 'search')
    print(settings.get('email', ''))
    print(search_settings.get('freq', ''))


def getEmail(session_key):
    settings = read_conf(session_key, 'settings', 'profile')
    print(settings.get('email', ''))


def updateProfile(email, session_key):
    try:
        settings = read_conf(session_key, 'settings', 'profile')
        email = settings.get('email', email)
        avert_conf = read_conf(session_key, 'avert', 'config')
        profile_url = avert_conf.get('profile', '').strip('"')
        profile_id = settings.get('id', '')

        requests.post(profile_url, json={"email": email, "id": profile_id}, timeout=(3, 10))
    except Exception:
        pass


def updateFreq(cron, earliest_time, session_key):
    """Update cron schedule and earliest_time for all saved searches via REST."""
    endpoint = f'/servicesNS/-/{APP_NAME}/saved/searches?count=0&output_mode=json'
    result = splunk_rest('GET', endpoint, session_key)
    for entry in result.get('entry', []):
        name = entry['name']
        search_endpoint = f'/servicesNS/-/{APP_NAME}/saved/searches/{requests.utils.quote(name, safe="")}'
        try:
            splunk_rest('POST', search_endpoint, session_key,
                        data={'cron_schedule': cron, 'dispatch.earliest_time': earliest_time,
                              'output_mode': 'json'})
        except Exception:
            pass


def storeEmail(email, session_key):
    try:
        write_conf(session_key, 'settings', 'profile', {'email': email})
        try:
            avert_conf = read_conf(session_key, 'avert', 'config')
            register_url = avert_conf.get('register', '').strip('"')
            dat = requests.post(register_url, json={"email": email}, timeout=(3, 10))
            if dat.status_code == 200:
                info = dat.json()
                storeID(info["id"], session_key)
        except Exception:
            storeID("failed-id", session_key)
        return 1
    except Exception:
        pass


def storeSearchFreq(freq, session_key):
    try:
        write_conf(session_key, 'settings', 'search', {'freq': freq})
    except Exception:
        pass


def storeID(id_val, session_key):
    try:
        write_conf(session_key, 'settings', 'profile', {'id': id_val})
        return 1
    except Exception:
        pass


def options():
    print("settings.py <options> <value>\n")
    print("options:")
    print("\t\t\t - email <email@example.com>")
    print("\t\t\t - freq <realtime, 30mins, 1hour, 6hours, 12hours, 24hours, disable>")


freq = {
    "realtime": "",
    "30mins": "*/30 * * * *",
    "1hour": "0 * * * *",
    "6hours": "0 */6 * * *",
    "12hours": "0 */12 * * *",
    "24hours": "0 0 * * *",
}
earliest_time = {
    "realtime": "-10m",
    "30mins": "-30m",
    "1hour": "-60m",
    "6hours": "-6h",
    "12hours": "-12h",
    "24hours": "-12h",
}

if __name__ == '__main__':
    session_key = get_session_key()

    if len(sys.argv) >= 2:
        try:
            option = sys.argv[1].strip()
            print(option)
            if option == "register":
                email = sys.argv[2].strip()
                storeEmail(email, session_key)
            elif option == "update":
                search_sch = sys.argv[2].strip()
                email = sys.argv[3].strip()
                storeEmail(email, session_key)
                storeSearchFreq(search_sch, session_key)
                updateFreq(freq[search_sch], earliest_time[search_sch], session_key)
            elif option == "getemail":
                getdata(session_key)
        except Exception as er:
            print(er)
