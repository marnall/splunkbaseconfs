import requests
from requests_ntlm import HttpNtlmAuth
import urllib.parse
from datetime import datetime, timedelta
import time
import pathlib
import config
from json_converter import csv_to_json, xlsx_to_json, xml_to_json, json_to_json
from datetime import datetime
import jwt
import base64
import subprocess
import os
from sqs_utils import json_file_to_sqs
from s3_utils import upload_to_s3

token=''

def get_client_assertion():
    cert_path = f'{pathlib.Path(__file__).parent.absolute()}/../cert'
    sp=subprocess.run(f'openssl x509 -in {cert_path}/cert.crt -fingerprint -sha1 --noout', shell=True, stdout=subprocess.PIPE)
    cert_thumbprint_hex=sp.stdout.decode().strip().split('=')[1].replace(':', '')
    cert_thumbprint_b64 = base64.b64encode(bytes.fromhex(cert_thumbprint_hex)).decode()
    headers = {
        "alg": "RS256",
        "typ": "JWT",
        "x5t": cert_thumbprint_b64
    }
    payload = {
        "aud": f"https://login.microsoftonline.com/{config.TENANT_ID}/oauth2/v2.0/token",
        "exp": (datetime.now() + timedelta(hours=3)).timestamp(),
        "iss": config.CLIENT_ID,
        "jti": "random_unique_identifier",
        "nbf": datetime.now().timestamp(),
        "sub": config.CLIENT_ID
    }

    with open(f'{cert_path}/cert.key', 'r') as key_file:
        private_key=key_file.read()

    encoded = jwt.encode(payload, private_key, headers=headers, algorithm="RS256")
    return encoded


def get_token():
    global token
    if not token:
        url = f"https://login.microsoftonline.com/{config.TENANT_ID}/oauth2/v2.0/token"
        payload = f'grant_type=client_credentials&client_id={config.CLIENT_ID}&scope=https%3A%2F%2Fcyberdashcryptometrics.sharepoint.com%2F.default&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth%3Aclient-assertion-type%3Ajwt-bearer&client_assertion={get_client_assertion()}'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = requests.request("GET", url, headers=headers, data=payload)
        token = response.json().get('access_token')
        print(f'Token acquired')
    return token


def get_response(url):
    headers = {
        'Accept': 'application/json;odata=verbose',
    }
    if config.ONPREM:
        resp = requests.get(
            url,
            headers=headers,
            auth=HttpNtlmAuth(config.USER, config.PASS),
        )
    else:
        headers['Authorization'] = f'Bearer {get_token()}'
        resp = requests.get(
            url,
            headers=headers,
        )
    return resp


def get_list(folder, f_type):
    try:
        resp = get_response(f"{config.SERVER}/_api/web/GetFolderByServerRelativeUrl('/{urllib.parse.quote(folder)}')/{f_type}")
        data = resp.json()
        # print(data)
    except Exception as ex:
        # print(ex)
        print('Sharepoint server connection failed, exiting...')
        exit(0)
    return [{
       'name': item.get('Name'),
       'modified': item.get('TimeLastModified'),
       'path': item.get('ServerRelativeUrl')
    } for item in data.get('d').get('results')]



def download_file(fl_list):
    global last_synched
    for fl in fl_list:
        print(fl)
        try:
            fl_name, fl_ext = fl["name"].split('.')
            if fl_ext.lower() in ('csv', 'xml', 'xlsx', 'json'):
                modified = datetime.strptime(fl["modified"], "%Y-%m-%dT%H:%M:%SZ")
                if modified > last_synched and modified.month == datetime.now().month:
                    # resp = get_response(f"{config.SERVER}/{urllib.parse.quote(fl['path'])}")
                    resp = get_response(f"{config.SERVER}/_api/web/GetFileByServerRelativeUrl('/{urllib.parse.quote(fl['path'])}')/OpenBinaryStream()")
                    dnload_file = f'{config.DNLOAD_DIR}/{modified.strftime("%Y%m%d")}_{fl["name"]}'
                    out_file = f'{config.OUT_DIR}/{modified.strftime("%Y%m%d")}_{fl_name}.json'
                    with open(dnload_file, 'wb') as f:
                        f.write(resp.content)
                        print(f'*** {fl["name"]} downloaded as {dnload_file}')
                    if fl_ext.lower() == 'csv':
                        csv_to_json(dnload_file, out_file)
                        print(f'****** converted as {out_file}')
                    elif fl_ext.lower() == 'xml':
                        xml_to_json(dnload_file, out_file)
                        print(f'****** converted as {out_file}')
                    elif fl_ext.lower() == 'xlsx':
                        xlsx_to_json(dnload_file, out_file)
                        print(f'****** converted as {out_file}')
                    elif fl_ext.lower() == 'json':
                        json_to_json(dnload_file, out_file)
                        print(f'****** converted as {out_file}')
        except Exception as ex:
            print(ex)
            continue


def download_folder(folder):
    print('\nFolder: ' + folder + ' -------->')
    fls=get_list(folder, 'Files')
    download_file(fls)
    fols=get_list(folder, 'Folders')
    for fol in fols:
        download_folder(fol['path'])


def upload_folder(dir):
    if not config.UPLOAD_TO_SQS and not config.UPLOAD_TO_S3:
        return
    for x in os.listdir(dir):
        if x.endswith(".json"):
            try:
                print(f'Uploading {dir}/{x}')
                if config.UPLOAD_TO_SQS:
                    json_file_to_sqs(f'{dir}/{x}')
                if config.UPLOAD_TO_S3:
                    upload_to_s3(f'{dir}/{x}', x)
                time.sleep(0.5)
                os.remove(f'{dir}/{x}')
            except Exception as ex:
                print(ex)

try:
    f = open('last_synched', 'r')
    last_synched = datetime.fromisoformat(f.readline())
    print("Last synched at ", last_synched)
except Exception as ex:
    last_synched = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

download_folder(config.ROOT_DIR)
upload_folder(config.OUT_DIR)

with open('last_synched', 'w') as f:
    f.write(datetime.now().isoformat())
