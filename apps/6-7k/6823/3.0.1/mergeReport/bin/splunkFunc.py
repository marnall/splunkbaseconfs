import requests, json, time, xlsxwriter, csv, argparse, smtplib, ssl, os
from requests.auth import HTTPBasicAuth
from collections import OrderedDict
from datetime import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
from os import path
from pathlib import Path
from smtplib import *
requests.packages.urllib3.disable_warnings(InsecureRequestWarning) # Disable warnings (if tested using native Python)

def create_url(server,protocol='https',port=8089,user='admin',app='search'):
    url = protocol + '://' + server + ':' + str(port) + '/servicesNS/' + user + '/' + app + '/search/jobs'
    return url

def run_splunk_search(server,searchstring,user,password,protocol='https',port=8089,app='search',timeout=1200,recheck=1,getPreview=True):
    headers={
        'Accept':'application/json',
        'Content-Type':'application/x-www-form-urlencoded'
    }
    
    params={"output_mode":"json"}

    authentication = HTTPBasicAuth(user,password)
    url = create_url(server=server,protocol=protocol,port=port,user=user,app=app)
    
    if (searchstring.strip()[0:1] != '|' and searchstring.strip()[0:6] != 'search'):
        target_searchstring = 'search ' + searchstring
    else:
        target_searchstring = searchstring
    body = {
        "search": target_searchstring,
        "output_mode": "json"
    }
    returnobj = []
    result = requests.post(url,auth=authentication,verify=False,headers=headers,data=body)
    if result.status_code == 201:
        #201 created means the job is created successfully
        sid = result.json()["sid"]
        status_url = url + '/' + sid
        dispatchstate = ""
        totalcheck = int(timeout/recheck)
        for i in range(0,totalcheck):
            status = requests.get(status_url,auth=authentication,verify=False,params=params)
            dispatchstate = status.json()["entry"][0]["content"]["dispatchState"]
            #print(time.strftime("%Y %b %d %H:%M:%S") + ">Current Status for job (" + sid + "): " + dispatchstate)
            if(dispatchstate == "DONE"):
                if(getPreview == True):
                    preview_params = {
                        "output_mode" : "json",
                        "count" : 1 #max rows to be returned. 0 means all.
                    }
                    preview_url = url + '/' + sid + '/results_preview'
                    preview = requests.get(preview_url,auth=authentication,verify=False,params=preview_params)
                    returnobj = preview.json()["results"]
                else:
                    results_params= {
                        "output_mode" : "json",
                        "count" : 0 #max rows to be returned. 0 means all.
                    }
                    results_url = url + '/' + sid + '/results'
                    results = requests.get(results_url,auth=authentication,verify=False,params=results_params)
                    if result.status_code == 201:
                        returnobj = results.json()["results"]
                break
            time.sleep(recheck)
    else:
        #print(result.status_code)
        returnobj = result.json()
    return returnobj

def json_to_excel(wb, ws, data, row=0, col=0):
    if isinstance(data, list):
        row -= 1
        for value in data:
            row = json_to_excel(wb, ws, value, row+1, col)
    elif isinstance(data, dict):
        max_row = row
        start_row = row
        for key, value in data.items():
            row = start_row
            if row==0:
                cell_format = wb.add_format({'bold': True}) 
                ws.write_string(row, col, key, cell_format)
            row = json_to_excel(wb, ws, value, row+1, col)
            max_row = max(max_row, row)
            col += 1
        row = max_row
    else:
        if row!=1:
            row-=1
        ws.write_string(row, col, data)

    return row

def readCSV(csvFile):
    csvData = []
    try:
        with open(csvFile) as csvDataFile:
            csvReader = csv.reader(csvDataFile)
            try:
                for row in csvReader:
                    csvData.append(row)
                return csvData
            except csv.Error as e:
                print("Error reading " + csvFile + ". Error is " + e)
                return csvData
    except EnvironmentError:
        return csvData

def sendEmail(send_from,send_to,send_cc,send_bcc,subject,attachmentFile,emailText,smtpServer,smtpPort,smtpUsername,smtpPassword,smtpLogin,isTls):
    bcc = send_bcc
    cc = send_cc
    rcpt = cc.split(",") + bcc.split(",") + send_to.split(",")
    
    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = send_to
    msg['CC'] = send_cc
    msg['Date'] = formatdate(localtime = True)
    msg['Subject'] = subject
    msg.attach(MIMEText(emailText))

    if attachmentFile:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(attachmentFile, "rb").read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="' + os.path.basename(attachmentFile) + '"')
        msg.attach(part)

    #context = ssl.SSLContext(ssl.PROTOCOL_SSLv3)
    #SSL connection only working on Python 3+
    try:
        smtp = smtplib.SMTP(smtpServer, smtpPort)
        if isTls:
            smtp.starttls()
        if smtpLogin:
            smtp.login(smtpUsername,smtpPassword)
        smtp.sendmail(send_from, rcpt, msg.as_string())
        smtp.quit()
        return True, "OK"
    except SMTPResponseException as e:
        return False, e.smtp_error      

def makeDirectoryIfNotExists(dirname):
    path=Path(dirname)
    path.mkdir(parents=True, exist_ok=True)

