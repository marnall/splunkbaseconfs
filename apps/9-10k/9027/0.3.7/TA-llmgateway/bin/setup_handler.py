"""
setup_handler.py
Splunk custom REST handler for TA-llmgateway setup page.
Writes settings to local/ta_llmgateway_settings.conf and local/inputs.conf.
Called via: /services/TA-llmgateway/setup

No external dependencies - uses only Splunk bundled Python.
"""
import os

import splunk.admin as admin
import splunk.entity as entity


APP_NAME    = "TA-llmgateway"
try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
    APP_LOCAL = make_splunkhome_path(["etc", "apps", APP_NAME, "local"])
except Exception:
    APP_LOCAL = os.path.join(os.environ.get("SPLUNK_HOME", ""), "etc", "apps", APP_NAME, "local")
SETTINGS_CONF = os.path.join(APP_LOCAL, "ta_llmgateway_settings.conf")
INPUTS_CONF   = os.path.join(APP_LOCAL, "inputs.conf")


def ensure_local_dir():
    if not os.path.exists(APP_LOCAL):
        os.makedirs(APP_LOCAL)


def write_settings_conf(db_path, index, interval, batch_size, disabled):
    ensure_local_dir()
    content = (
        "[bifrost]\n"
        "db_path    = {db_path}\n"
        "index      = {index}\n"
        "interval   = {interval}\n"
        "batch_size = {batch_size}\n"
        "disabled   = {disabled}\n"
    ).format(
        db_path=db_path,
        index=index,
        interval=interval,
        batch_size=batch_size,
        disabled=disabled,
    )
    with open(SETTINGS_CONF, "w") as f:
        f.write(content)


def write_inputs_conf(index, interval, disabled):
    ensure_local_dir()
    disabled_val = "true" if str(disabled).lower() in ("true", "1", "yes") else "false"
    content = (
        "[script://$SPLUNK_HOME/etc/apps/TA-llmgateway/bin/bifrost_logs.py]\n"
        "disabled   = {disabled}\n"
        "index      = {index}\n"
        "sourcetype = llmgateway:bifrost\n"
        "interval   = {interval}\n"
        "python.version = python3\n"
    ).format(
        disabled=disabled_val,
        index=index,
        interval=interval,
    )
    with open(INPUTS_CONF, "w") as f:
        f.write(content)


class SetupHandler(admin.MConfigHandler):

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for field in ("db_path", "index", "interval", "batch_size", "disabled"):
                self.supportedArgs.addOptArg(field)

    def handleList(self, confInfo):
        """Return current settings."""
        defaults = {
            "db_path":    os.path.join(
                os.path.expanduser("~"), "AppData", "Roaming", "bifrost", "logs.db"
            ),
            "index":      "llmgateway",
            "interval":   "30",
            "batch_size": "500",
            "disabled":   "false",
        }
        if os.path.exists(SETTINGS_CONF):
            with open(SETTINGS_CONF, "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#") and not line.startswith("["):
                        k, _, v = line.partition("=")
                        k = k.strip()
                        v = v.strip()
                        if k in defaults:
                            defaults[k] = v
        confInfo["bifrost"].update(defaults)

    def handleEdit(self, confInfo):
        """Save settings."""
        db_path    = self.callerArgs.data.get("db_path",    [""])[0] or ""
        index      = self.callerArgs.data.get("index",      ["llmgateway"])[0]
        interval   = self.callerArgs.data.get("interval",   ["30"])[0]
        batch_size = self.callerArgs.data.get("batch_size", ["500"])[0]
        disabled   = self.callerArgs.data.get("disabled",   ["false"])[0]

        write_settings_conf(db_path, index, interval, batch_size, disabled)
        write_inputs_conf(index, interval, disabled)

        # Mark app as configured
        try:
            entity.setEntity(
                entity.getEntity(
                    "apps/local", APP_NAME,
                    sessionKey=self.getSessionKey()
                ),
                {"configured": "1"},
                sessionKey=self.getSessionKey()
            )
        except Exception:
            pass

        confInfo["bifrost"]["db_path"]    = db_path
        confInfo["bifrost"]["index"]      = index
        confInfo["bifrost"]["interval"]   = interval
        confInfo["bifrost"]["batch_size"] = batch_size
        confInfo["bifrost"]["disabled"]   = disabled


admin.init(SetupHandler, admin.CONTEXT_APP_ONLY)
