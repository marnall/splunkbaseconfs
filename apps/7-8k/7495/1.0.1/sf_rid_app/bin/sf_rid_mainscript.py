#!/usr/bin/env python3
#
# Secure Future S.r.l.
#

         
         
import subprocess
import json
import os
import requests
import logging
import re

# logging configuration
log_file = '/opt/splunk/var/log/splunk/sf_rid.log'

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s', filename=log_file, filemode='w')
logger = logging.getLogger(__name__)

# Splunk configuration
TIKA_JAR_PATH = '/opt/splunk/etc/apps/sf_rid_app/lib/tika-app-2.9.2.jar' # insert TIKA library path
SPLUNK_HEC_URL = 'https://localhost:8088/services/collector' # insert Splunk HEC URL
SPLUNK_HEC_TOKEN = '05840b40-9805-4a83-965c-7f8fbc974ec4' # insert HEC token generated
MONITORED_DIRECTORY = '/opt/sf_riddoc'  # insert path where documents to be analized are stored 

# document analizer pattern
email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'                          # email
iban_regex = r'IT[0-9]{2}[A-Z0-9]{22}\b'                                                 # iban 
codfisc_regex = r'[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]\b'                     # codice fiscale
coddoc_regex = r'SGI-\d+(?:\.\d+)*'                                                      # documents --> customized:  SGI-1, SGI-1.1, SGI-1.1.1
phone_regex = r'\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{1,4}\)?[-.\s]?)?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'  # phone number  --> +39-06-00000000
#address_regex = r'\b\d{1,4}\s[A-Za-z\s]+\d{5}\b'                                        # address: example 1
address_regex = r'\b((Via|Piazza|Viale|Piazzale|Vicolo)\s+[A-Za-z\s]+\s+\d+)\b'          # address: example 2 (italian address)
name_regex = r'\b(?!Via\s|Viale\s|Piazza\s|Piazzale\s|Vicolo\s)[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b'  # Name or Entity


def extract_content(file_path):
    logger.debug(f"Extracting content from {file_path}")
    cmd = ['java', '-jar', TIKA_JAR_PATH, '--text', file_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0:
        logger.debug(f"Extraction successful for {file_path}")
        return result.stdout.decode('utf-8')
    else:
        logger.error(f"Error processing file {file_path}: {result.stderr.decode('utf-8')}")
        raise Exception(f"Error processing file {file_path}: {result.stderr.decode('utf-8')}")

def extract_emails(content):
    return re.findall(email_regex, content)                                    

def extract_iban(content):
    return re.findall(iban_regex, content)
    
def extract_codfisc(content):
    return re.findall(codfisc_regex, content)

def extract_coddoc(content):
    return re.findall(coddoc_regex, content)

def extract_name(content):
    return re.findall(name_regex, content)

def extract_phone(content):
    return re.findall(phone_regex, content)

def extract_address(content):
    return re.findall(address_regex, content)


def send_to_splunk(content, file_path):
    if content.strip():  # chack if content is null
        logger.debug(f"Sending content of {file_path} to Splunk")
        headers = {'Authorization': f'Splunk {SPLUNK_HEC_TOKEN}'}
        emails = extract_emails(content)
        iban = extract_iban(content)
        codfisc = extract_codfisc(content)
        coddoc = extract_coddoc(content)
        name = extract_name(content)
        phone = extract_phone(content)
        address = extract_address(content)

        event = {
            "index": "sf_rid",
            "sourcetype": "sf_rid",
            "event": {
                "email_list": emails,
                "iban_list": iban, 
                "codfisc_list": codfisc,
                "coddoc_list": coddoc,
                "name_list": name,
                "phone_list": phone,
                "address_list": address
                },
            "source": file_path
        }

        logger.debug(f"Event data: {json.dumps(event)}")  # event data logging
        response = requests.post(SPLUNK_HEC_URL, headers=headers, data=json.dumps(event), verify=False)
        logger.debug(f"Splunk HEC response status code: {response.status_code}")
        logger.debug(f"Splunk HEC response text: {response.text}")
        if response.status_code == 200:
            logger.debug(f"Successfully sent data to Splunk for {file_path}")
        else:
            logger.error(f"Failed to send data to Splunk: {response.text}")
            raise Exception(f"Failed to send data to Splunk: {response.text}")
    else:
        logger.debug(f"File {file_path} is empty or contains only whitespace; skipping")

def main():
    logger.debug(f"Monitoring directory {MONITORED_DIRECTORY}")
    for root, dirs, files in os.walk(MONITORED_DIRECTORY):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if os.path.isfile(file_path):
                try:
                    logger.debug(f"Processing file {file_path}")
                    content = extract_content(file_path)
                    send_to_splunk(content, file_path)
                except Exception as e:
                    logger.error(f"Failed to process file {file_path}: {e}")
                finally:
                    logger.debug(f"Finished processing file {file_path}")

if __name__ == '__main__':
    main()
