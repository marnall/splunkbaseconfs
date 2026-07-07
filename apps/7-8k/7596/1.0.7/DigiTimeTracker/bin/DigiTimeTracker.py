import requests
from requests.auth import HTTPBasicAuth
import configparser
import logging
import logging.handlers
import time
from datetime import datetime
import csv
import os
import urllib3

urllib3.disable_warnings()

port = 8089
username = ""
password = ""
host = ""
config_dict = {}
index_winevent = ""
user_info = ""
dt = datetime.today().strftime('%Y-%m-%d')
ldapcon = ""
ldaprequired = ""


def setuplogging():
    scriptpath = os.path.dirname(os.path.abspath(__file__))
    dir = os.path.dirname(scriptpath)
    logpath = dir + '\data\log\logfile.log'

    # if not os.path.exists(logpath):
    #     with open(logpath,'w'):
    #         pass
    # os.chmod(os.path.join(scriptpath, 'data/log'), 0o777)
    logging.basicConfig(level=logging.DEBUG, filename=logpath, filemode="a",
                        format="%(asctime)s %(levelname)s %(message)s")
    logging.info("logging configured", exc_info=True)


def IntializeCofig():
    try:
        global username,password,config_dict,host,port,index_winevent,user_info,datafilepath,ldapcon,ldaprequired
        config = configparser.ConfigParser()
        scriptpath = os.path.dirname(os.path.abspath(__file__))
        dirpath = os.path.dirname(scriptpath)
        confpath = os.path.join(dirpath, 'data/config', 'Connection.conf')
        datafilepath = os.path.join(dirpath, 'data/Files')
        config.read_file(open(confpath))
        username = config.get('splunk', 'username')
        password = config.get('splunk', 'password')
        host = config.get('splunk', 'host')
        port = config.get('splunk', 'port')
        index_winevent = config.get('splunk', 'index_winevent')
        ldapcon = config.get('splunk', 'ldapconnection_name')
        ldaprequired = config.get('splunk', 'ldaprequired')
        user_info = config.get('splunk', 'userinfolookup')
    except Exception as e:
        logging.error('Exception occurred - Configuration ' + str(e), exc_info=True)
        exit()


def splunk_search(query):
    try:
        url = f"https://{host}:{port}/services/search/jobs"

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        payload = {
            'search': query,
            'output_mode': 'json'
        }

        response = requests.post(
            url,
            data=payload,
            headers=headers,
            auth=HTTPBasicAuth(username, password),
            verify=True)

        if response.status_code == 201:
            searchid = response.json()["sid"]
            return searchid
        else:
            logging.error("Error occurred " + response.text, exc_info=True)
            return None
    except Exception as e:
        logging.error("Exception occurred - splunk search", exc_info=True)


def getdata(sid):
    try:
        url = f"https://{host}:{port}/services/search/v2/jobs/{sid}/results"
        params = {'output_mode': 'json'}

        while True:
            response = requests.get(url, params=params, auth=HTTPBasicAuth(username, password), verify=True)
            if response.status_code == 200 and response.json()['results']:
                return response.json()['results']
            else:
                logging.error("Error occurred " + response.text, exc_info=True)
                return []
    except Exception as e:
        logging.error("Exception occurred - get search id", exc_info=True)


def process():
    try:
        ldap_fullname = "",
        ldap_groups = "",
        ldap_email = "",
        ldap_title = "",
        ldap_department = ""
        # query = """search index=wineventlog EventCode=4624 OR EventCode=4634  earliest=-d
        #         | eval first_name="Test"
        #         | eval last_name = "T"
        #         | eval emailid="ss@splunk.com"|table _time, Account_Name, EventCode, first_name, last_name, emailid"""
        if ldaprequired.upper() == "FALSE":
            query = f"search index={index_winevent} EventCode=4624 OR EventCode=4634 earliest=-d | mvexpand  Account_Name| table _time, Account_Name, EventCode "
        else:
            query = f"""search index={index_winevent} EventCode=4624 OR EventCode=4634 earliest=-d | mvexpand  Account_Name 
                    | fields _time, Account_Name, EventCode
                    | [| ldapsearch domain={ldapcon} search="(&(objectclass=user)(!(objectClass=computer)(sAMAccountName=$Account_Name$))"
                    | fields sAMAccountName, cn, mail, memberOf, title, department]
                    | eval ldap_fullname=coalesce(cn, "No Value")
                    | eval ldap_email=coalesce(mail, "No Value")
                    | eval ldap_groups=coalesce(memberOf, "No Value")
                    | eval ldap_title=coalesce(title, "No Value")
                    | eval ldap_department=coalesce(department, "No Value")| table _time, Account_Name, EventCode, 
                    ldap_fullname, ldap_email, ldap_groups, ldap_title, ldap_department"""

        search_id = splunk_search(query)
        if search_id:
            time.sleep(5)
            results = getdata(search_id)
            attendance = {}

            for record in results:
                Account_Name = str(record["Account_Name"])
                # print(user)
                if ldaprequired.upper() == 'TRUE':
                    ldap_fullname = str(record["ldap_fullname"])
                    ldap_groups = str(record["ldap_groups"])
                    ldap_email = str(record["ldap_email"])
                    ldap_title = str(record["ldap_title"])
                    ldap_department = str(record["ldap_department"])
                event_code = str(record["EventCode"])
                event_time = datetime.strptime(record["_time"], '%Y-%m-%dT%H:%M:%S.%f%z')

                if event_code == "4624":
                    if Account_Name not in attendance:
                        attendance[Account_Name] = {"logon_time": event_time, "logoff_time": None,
                                                    'ldap_fullname': ldap_fullname,
                                                    'ldap_groups': ldap_groups,
                                                    'ldap_email': ldap_email,
                                                    'ldap_title': ldap_title,
                                                    'ldap_department': ldap_department
                                                    }
                    else:
                        attendance[Account_Name]['logon_time'] = min(attendance[Account_Name]['logon_time'], event_time)

                elif event_code == "4634":
                    if Account_Name in attendance:
                        attendance[Account_Name]['logoff_time'] = event_time

            for Account_Name, items in attendance.items():
                if items['logon_time'] and items['logoff_time']:
                    duration = items['logoff_time'] - items['logon_time']
                    items['Totalduration'] = duration.total_seconds()
                else:
                    items['Totalduration'] = None

            return attendance
        else:
            logging.info("Failed to process", exc_info=True)

            return None
    except Exception as e:
        logging.error("Exception occurred - data process", exc_info=True)


def writedata(attendance_data):
    try:
        with open(datafilepath + '/attendance_report_' + str(dt) + '.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            if ldaprequired.upper() == 'TRUE':
                writer.writerow(['Account_Name', 'FirstLogon', 'LastLogoff', 'Duration','ldap_fullname','ldap_email','ldap_groups','ldap_title','ldap_department'])
            else:
                writer.writerow(['Account_Name', 'FirstLogon', 'LastLogoff', 'Duration'])
            for Account_Name, row in attendance_data.items():
                print(Account_Name)
                duration = row.get('Totalduration', 'NA')
                Account_Name = str(Account_Name)
                logon = row.get('logon_time', 'NA')
                logoff = row.get('logoff_time', 'NA')
                # first_name = row['first_name']
                # last_name = row['last_name']
                # emailid = row['email']
                if ldaprequired.upper() == 'TRUE':
                    ldap_fullname = row.get("ldap_fullname", 'NA')
                    ldap_groups = row.get("ldap_groups", 'NA')
                    ldap_email = row.get("ldap_email", 'NA')
                    ldap_title = row.get("ldap_title", 'NA')
                    ldap_department = row.get("ldap_department", 'NA')
                    writer.writerow([Account_Name, logon, logoff, duration,ldap_fullname, ldap_email, ldap_groups, ldap_title, ldap_department])
                else:
                    writer.writerow([Account_Name, logon, logoff, duration])
    except Exception as e:
        logging.error("Exception occurred - writedata", exc_info=True)
        print(e)


def createlookup():
    lookupname = "DigiTimeReport.csv"
    # url = f"https://{host}:{port}/servicesNS/nobody/search/data/lookup-table-files/{lookupname}"
    url = f"https://{host}:{port}/services/receivers/simple?index=main&sourcetype=csv"
    headers = {"Content-Type":"text/plain"}
    # fileinfo = {'eai:data':open(datafilepath + '/attendance_report.csv', 'rb')}
    csvpath = datafilepath + '/attendance_report.csv'
    with open(csvpath,"r") as file:
        csvdata = file.read()
        # fileinfo = {"file":(lookupname, file, "text/csv")}

    # data = {'name': 'DigiTimeReport', 'output_mode': 'json'}
        response = requests.post(url, headers=headers, data=csvdata, auth=HTTPBasicAuth(username, password), verify=True)
    if response.status_code == 200:
        logging.info("Lookup created successfully", exc_info=True)
    else:
        logging.error("Error occurred " + response.text, exc_info=True)


def lock_process():
    try:
        query = f'''search index={index_winevent} EventCode=4800 OR EventCode=4801 earliest=-d | mvexpand  Account_Name
                | eval EventType=case(EventCode=="4800", "Locked", EventCode=="4801", "Unlocked"
                | table _time, Account_Name, EventCode, EventType | sort -_time
                '''

        searchid = splunk_search(query)
        if searchid:
            time.sleep(5)
            results = getdata(searchid)
            with open(datafilepath + '/windows_Account_Lock_' + str(dt) + '.csv', "w", newline='') as file:
                writer = csv.DictWriter(file, fieldnames=['_time', 'Account_Name', 'EventCode', 'EventType'])
                writer.writeheader()
                for result in results:
                    writer.writerow(result)
    except Exception as e:
        logging.error("Exception occurred - lock data process", exc_info=True)


if __name__ == "__main__":
    # Setting up logging
    setuplogging()
    # Read configuration
    IntializeCofig()
    # Process the event log data
    data = process()
    if data is not None:
        writedata(data)
        logging.info("Report created successfully", exc_info=True)
        # createlookup()
    else:
        logging.info("No Data to process", exc_info=True)

    # Process the account lock data
    lock_process()
