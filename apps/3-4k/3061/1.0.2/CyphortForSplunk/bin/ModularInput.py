"""
Written by Kyle Smith for Aplura, LLC
Copyright (C) 2016 Aplura, ,LLC

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import itertools
import json
import logging as logger
import logging.handlers as handlers
import os
import os.path
import sys
import time
import xml.dom.minidom
import xml.sax.saxutils
from datetime import timedelta, datetime


# Add Additional Imports Here
class Unbuffered:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


class ModularInput:
    """ Base Class for splunk Modular Input """
    """ These are the basic Variables used through out the class """
    _SPLUNK_HOME = os.getenv("SPLUNK_HOME")
    _should_print_debug = False
    _service_checkpoints = {}
    _log_level = logger.INFO
    log = logger
    _config = {}
    _scheme = {}
    _required_schema_arguments = []
    _loaded_checkpoints = {}
    _default_checkpoint_lookback_minutes = 60
    _proxy_config = {}

    # Properties
    @property
    def scheme_title(self):
        return self._scheme["title"]

    @property
    def scheme_description(self):
        return self._scheme["description"]

    @property
    def scheme_args(self):
        return self._scheme["args"]

    @property
    def cim_model(self):
        return self.__cim_model

    @cim_model.setter
    def cim_model(self, x):
        self.__cim_model = x

    @property
    def _use_cim(self):
        return self.__use_cim

    @_use_cim.setter
    def _use_cim(self, x):
        self.__use_cim = x

    @property
    def _splunk_home(self):
        return self.__splunk_home

    @_splunk_home.setter
    def _splunk_home(self, s):
        self.__splunk_home = s

    @property
    def _app_name(self):
        return self.__app_name

    @_app_name.setter
    def _app_name(self, s):
        self.__app_name = s

    @property
    def _app_home(self):
        return self.__app_home

    @_app_home.setter
    def _app_home(self, s):
        self.__app_home = s

    @property
    def _proxy_home(self):
        return self.__proxy_home

    @_proxy_home.setter
    def _proxy_home(self, s):
        self.__proxy_home = s

    # Begin Methods
    def __init__(self, app_name=None, scheme={}, cim_fields=None):
        try:
            self.__splunk_home = None
            if app_name is None:
                raise Exception("App Name not passed to Modular Input")
            self._app_name = app_name
            self._use_cim = False
            self.log.debug("Splunk App Name set: %s" % self._app_name)
            self.source(app_name)
            self.sourcetype(app_name)
            self.host(app_name)
            if self._splunk_home is None:
                self._splunk_home = os.getenv("SPLUNKHOME")
            if self._splunk_home is None:
                self._splunk_home = os.getenv("SPLUNK_HOME")
            if self._splunk_home is None and not os.name == "nt":
                self._splunk_home = os.path.join(os.path.sep, "opt", "splunk")
            if self._splunk_home is None and os.name == "nt":
                self._splunk_home = os.path.join("C:", "Program Files", "Splunk")
            if self._splunk_home is None:
                raise Exception("SPLUNK HOME UNABLE TO BE SET")
            self.log.debug("Splunk Home set: %s" % self._splunk_home)
            self._app_home = os.path.join(self._splunk_home, "etc", "apps", self._app_name)
            self._proxy_home = os.path.join(self._splunk_home, "etc", "splunk-launch.conf")
            self.log.debug("Splunk Proxy set: %s" % self._proxy_home)
            self._setup_logging()
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = {"msg": str((e)),
                      "exception_type": "%s" % type(e).__name__,
                      "exception_arguments": "%s" % e,
                      "filename": fname,
                      "line": exc_tb.tb_lineno
                      }
            raise Exception(myJson)
        self.log.debug("Starting MI __init__ : app_name=%s scheme=%s " % (app_name, scheme))
        self.log.debug("Splunk Home set: %s" % self._app_home)
        self.log.debug("Building Scheme: %s" % scheme)
        self._build_scheme(scheme=scheme)
        if cim_fields is not None:
            self._use_cim = True
            self.cim_model = cim_fields

        sys.stdout = Unbuffered(sys.stdout)

    def set_logger(self, log):
        self.log = log

    def _setup_logging(self):
        logger.Formatter.converter = time.gmtime
        log = logger.Logger(self._app_name)
        log.setLevel(self._log_level)
        log_location = os.path.join(self._splunk_home, "var", "log", "splunk", self._app_name)
        if not os.path.isdir(log_location):
            os.mkdir(log_location)
        output_file_name = os.path.join(log_location, 'modularinput.log')
        handler = self._create_logger_handler(output_file_name, self._log_level)
        log.addHandler(handler)
        self.log = log

    def _create_logger_handler(self, fd, level, max_bytes=10240000, backup_count=5):
        handler = handlers.RotatingFileHandler(fd, maxBytes=max_bytes, backupCount=backup_count)
        handler.setFormatter(logger.Formatter('%(asctime)s [%(levelname)s] [%(filename)s] %(message)s'))
        handler.setLevel(level)
        return handler

    def _apply_cim(self, event):
        for cm in self.cim_model:
            try:
                event[cm] = self.cim_model[cm]
            except:
                pass
        return event

    class Unbuffered:
        def __init__(self, stream):
            self.stream = stream

        def write(self, data):
            self.stream.write(data)
            self.stream.flush()

        def __getattr__(self, attr):
            return getattr(self.stream, attr)

    def _build_scheme(self, scheme={}):
        """ Let's build a scheme for the modular input.
        Keyword arguments:
        scheme -- the schema object that will configure the input.
        { "title" : "my title", "description": " my description" }
        """
        tmp = "<scheme><title>%(title)s</title><description>%(description)s</description><use_external_validation>true</use_external_validation><streaming_mode>xml</streaming_mode><endpoint><args>" % scheme
        self._scheme = scheme
        for arg in scheme["args"]:
            if "required" in arg:
                self._required_schema_arguments.append(arg["name"])
            tmp = "%s<arg name=\"%s\"><title>%s</title><description>%s</description></arg>" % (
                tmp, arg["name"], arg["title"], arg["description"])
        tmp = "%s</args></endpoint></scheme>" % tmp
        self.log.debug("Built A Scheme: %s" % tmp)
        self.scheme(tmp)

    def _print(self, s):
        print "%s" % s

    def compress_ranges(self, i):
        c = []
        i = list(set(i))
        i.sort(key=int)
        for a, b in itertools.groupby(enumerate(i), lambda (x, y): y - x):
            b = list(b)
            c.append((b[0][1], b[-1][1]))
        return c

    def decompress_ranges(self, i):
        c = []
        for tup in i:
            mini, maxi = tup
            c = itertools.chain(c, range(mini, int(maxi) + 1))
        return [x for x in c]

    def _escape(self, s):
        return xml.sax.saxutils.escape("%s" % s)

    def _require_configuration(self, config, key):
        if key not in config:
            raise Exception, "Invalid configuration received from Splunk: key '%s' is missing." % key

    def _print_debug(self, s):
        myStr = "app=%s source=%s sourcetype=%s host=%s %s" % (
            self._app_name, self.source(), self.sourcetype(), self.host(), s)
        logger.debug(myStr)

    def debug(self, s):
        self._print_debug(s)

    def info(self, s):
        self._print_info(s)

    def _print_info(self, s):
        myStr = "app=%s source=%s sourcetype=%s host=%s %s" % (
            self._app_name, self.source(), self.sourcetype(), self.host(), s)
        logger.info(myStr)

    def _catch_error(self, e):
        myJson = {"timestamp": self.gen_date_string(), "log_level": "ERROR"}
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        myJson["errors"] = [{"msg": str((e)),
                             "exception_type": "%s" % type(e).__name__,
                             "exception_arguments": "%s" % e,
                             "filename": fname,
                             "line": exc_tb.tb_lineno,
                             "input_name": self.get_config("name")
                             }]
        oldst = self.sourcetype()
        self.sourcetype("%s:error" % self._app_name)
        self.print_error("%s" % json.dumps(myJson))
        self.print_event("%s" % (json.dumps(myJson)))
        self.sourcetype(oldst)

    def _checkpoint(self, key, value=False, checkpoint_time=None, is_object=False):
        chkpointfile = os.path.join(self._config["checkpoint_dir"], "%s_%s" % (self.host(), key))
        if not value:
            chk_time = 0
            self._loaded_checkpoints[key] = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            self.debug("set checkpoint load time to: %s" % self._loaded_checkpoints[key])
            try:
                if os.path.isfile(chkpointfile):
                    self.debug("File Exists: %s" % chkpointfile)
                    f = open(chkpointfile, "r")
                    chk_time = "%s" % (f.read().strip())
                    self.debug("found a value in the file for %s : %s" % (key, chk_time))
                    f.close()
                    if not is_object:
                        chk_time = float(chk_time)
                    else:
                        chk_time = json.loads(chk_time)
                else:
                    # assume that this means the checkpoint is not there
                    # Let's Default to 60 minutes ago. Just to start pulling data.
                    # TODO: Make loading a checkpoint configurable in respect to the look back time (in minutes)
                    self.debug("Setting Checkpoint %s default time" % key)
                    wibbly_wobbly_timey_wimey = datetime.utcnow() - timedelta(
                        minutes=self.checkpoint_default_lookback())
                    chk_time = (wibbly_wobbly_timey_wimey - datetime.utcfromtimestamp(0)).total_seconds()
                    chk_time = float(chk_time)
                    if is_object:
                        chk_time = {}
            except Exception, e:
                self._catch_error(e)
            self.debug("Returning CheckPoint Time %s" % chk_time)
            return chk_time
        else:
            try:
                # So to avoid "long runs" and "time lapse" in checkpointing,
                # if no time is passed, use the time the checkpoint was loaded.
                # if "now" is passed, use "now". Can I haz tautology?
                # First identified in ASA-3
                chk_time = checkpoint_time
                if chk_time is None:
                    chk_time = self._loaded_checkpoints[key]
                if chk_time is "now":
                    chk_time = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
                if is_object:
                    chk_time = json.dumps(chk_time)
                f = open(chkpointfile, "w")
                f.write("%s" % chk_time)
                f.close()
                return True
            except Exception, e:
                self._catch_error(e)
                return False

    # read XML configuration passed from splunkd
    def _get_config(self):
        self.log.debug("Starting _get_config")
        config = {}
        try:
            # read everything from stdin
            config_str = sys.stdin.read()
            self.log.debug("Found a configuration string: %s" % config_str)
            # parse the config XML
            doc = xml.dom.minidom.parseString(config_str)
            root = doc.documentElement
            chkpointdir = root.getElementsByTagName("checkpoint_dir")[0].firstChild.data
            config["checkpoint_dir"] = chkpointdir
            sessionkey = root.getElementsByTagName("session_key")[0].firstChild.data
            config["session_key"] = sessionkey
            self.log.debug("XML: found checkpoint_dir: %s" % chkpointdir)
            conf_node = root.getElementsByTagName("configuration")[0]
            if conf_node:
                self.log.debug("XML: found configuration")
                self.log.debug("%s" % conf_node)
                stanza = conf_node.getElementsByTagName("stanza")[0]
                if stanza:
                    stanza_name = stanza.getAttribute("name")
                    if stanza_name:
                        self.log.debug("XML: found stanza " + stanza_name)
                        config["name"] = stanza_name
                        params = stanza.getElementsByTagName("param")
                        for param in params:
                            param_name = param.getAttribute("name")
                            self.log.debug("XML: found param '%s'" % param_name)
                            if param_name and param.firstChild and \
                                            param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                                data = param.firstChild.data
                                config[param_name] = data
                                self.log.debug("XML: '%s' -> '%s'" % (param_name, data))
            for arg in self._required_schema_arguments:
                self._require_configuration(config, arg)
            if not config:
                self.print_error("Invalid Configuration received from Splunk.")
                raise Exception("Invalid configuration received from Splunk.")

                # just some validation: make sure these keys are present (required)
        except Exception, e:
            raise Exception("Error getting Splunk configuration via STDIN: %s" % str(e))

        self._print_info("config found: %s" % config)
        return config

    def _get_proxy_config(self):
        self.log.debug("Starting _get_proxy_config")

        proxy_config = {}

        with open(self._proxy_home) as f:

            proxy_config["use_proxy"] = False
            proxy_config["proxy_host"] = ""
            proxy_config["proxy_port"] = ""

            for line in f:
                proxy_string = ''
                found_proxy = line.upper().startswith('HTTPS_PROXY')
                self.log.debug("found_proxy_https: %s" % found_proxy)
                if found_proxy is True:
                    proxy_string = 'HTTPS_PROXY'
                else:
                    found_proxy = line.upper().startswith('HTTP_PROXY')
                    self.log.debug("found_proxy_http: %s" % found_proxy)
                    if found_proxy is True:
                        proxy_string = 'HTTP_PROXY'

                if proxy_string != '':
                    proxy_config["use_proxy"] = True
                    print("Get proxy host info")
                    line = line.split('=')
                    line[0] = line[0].strip()

                    if line[0].upper() == proxy_string:
                        proxy_split = line[1].split(':')
                        proxy_config["proxy_host"] = proxy_split[0].strip()
                        proxy_config["proxy_port"] = proxy_split[1]

                    break

        return proxy_config

    def _get_validation_data(self):
        val_data = {}
        # read everything from stdin
        val_str = sys.stdin.read()
        # parse the validation XML
        doc = xml.dom.minidom.parseString(val_str)
        root = doc.documentElement
        self.log.debug("XML: found items")
        try:
            item_node = root.getElementsByTagName("item")[0]
        except:
            item_node = root.getElementsByTagName("configuration")[0]
        if item_node:
            self.log.debug("XML: found item")
            name = item_node.getAttribute("name")
            val_data["stanza"] = name
            params_node = item_node.getElementsByTagName("param")
            for param in params_node:
                name = param.getAttribute("name")
                self.log.debug("Found param %s" % name)
                if name and param.firstChild and \
                                param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                    val_data[name] = param.firstChild.data
        return val_data

    def _multiple_events(self, events, time_field="timestamp"):
        self.log.debug("Got this event object: {0}".format(events))
        for evt in events:
            self.print_event(json.dumps(evt), time_field=time_field)
            self.log.debug("printed a multi event event")

    def _validate_arguments(self, val_data):
        """
        :param val_data: The data that requires validation.
        :return: perform logic to validate the passed data custom to your environment.
        """
        return True

    """ PUBLIC FUNCTIONS """

    def start(self):
        self.run()
        self.init_stream()

    def stop(self):
        self.print_done_event()
        self.end_stream()

    def run(self):
        self.log.debug("Building Config")
        self._config = self._get_config()
        self.log.debug("Config Built: %s" % self._config)
        self._proxy_config = self._get_proxy_config()
        self.log.debug("Proxy Config Built: %s" % self._proxy_config)

    def scheme(self, scheme=False):
        if scheme:
            self.log.debug("Setting Scheme: %s" % scheme)
            self._SCHEME = scheme
        else:
            self._print(self._SCHEME)
        return self._SCHEME

    def checkpoint_default_lookback(self, new_time=None):
        if new_time is not None:
            self._default_checkpoint_lookback_minutes = new_time
        return self._default_checkpoint_lookback_minutes

    def sourcetype(self, sourcetype=False):
        if sourcetype:
            self._SOURCETYPE = sourcetype
        return self._SOURCETYPE

    def source(self, source=False):
        if source:
            self._SOURCE = source
        return self._SOURCE

    def host(self, host=False):
        if host:
            self._HOST = host
        return self._HOST

    def _get_checkpointfile(self, key):
        return os.path.join(self._config["checkpoint_dir"], "{0}_{1}".format(self.host(), key))

    def _get_checkpoint(self, key):
        """
        Internal Function to get the checkpoint. Disassociate all this stuff.
        :param key:
        :return:
        """
        chkpointfile = self._get_checkpointfile(key)
        chk_time = 0
        self._loaded_checkpoints[key] = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
        self.debug("set checkpoint load time to: %s" % self._loaded_checkpoints[key])
        try:
            if os.path.isfile(chkpointfile):
                self.debug("File Exists: %s" % chkpointfile)
                f = open(chkpointfile, "r")
                chk_time = "%s" % (f.read().strip())
                self.debug("found a value in the file for %s : %s" % (key, chk_time))
                f.close()
                if isinstance(type(chk_time), float) or isinstance(type(chk_time), int):
                    chk_time = float(chk_time)
                else:
                    chk_time = json.loads(chk_time)
            else:
                # assume that this means the checkpoint is not there
                # We will not auto-create one. It is not up to the getter to create a checkpoint. Return none,
                # have MI do the check.
                return None
        except Exception, e:
            self._catch_error(e)
        self.debug("Returning CheckPoint %s" % chk_time)
        return chk_time

    def get_checkpoint(self, key, isObject=False):
        return self._checkpoint(key, value=False, is_object=isObject)

    def _set_checkpoint(self, key, object=None):
        try:
            # So to avoid "long runs" and "time lapse" in checkpointing,
            # if no time is passed, use the time the checkpoint was loaded.
            # if "now" is passed, use "now". Can I haz tautology?
            # First identified in ASA-3
            chkpointfile = self._get_checkpointfile(key)
            checkpoint = object
            if checkpoint is None:
                checkpoint = self._loaded_checkpoints[key]
            if checkpoint is "now":
                checkpoint = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            if not isinstance(object, int) and not isinstance(object, float):
                checkpoint = json.dumps(checkpoint)
            f = open(chkpointfile, "w")
            f.write("%s" % checkpoint)
            f.close()
            return True
        except Exception, e:
            self._catch_error(e)
            return False

    def set_checkpoint(self, key, checkpoint_time=None, isObject=False):
        """

        :param key: The key to use when storing the checkpoint.
        :param checkpoint_time: The time to use. If not sent, will default to the time the checkpoint was loaded.
        :param isObject: IS the checkpoint item an object?
        :return: The Time that was saved.
        """
        return self._checkpoint(key, value=True, checkpoint_time=checkpoint_time, is_object=isObject)

    def get_config(self, key=None):
        if key is None:
            return self._config
        return self._config[key]

    def config(self, key=None):
        return self.get_config(key)

    def get_proxy_config(self, key=None):
        if key is None:
            return self._proxy_config
        return self._proxy_config[key]

    def init_stream(self):
        self._print("<stream>")
        self.log.debug("printed start of stream")

    def end_stream(self):
        self._print("</stream>")
        self.log.debug("printed end of stream")

    # TODO: Add an argument that is a function that will transform the data prior to output in the XML Stream
    def print_event(self, event_data, time_field="timestamp", explicit_time=None):
        if len(event_data) < 1:
            event_data = ""
        _isJson = False
        try:
            event_data = json.loads(event_data)
            self.log.debug("successful parse of JSON data: Is Dict: %s" % isinstance(event_data, dict))
            _isJson = True
        except ValueError, e:
            pass
        my_time = None
        if isinstance(event_data, dict) or _isJson:
            if time_field not in event_data and "timestamp" not in event_data:
                event_data["timestamp"] = self.gen_date_string()
                self.log.debug("setting timestamp to generated time: %s" % event_data["timestamp"])
            elif time_field in event_data and "timestamp" not in event_data:
                event_data["timestamp"] = event_data[time_field]
                self.log.debug("setting timestamp to time_field %s time: %s" % (event_data[time_field],
                                                                                event_data["timestamp"]))
            else:
                self.log.debug("unknown condition: time_field %s " % event_data[time_field])
            event_data["modular_input_consumption_time"] = self.gen_date_string()
            my_time = event_data["timestamp"]
            event_data = json.dumps(event_data)
        if explicit_time is not None:
            my_time = explicit_time
        explicit_time_tag = ""
        if my_time is not None and (isinstance(my_time, float) or isinstance(my_time, int)):
            explicit_time_tag = "<time>{}</time>".format(my_time)
        # escape didn't work. Updated to self reference to _escape ASA-22
        explicit_time_tag = ""
        eventxml = "<event>%s<data><![CDATA[%s]]></data><sourcetype>%s</sourcetype><source>%s</source><host>%s</host><done /></event>\n" % (
            explicit_time_tag, self._escape(event_data), self._escape(self.sourcetype()), self._escape(self.source()),
            self._escape(self.host()))
        self._print(eventxml)
        self.log.debug("printed an event")

    def print_multiple_events(self, event_data, time_field="timestamp"):
        self._multiple_events(event_data, time_field=time_field)

    def print_done_event(self):
        eventxml = "<event><data></data><sourcetype>%s</sourcetype><source>%s</source><host>%s</host><done/></event>\n" % (
            self._escape(self.sourcetype()), self._escape(self.source()), self._escape(self.host()))
        self._print(eventxml)
        self.log.debug("printed a done event")

    def print_error(self, s):
        tmp = self.sourcetype()
        self.sourcetype("%s:error" % self._app_name)
        self.log.error("host=%s sourcetype=%s source=%s %s" % (self.host(), self.sourcetype(), self.source(), s))
        self._print("<error><message>%s</message></error>" % self._escape(s))
        self.print_event("%s" % s)
        self.sourcetype(tmp)

    def gen_date_string(self):
        st = time.localtime()
        tm = time.mktime(st)
        return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(tm))

    def validate_arguments(self):
        val_data = self._get_validation_data()
        try:
            self._validate_arguments(val_data)
        except Exception, e:
            self.print_error("Invalid configuration specified: %s" % str(e))
            sys.exit(1)
