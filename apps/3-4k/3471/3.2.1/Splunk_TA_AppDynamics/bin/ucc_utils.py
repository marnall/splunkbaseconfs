import urllib
from solnlib import conf_manager, log

__all__ = ["Util"]

logger = log.Logs().get_logger("ucc_utilities")

class Util:
    @staticmethod
    def get_app_name():
        return "Splunk_TA_AppDynamics"

    @staticmethod
    def get_conf_name():
        return "splunk_ta_appdynamics_settings"

    @staticmethod
    def get_max_workers(session_key):
        cfm = conf_manager.ConfManager(
            session_key,
            Util.get_app_name(),
        )
        conf = cfm.get_conf(Util.get_conf_name(), True)
        max_workers = conf.get("additional_parameters").get("max_workers")
        if max_workers is None:
            logger.debug(f"No max_workers for {session_key} set, returning 25 as default")
            return int(25)
        logger.debug(f"max_workers for {session_key} set, returning {max_workers}")
        return int(max_workers)

    @staticmethod
    def get_timeout(session_key):
        cfm = conf_manager.ConfManager(
            session_key,
            Util.get_app_name(),
        )
        timeout_conf = cfm.get_conf(Util.get_conf_name(), True)
        timeout = timeout_conf.get("additional_parameters").get("timeout")
        if timeout is None:
            logger.debug(f"No timeout for {session_key} set, returning 15.0 as default")
            return float(15.0)
        logger.debug(f"Timeout for {session_key} set, returning {timeout}")
        return float(timeout)

    @staticmethod
    def get_default_index(session_key):
        cfm = conf_manager.ConfManager(
            session_key,
            Util.get_app_name(),
        )
        conf = cfm.get_conf(Util.get_conf_name(), True)
        index = conf.get("additional_parameters").get("index")
        if not index:
            logger.debug(f"No default index for {session_key} set, returning appdynamics")
            return "appdynamics"
        logger.debug(f"Default index for {session_key} set, returning {index}")
        return str(index)

    @staticmethod
    def get_output_index(helper, stanza_name=None):
        # Prefer per-input index, then fall back to global default index.
        session_key = helper.context_meta.get("session_key")
        default_index = Util.get_default_index(session_key) if session_key else "appdynamics"

        idx = helper.get_output_index()
        if isinstance(idx, dict):
            if stanza_name is not None:
                idx = idx.get(stanza_name)
            else:
                return {name: value or default_index for name, value in idx.items()}

        if not idx:
            return default_index

        return idx

    @staticmethod
    def get_proxy(session_key):
        proxy_config = conf_manager.get_proxy_dict(logger, session_key, Util.get_app_name(), Util.get_conf_name())
        if proxy_config.get("proxy_enabled", 0) is None:
            return {}
        if int(proxy_config.get("proxy_enabled", 0)) == 1:
            proxy_password = proxy_config.get("proxy_password")
            if proxy_password is None:
                proxy_password = ""
            else:
                proxy_password = str(proxy_password)
            proxy_username = proxy_config.get("proxy_username")
            if proxy_username is None:
                proxy_username = ""
            else:
                proxy_username = str(proxy_username)

            escaped_username = urllib.parse.quote(proxy_username, safe="")
            escaped_password = urllib.parse.quote(proxy_password, safe="")
            scheme = proxy_config.get("proxy_type")
            if proxy_config.get("proxy_username") is None:
                return {
                    "http": "{}://{}:{}".format(scheme, proxy_config.get("proxy_url"), proxy_config.get("proxy_port")),
                    "https": "{}://{}:{}".format(scheme, proxy_config.get("proxy_url"), proxy_config.get("proxy_port"))
                }
            else:
                if proxy_config.get("proxy_password") is None:
                    return {
                        "http": "{}://{}@{}:{}".format(scheme, escaped_username, proxy_config.get("proxy_url"), proxy_config.get("proxy_port")),
                        "https": "{}://{}@{}:{}".format(scheme, escaped_username, proxy_config.get("proxy_url"), proxy_config.get("proxy_port"))
                    }
                else:
                    return {
                        "http": "{}://{}:{}@{}:{}".format(scheme, escaped_username, escaped_password, proxy_config.get("proxy_url"), proxy_config.get("proxy_port")),
                        "https": "{}://{}:{}@{}:{}".format(scheme, escaped_username, escaped_password, proxy_config.get("proxy_url"), proxy_config.get("proxy_port"))
                    }
        return {}

    @staticmethod
    def get_verify_ssl(session_key) -> bool:
        cfm = conf_manager.ConfManager(
            session_key,
            Util.get_app_name(),
        )
        conf = cfm.get_conf(Util.get_conf_name(), True)
        verify = conf.get("additional_parameters").get("verify_ssl")
        if verify is None:
            return True
        return str(verify).strip().lower() == "true"

    @staticmethod
    def apply_log_level(session_key, external_logger, default="INFO") -> logger:
        import logging
        cfm = conf_manager.ConfManager(
            session_key,
            Util.get_app_name()
        )
        conf = cfm.get_conf(Util.get_conf_name(), True)
        level = conf.get("logging").get("loglevel", default)
        external_logger.setLevel(getattr(logging, level, logging.INFO))
        return external_logger
