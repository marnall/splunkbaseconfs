import os, sys,json, re
import requests
import logging
import logging.handlers
import base64
from collections import OrderedDict
import datetime
from datetime import datetime
from splunk.clilib import cli_common as cli
import certifi



def setup_logger(level):
    logger = logging.getLogger('sirp')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/sirp.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.INFO)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        logger.info(payload)
        config=payload['configuration']
        config=payload.get('configuration')
    try:
        cfg = cli.getConfStanza('macros','configuration')
        # print cfg.get('parameter')
        server_url=cfg.get('serverurl')
        apikey=cfg.get('apikey')
        certloc=cfg.get('certloc')
    except:
        print("Missing Configuration. Enter the Correct Configuration", file=sys.stderr)
        exit()
    artifacts=config.get('artifact')
    additionalinput=config.get('fields')
    subject=config.get('subject')
    priority=config.get('priority')
    severity=config.get('severity')
    event_result=payload.get('result')
    temp_container={}
    
    if additionalinput!=None:
        
        try:
            additionalinput=json.loads(additionalinput.replace("\n",",").replace("\r","").replace("\t",""))

            for k,v in additionalinput.items():
                v= str(v).strip()
                k= k.strip()
                if (k.lower()=="ingestion unique id"):
                    temp_container['iti_ingest_input']=v
                if (k.lower()=="subject" ):
                    temp_container['iti_subject']=v
                if (k.lower()=="description") :
                    temp_container['iti_description']=v
                if (k.lower() =="priority"):
                    if (v.lower() =="high" or v.lower()=="medium" or v.lower()=="low" ):
                        temp_container['iti_priority']=v.lower().capitalize()
                    else:
                        print("Value of Priority is Incorrect. It should b either 'Low', 'Medium' or 'Low'", file=sys.stderr)
                        exit()
                if (k.lower()=="category"):
                    temp_container['iti_category_id']=v
                if (k.lower()=="disposition"):
                    temp_container['iti_disposition_id']=5
                if (k.lower()=="summary"):
                    temp_container['iti_analysis_summary']=v
                if (k.lower()=="follow up date"):
                    try:
                        datetime.strptime(str(v), '%Y-%m-%d %H:%M:%S')
                        temp_container['iti_followup_date']=v
                    except Exception as e:
                        try:
                            v=datetime.fromtimestamp(int(v)).strftime('%Y-%m-%d %H:%M:%S')
                            temp_container['iti_followup_date']=v
                        except Exception as e:
                            print(e,"Follow Up Date should be in 2022-11-12 09:22:22 format or in Unix format", file=sys.stderr)
                            exit()

                    
                if (k.lower()=="attack duration"):
                    if v.isdigit()==True:
                        temp_container['iti_attack_duration']=v
                    else:
                        print("Attack Duration should be Numeric.", file=sys.stderr)
                        exit()
                if (k.lower()=="severity"):
                    if (v.lower()=="critical" or v.lower()=="high" or v.lower()=="medium" or v.lower()=="low"):
                        temp_container['iti_attack_severity']=v.lower().capitalize()
                    else:
                        print("Value of Severity Field is wrong. Is should be either Critical, High, Medium or Low", file=sys.stderr)
                        exit()                       

                if (k.lower()=="estimated recovery clock" ) :
                    if v.isdigit()==True:
                        temp_container['iti_estimated_recovery_clock']=v
                    else:
                        print("Estimated Recovery Clock should be Numeric.", file=sys.stderr)
                        exit()
                if (k.lower()=="estimated recovery hours"):
                    if v.isdigit()==True:
                        temp_container['iti_estimated_recovery_hours']=v
                    else:
                        print("Estimated Recovery Hours should be Numeric.", file=sys.stderr)
                        exit()
                    
                if (k.lower()=="number of users affected"):
                    if v.isdigit()==True:
                        temp_container['iti_approx_users_affeacted']=v
                    else:
                        print("Number of Users Affected should be Numeric.", file=sys.stderr)
                        exit()
                    
                if (k.lower()=="number of hosts affected"):
                    if v.isdigit()==True:
                        temp_container['iti_approx_host_affeacted']=v
                    else:
                        print("Number of Hosts Affected should be Numeric.", file=sys.stderr)
                        exit()
                    

                if (k.lower()=="attack date") :
                    try:
                        datetime.strptime(str(v), '%Y-%m-%d %H:%M:%S')
                        temp_container['iti_attack_date']=v
                    except Exception as e:

                        try:
                            v=datetime.fromtimestamp(int(v)).strftime('%Y-%m-%d %H:%M:%S')
                            temp_container['iti_attack_date']=v
                        except Exception as e:
                            print(e,"Attack date should be in 2022-11-12 09:22:22 format or in Unix format", file=sys.stderr)
                            exit()                        
            
                if (k.lower()=="due date"):
                    
                    try:
                        datetime.strptime(str(v), '%Y-%m-%d %H:%M:%S')
                        temp_container['iti_due_date']=v
                    except Exception as e:
                        try:
                            v=datetime.fromtimestamp(int(v)).strftime('%Y-%m-%d %H:%M:%S')
                            temp_container['iti_due_date']=v
                        except Exception as e:
                            print(e,"Due Date should be in 2022-11-12 09:22:22 format or in Unix format", file=sys.stderr)
                            exit()
                if (k.lower()=="detection Date") :
                    try:
                        datetime.strptime(str(v), '%Y-%m-%d %H:%M:%S')
                        temp_container['iti_detect_date']=v
                    except Exception as e:
                        try:
                            v=datetime.fromtimestamp(int(v)).strftime('%Y-%m-%d %H:%M:%S')
                            temp_container['iti_detect_date']=v
                        except Exception as e:
                            print(e,"Detection Date should be in 2022-11-12 09:22:22 format or in Unix format", file=sys.stderr)
                            exit()
                if (k.lower()=="escalation date") :
                    try:
                        datetime.strptime(str(v), '%Y-%m-%d %H:%M:%S')
                        temp_container['iti_escalation_date']=v
                    except Exception as e:
                        try:
                            v=datetime.fromtimestamp(int(v)).strftime('%Y-%m-%d %H:%M:%S')
                            temp_container['iti_escalation_date']=v
                        except Exception as e:
                            print(e,"Escalation Date should be in e.g 2022-11-12 09:22:22 format or in Unix format", file=sys.stderr)
                            exit()
                
                if (k.lower()=="evidence description"):
                    temp_container['iti_evidence_description']=v
                if (k.lower()=="damage details"):
                    temp_container['iti_system_damage_detail']=v
                if (k.lower()=="data compromised detail") :
                    temp_container['iti_data_compromised_detail']=v
                if (k.lower()=="remediation details"):
                    temp_container['iti_suggestions_recovery']=v
                if (k.lower()=="implemented remediation"):
                    temp_container['iti_closed_remediation']=v
                if (k.lower()=="root cause analysis"):
                    temp_container['iti_rca']=v

                if (k.lower()=="data compromised"):
                    if (v.lower()=="yes" or v.lower()=="no"):
                        temp_container['iti_data_compromised']=v.lower().capitalize() 
                    else:
                        print("Incorrect value for Data Compromised Field. It should be either 'Yes' or 'No'", file=sys.stderr)
                        exit()
                if (k.lower()=="affected assets"):
                    temp_container["iti_compromised_asset"]=v
        except Exception as e:
            print("Enter Payload in Correct Json Format. ",e, file=sys.stderr)
            exit()

    if artifacts!=None:
        try:
            artifacts=json.loads(artifacts.replace("\n",",").replace("\r","").replace("\t",""))

            newlist=[]
            for k,v in artifacts.items():
                v= str(v).strip()
                k= k.strip()
                newlist.append(k)
                result=k.replace(" ","_")
                temp_container['Artifact_'+result]=v
            temp_container["iti_artifacts"]=newlist
        except Exception as e:
            print("Enter Artifacts in Correct Json Format. ",e, file=sys.stderr)
            exit()

    if 'iti_subject' not in temp_container:
        if subject == None:
            temp_container['iti_subject']=""
        else:
            temp_container['iti_subject']=subject.replace("\n"," ").replace("\r","").replace("\t","")
    if 'iti_attack_severity' not in temp_container:
        if severity == None:
            temp_container['iti_attack_severity']=""
        else:
            temp_container['iti_attack_severity']=severity
    if 'iti_priority' not in temp_container:
        if priority==None:
            temp_container['iti_priority']=""
        else:
            temp_container['iti_priority']=priority
    temp_container['iti_disposition_id']=5
    temp_container['iti_ticket_status']="Open"


    payload['result']['_time']=datetime.fromtimestamp(int(payload['result']['_time'])).strftime('%Y-%m-%d %H:%M:%S')
    payload['result']['_indextime']=datetime.fromtimestamp(int(payload['result']['_indextime'])).strftime('%Y-%m-%d %H:%M:%S')
    del payload['configuration']
    temp_container["iti_payload_full"]=json.dumps(payload)
    server_url=server_url
    apikey=apikey
    headers = {
    'x-api-key': apikey,
    'cache-control': "no-cache",
    }
    try:

        url=server_url+"/api/v1/incident-management/quick-create"
        #print("Okaaaaaaaaaaaaaaaaayyyyyyyy!!!!!!!!!!!!!!!!!!!!!!!1", file=sys.stderr)
        if certloc:
            try:
                response=requests.post(url=url,headers=headers,json=temp_container, timeout=60,cert=certloc)
            except requests.exceptions.SSLError:
                print("Enter Correct Path to the SSL Certificate", file=sys.stderr)
                
        else:
            response=requests.post(url=url,headers=headers,json=temp_container, timeout=60,verify=False)
            #print(response.text,"+++++++++++++++++++++++++++++++", file=sys.stderr)
            rescode=response
            response=response.text
            resp=json.loads(response)
            if rescode.status_code==200:
                print(json.dumps(resp["data"]).replace("{","").replace("}","").replace('"',''), file=sys.stderr)
            elif rescode.status_code >200:
                print("Incident Cannot be Created. Error: ",json.dumps(resp["data"]).replace("{","").replace("}","").replace('"',''), file=sys.stderr)
    except Exception as e:
        print("Invalid Server URL. ",e, file=sys.stderr)


if __name__ == "__main__":
    main()

