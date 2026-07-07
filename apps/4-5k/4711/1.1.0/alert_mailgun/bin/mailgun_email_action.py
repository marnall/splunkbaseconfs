import sys, requests, json, re, os
import logging, logging.handlers
import splunk


def setup_logging():
    logger = logging.getLogger('splunk.mailgun')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "mailgun.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a') 
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger


def check_inputs(config, logger):
    if 'url' in config:
        matched = re.match(r'https?:\/\/[^.]+\.[^.]+.*',config['url'])
        if not matched:
            logger.error("Invalid URL")
            return False
    else:
        logger.error("No URL specified")
        return False
    if not 'api_key' in config:
        logger.error("No API key specified")
        return False
    if 'email_type' in config:
        if config['email_type']!="html" and config['email_type']!="text":
            logger.error("Invalid email type")
            return False
    else:
        logger.error("No email type specified")
        return False
    if not 'to' in config:
        logger.error("No to email address specified")
        return False
    if not 'from' in config:
        logger.error("No from email address specified")
        return False

    return True

if len(sys.argv) > 1 and sys.argv[1] == "--execute":
    logger = setup_logging()
    alert = json.load(sys.stdin)
    if check_inputs(alert['configuration'], logger):
        #load config
        config = alert['configuration']
        url = config['url']
        email_type = config['email_type']
        content = config['content']
        to = config['to'].split(",")
        #construct call
        auth=('api',config['api_key'])
        data = {}
        data['from'] = config['from']
        data['to'] = to
        data['subject'] = config['subject']
        if email_type == "text":
            data['text'] = content
        elif email_type == "html":
            data['html'] = content
            data['text'] = "Error: HTML support is needed to view this email."
        #doit
        r = requests.post(url,auth=auth,data=data,verify=False)
        if r.status_code == 200:
            logger.info("200: Success sending email")
        else:
            logger.error(str(r.status_code)+": "+r.text)

    else:
        logger.error("Invalid configuration detected. Stopped.")
else:
    print("FATAL No execute flag given")
