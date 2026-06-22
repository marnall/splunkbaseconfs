"""Dummy modular input to enable embedded dashboards for Userful (Py3-ready)."""
__author__ = "Userful (forked from Michael Uschmann / MuS)"
__date__ = "Copyright $Oct 25, 2018 11:00:00 AM$"
__version__ = "0.1.1-userful"

import logging
import os
import re
import signal
import subprocess
import sys
import time
import xml.dom.minidom

SPLUNK_HOME = os.environ["SPLUNK_HOME"]
my_path = os.path.dirname(os.path.realpath(__file__))

LOG_FORMAT = "%(asctime)s level=%(levelname)s component=userful_proxy %(message)s"
RESTART_BACKOFF_INITIAL_SEC = 1
RESTART_BACKOFF_MAX_SEC = 30
RESTART_BACKOFF_RESET_RUNTIME_SEC = 60
CHILD_SHUTDOWN_TIMEOUT_SEC = 5

SCHEME = """<scheme>
    <title>Userful Embedded Dashboards</title>
    <description>Configure embedded dashboards for Splunk.</description>
    <endpoint>
        <args>
            <arg name="username">
                <title>Splunk Username</title>
                <description>This is the local Splunk user name to be used to login
                </description>
            </arg>
            <arg name="connect_from">
                <title>The IP that is allowed to connect</title>
                <description>This is the IP of the client that will connect and display the dashboard.</description>
            </arg>
            <arg name="port">
                <title>The port we are using to connect to</title>
                <description>This is the port the Userful proxy will listen on.</description>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def do_scheme():
    """show a different setup screen"""
    print(SCHEME)


def validate_arguments():
    """validate setup values from Splunk and fail fast on invalid config"""
    try:
        config = {}
        input_xml = sys.stdin.read().strip()
        if input_xml:
            doc = xml.dom.minidom.parseString(input_xml)
            params = doc.getElementsByTagName("param")
            for param in params:
                name = param.getAttribute("name")
                if (
                    name
                    and param.firstChild
                    and param.firstChild.nodeType == param.firstChild.TEXT_NODE
                ):
                    config[name] = param.firstChild.data
        if config:
            normalize_and_validate_config(config)
        print("<validation><status>success</status></validation>")
    except Exception as exc:
        print(
            "<validation><status>failure</status><message>%s</message></validation>"
            % xml_escape(str(exc))
        )
        sys.exit(1)


def xml_escape(value):
    """escape XML entities for validation output"""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def get_config():
    """read XML configuration passed from splunkd"""
    try:
        config = {}
        # read everything from stdin
        config_str = sys.stdin.read()
        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            logging.debug("XML: found configuration")
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    logging.debug("XML: found stanza " + stanza_name)
                    config["name"] = stanza_name
                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        logging.debug("XML: found param '%s'" % param_name)
                        if param_name and param.firstChild and param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            logging.debug("XML: '%s' -> '%s'" % (param_name, data))

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config["checkpoint_dir"] = checkpnt_node.firstChild.data
        if not config:
            raise Exception("Invalid configuration received from Splunk.")
    except Exception as exc:
        raise Exception("Error getting Splunk configuration via STDIN: %s" % str(exc))

    return config

def normalize_and_validate_config(config):
    """normalize config values and enforce required arguments"""
    required = ("username", "connect_from", "port")
    missing = [key for key in required if not str(config.get(key, "")).strip()]
    if missing:
        raise Exception("Missing required input values: %s" % ", ".join(missing))

    username = str(config["username"]).strip()
    connect_from = str(config["connect_from"]).strip()
    port_raw = str(config["port"]).strip()
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise Exception("Invalid port '%s': must be an integer" % port_raw) from exc

    if port < 1 or port > 65535:
        raise Exception("Invalid port '%s': must be between 1 and 65535" % port_raw)

    config["username"] = username
    config["connect_from"] = connect_from
    config["port"] = str(port)
    return config


def join_env_path(*parts):
    """join env path fragments without empty entries"""
    clean = [part for part in parts if part]
    return ":".join(clean)


def is_process_alive(pid):
    """check if pid exists"""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def terminate_process(pid, timeout_sec=CHILD_SHUTDOWN_TIMEOUT_SEC):
    """terminate a process with a timeout and final SIGKILL fallback"""
    if not is_process_alive(pid):
        return

    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        return

    deadline = time.time() + max(timeout_sec, 0)
    while time.time() < deadline:
        if not is_process_alive(pid):
            return
        time.sleep(0.1)

    if is_process_alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass


def remove_pidfile(pidfile):
    """remove a stale pidfile if present"""
    try:
        os.remove(pidfile)
    except FileNotFoundError:
        return
    except Exception:
        pass


def kill_prior_proxy_instances(config, pidfile):
    """
    Kill any prior proxy for this stanza to pick up config changes immediately,
    even if port or IP changed.
    """
    if os.path.exists(pidfile):
        try:
            with open(pidfile, encoding="utf-8") as pid_handle:
                old_pid = int(pid_handle.read().strip())
            terminate_process(old_pid)
        except Exception:
            pass
        remove_pidfile(pidfile)

    # Fall back to scanning for lingering dash-proxy.js instances on this port.
    try:
        port_re = re.compile(r"\bdash-proxy\.js\b.*\b%s\b" % re.escape(config["port"]))
        ps_out = subprocess.check_output(
            ["ps", "-eo", "pid,args"], text=True, errors="ignore"
        )
        for line in ps_out.splitlines():
            if not port_re.search(line):
                continue
            try:
                old_pid = int(line.strip().split()[0])
                terminate_process(old_pid)
            except Exception:
                pass
    except Exception:
        pass

    time.sleep(0.3)


class ProxySupervisor:
    """Keeps dash-proxy.js running and restarts it on crashes."""

    def __init__(self, config):
        self.config = config
        self.stanza = config.get("name", "default")
        self.pidfile_dir = config.get("checkpoint_dir") or my_path
        self.pidfile = os.path.join(self.pidfile_dir, f"userful_proxy_{self.stanza}.pid")
        self.proc = None
        self.stopping = False

    def handle_signal(self, signum, _frame):
        logging.info("received signal=%s, stopping proxy supervisor", signum)
        self.stopping = True
        self.stop_child()

    def write_pidfile(self, pid):
        os.makedirs(self.pidfile_dir, exist_ok=True)
        with open(self.pidfile, "w", encoding="utf-8") as pid_handle:
            pid_handle.write(str(pid))

    def build_child_env(self):
        env = os.environ.copy()
        env["NODE_PATH"] = join_env_path(env.get("NODE_PATH", ""), my_path)
        env["LD_LIBRARY_PATH"] = join_env_path(
            "/opt/openssl-3/lib64",
            env.get("LD_LIBRARY_PATH", ""),
            f"{SPLUNK_HOME}/lib",
        )
        return env

    def start_child(self):
        args = [
            f"{SPLUNK_HOME}/bin/splunk",
            "cmd",
            "node",
            f"{my_path}/dash-proxy.js",
            self.config["username"],
            self.config["port"],
            self.config["connect_from"],
        ]
        self.proc = subprocess.Popen(args, env=self.build_child_env())
        self.write_pidfile(self.proc.pid)
        logging.info(
            "started dash-proxy.js pid=%s stanza=%s port=%s",
            self.proc.pid,
            self.stanza,
            self.config["port"],
        )

    def stop_child(self):
        if self.proc is None:
            return
        if self.proc.poll() is not None:
            return

        try:
            self.proc.terminate()
            self.proc.wait(timeout=CHILD_SHUTDOWN_TIMEOUT_SEC)
        except subprocess.TimeoutExpired:
            try:
                self.proc.kill()
                self.proc.wait(timeout=1)
            except Exception:
                pass
        except Exception:
            pass

    def sleep_with_stop(self, seconds):
        deadline = time.time() + max(seconds, 0)
        while time.time() < deadline:
            if self.stopping:
                return
            time.sleep(0.2)

    def run(self):
        os.makedirs(self.pidfile_dir, exist_ok=True)
        kill_prior_proxy_instances(self.config, self.pidfile)

        restart_backoff_sec = RESTART_BACKOFF_INITIAL_SEC
        while not self.stopping:
            self.start_child()
            started_at = time.time()

            while not self.stopping:
                return_code = self.proc.poll()
                if return_code is None:
                    time.sleep(0.5)
                    continue

                runtime_sec = time.time() - started_at
                remove_pidfile(self.pidfile)
                if self.stopping:
                    break

                logging.error(
                    "dash-proxy.js exited rc=%s after %.1fs; restarting in %ss",
                    return_code,
                    runtime_sec,
                    restart_backoff_sec,
                )
                self.sleep_with_stop(restart_backoff_sec)
                if runtime_sec >= RESTART_BACKOFF_RESET_RUNTIME_SEC:
                    restart_backoff_sec = RESTART_BACKOFF_INITIAL_SEC
                else:
                    restart_backoff_sec = min(
                        restart_backoff_sec * 2, RESTART_BACKOFF_MAX_SEC
                    )
                break

        self.stop_child()
        remove_pidfile(self.pidfile)
        logging.info("proxy supervisor stopped stanza=%s", self.stanza)


def run_main():
    """start supervisor and keep proxy alive"""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    config = normalize_and_validate_config(get_config())
    supervisor = ProxySupervisor(config)
    signal.signal(signal.SIGTERM, supervisor.handle_signal)
    signal.signal(signal.SIGINT, supervisor.handle_signal)
    supervisor.run()


if __name__ == "__main__":
    """Script must implement these args: scheme, validate-arguments."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_arguments()
        else:
            sys.exit(0)
    else:
        run_main()
