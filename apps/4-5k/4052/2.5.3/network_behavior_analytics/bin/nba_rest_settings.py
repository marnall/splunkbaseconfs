import sys

# add nba bin to sys.path so we can use nbalib package
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'network_behavior_analytics', 'bin']))

import os
import json
import time
import zipfile
import datetime

from contextlib import closing
import splunk.rest

from nbalib import validators
from nbalib import sections
from nbalib import confs
from nbalib import rest
from nbalib import logger
from nbalib import alerts
from nbalib import period

from nbalib.asoc3.six.moves import urllib_parse
from nbalib.asoc3 import six

MAX_MODULE_NOT_WORKING_MINUTES = 30
MIN_LOG_FILE_BYTES = 300000


class ConfigProxy(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        try:
            sp = confs.StoragePasswords(self.sessionKey)
            config = confs.Config(self.sessionKey)

            payload = {
                'address': config.get('proxy_address', ''),
                'credentials': config.get('proxy_requires_password', '0'),
                'username': config.get('proxy_username', ''),
                'password': sp.get('asoc_nba_proxy_password'),
            }
        except:
            rest.Response.error(self.response, "Unable to get proxy details from configuration files.")
            return

        rest.Response.set(self.response, payload)

    def handle_POST(self):
        try:
            address = self.clean_address(self.args.get('address', ''))
            credentials = self.clean_checkbox(self.args.get('credentials', '0'))

            username = self.clean_credentials(self.args.get('username', ''), 'username')
            password = self.clean_credentials(self.args.get('password', ''), 'password')
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        if not address and credentials:
            rest.Response.error(self.response, "Please provide a valid proxy address.")
            return

        try:
            self.save_proxy(address, credentials, username, password)
        except:
            rest.Response.error(self.response, "Unable to save proxy details in configuration files.")
            return

        rest.Response.set(self.response, {})

    @staticmethod
    def clean_address(address):
        if not isinstance(address, six.string_types):
            raise ValueError('Parameter "address" has invalid format.')

        address = address.strip()
        if address:
            parts = urllib_parse.urlsplit(address)
            if not parts.scheme:
                raise ValueError('Proxy address must include the protocol (eg. http://).')

            if not parts.netloc:
                raise ValueError('Proxy address must include a valid hostname.')

            if parts.username or parts.password:
                raise ValueError('Please use suitable form fields for proxy credentials.')

        return address

    @staticmethod
    def clean_checkbox(value):
        if not isinstance(value, six.string_types):
            raise ValueError('Parameter "requires_password" has invalid format.')

        return value == '1'

    @staticmethod
    def clean_credentials(value, param_label):
        if not isinstance(value, six.string_types):
            raise ValueError('Parameter "{0}" has invalid format.'.format(param_label))

        return value

    def save_proxy(self, address, credentials, username, password):
        sp = confs.StoragePasswords(self.sessionKey)
        config = confs.Config(self.sessionKey)

        config.begin_batch()
        config.set('proxy_requires_password', credentials)
        config.set('proxy_address', address)
        config.set('proxy_username', username)

        sp.set('asoc_nba_proxy_password', password)

        config.commit()


class LogsIndex(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        section = self.args.get('section', '')
        try:
            validators.Sections.check_data_section(section)
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        try:
            config = confs.Config(self.sessionKey, stanza=section)
            payload = {'index': config.get('logs_index', '')}
        except:
            rest.Response.error(self.response, "Unable to get index from configuration file.")
            return

        rest.Response.set(self.response, payload)

    def handle_POST(self):
        index = self.args.get('index', '')
        section = self.args.get('section', '')

        try:
            validators.Sections.check_data_section(section)
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        if not isinstance(index, six.string_types):
            rest.Response.error(self.response, "Index name is invalid.")
            return

        try:
            macro = self._split_validate(index)
        except ValueError as exc:
            rest.Response.error(self.response, str(exc))
            return

        try:
            self._update_configs(index, macro, section)
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        rest.Response.set(self.response, {})

    def _split_validate(self, index):
        indexes = index.split(',')

        elements = len(indexes)
        if elements == 0 or (elements == 1 and indexes[0] == ""):
            return "index=*"

        for i, name in enumerate(indexes):
            name = name.strip()
            validators.Args.check_index(name)
            indexes[i] = 'index="{0}"'.format(name)

        if elements == 1:
            return indexes[0]

        return "(" + " OR ".join(indexes) + ")"

    def _update_configs(self, index, macro, section):
        stanza = 'nbalogsindex' + section

        config_macros = confs.Config(self.sessionKey, name='macros', stanza=stanza)
        config_macros.begin_batch()

        config_app = confs.Config(self.sessionKey)
        config_app.begin_batch()

        config_macros.set('definition', macro)
        config_app.set_in_stanza('logs_index', index, stanza=section)

        config_macros.commit()
        config_app.commit()


class EventsIndex(splunk.rest.BaseRestHandler):
    scripts = [
        "script://./bin/nba_sendlog_dns.py",
        "script://.\\bin\\nba_sendlog_dns.py",
        "script://./bin/nba_sendlog_ip.py",
        "script://.\\bin\\nba_sendlog_ip.py",
        "script://./bin/nba_sendlog_http.py",
        "script://.\\bin\\nba_sendlog_http.py",
        "script://./bin/nba_sendlog_dhcp.py",
        "script://.\\bin\\nba_sendlog_dhcp.py",
        "script://./bin/nba_sendlog_tls.py",
        "script://.\\bin\\nba_sendlog_tls.py",
        "script://./bin/nba_sendlog_vpn.py",
        "script://.\\bin\\nba_sendlog_vpn.py",
        "script://./bin/nba_scorer.py",
        "script://.\\bin\\nba_scorer.py",
    ]

    def handle_GET(self):
        try:
            config = confs.Config(self.sessionKey, stanza=sections.Alerts.name)
            payload = {'index': config.get('events_index', '')}
        except:
            rest.Response.error(self.response, "Unable to get alerts index from configuration file.")
            return

        rest.Response.set(self.response, payload)

    def handle_POST(self):
        index = self.args.get('index', '')

        if not isinstance(index, six.string_types):
            rest.Response.error(self.response, "Alerts index name is invalid.")
            return

        index = index.strip()
        if not index:
            rest.Response.error(self.response, "Alerts index name is required.")
            return

        try:
            validators.Args.check_index(index)
        except ValueError as exc:
            rest.Response.error(self.response, str(exc))
            return

        try:
            self._update_configs(index)
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        rest.Response.set(self.response, {})

    def _update_configs(self, index):
        config_inputs = confs.Config(self.sessionKey, name='inputs')
        config_inputs.begin_batch()

        config_macros = confs.Config(self.sessionKey, name='macros', stanza='nbaeventsindex')
        config_macros.begin_batch()

        config_app = confs.Config(self.sessionKey, stanza=sections.Alerts.name)
        config_app.begin_batch()

        self._update_inputs_config(index, config_inputs)
        self._update_macros_config(index, config_macros)
        self._update_app_config(index, config_app)

        config_inputs.commit()
        config_macros.commit()

        error_msg = self._refresh()
        config_app.commit()

        if error_msg:
            raise ValueError(error_msg)

    def _update_inputs_config(self, name, config):
        for script in self.scripts:
            config.set_in_stanza('index', name, stanza=script)

    @staticmethod
    def _update_macros_config(name, config):
        macro_definition = 'index="{0}" sourcetype="asoc:nba:event"'.format(name)
        config.set('definition', macro_definition)

    @staticmethod
    def _update_app_config(name, config):
        config.set('events_index', name)

    def _refresh(self):
        try:
            resp, _ = splunk.rest.simpleRequest(
                "/services/data/inputs/script/_reload",
                sessionKey=self.sessionKey,
                method='POST'
            )
        except:
            resp = None

        if not resp or resp.status != 200:
            return "Error reloading configuration. Please reload Splunk manually."

        return None


class PullIndex(splunk.rest.BaseRestHandler):
    section = sections.Destinations.name
    macroName = "nbadestsummary"
    macroSourceType = "asoc:nba:dest:summary"
    scripts = [
        "script://./bin/nba_dest_pull.py",
        "script://.\\bin\\nba_dest_pull.py",
    ]

    def handle_GET(self):
        try:
            config = confs.Config(self.sessionKey, stanza=self.section)
            payload = {"index": config.get("index", "")}
        except:
            rest.Response.error(self.response, "Unable to get index from configuration file.")
            return

        rest.Response.set(self.response, payload)

    def handle_POST(self):
        index = self.args.get("index", "")
        if not isinstance(index, six.string_types):
            rest.Response.error(self.response, "Index name is invalid.")
            return

        index = index.strip()
        if not index:
            rest.Response.error(self.response, "Index name is required.")
            return

        try:
            validators.Args.check_index(index)
        except ValueError as exc:
            rest.Response.error(self.response, str(exc))
            return

        try:
            self._update_configs(index)
        except ValueError as exc:
            rest.Response.error(self.response, str(exc))
            return
        except Exception as exc:
            rest.Response.error(self.response, "Unexpected error: unable to update configuration file.")
            return

        rest.Response.set(self.response, {})

    def _update_configs(self, index):
        config_inputs = confs.Config(self.sessionKey, name='inputs')
        config_inputs.begin_batch()

        config_macros = confs.Config(self.sessionKey, name='macros', stanza=self.macroName)
        config_macros.begin_batch()

        config_app = confs.Config(self.sessionKey, stanza=self.section)
        config_app.begin_batch()

        self._update_inputs_config(config_inputs, index)
        self._update_macros_config(config_macros, index)
        self._update_app_config(config_app, index)

        config_inputs.commit()
        config_macros.commit()

        error_msg = self._refresh()
        config_app.commit()

        if error_msg:
            raise ValueError(error_msg)

    def _update_inputs_config(self, config, name):
        for script in self.scripts:
            config.set_in_stanza('index', name, stanza=script)

    def _update_macros_config(self, config, name):
        macro_definition = 'index="{0}" sourcetype="{1}"'.format(name, self.macroSourceType)
        config.set('definition', macro_definition)

    @staticmethod
    def _update_app_config(config, name):
        config.set('index', name)

    def _refresh(self):
        try:
            resp, _ = splunk.rest.simpleRequest(
                "/services/data/inputs/script/_reload",
                sessionKey=self.sessionKey,
                method='POST'
            )
        except:
            resp = None

        if not resp or resp.status != 200:
            return "Error reloading configuration. Please reload Splunk manually."

        return None


class DataStatus(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        mode = self.args.get('mode', '')
        if mode == "notify":
            self.status_notify()
        else:
            self.status_full()

    def status_notify(self):
        non_empty_sections = []

        try:
            for section in validators.Sections.data:
                messages = self.section_messages(section)
                if messages:
                    non_empty_sections.append(section)

            rest.Response.set(self.response, {'sections': non_empty_sections})
        except:
            rest.Response.error(self.response, "Unable to get data status messages from configuration file.")

    def status_full(self):
        section = self.args.get('section', '')
        try:
            validators.Sections.check_app_section(section)
        except Exception as exc:
            rest.Response.error(self.response, str(exc))
            return

        try:
            response = {"messages": self.section_messages(section)}
            if section in validators.Sections.data:
                backlog = self.section_backlog(section)
                response["max_backlog"] = backlog[0]
                response["backlog"] = backlog[1]

            rest.Response.set(self.response, response)
        except:
            rest.Response.error(self.response, "Unable to get data status messages from configuration file.")

    def section_backlog(self, section):
        config = confs.Config(self.sessionKey, stanza=section)

        max_backlog = config.get_from_stanza("sendlog_max_backlog_seconds", stanza=sections.NBA.stanza)
        backlog = config.get("backlog")

        try:
            max_backlog = int(max_backlog)
        except (TypeError, ValueError):
            max_backlog = period.DEFAULT_MAX_BACKLOG_SECONDS

        if not isinstance(max_backlog, int) or max_backlog < 0:
            max_backlog = period.DEFAULT_MAX_BACKLOG_SECONDS

        try:
            backlog = int(backlog)
        except (TypeError, ValueError):
            backlog = 0

        if not isinstance(backlog, int) or backlog < 0:
            backlog = 0

        return (max_backlog, backlog)

    def section_messages(self, section):
        config = confs.Config(self.sessionKey, stanza=section)
        is_cloud = validators.Splunk.is_cloud_instance(self.sessionKey)

        if not validators.Permissions.is_config_writable(self.sessionKey):
            messages = [logger.MessageConfigNotWritable().dumps()]
        elif not config.is_enabled('enabled', default=True):
            if section == sections.Destinations.name:
                messages = [logger.MessageDisabledPull().dumps()]
            else:
                messages = [logger.MessageDisabled().dumps()]
        elif is_cloud and not validators.Splunk.are_inputs_enabled(self.sessionKey):
            messages = [logger.MessageCloudBrokenInputs().dumps()]
        else:
            raw_messages = config.get('data_messages', [])
            messages = json.loads(raw_messages)
            if not isinstance(messages, list):
                raise ValueError()

            if not self.is_module_working(config):
                messages.append(logger.MessageNotWorking().dumps())

        return messages

    @staticmethod
    def is_module_working(config):
        try:
            last_runtime = config.get('last_runtime')
            since_last_runtime = int(time.time()) - int(last_runtime)
            return since_last_runtime <= MAX_MODULE_NOT_WORKING_MINUTES * 60
        except:
            return True


class SendlogSettings(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        try:
            config = confs.Config(self.sessionKey, stanza=sections.NBA.stanza)
            max_backlog = config.get('sendlog_max_backlog_seconds', None)
        except:
            rest.Response.error(self.response, "Unable to get max backlog value from configuration file.")
            return

        try:
            max_backlog = int(max_backlog)
        except (TypeError, ValueError):
            max_backlog = None

        if not isinstance(max_backlog, int) or max_backlog < 0:
            max_backlog = period.DEFAULT_MAX_BACKLOG_SECONDS

        rest.Response.set(self.response, {'max_backlog': max_backlog})

    def handle_POST(self):
        try:
            max_backlog = int(self.args.get("max_backlog", None))
        except (ValueError, TypeError):
            rest.Response.error(
                self.response,
                "Invalid max backlog value. It must be an integer.",
            )
            return

        if max_backlog is None or not isinstance(max_backlog, int) or max_backlog < 0:
            rest.Response.error(
                self.response,
                "Invalid max backlog value. It must be greater than or equal to zero.",
            )
            return
        elif max_backlog > period.MAX_BACKLOG_SECONDS:
            rest.Response.error(
                self.response,
                "Invalid max backlog value. It must be less than or equal to {0} seconds.".format(
                    period.MAX_BACKLOG_SECONDS
                ),
            )
            return

        try:
            config = confs.Config(self.sessionKey, stanza=sections.NBA.stanza)
            config.set("sendlog_max_backlog_seconds", max_backlog)
        except:
            rest.Response.error(
                self.response,
                "Unable to update max backlog value in configuration file.",
            )
            return

        rest.Response.set(self.response, {})


class LogsExport(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        file_name = "alphasoc-nba-logs-{0}.zip".format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        self.set_headers(file_name)

        log_files = self.get_log_files()
        with closing(six.BytesIO()) as output:
            with zipfile.ZipFile(output, mode='w', compression=zipfile.ZIP_DEFLATED) as zipped:
                for log_file in log_files:
                    zipped.write(log_file, arcname=os.path.basename(log_file))

            self.response.write(output.getvalue())

    def set_headers(self, file_name):
        self.response.setStatus(200)
        self.response.setHeader('content-type', 'application/zip')
        self.response.setHeader('content-disposition', 'attachment; filename="{0}"'.format(file_name))

    def get_log_files(self):
        processes = [
            "sendlog_dns", "sendlog_ip", "sendlog_http",
            "sendlog_dhcp", "sendlog_tls", "sendlog_vpn",
            "scorer", "dest_pull"
        ]
        log_files = []

        for process_name in processes:
            log_files += self.get_process_log_files(process_name)

        return log_files

    @staticmethod
    def get_process_log_files(name):
        log_files = []

        log_id = logger.Logger.get_id(sections.NBA.name, name)
        log_file = logger.Logger.get_path(log_id)
        if not os.path.isfile(log_file):
            return log_files
        log_files.append(log_file)

        log_size = os.stat(log_file).st_size
        if log_size < MIN_LOG_FILE_BYTES:
            log_file_rotated = "{0}.1".format(log_file)
            if os.path.isfile(log_file_rotated):
                log_files.append(log_file_rotated)

        return log_files


class SourceDisplay(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        sds = alerts.SourceDisplayStorage(self.sessionKey)

        try:
            sdtype = sds.get_type()
        except alerts.InvalidSourceDisplayType:
            rest.Response.error(self.response, "Unrecognized source display mode.", code=404)
            return
        except:
            rest.Response.error(self.response, "Unable to load source display type from configuration file.")
            return

        rest.Response.set(self.response, {"type": sdtype})

    def handle_POST(self):
        sds = alerts.SourceDisplayStorage(self.sessionKey)
        sdtype = self.args.get("type", "")

        try:
            sds.save(sdtype)
        except alerts.InvalidSourceDisplayType:
            rest.Response.error(self.response, "Invalid source display type.")
            return
        except:
            rest.Response.error(self.response, "Unable to update source display type in configuration file.")
            return

        rest.Response.set(self.response, {})


class InputsUser(splunk.rest.BaseRestHandler):
    scripts = [
        "script://./bin/nba_sendlog_dns.py",
        "script://.\\bin\\nba_sendlog_dns.py",
        "script://./bin/nba_sendlog_ip.py",
        "script://.\\bin\\nba_sendlog_ip.py",
        "script://./bin/nba_sendlog_http.py",
        "script://.\\bin\\nba_sendlog_http.py",
        "script://./bin/nba_sendlog_dhcp.py",
        "script://.\\bin\\nba_sendlog_dhcp.py",
        "script://./bin/nba_sendlog_tls.py",
        "script://.\\bin\\nba_sendlog_tls.py",
        "script://./bin/nba_sendlog_vpn.py",
        "script://.\\bin\\nba_sendlog_vpn.py",
        "script://./bin/nba_scorer.py",
        "script://.\\bin\\nba_scorer.py",
        "script://./bin/nba_dest_pull.py",
        "script://.\\bin\\nba_dest_pull.py",
    ]

    def handle_GET(self):
        payload = {}

        try:
            config = confs.Config(self.sessionKey)
            payload["username"] = config.get("inputs_username", "")
        except:
            rest.Response.error(self.response, "Unable to get username from configuration file.")
            return

        rest.Response.set(self.response, payload)

    def handle_POST(self):
        username = self.args.get("username", "")
        if not isinstance(username, six.string_types):
            rest.Response.error(self.response, "Username name is invalid.")
            return

        username = username.strip()
        if not username:
            rest.Response.error(self.response, "Username name is required.")
            return

        try:
            self._update_configs(username)
        except ValueError as exc:
            rest.Response.error(self.response, str(exc))
            return
        except:
            rest.Response.error(self.response, "Unexpected error: unable to update configuration file.")
            return

        rest.Response.set(self.response, {})

    def _update_configs(self, username):
        config_inputs = confs.Config(self.sessionKey, name='inputs')
        config_inputs.begin_batch()

        config_app = confs.Config(self.sessionKey)
        config_app.begin_batch()

        for script in self.scripts:
            config_inputs.set_in_stanza('passAuth', username, stanza=script)

        config_app.set('inputs_username', username)

        config_inputs.commit()
        config_app.commit()
