import logging
import logging.handlers
import os

import import_declare_test  # noqa
import solnlib
import splunk
import splunk.clilib.cli_common as cli_c
import ta_ms_advanced_hunting_declare

APP_NAME = ta_ms_advanced_hunting_declare.APP_NAME
ACCOUNT_CONF_NAME = ta_ms_advanced_hunting_declare.ACCOUNT_CONF_NAME
SETTINGS_CONF_NAME = ta_ms_advanced_hunting_declare.SETTINGS_CONF_NAME

def get_secret(logger, session_key, secret_realm, secret_name):
    # context of this app
    cm = solnlib.credentials.CredentialManager(session_key=session_key,
                                              app=APP_NAME,
                                              realm=secret_realm)
    try:
      return cm.get_password(secret_name) 
    except Exception as e:
      logger.error(e)

    return None

    # context of current app
    # secrets = service.storage_passwords

    # try:
    #     return next(secret for secret in secrets if (secret.realm == secret_realm and secret.username == secret_name)).clear_password
    # except StopIteration: 
    #     return None

def get_secrets(logger, session_key, secret_realm):
    # context of this app
    cm = solnlib.credentials.CredentialManager(session_key=session_key,
                                              app=APP_NAME,
                                              realm=secret_realm)
    try:
      return cm.get_clear_passwords_in_realm() 
    except Exception as e:
      logger.error(e)

    return []


def get_all_secret_name(logger, service, secret_realm):
    
    # context of this app 
    secrets = service.storage_passwords
    return  [ 
              secret.username for secret in secrets \
              if (secret.realm == secret_realm)
            ] 

def create_secret(logger, session_key, secret_realm, secret_name, secret):

    # context of current app
    # storage_password = service.storage_passwords.create(secret, secret_name, secret_realm)
    # logger.info("Created storage password with name: {}".format(storage_password.name))

    # context of this app 
    cm = solnlib.credentials.CredentialManager(session_key=session_key,
                                              app=APP_NAME,
                                              realm=secret_realm)
    try:
      cm.set_password(secret_name, secret)
    except Exception as e:
      logger.error(e)

    logger.info({'message': f'Created/Updated secret::{secret_name}'})

        
def update_secret(logger, service, secret_realm, secret_name, secret):
    
    try:
        service.storage_passwords.delete(secret_name, realm=secret_realm)
    except Exception as e:
        logger.error(e)

    try:
        storage_password = service.storage_passwords.create(secret, secret_name, realm=secret_realm)
    except Exception as e:
        logger.error(e)

    logger.info({'message': f'Update storage password with name: {storage_password.name}'})


def setup_logger(logger, log_level):
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = f"{APP_NAME}.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a') 
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    logger.setLevel(log_level)


def get_settings_loglevel(logger, session_key: str=None):
    
    log_level = solnlib.conf_manager.get_log_level(
      logger=logger,
      session_key=session_key,
      app_name=APP_NAME,
      conf_name=SETTINGS_CONF_NAME,
    )
    return log_level

def get_settings_proxy(logger, session_key: str=None):
    
    proxy_dict = solnlib.conf_manager.get_proxy_dict(
      logger=logger,
      session_key=session_key,
      app_name=APP_NAME,
      conf_name=SETTINGS_CONF_NAME,
    )
    return proxy_dict


def get_account_config(session_key: str=None):
    
    # pattern 1
    return cli_c.getConfStanzas(ACCOUNT_CONF_NAME)

    # pattern 2
    """
    cfm = conf_manager.ConfManager(
        session_key,
        APP_NAME,
        realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{ACCOUNT_CONF_NAME}",
    )

    account_conf_file = cfm.get_conf(ACCOUNT_CONF_NAME)
    return account_conf_file.get_all()
    """
