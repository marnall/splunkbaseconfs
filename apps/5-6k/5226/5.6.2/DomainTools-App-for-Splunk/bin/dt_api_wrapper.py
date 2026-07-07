from __future__ import absolute_import
from domaintools import API
from splunklib import client
from splunklib import six
from domaintools import __version__ as dt_api_version
from settings import APP_ID
from settings import APP_VERSION
import certifi
import ssl


class DtApiWrapper:
    """This takes params from the front end, or data from the kvstore to create
    a domaintools api.

    """

    def __init__(self, service, logger, params=False):
        """Args:
        session_key (str): User's splunk session key
        logger (DTLogger): An instance of DTLogger

        Attributes:
        __service (str): splunk service
        __dt_settings (int): Settings to send to retrive domaintools api
        __dt_log (DTLogger): Calling classes logger
        __params (dict or boolean) optional: dict of settings to get a dt api default False
        """
        self.__service = service
        self.__dt_settings = self.__dt_settings_template()
        self.__dt_log = logger
        self.__params = {} if not params else params
        if not params:
            self.__get_params()  # this call has to be done outside of assignment because it refers to self.__params

    def create_dt_api(self):
        """Create an instance of domaintools api
        Args:
          params (str or boolean): URL encoded json string of dt settings

        Returns:
          An instance domaintools API
        """
        self.__update_settings()
        self.__dt_log.info("Creating DT API")
        return API(
            self.__dt_settings["user"],
            self.__dt_settings["key"],
            app_partner=self.__dt_settings["app_partner"],
            app_name=self.__dt_settings["app_name"],
            app_version=self.__dt_settings["app_version"],
            api_version=self.__dt_settings["api_version"],
            proxy_url=self.__dt_settings["proxy_url"],
            verify_ssl=self.__dt_settings["verify_ssl"],
            always_sign_api_key=self.__dt_settings["always_sign_api_key"],
        )

    def __get_credentials(self):
        """Pull dt credentials from kvstore

        Returns:
          (dict) username and api key for dt api
        """
        user = ""
        key = ""
        proxy_username = ""
        proxy_password = ""
        credentials = self.__service.storage_passwords
        for credential in credentials:
            if credential.realm == "DomainTools":
                user = credential.username
                key = credential.clear_password
            if credential.realm == "DomainToolsProxy":
                proxy_username = credential.username
                proxy_password = credential.clear_password
        return {
            "user": user,
            "key": key,
            "proxy_username": proxy_username,
            "proxy_password": proxy_password,
        }

    def __get_conf_stanzas(self, conf_file, stanza_name):
        """Pull any conf file's stanza by name

        Returns:
          stanza object
        """
        stanzas = self.__service.confs[conf_file].list()
        for stanza in stanzas:
            if stanza.name == stanza_name:
                return stanza
        return None

    def __dt_settings_template(self):
        """Set up settings to send to connect to dt api

        Returns:
          (dict) Settings we know about
        """
        app_conf = self.__get_conf_stanzas("app", "launcher")
        return {
            "user": "",
            "key": "",
            "app_partner": "splunk",
            "app_name": APP_ID,
            "app_version": APP_VERSION,
            "api_version": dt_api_version,
            "proxy_url": None,
            "verify_ssl": False,
            "always_sign_api_key": None,  # Default value is handled inside the API class
        }

    def __update_settings(self):
        """Fills out the settiings comming in from the page or kvstore"""
        self.__dt_settings["user"] = self.__params["user"]
        self.__dt_settings["key"] = self.__params["key"]

        if self.__params["proxy_enabled"] == "1":
            if self.__params["proxy_server"] and self.__params["proxy_port"]:
                self.__dt_settings["proxy_url"] = (
                    self.__params["proxy_server"] + ":" + self.__params["proxy_port"]
                )
            else:
                self.__dt_log.error(
                    "When proxy turned on you must provide both a Proxy Server and Proxy Port"
                )
                raise Exception("You must provide both a Proxy Server and Proxy Port")
            if self.__params.get("proxy_authentication") == "1":
                split_url = self.__dt_settings["proxy_url"].split("://")
                protocol = "http"
                if len(split_url) == 2:
                    protocol = split_url[0]
                    server_address = split_url[1]
                else:
                    server_address = self.__dt_settings["proxy_url"]
                self.__dt_settings["proxy_url"] = "{}://{}:{}@{}".format(
                    protocol,
                    self.__params["proxy_username"],
                    self.__params["proxy_password"],
                    server_address,
                )

        ctx = ssl.create_default_context(cafile=certifi.where())
        self.__dt_settings["verify_ssl"] = ctx
        if self.__params["custom_certificate_enabled"] == "1":
            ctx = ssl.create_default_context(cafile=self.__params["custom_certificate_path"])
            self.__dt_settings["verify_ssl"] = ctx

    def __get_params(self):
        """Fills out the self.__params if no params sent from the page"""
        credentials = self.__get_credentials()
        dt_conf = self.__get_conf_stanzas("domaintools", "domaintools")
        self.__params["user"] = credentials["user"]
        self.__params["key"] = credentials["key"]
        self.__params["proxy_username"] = credentials["proxy_username"]
        self.__params["proxy_password"] = credentials["proxy_password"]
        self.__params["proxy_server"] = dt_conf["proxy_server"]
        self.__params["proxy_port"] = dt_conf["proxy_port"]
        self.__params["proxy_enabled"] = dt_conf["proxy_enabled"]
        self.__params["proxy_authentication"] = dt_conf["proxy_authentication"]
        self.__params["custom_certificate_enabled"] = dt_conf["custom_certificate_enabled"]
        self.__params["custom_certificate_path"] = dt_conf["custom_certificate_path"]
