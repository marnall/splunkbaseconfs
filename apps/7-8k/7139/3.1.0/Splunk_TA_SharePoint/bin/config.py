from configparser import ConfigParser
import pathlib
import os


cfg = ConfigParser()
cfg.read(f'{pathlib.Path(__file__).parent.absolute()}/../config.ini')

SERVER = cfg['GENERAL']['SERVER']
ONPREM = cfg['GENERAL']['ONPREM'] in ('YES', 'Y', 'Yes', 'y', True, 1)
USER = cfg['GENERAL']['USER']
PASS = cfg['GENERAL']['PASS']
TENANT_ID = cfg['GENERAL']['TENANT_ID']
CLIENT_ID = cfg['GENERAL']['CLIENT_ID']

ROOT_DIR = cfg['GENERAL']['ROOT_DIR']
OUT_DIR = cfg['GENERAL']['OUT_DIR']
DNLOAD_DIR = cfg['GENERAL']['DNLOAD_DIR']
TIMESTAMP_FIELD = cfg['GENERAL']['TIMESTAMP_FIELD']

AWS_REGION=cfg['GENERAL']['AWS_REGION']
ACCESS_KEY=cfg['GENERAL']['ACCESS_KEY']
SECRET_KEY=cfg['GENERAL']['SECRET_KEY']
ACCOUNT=cfg['GENERAL']['ACCOUNT']
SQS_QUEUE=cfg['GENERAL']['SQS_QUEUE']
SQS_URL=f'https://sqs.{AWS_REGION}.amazonaws.com/{ACCOUNT}/{SQS_QUEUE}'
S3_BUCKET=cfg['GENERAL']['S3_BUCKET']
UPLOAD_TO_SQS=cfg['GENERAL']['UPLOAD_TO_SQS'] in ('YES', 'Y', 'Yes', 'y', True, 1)
UPLOAD_TO_S3=cfg['GENERAL']['UPLOAD_TO_S3'] in ('YES', 'Y', 'Yes', 'y', True, 1)

try:
    os.makedirs(DNLOAD_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
except:
    print('Output directory creation failed')
    exit(0)
