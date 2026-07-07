from splunk.clilib import cli_common as cli
import sys, os
import json
import copy
import time
import threading
import splunk.entity as entity
import logging
import logging.handlers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "BaseClient"))
from baseclient import BaseClient
import endpoints


def setup_logger(level):
    """
    This function creates logger file
    """
    logger = logging.getLogger('strikeready')
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/strikeready.log',
                                                        maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def get_self_conf_stanza(stanza, conf):
    appdir = os.path.dirname(os.path.dirname(__file__))
    apikeyconfpath = os.path.join(appdir, "default", conf)
    apikeyconf = cli.readConfFile(apikeyconfpath)
    return apikeyconf[stanza]


logger = setup_logger(logging.INFO)
stanza = get_self_conf_stanza(endpoints.index_stanza, "inputs.conf")
index = stanza['index']
base_obj = BaseClient()
output_mode = {'output_mode': 'json'}


def check_duplicate(ip, user, passw):
    """
    This function checks and removes the duplicate iocs from the index
    """
    time.sleep(5)
    session = (user, passw)
    query = {'search': 'search index="{0}" earliest=0 | eventstats count values(_raw) by _raw | WHERE count>1'.format(index)}
    data = copy.deepcopy(endpoints.data)
    data.update(query)
    url = ip + endpoints.baseurl
    r = base_obj.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=data, method='POST', auth=session)
    res = json.loads(r.content.decode())
    sid = res['sid']
    url = endpoints.get_result
    url = url.format(sid)
    url = ip + url
    r = base_obj.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=data, method='GET', auth=session)
    res = json.loads(r.content.decode())

    while not res['entry'][0]['content']['isDone']:
        searchjob = base_obj.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=output_mode,
                                         method='GET', auth=session)
        res = searchjob.json()
    else:
        url = url + 'results/'
        r = base_obj.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=data, method='GET', auth=session)
        res = json.loads(r.content.decode())
        MyList = []
        for x in res['results']:
            x = json.loads(x['_raw'])
            MyList.append(x['value'])

        dup = {i: MyList.count(i) for i in MyList}
        value = ""
        for x in dup:
            temp_value = '"{}" OR'
            temp_value = temp_value.format(x)
            value = value + temp_value

        value = value.rstrip('OR')
        search = {'search': 'search index="{0}" minutesago=10 value={1}| delete'.format(index, value)}
        del_dulicate = copy.deepcopy(endpoints.data)
        del_dulicate.update(search)
        url = ip + endpoints.baseurl
        base_obj.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=del_dulicate, method='POST', auth=session)


def get_credentials(session_key):
    """
    This function gets credentials from passwords.conf file
    """
    myapp = 'strikereadyapp'
    data = {}
    try:
        entities = entity.getEntities(['admin', 'passwords'], namespace=myapp, owner='nobody', sessionKey=session_key)
        # logger.info(entities)
    except Exception as e:
        raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))
    for i, c in entities.items():
        app_name = c.get("eai:acl", {}).get("app", "")
        if app_name == myapp:
            logger.info("Credentials found for {}".format(myapp))
            data = {
                'user': c['username'],
                'pass': c['clear_password'],
                'url': c['realm']
            }
            return data
        else:
            logger.debug("app name: {}".format(app_name))
    else:
        logger.error(f"Credentials not found for {myapp}")

    return data


def main():
    """
    This function index's ioc in StrikeReady index
    """
    session_key = sys.stdin.readline().strip()
    dat = get_credentials(session_key)
    session = (dat['user'], dat['pass'])
    url = dat['url'] + endpoints.ioc_collection
    endpoints.verify_ssl = base_obj.getSelfConfStanza('verify_ssl')
    response = base_obj.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=output_mode, method='GET',
                                    auth=session)
    if response:
        r = response.json()
        lis = []
        for x in r:
            lis.append(x['ioc'])
        for x in lis:
            data = json.dumps(x)
            print(data)
        logger.info("Total IOCs indexed: {}".format(len(lis)))
    else:
        logger.error("Unable to index IOCs.")
    dup_thread = threading.Thread(target=check_duplicate, args=[dat['url'], dat['user'], dat['pass']])
    dup_thread.start()
    base_obj.http_method(url=url, verify_ssl=endpoints.verify_ssl, data=output_mode, method='DELETE', auth=session)


if __name__ == "__main__":
    main()
