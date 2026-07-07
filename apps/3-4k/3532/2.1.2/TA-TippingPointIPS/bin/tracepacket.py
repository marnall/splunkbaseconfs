import zipfile
import requests
import glob
import splunk.Intersplunk
import sys, os
import logging, logging.handlers
import splunk


def setup_logging():
    logger = logging.getLogger('splunk.tracepacket')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']

    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = 'tippingpoint_ips.log'
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = '%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s'
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger


def remove_files(fileList):
    for filePath in fileList:
        try:
            os.remove(filePath)
        except Exception as e:
            logger.error('Error while deleting file : {} due to {}'.format(filePath.str(e)))

def write_pcapfile(filename, sms_response):
    if sms_response.headers.get('transfer-encoding') and 'chunked' in sms_response.headers.get('transfer-encoding'):
        with open(filename + '.pcap', 'wb') as resultFile:
            for chunk in response.iter_content():
                resultFile.write(chunk)
    else:
        with open(filename + '.pcap', 'wb') as resultFile:
            resultFile.write(sms_response.content)

try:
    logger = setup_logging()
    if len(sys.argv) != 4:
        logger.error('Get incorrect args: ' + str(sys.argv))
        logger.error('Usage: tracepacket <devicename> <apikey> <filename>')
        sys.exit(0)

    eventIdCsv = os.path.join(os.environ['SPLUNK_HOME'], 'var', 'run', 'splunk', 'csv', 'eventids.csv')

    sms = sys.argv[1]
    apikey = sys.argv[2]
    filename = sys.argv[3]

    eventId = ''
    count = 0
    with open(eventIdCsv) as f:
        for line in f:
            if count == 1:
                eventId = line.replace('\n', '')
            if count > 1:
                eventId += ',' + line.replace('\n', '')
            count += 1
    logger.info('event ids are: {}'.format(eventId))
    uploadFile = os.path.join(os.environ['SPLUNK_HOME'], 'var', 'run', 'splunk', 'csv', 'eventids.txt')

    with open(uploadFile, 'w') as uploadFileE:
        uploadFileE.write(eventId)

    pcapFilePath = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'TA-TippingPointIPS', 'appserver', 'static')

    zipFileList = glob.glob(pcapFilePath + '*.zip')
    pcapFileList = glob.glob('*.pcap')
    remove_files(zipFileList)
    remove_files(pcapFileList)

    url = 'https://{}/pcaps/getByEventIds'.format(sms)
    headers = {'X-SMS-API-KEY': apikey}
    files = {'file': open(uploadFile, 'rb')}

    response = requests.post(url, headers=headers, files=files, verify=False, stream=True, allow_redirects=False)

    if response.status_code == requests.codes.ok:
        write_pcapfile(filename, response)
        out = zipfile.ZipFile(os.path.join(pcapFilePath, filename + '.zip'), 'w')
        out.write(filename + '.pcap')
        out.close()

    logger.info('The result of request:{} {}'.format(response.status_code, response.reason))
    result = '&http_return_code={}&http_return_msg={} {}'.format(response.status_code, response.status_code, response.reason)
    splunk.Intersplunk.generateErrorResults([{'request': result}])
    sys.exit(0)

except Exception as e:
    logger.exception('Exception: {}'.format(str(e)))
    result = '&http_return_code={}&http_return_msg={}'.format('500', 'Internal Script Error')
    splunk.Intersplunk.generateErrorResults([{'request': result}])