"""The Splunk side of `jev`: settings and key from the UCC configuration page, the KV store, the log.

Everything here needs a running Splunk, so it is kept thin and is verified on a real instance
(docs/test-environment.md). Decisions live in jev_setup.py and jev_engine.py, which are tested.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from solnlib import conf_manager, log  # noqa: E402
from splunklib import client  # noqa: E402

import jev_setup  # noqa: E402

SETTINGS_CONF = "jev_for_splunk_settings"
COLLECTION = "jev_cache"


def read_settings(session_key):
    """jev_setup.settings() from the saved configuration page, the API key decrypted."""
    realm = "__REST_CREDENTIAL__#%s#configs/conf-%s" % (jev_setup.APP, SETTINGS_CONF)
    try:
        conf = conf_manager.ConfManager(session_key, jev_setup.APP, realm=realm).get_conf(SETTINGS_CONF)
        stanzas = {}
        for name in ("typesafe", "proxy", "limits"):
            try:
                stanzas[name] = conf.get(name)
            except conf_manager.ConfStanzaNotExistException:
                stanzas[name] = {}
    except Exception as e:
        # Only the kind of error is shown. This path decrypts the API key, and the text of an exception
        # raised while doing so is not ours to vouch for.
        raise ValueError("jev: could not read the app's settings (%s). Reading the stored API key needs the "
                         "list_storage_passwords capability as well as %s."
                         % (type(e).__name__, jev_setup.CAPABILITY))
    return jev_setup.settings(**stanzas)


def current_context(service):
    return json.loads(service.get("authentication/current-context", output_mode="json").body.read().decode("utf-8"))


def get_logger(session_key):
    """$SPLUNK_HOME/var/log/splunk/jev_for_splunk.log at the level the Logging tab sets."""
    logger = log.Logs().get_logger(jev_setup.APP)
    try:
        logger.setLevel(conf_manager.get_log_level(logger=logger, session_key=session_key,
                                                   app_name=jev_setup.APP, conf_name=SETTINGS_CONF))
    except Exception:
        logger.setLevel("INFO")
    return logger


class KV:
    """The interface jev_cache needs, over the jev_cache collection. Always addressed in this
    app's namespace as nobody, so the cache is shared whichever app the search runs in."""

    def __init__(self, service):
        shared = client.Service(scheme=service.scheme, host=service.host, port=service.port,
                                token=service.token, owner="nobody", app=jev_setup.APP)
        self.data = shared.kvstore[COLLECTION].data

    def query(self, query):
        return self.data.query(query=json.dumps(query))

    def batch_save(self, documents):
        self.data.batch_save(*documents)

    def delete(self, query):
        self.data.delete(query=json.dumps(query))
