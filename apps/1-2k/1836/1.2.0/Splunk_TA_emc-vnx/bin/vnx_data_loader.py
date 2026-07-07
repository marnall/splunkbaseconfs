#!/usr/bin/python

"""
This is the main entry point for VNX TA
"""

import sys
import os
import os.path as op
import ConfigParser
import traceback

import data_loader as dl
import job_factory as jf
import configure as conf


_LOGGER = conf.setup_logging("ta_vnx")


def do_scheme():
    """
    Feed splunkd the TA's scheme
    """

    print """
    <scheme>
    <title>EMC TA</title>
    <description>EMC TA</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>true</use_single_instance>
    <endpoint>
      <args>
        <arg name="name">
          <title>Unique stanza name for differentiation</title>
        </arg>
        <arg name="network_addr">
          <title>IP or DNS hostname of the endpoint for data collection</title>
        </arg>
        <arg name="network_addr2">
          <title>Secondary IP or DNS hostname of the endpoint for data collection</title>
        </arg>
        <arg name="username">
          <title>Login username</title>
        </arg>
        <arg name="password">
          <title>Login password</title>
        </arg>
        <arg name="platform">
          <title>VNX File/VNX Block</title>
        </arg>
        <arg name="site">
          <title>Location information of VNX</title>
        </arg>
        <arg name="loglevel">
          <title>Logging level</title>
        </arg>
      </args>
    </endpoint>
    </scheme>
    """


class VnxConfig(object):
    """
    Handles VNX related config, password encryption/decryption
    """

    encrypted = "<encrypted>"
    username_password_sep = "``"

    def __init__(self):
        import credentials as cred

        meta_configs, modinput_configs = self.get_modinput_configs()
        self.meta_configs = meta_configs
        self.modinput_configs = modinput_configs
        self.cred_manager = cred.CredentialManager(meta_configs["session_key"],
                                                   meta_configs["server_uri"])
        self.app_dir = op.dirname(op.dirname(op.abspath(__file__)))
        self.app = op.basename(self.app_dir)
        user_credentials = self.cred_manager.get_all_user_credentials(self.app)
        self.user_credentials = user_credentials
        self._clean_stale_credentials()
        self._encrypt_new_credentials()
        self._decrypt_existing_credentials()
        default_collection_configs = self._get_default_collection_configs()
        self.stanza_configs = self._merge_configs(default_collection_configs)

    @staticmethod
    def get_modinput_configs():
        """
        Get modinput from stdin which is feed by splunkd
        """

        try:
            config_str = sys.stdin.read()
        except Exception:
            _LOGGER.error(traceback.format_exc())
            raise

        return conf.parse_modinput_configs(config_str)

    @staticmethod
    def _get_default_collection_configs():
        """
        Get default collection configuration of this TA
        If default/ta_vnx_collection.conf doesn't contain the default config
        assign the default configuration
        """

        parser = ConfigParser.ConfigParser()
        app_dir = op.dirname(op.dirname(op.abspath(__file__)))
        interval_conf = op.join(app_dir, "local", "ta_vnx_collection.conf")
        if not op.exists(interval_conf):
            _LOGGER.info("Didn't find local/ta_vnx_collection.conf. "
                         "Use default/ta_vnx_collection.conf")
            interval_conf = op.join(app_dir, "default",
                                    "ta_vnx_collection.conf")
        parser.read(interval_conf)

        # collect category interval name, default interval, default priority
        defaults = (("vnx_file_inventory_interval", 3600, 10),
                    ("vnx_file_sys_performance_interval", 120, 9),
                    ("vnx_file_nfs_performance_interval", 120, 8),
                    ("vnx_file_cifs_performance_interval", 120, 8),
                    ("vnx_block_performance_interval", 120, 8),
                    ("vnx_block_inventory_interval", 3600, 10),
                    ("vnx_block_status_interval", 300, 9))

        default_configs = {}
        for default in defaults:
            try:
                interval = parser.getint("default", default[0])
                default_configs[default[0]] = (interval, default[-1])
            except ConfigParser.NoOptionError:
                default_configs[default[0]] = (default[1], default[-1])
        return default_configs

    def _merge_configs(self, default_collection_configs):
        """
        @default_collection_configs: default collection configs
        """

        platform_metrics = {
            "VNX File": ("vnx_file_inventory", "vnx_file_sys_performance",
                         "vnx_file_nfs_performance",
                         "vnx_file_cifs_performance"),
            "VNX Block": ("vnx_block_performance", "vnx_block_inventory",
                          "vnx_block_status"),
        }

        configs = []
        for modinput_config in self.modinput_configs:
            if all((tag in modinput_config for tag in
                    ("metric_type", "duration", "priority"))):
                # this is a customized config
                modinput_config["duration"] = int(modinput_config["duration"])
                modinput_config["priority"] = int(modinput_config["priority"])
                configs.append(modinput_config)
                continue

            platform = modinput_config["platform"]
            for metric in platform_metrics.get(platform, ()):
                config = {}
                config.update(modinput_config)
                config["metric_type"] = metric
                interval_key = metric + "_interval"
                duration_priority = default_collection_configs[interval_key]
                config["duration"], config["priority"] = duration_priority
                configs.append(config)
        return configs

    def _clean_stale_credentials(self):
        """
        Remove the user credentials from splunkd if it isn't in inputs.conf
        @use_credentials are from splunkd
        @modinput_configs are from local/inputs.conf
        @return None
        """
        for i, user_cred in self.user_credentials:
            for mod_config in self.modinput_configs:
                if user_cred["realm"] == mod_config["network_addr"]:
                    break
            else:
                # not in inputs.conf, remove
                deleted = self.cred_manager.delete(user_cred["realm"],
                                                   user_cred["username"],
                                                   self.app)
                if deleted:
                    _LOGGER.info("Clean staled user credential for %s",
                                 user_cred["realm"])
                else:
                    _LOGGER.error("Failed to clean user credential for %s",
                                  user_cred["realm"])

    def _encrypt_new_credentials(self):
        """
        Encrypt the user credentials if it is new inputs.conf
        Update the user credentials if it exists in splunkd and inputs.conf
        Encrypt strategy is encrypting both username and password. Splunkd only
        encrypt password, the code works around this by concatenating username
        and password by "``" and treat the concantenated string as password,
        then encrypt the concatenated string. Username is given as "dummy"
        @return None
        """

        encrypted = self.encrypted
        sep = self.username_password_sep
        found_clear_credential = False
        encrypted_credentials = set()

        for mod_config in self.modinput_configs:
            network_addr = mod_config["network_addr"]
            if network_addr in encrypted_credentials:
                _LOGGER.warn("%s is already encrypted, will skip encrypting "
                             "it again in Splunk. If this is an mistake, "
                             "please remove it from local/inputs.conf, "
                             "otherwise it may cause duplicate data "
                             "collection.", network_addr)
                continue
            username, password = mod_config["username"], mod_config["password"]
            user_password = sep.join((username, password))

            for i, user_cred in self.user_credentials:
                if user_cred["realm"] == network_addr:
                    if username == encrypted and password == encrypted:
                        pass
                    elif username != encrypted and password != encrypted:
                        self.cred_manager.update(network_addr, "dummy",
                                                 user_password, self.app)
                        _LOGGER.info("Update credential for %s", network_addr)
                        found_clear_credential = True
                        encrypted_credentials.add(network_addr)
                    else:
                        raise Exception("Invalid config %s: %s. Both usename"
                                        "and password shall be <encrypted> or "
                                        "shall neither of them be."
                                        % (username, password))
                    break

            else:
                if username != encrypted and password != encrypted:
                    # new user credential in inputs.conf, shall be plain text
                    # credentials
                    self.cred_manager.create(network_addr, "dummy",
                                             user_password, self.app)
                    _LOGGER.info("Encrypt credential for %s", network_addr)
                    found_clear_credential = True
                else:
                    raise Exception("Invalid config %s: %s. Detect %s is a "
                                    "new entry in local/inputs.conf, but "
                                    "either username or password is set to "
                                    "<encrypted>. Both shall not be set to "
                                    "<encrypted> when the entry is new."
                                    % (username, password, network_addr))

        if found_clear_credential:
            self._encrypt_inputs_conf()

    def _encrypt_inputs_conf(self):
        """
        Encrypt username/password in local/inputs.conf
        """

        inputs_conf = op.join(self.app_dir, "local", "inputs.conf")
        new_cp = ConfigParser.ConfigParser()
        parser = ConfigParser.ConfigParser()
        parser.read(inputs_conf)
        for section in parser.sections():
            new_cp.add_section(section)
            for option in parser.options(section):
                if option in ("username", "password"):
                    op_val = self.encrypted
                else:
                    op_val = parser.get(section, option)
                new_cp.set(section, option, op_val)

        encrypted_inputs = op.join(self.app_dir, "local", ".inputs.conf.new")
        with open(encrypted_inputs, "w") as new_file:
            new_cp.write(new_file)

        os.rename(inputs_conf, inputs_conf + ".old")
        os.rename(encrypted_inputs, inputs_conf)
        os.remove(inputs_conf + ".old")

    def _decrypt_existing_credentials(self):
        """
        Decrypt the user credentials if it is encrypted in inputs.conf
        @return None
        """

        encrypted = self.encrypted
        sep = self.username_password_sep

        for mod_config in self.modinput_configs:
            network_addr = mod_config["network_addr"]
            username, password = mod_config["username"], mod_config["password"]
            if username == encrypted and password == encrypted:
                password = self.cred_manager.get_clear_password(network_addr,
                                                                "dummy",
                                                                self.app)
                if password is None:
                    raise Exception("Either database curruption or invalid "
                                    "configuration in local/inputs.conf. "
                                    "%s shows encrypted username/password, "
                                    "but failed to get this entry in splunkd. "
                                    "If the latter case, remove this invalid "
                                    "configuration from local/inputs.conf"
                                    % network_addr)
                username, password = password.split(sep)
                mod_config["username"] = username
                mod_config["password"] = password


def _setup_signal_handler(data_loader):
    """
    Setup signal handlers
    @data_loader: data_loader.DataLoader instance
    """

    import signal

    def _handle_exit(signum, frame):
        _LOGGER.info("VNX TA is going to exit...")
        data_loader.tear_down()

    signal.signal(signal.SIGTERM, _handle_exit)
    signal.signal(signal.SIGINT, _handle_exit)


def run():
    """
    Main loop. Run this TA for ever
    """

    _LOGGER.info("Start VNX TA")
    try:
        vnx_conf = VnxConfig()
    except Exception as ex:
        _LOGGER.error("Failed to setup config for VNX TA: %s", ex.message)
        _LOGGER.error(traceback.format_exc())
        raise

    if vnx_conf.stanza_configs:
        loglevel = vnx_conf.stanza_configs[0].get("loglevel", "INFO")
        if loglevel != "INFO":
            conf.setup_logging("ta_vnx", loglevel)
            conf.setup_logging("data_loader", loglevel)
    else:
        _LOGGER.info("No data collection for VNX is found in the inputs.conf. "
                     "Do nothing and Quit the TA")
        return

    data_loader = dl.GlobalDataLoader.get_data_loader(vnx_conf.meta_configs,
                                                      vnx_conf.stanza_configs,
                                                      jf.JobFactory())
    _setup_signal_handler(data_loader)
    data_loader.run()
    _LOGGER.info("End VNX TA")


def print_supported_metric_types():
    """
    Print supported metric types of this TA
    """

    for vnx in ("VNX File", "VNX Block"):
        metric_types = jf.JobFactory.get_supported_metric_types(vnx)
        for platform, metrics in metric_types.iteritems():
            print "Platform: %s" % platform
            for metric in metrics:
                print "\t%s" % metric
            print "\n"


def validate_config():
    """
    Validate inputs.conf
    """

    _, configs = VnxConfig.get_modinput_configs()
    for config in configs:
        stanza = config["name"]
        if not config.get("network_addr", None):
            raise Exception("Missing network address in stanza: %s" % stanza)

        if not config.get("username", None):
            raise Exception("Missing username in stanza: %s" % stanza)

        if config.get("duration", None):
            try:
                duration = int(config.get("duration"))
            except ValueError:
                raise Exception("duration should be an interger in stanza: %s"
                                % stanza)

            if duration <= 0:
                raise Exception("duration should be an positive interger"
                                " in stanza: %s" % stanza)

        if config.get("priority", None):
            try:
                int(config.get("priority"))
            except ValueError:
                raise Exception("priority should be an interger in stanza: %s"
                                % stanza)

        platform = config.get("platform", None)
        if not platform:
            raise Exception("Missing platform in stanza: %s" % stanza)
        elif platform not in ("VNX File", "VNX Block"):
            raise Exception("Unsupported platform '%s' in stanza: %s."
                            "Only 'VNX File' and 'VNX Block' are valid"
                            % (platform, stanza))

        if platform == "VNX Block" and not config.get("password", None):
            raise Exception("Missing password in stanza: %s" % stanza)

        if platform == "VNX Block" and not config.get("scope", None):
            raise Exception("Missing scope in stanza: %s. By default scope will be set as 0." % stanza)

        elif platform == "VNX Block" and (int(config["scope"])>2 or  int(config["scope"])<0):
            raise Exception("Invalid scope in stanza: %s" % stanza)

        metric_type = config.get("metric_type", None)
        if metric_type:
            metric_types = jf.JobFactory.get_supported_metric_types(platform)
            if metric_type not in metric_types:
                raise Exception("Metric type %s not supported for platform %s "
                                "in stanza: %s. Run"
                                "'--print_supported_metric_types' for valid"
                                "metric types"
                                % (metric_type, platform, stanza))
    sys.exit(0)


def usage():
    """
    Print usage of this binary
    """

    hlp = "%s --scheme|--validate-arguments|--print_supported_metric_types|-h"
    print >> sys.stderr, hlp % sys.argv[0]
    sys.exit(1)


def main():
    """
    Main entry point
    """

    args = sys.argv
    if len(args) > 1:
        if args[1] == "--scheme":
            do_scheme()
        elif args[1] == "--validate-arguments":
            validate_config()
        elif args[1] == "--print_supported_metric_types":
            print_supported_metric_types()
        elif args[1] in ("-h", "--h", "--help"):
            usage()
        else:
            usage()
    else:
        run()
    sys.exit(0)


if __name__ == "__main__":
    main()
