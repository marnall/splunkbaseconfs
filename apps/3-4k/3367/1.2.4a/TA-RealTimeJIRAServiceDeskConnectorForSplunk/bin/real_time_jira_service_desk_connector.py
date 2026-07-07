import sys
import os
import json
import urllib2
import logging
import logging.handlers
import splunk


def setup_logging(level):
    print >> sys.stdout, "INFO entered setup_logging"
    logger = logging.getLogger('splunk.ta-realtimejiraservicedeskconnectorforsplunk')
    logger.setLevel(level)
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "ta-real_time_jira_service_desk_connector_for_splunk.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    LOGFILE = SPLUNK_HOME + "/" + BASE_LOG_PATH + "/" + LOGGING_FILE_NAME
    print >> sys.stdout, "INFO logging to file:" + LOGFILE
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    print >> sys.stdout, "INFO created splunk_log_handler..."
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    print >> sys.stdout, "INFO set log formatter..."
    logger.addHandler(splunk_log_handler)
    print >> sys.stdout, "INFO added handler..."
    return logger


def send_message(settings):
    print >> sys.stdout, str(settings)
    project_key = settings.get("project_key")
    server_id = settings.get("server_id")
    server_url = settings.get("server_url").rstrip('/')
    results_link = settings.get("results_link")
    search = settings.get("search")
    severity = settings.get("severity")
    auth_token = settings.get('auth_token')
    # logger.debug("project_key ==>:" + project_key)
    # logger.debug("server_id ==>:" + server_id)
    # logger.debug("server_url ==>:" + server_url)
    # logger.debug("results ==>:" + results_link)
    # logger.debug("search ==>:" + search)
    # logger.debug("severity ==>:" + severity)
    url = "%s/rest/controllers/issues/request/%s" % (
        server_url, urllib2.quote(server_id)
    )
    logger.debug("url ==>:" + url)
    # summary = search + "Caught " + severity + " severity alert"
    summary = "Caught " + severity + " severity alert"
    # logger.debug("summary ==>:" + summary)
    description = "Results " + results_link + "\n" + summary
    # logger.debug("description ==>:" + description)
    key_name = project_key
    issue_type_name = "Incident"
    body = json.dumps(dict(fields=dict(project=dict(key=key_name), summary=summary, description=description,
                                       issuetype=dict(name=issue_type_name))))
    auth_type = 'Basic ' + auth_token
    req = urllib2.Request(url, body, {'Content-Type': 'application/json', 'Authorization': auth_type})
    try:
        res = urllib2.urlopen(req)
        body = res.read()
        return 200 <= res.code < 300
    except urllib2.HTTPError, e:
        print >> sys.stderr, "ERROR Error sending message: %s" % e
        return False


if __name__ == "__main__":
    logger = setup_logging(logging.DEBUG)
    logger.debug('Number of arguments:' + str(len(sys.argv)) + ' arguments..')
    logger.debug('Argument List:' + str(sys.argv))
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        logger.debug('JSON payload')
        if not send_message(payload.get('configuration')):
            print >> sys.stderr, "FATAL Failed trying to create JIRA Issue"
            sys.exit(2)
        else:
            print >> sys.stderr, "INFO JIRA Issue successfully created"
    else:
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
