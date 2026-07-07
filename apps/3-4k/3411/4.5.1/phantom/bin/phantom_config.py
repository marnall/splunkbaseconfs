# File: phantom_config.py
# Copyright (c) 2016-2025 Splunk Inc.
#
# SPLUNK CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Splunk Inc. is PROHIBITED.

import json
import logging
import os
from collections.abc import MutableMapping as DictMixin
from configparser import ConfigParser
from io import StringIO

import splunk as splunkmod

import ta_addonphantom_declare  # noqa: F401

from phantom_splunk import Splunk
from phantom_imports import DEFAULT_LOGGING_MAX_SIZE, DEFAULT_LOGGING_BACKUP_COUNT


PHANTOM_KEY = "phantom"
PHANTOM_AR_KEY = "phantom_ar"
SEVERITIES = "severities"
SEVERITIES_AR = "severities_ar"
PLAYBOOKS = "playbooks"
PLAYBOOKS_AR = "playbooks_ar"
WORKBOOK_KEY = "workbooks"
WORKBOOK_LAST_SYNC_TIME = "last_sync_time"
WORKBOOK_SYNC_KEY = "sync_key"
VERSION_KEY = "version"
LOGGING_CONFIG = "enable_logging"
ACCEPTED = "accepted"
TOKEN_KEY = "ph-auth-token"
VERIFY_KEY = "verify_certs"
FIELD_MAPPING = "field_mapping"
ARTIFACT_AR = "artifact_ar"

TOP_LEVEL_SETTINGS = (
    PHANTOM_KEY,
    PHANTOM_AR_KEY,
    SEVERITIES,
    SEVERITIES_AR,
    PLAYBOOKS,
    PLAYBOOKS_AR,
    VERSION_KEY,
    LOGGING_CONFIG,
    ACCEPTED,
    VERIFY_KEY,
    FIELD_MAPPING,
    ARTIFACT_AR,
    WORKBOOK_KEY,
    WORKBOOK_LAST_SYNC_TIME,
    WORKBOOK_SYNC_KEY,
)

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APPCONF = os.path.join(APP_DIR, "default", "app.conf")

OLD_CONFIG_FILE = os.path.join(
    os.environ["SPLUNK_HOME"], "etc", "apps", "phantom", "local", "data", "config", "config.json"
)
OLDER_CONFIG_FILE = os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", "phantom", "config.json")

CIM_MAPPING_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cim_cef.json")

LOG_MAPPING = {
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}

CONFIG_ENDPOINT = "/servicesNS/nobody/phantom/configs/conf-phantom"


def get_safe(d, k, default):
    x = d.get(k)
    if not x:
        x = default
    return x


class PhantomConfig(DictMixin):
    def __init__(self, component_name, session=None):
        if isinstance(component_name, logging.Logger):
            self.logger = component_name
            self.component_name = self.logger.name
        else:
            self.component_name = component_name
            self.logger = self.get_logger(self.component_name)
        self.splunk = Splunk(session, self.logger)
        j = self._get_config()
        self._config = j
        log_level = self._config.get("enable_logging", "INFO")
        self.update_log_level(log_level)
        self.version = self.get_version()
        self.fips_is_enabled = self.fips_enabled()

    def update_log_level(self, level):
        if level == 1 or level == "DEBUG":
            self.logger.setLevel(logging.DEBUG)
        elif level == "INFO":
            self.logger.setLevel(logging.INFO)
        elif level == 0 or level == "ERROR":
            self.logger.setLevel(logging.ERROR)
        elif level == "true":
            self.logger.info("Updating the log level to DEBUG")
            self.logger.setLevel(logging.DEBUG)
        elif level == "false":
            self.logger.info("Updating the log level to ERROR")
            self.logger.setLevel(logging.ERROR)
        self.logger.info(f"Log level in config: {level}")

    def get_passwords(self):
        return self.splunk.get_passwords()

    def delete_password(self, pw_id):
        self.splunk.delete_password(pw_id)

    def update_password(self, name, token):
        self.splunk.update_password(name, token)

    def update_workbook(self, name, value):
        self.splunk.update_workbook(name, value)

    def log_info(self, info):
        self.logger.info(info)

    def log_debug(self, info):
        self.logger.debug(info)

    def log_error(self, info):
        self.logger.error(info)

    def get_version(self):
        self.logger.info("Getting app version...")
        with open(APPCONF) as f:
            cp = None
            try:
                cp = ConfigParser(delimiters=("="), strict=False)
            except Exception:
                cp = ConfigParser()
            cp.read_file(f)
            version = cp.get("launcher", "version")
        self.logger.info(f"App version: {version}")
        return version

    def fips_enabled(self):
        return self.splunk.get_fips_mode()

    def get_cim_mapping(self):
        return json.loads(open(CIM_MAPPING_JSON).read())

    def _get_config(self):
        j = self._load_from_rest()
        if not j.get(PHANTOM_KEY) and len(j) <= len(TOP_LEVEL_SETTINGS):
            # no phantom configs and no output configs
            if os.path.isfile(OLD_CONFIG_FILE):
                j = json.loads(open(OLD_CONFIG_FILE).read())
            elif os.path.isfile(OLDER_CONFIG_FILE):
                j = json.loads(open(OLDER_CONFIG_FILE).read())

        if j and j.get(PHANTOM_KEY) is not None and j.get(VERSION_KEY):
            pass
        else:
            j = {}
        # commented out line below temporarily because of unicode .get() error
        # self._do_migrations(j)
        for k, v in j[PHANTOM_KEY].items():
            v[TOKEN_KEY] = self.splunk.load_auth_token(k)

        return j

    def _do_migrations(self, config):
        self.logger.info("doing migration")
        resave_server_configs = False
        do_save = False

        if PHANTOM_KEY in config:
            server_config = config[PHANTOM_KEY]
            if server_config.get(TOKEN_KEY):
                t = config[PHANTOM_KEY]
                config[PHANTOM_KEY] = {"phantom": t}
                do_save = True
        else:
            config[PHANTOM_KEY] = {}
            do_save = True

        if VERSION_KEY not in config:
            for k, v in config.items():
                if k in TOP_LEVEL_SETTINGS or not v:
                    continue
                v["_enabled"] = v["_enabled"] in (True, "true")
            resave_server_configs = True
        else:
            major, minor, rev = config[VERSION_KEY].split(".", 2)
            major, minor, rev = int(major), int(minor), int(rev)
            if major < 2 or (minor < 1 and rev <= 10):
                resave_server_configs = True
                targets = config.get(PHANTOM_KEY, {})
                for k, v in config.items():
                    if not v or k in TOP_LEVEL_SETTINGS:
                        continue
                    t = v.get("_target")
                    if t in targets:
                        v["_target"] = f"{t}"
            else:
                if config[VERSION_KEY] != self.get_version():
                    do_save = True
                else:
                    self.logger.info("no migration needed")
        if VERIFY_KEY not in config:
            config[VERIFY_KEY] = True
        if resave_server_configs:
            for k, v in config[PHANTOM_KEY].items():
                config_id = v.get("ph_auth_config_id")
                token = v.get(TOKEN_KEY)
                if config_id and token:
                    self.splunk.save_auth_token(config_id, token)
                    del v[TOKEN_KEY]
                    pcfg = config[PHANTOM_KEY]
                    pcfg[config_id] = v
                    del pcfg[k]
            self.logger.info("moving passwords to store")
            do_save = True
        if do_save:
            config[VERSION_KEY] = self.version
            self.save_config(config)
            self.logger.info("updated config")

    def _load_from_rest(self):
        success, content = self.splunk.get(CONFIG_ENDPOINT, params={"count": -1})
        config = {}
        if success and content:
            for entry in content.get("entry", []):
                val = entry.get("content", {}).get("value")
                if val and entry.get("name") != "enable_logging":
                    val = json.loads(val)
                config[entry.get("name", "")] = val
        if "" in config:
            config.pop("")
        if "config" in config:
            config.pop("config")

        # self.logger.info(config)
        return config

    def save_config(self, j):
        for k, v in j.items():
            if k == VERSION_KEY:
                v = self.get_version()
            args = {
                "name": k,
            }
            try:
                self.splunk.post(CONFIG_ENDPOINT, args)
            except Exception:
                pass  # fails if it already exist
            args = {"value": json.dumps(v)}
            success, content = self.splunk.post(f"{CONFIG_ENDPOINT}/{k}", args)

    def __len__(self):
        return len(self.keys())

    def __iter__(self):
        for i in self.keys():
            yield i

    def __str__(self):
        parser = None
        try:
            parser = ConfigParser(delimiters=("="), strict=False)
        except Exception:
            parser = ConfigParser()
        for k, v in self._config.items():
            parser.add_section(k)
            parser.set(k, "value", json.dumps(v))
        sio = StringIO()
        parser.write(sio)
        return sio.getvalue()

    def __delitem__(self, key):
        succeeded, result = self.splunk.rest(f"{CONFIG_ENDPOINT}/{key}", {}, "DELETE")
        if succeeded:
            del self._config[key]

    def __getitem__(self, key):
        return self._config[key]

    def __setitem__(self, key, value):
        if key == PHANTOM_KEY:
            for server, info in value.items():
                if TOKEN_KEY in info:
                    self.splunk.save_auth_token(server, info[TOKEN_KEY])
                    del info[TOKEN_KEY]

        args = {
            "name": key,
        }
        try:
            self.splunk.post(CONFIG_ENDPOINT, args)
        except Exception:
            pass  # fails if it already exist
        success, content = self.splunk.post(
            f"{CONFIG_ENDPOINT}/{key}", {"value": json.dumps(value)}
        )
        if success:
            self._config[key] = value

    def __contains__(self, value):
        return value in self._config

    def keys(self):
        return self._config.keys()

    def get_server_config(self, name):
        return self[PHANTOM_KEY].get(name)

    def set_server_config(self, name, config):
        pcfg = self[PHANTOM_KEY]
        pcfg[name] = config.json() if hasattr(config, "json") else config
        self[PHANTOM_KEY] = pcfg

    def get_forwarding_configs(self):
        return [v for k, v in self.items() if v and k not in TOP_LEVEL_SETTINGS]

    @classmethod
    def get_logger(cls, component_name):
        logger = logging.getLogger("splunk.phantom." + component_name)
        logger.setLevel(logging.ERROR)  # Not logging init log messages
        SPLUNK_HOME = os.environ["SPLUNK_HOME"]

        DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log.cfg")
        LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log-local.cfg")
        LOGGING_STANZA_NAME = "python"
        LOGGING_FILE_NAME = f"phantom_{component_name}.log"
        BASE_LOG_PATH = os.path.join("var", "log", "splunk")
        LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
        splunk_log_handler = logging.handlers.RotatingFileHandler(
            os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME),
            maxBytes=DEFAULT_LOGGING_MAX_SIZE,
            backupCount=DEFAULT_LOGGING_BACKUP_COUNT,
        )
        splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        logger.propagate = False
        handlers_exists = any([True for h in logger.handlers if h.baseFilename == component_name])
        if not handlers_exists:
            logger.addHandler(splunk_log_handler)
        splunkmod.setupSplunkLogger(
            logger, DEFAULT_CONFIG_FILE, LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME
        )
        logger.setLevel(logging.DEBUG)
        return logger
