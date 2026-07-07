
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
import json
import pyodbc

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# === CONFIGURATION ===

urllib3.disable_warnings()

port = 8089
username = ""
password = ""
host = ""
config_dict = {}
index_winevent = ""
user_info = ""
searchquery = ""
remedyapiurl = ""
remedyuser = ""
remedypassword = ""
virustotalapikey = ""
virustotalurl = ""
DB_DRIVER = ""
SQL_SERVER = ""
SQL_DB = ""
SQL_USER = ""
SQL_PASSWORD = ""
TABLE_NAME = ""
ml_enabled = False
db_enabled = False
dt = datetime.today().strftime('%Y-%m-%d')

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
        global username,password,config_dict,host,port,index_winevent,user_info,datafilepath,searchquery,remedyapiurl,ml_enabled,db_enabled
        global remedyuser,remedypassword,virustotalapikey,virustotalurl,SQL_SERVER,SQL_DB,SQL_PASSWORD,SQL_USER,DB_DRIVER,TABLE_NAME
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
        searchquery = config.get('splunk', 'searchquery')     
        remedyapiurl = config.get('splunk', 'remedyapiurl')   
        remedyuser = config.get('splunk', 'remedyuser')   
        remedypassword = config.get('splunk', 'remedypassword')   
        virustotalapikey = config.get('splunk', 'virustotalapikey')   
        virustotalurl = config.get('splunk', 'virustotalurl')   
        ml_enabled = config.get('splunk', 'mlenabled')   
        # DB
        SQL_USER = config.get('splunk', 'sqluser')   
        SQL_PASSWORD = config.get('splunk', 'sqlpassword')   
        SQL_DB = config.get('splunk', 'sqldb')   
        SQL_SERVER = config.get('splunk', 'sqlserver')   
        DB_DRIVER = config.get('splunk', 'dbdriver') 
        TABLE_NAME = config.get('splunk', 'tablename') 
        db_enabled = config.get('splunk', 'dbenabled')   
    except Exception as e:
        logging.error('Exception occurred - Configuration ' + str(e), exc_info=True)
        exit()


def db_connet():
    try:
        con_str = (
            f"DRIVER={DB_DRIVER};"
            f"SERVER={SQL_SERVER};DATABASE={SQL_DB};UID={SQL_USER};PWD={SQL_PASSWORD};"
        )
        return pyodbc.connect(con_str)
    except Exception as e:
        logging.error("Exception occurred - db connect", exc_info=True)


def DBProcess(con,event):
    try:
        cursor = con.cursor()
        cursor.execute(f"""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{TABLE_NAME}' AND xtype='U')
        CREATE TABLE {TABLE_NAME} (
            ip VARCHAR(100),
            reputation varchar(200),
            malicious INT,
            suspicious INT,
            predicted_label INT NULL,
            prediction_score FLOAT NULL,
            date_enriched DATETIME DEFAULT GETDATE()
        )
        """)


        cursor.execute(f"""
                MERGE {TABLE_NAME} AS target
                USING (SELECT ? AS ip) AS source
                ON target.ip = source.ip
                WHEN MATCHED THEN
                    UPDATE SET malicious=?, suspicious=?, date_enriched=GETDATE()
                WHEN NOT MATCHED THEN
                    INSERT (ip, malicious, suspicious)
                    VALUES (?, ?, ?);
            """, event.get('src_ip'), event.get('malicious'), event.get('suspicious'))

        con.commit()
        cursor.close()
    except Exception as e:
        logging.error("Exception occurred - db process", exc_info=True)

def fetch_data_for_ml(conn):
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT ip, malicious, suspicious FROM {TABLE_NAME} WHERE malicious >= 0")
        rows = cursor.fetchall()
        cursor.close()
        return rows
    except Exception as e:
        logging.error("Exception occurred - fetch ml data", exc_info=True)

def train_and_predict(data_rows,con):
    try:
        X = []
        y = []
        ips = []

        for ip, malicious, suspicious in data_rows:
            X.append([malicious, suspicious])
            y.append(1 if malicious > 0 else 0)
            ips.append(ip)

        X = np.array(X)
        y = np.array(y)

        if len(set(y)) < 2:
            logging.info("Not enough data variation for training.", exc_info=True)
            return

        X_train, X_test, y_train, y_test, ip_train, ip_test = train_test_split(
        X, y, ips, test_size=0.2, random_state=42
        )

        model = RandomForestClassifier(n_estimators=100)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)

        # Update DB with predictions
        cursor = con.cursor()
        for ip, label, prob in zip(ip_test, y_pred, y_prob):
            score = round(float(prob[1]), 4)
            try:
                cursor.execute(f"""
                    UPDATE {TABLE_NAME}
                    SET predicted_label = ?, prediction_score = ?
                    WHERE ip = ?;
                """, int(label), score, ip)
            except Exception as e:
                print(f"Failed to update prediction for {ip}: {e}")

        con.commit()
        cursor.close()
    except Exception as e:
        logging.error("Exception occurred - predict", exc_info=True)


# === API FUNCTIONS ===

REMEDY_API_URL = remedyapiurl
REMEDY_AUTH = (remedyuser, remedypassword)

VIRUSTOTAL_API_KEY = virustotalapikey
VIRUSTOTAL_URL = virustotalurl #"https://www.virustotal.com/api/v3/ip_addresses/{}"

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
        # query = """search index=notable earliest=-d
        #         | table _time, rule_name, src, dest, src_ip, dest_ip, user, urgency, severity, status, event_id"""
        query = f"search {searchquery} "
        
        search_id = splunk_search(query)
        if search_id:
            time.sleep(5)
            results = getdata(search_id)  
            return results
        else:
            logging.info("Failed to process", exc_info=True)

            return None
    except Exception as e:
        logging.error("Exception occurred - data process", exc_info=True)


def enrich_event(event):
    """Use VirusTotal API to enrich based on src_ip. Use other APIs for furthor enrichments"""
    try:
        ip = event['src_ip']
        if not ip:
            event['reputation'] = 'N/A'
            return event

        headers = {"x-apikey": VIRUSTOTAL_API_KEY}
        response = requests.get(VIRUSTOTAL_URL.format(ip), headers=headers)

        if response.status_code == 200:
            data = response.json()
            stats = data['data']['attributes']['last_analysis_stats']
            event['reputation'] = data.get("data", {}).get("attributes", {}).get("reputation", "unknown")
            event['malicious'] = stats.get('malicious', 0)
            event['suspicious'] = stats.get('suspicious', 0)
        else:
            event['reputation'] = 'unavailable'
            event['malicious'] = -1
            event['suspicious'] = -1

        return event
    except Exception as e:
        logging.error("Exception occurred - enrich events", exc_info=True)


def createticket(event):
    """Send the enriched event to ticketing system. Modify based on the ticketing system deployment"""
    try:
        payload = {
            "First_Name": "Splunk",
            "Last_Name": "Automation",
            "Login_ID": "security_automation",
            "summary": f"Notable Event: {event.get('rule_name', 'No Rule Name')}",
            "description": json.dumps(event, indent=2),
            "Reported_Source": "Security System",
            "Impact": "3-Moderate/Limited",
            "Urgency": "2-High",
            "Status": "New",
            "Action": "CREATE"
        }

        headers = {'Content-Type': 'application/json'}
        response = requests.post(REMEDY_API_URL, auth=REMEDY_AUTH, headers=headers, json=payload)

        if response.status_code in (200, 201):
            logging.info("Ticket has been successfully created.", exc_info=True)           
        else:
            logging.info(f"Failed to create ticket: {response.status_code} - {response.text}", exc_info=True)            
    except Exception as e:
        logging.error("Exception occurred - create ticket", exc_info=True)



def main():
    requests.packages.urllib3.disable_warnings()

    try:
        
        # Setting up logging
        setuplogging()
        # Read configuration
        IntializeCofig()
         
        # Process the event log data
        if db_enabled:
             conn = db_connet()

        data = process()    
       
        for event in data:
            enriched_event = enrich_event(event)
            if db_enabled:
                DBProcess(conn,enriched_event)
            createticket(enriched_event)
        
        if ml_enabled: 
            ml_data = fetch_data_for_ml(conn)
            train_and_predict(ml_data,conn)
        if db_enabled:
            conn.close()

    except Exception as e:
        logging.error("Exception occurred - main", exc_info=True)


if __name__ == "__main__":
    main()
