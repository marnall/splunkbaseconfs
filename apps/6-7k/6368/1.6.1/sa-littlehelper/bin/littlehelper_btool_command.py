#!/usr/bin/env python

import os
import sys

APP_LIB_FOLDER = os.path.join(os.path.dirname(__file__), "..", "lib")
sys.path.insert(0, APP_LIB_FOLDER)
from sa_littlehelper import CurrentContext, Btool, LittleHelperCommand, KVPairMode, SPLUNK_HOME
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

# This capability allows one to run the btool command globally or for any arbitrary user/app scope
# It should be limited to admin / support types of roles.
GLOBAL_CAP = "run_btool_global"
# TODO / Future: A capability that would allow running btool command ONLY for the current user/app search context.
# LOCAL_CAP = "run_btool_local"


@Configuration(distributed=True)
class BtoolCommand(GeneratingCommand, LittleHelperCommand):
    allapps = Option(require=False, validate=validators.Boolean())
    app = Option(require=False)
    user = Option(require=False)
    debug = Option(require=False, validate=validators.Boolean())
    local = Option(require=False, validate=validators.Boolean())
    kvpairs = Option(require=False)
    sourcetype = Option(require=False)
    source = Option(require=False)
    host = Option(require=False)

    # This method corresponds to a custom modification to the Splunk SDK
    # merged in 6b0d6207fbc2beb31ac18c54e9f068f9fdc76ac7
    # It's pretty important for getting stanza prefixes with equal signs in them.
    # Also some of the magic for injecting the current app and current user if desired.
    def _protocol_v2_option_parser(self, arg):
        if not arg.startswith("--"):
            return [arg]
        result = arg[2:].split('=', 1)
        if len(result) == 1:
            return [result[0], True]
        return result

    def prepare(self):
        self.check_capability(GLOBAL_CAP)

        errors = None

        n_args = len(self.fieldnames)
        if n_args < 2:
            errors = ['Must specify at least filetype and "list"']
        if n_args > 3:
            errors = ['Too many arguments']

        if not errors:
            errors = self._validate_fields()        

        for err in errors:
            self.message_writer("ERROR", err)

        # Don't try to execute the command if there are argument errors
        if len(errors) > 0:
            self._configuration.distributed = False
            self.error_exit(ValueError(), "Argument validation failed for "
                                          f"{self.metadata.searchinfo.command} command.")


    def _validate_fields(self):
        self.__conf_file = self.fieldnames[0]
        self.__operation = self.fieldnames[1]
        self.__stanza = self.fieldnames[2] if len(self.fieldnames) == 3 else None
        
        errors = []

        if self.__operation != "list":
            if self.__conf_file != "props":
                errors.append(f'The list function is the only supported function for {self.__conf_file}')
            if self.__operation != "layer":
                errors.append('The list and layer functions are the only supported functions for props')

        if self.sourcetype or self.source or self.host:
            if self.__operation == "layer":
                if self.__stanza:
                    errors.append('--sourcetype, --source, and --host options are mutually exclusive with a third parameter')

                if self.sourcetype is True or self.source is True or self.host is True:
                    errors.append('--sourcetype, --source, and --host options require values to be set')

                params = []
                if self.source:
                    params.append(f'source::{self.source}')
                if self.host:
                    params.append(f'host::{self.host}')
                if self.sourcetype:
                    params.append(self.sourcetype)

                self.__stanza = "|".join(params) if not errors else self.__stanza

            else:
                errors.append('--sourcetype, --source, and --host options are only supported with layer')
                

        if self.app:
            self.app = self.app.strip() if self.app is not True else self.metadata.searchinfo.app

        if self.allapps:
            if self.app:
                errors.append('Cannot use both --app and --allapps')

        if self.user:
            self.user = self.user.strip() if self.user is not True else self.metadata.searchinfo.username

        if self.user and not (self.app or self.allapps):
            errors.append('Must specify app if specifying user')

        if self.kvpairs:
            parsed = None
            try:
                parsed = validators.Boolean()(self.kvpairs)
                if parsed:
                    parsed = KVPairMode.VALUES
            except ValueError:
                pass

            if parsed is None:
                try:
                    parsed = validators.Set(*list(KVPairMode))(self.kvpairs)
                    parsed = KVPairMode(parsed)
                except ValueError:
                    errors.append(f'Unrecognized kvpairs value: {self.kvpairs}')

            self.kvpairs = parsed

        if self.__operation == "layer" and self.kvpairs and not self.kvpairs.include_values:
            errors.append(f"layer with --kvpairs={self.kvpairs} will always return no results. (layer returns no stanzas)") 

        return errors 

    # Let's make some Events!
    def generate(self):
        info = self.service.info
        self.setup_defaults(info)

        remote = self.is_remote

        o_btool = Btool(file=self.__conf_file, filter_host=info["serverName"])

        peer_bundle = remote and (self.user or self.app or self.allapps) and not self.local

        if self.allapps:
            if peer_bundle:
                dirnames = [os.path.join(os.path.dirname(__file__), "..", "..")]
            else:
                etcdir = os.path.join(SPLUNK_HOME, "etc")
                dirnames = [os.path.join(etcdir, "apps"), os.path.join(etcdir, "slave-apps"), os.path.join(etcdir, "peer-apps")]

            apps = {'system'}
            for dirname in dirnames:
                try:
                    # get the list of folders (or symlinks to folders) that exist underneath the corresponding app directories above.
                    apps.update(next(os.walk(dirname, followlinks=True))[1])
                except StopIteration:
                    continue
        else:
            apps = self.app


        self._walk_lines = o_btool.walk_lines(
                                    stanza_prefix=self.__stanza,
                                    operation=self.__operation,
                                    app_ctx=apps,
                                    user_ctx=self.user,
                                    peer_bundle=peer_bundle,
                                    suppress_errors=self.allapps)

        method = self._emit_lines(self.kvpairs.include_stanzas, self.kvpairs.include_values) if self.kvpairs else self._emit_stanzas()

        for item in method:
            yield item

    def _sanitize_key(self, k):
        sanitize = False
        sanitize |= k.startswith('_')
        sanitize |= k.startswith('btool.')
        sanitize |= k == 'splunk_server'
        if sanitize:
            return f"VALUE_{k}"
        return k

    def _emit_stanzas(self):
        stanza_data = {'btool.keys':[]}
        stanza_body = []
        for obj in self._walk_lines:
            line_type = obj.pop('type')
            line = obj.pop('line')
            if line_type == 'stanza':
                if stanza_body:
                    yield self.mkevent("".join(stanza_body), **stanza_data)
                stanza_body = [line]
                stanza_data = {(f"btool.stanza.{k}" if k != "stanza" and not k.startswith("cmd.") else f"btool.{k}"): v for (k, v) in obj.items()}
                stanza_data['btool.keys'] = []
            else:
                k = obj.pop('key')
                v = obj.pop('value')
                stanza_body.append(line)
                stanza_data[self._sanitize_key(k)] = v
                stanza_data['btool.keys'].append(k)

        if stanza_body:
            yield self.mkevent("".join(stanza_body), **stanza_data)

    def _emit_lines(self, include_stanzas=False, include_values=True):
        stanza_data = {}
        for obj in self._walk_lines:
            line_type = obj.pop('type')
            line = obj.pop('line')
            if line_type == 'stanza':
                stanza_name = obj.pop('stanza')
                stanza_data = {( f"btool.stanza.{k}" if k != "stanza" and not k.startswith("cmd.") else f"btool.{k}"): v for (k, v) in obj.items()}
                if include_stanzas:
                    yield self.mkevent(line, **{"btool.stanza":stanza_name}, **stanza_data)
            else: 
                k = obj.pop('key')
                v = obj.pop('value')
                obj_data = {f"btool.{k}": v for (k, v) in obj.items()}
                obj_data[self._sanitize_key(k)] = v
                obj_data['btool.keys'] = [k]
                if include_values:
                    yield self.mkevent(line, **stanza_data, **obj_data)

    def setup_defaults(self, info):
        self.__defaults = {
          "_time": self.search_now,
          "splunk_server": info['serverName'],
          "btool.source": self.__conf_file
        }

    # Helper method so I didn't have as much copy pasta... (I didn't say none...)
    def mkevent(self, raw, **kwargs):
        data = {"_raw": raw, **kwargs}
        record = {**self.__defaults, **data}
        return self.gen_record(**record)


dispatch(BtoolCommand, sys.argv, sys.stdin, sys.stdout, __name__)
