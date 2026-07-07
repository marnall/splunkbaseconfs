#!/usr/bin/env python

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(local=True)
class drake(GeneratingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """

    quack = Option(require=True, validate=None)
    package = Option(require=True, validate=None)

    def generate(self):
        APP_HOME = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', self.package)

        if self.quack == 'localconf':
            checkdir = os.path.join(APP_HOME, 'local')

            if not os.path.isdir(checkdir):
                return

            confs = {
                self.package: {}
            }

            location = self.package

            confs[location] = {}

            for filename in os.listdir(checkdir):
                stanza = ''
                parameter = ''

                if  not os.path.isfile(os.path.join(checkdir, filename)):
                    continue

                filepart = filename.split(".")

                file = filepart[0]

                if not file in confs:
                    confs[location][file] = {}

                with open(os.path.join(checkdir, filename), 'rb') as f:
                    conffile = f.readlines()

                    multiline_param = False

                    for line in conffile:
                        if not line:
                            continue

                        line = line.decode('utf8')

                        matched = False

                        # Match stanzas
                        s_match = re.match("\s*\[(?P<stanza>[^\]]*)\]\s*", line)

                        if s_match:
                            matched = True
                            multiline_param = False
                            stanza = s_match.group('stanza')

                            if stanza == '':
                                stanza = 'EMPTY_META'

                            stanza = stanza.replace(" ", '::dysp::')
                            stanza = stanza.replace("%%", '::dypct::')

                            if not stanza in confs[location][file]:
                                confs[location][file][stanza] = {}

                        # Match parameters
                        kv_match = re.match("\s*(?P<parameter>[^\s=]+)\s*=\s*(?P<value>.*)", line)

                        if multiline_param and (stanza and parameter):
                            if isinstance(confs[location][file][stanza][parameter], list):
                                confs[location][file][stanza][parameter].append(line.rstrip())

                            if line.rstrip()[-1] != "\\":
                               multiline_param = False
                               parameter = ''

                            continue

                        if kv_match and not s_match and not multiline_param:
                            matched = True

                            parameter = kv_match.group('parameter')
                            value = kv_match.group('value').rstrip()

                            # This is the one weirdo that gets added to default/app.conf
                            if parameter == 'install_source_checksum':
                                continue

                            if value and value[-1] == "\\":
                                multiline_param = True
                                confs[location][file][stanza][parameter] = [value]
                            else:
                                multiline_param = False
                                confs[location][file][stanza][parameter] = value

            event = {
                'app': self.package
            }

            event['_raw'] = json.dumps(event)
            event['_time'] = time.time()
    
            for conf, stanzas in confs[location].items():
                cevent = event.copy()
                cevent['conf'] = conf

                cevent.pop('_raw', None)

                if 'stanza' in cevent:
                    cevent.pop('stanza', None)

                cevent['_raw'] = json.dumps(cevent)
                cevent['_time'] = time.time()
    
                yield cevent

                for stanza, params in stanzas.items():
                    sevent = cevent.copy()
                    sevent['stanza'] = stanza

                    sevent.pop('_raw', None)

                    if 'param' in sevent:
                        sevent.pop('param', None)

                    sevent['_raw'] = json.dumps(sevent)
                    sevent['_time'] = time.time()
    
                    yield sevent

                    for param, value in params.items():
                        pevent = sevent.copy()
                        pevent['param'] = param

                        pevent.pop('_raw', None)

                        pevent['_raw'] = json.dumps(pevent)
                        pevent['_time'] = time.time()
    
                        yield pevent

        if self.quack=="localignore":
            event = {'_time': time.time() }

            service = self.service

            if 'duckyeah_ignore_kv' in service.kvstore:
                collection = service.kvstore['duckyeah_ignore_kv']

                ignore_local_raw = collection.data.query(query={"app": self.package})

                event['ignore_local'] = json.dumps(collection.data.query(query={"app": self.package}))

                local_ignore = {}
                blanket_ignores = {}

                for ignore in ignore_local_raw:
                    conf = ignore['conf'] if 'conf' in ignore else False
                    stanza = ignore['stanza'] if 'stanza' in ignore else False
                    param = ignore['param'] if 'param' in ignore else False

                    if conf:
                        if stanza:
                            if conf in blanket_ignores:
                                continue
                            else:
                                if conf in blanket_ignores and stanza in blanket_ignores[conf]:
                                    continue
                                if param:
                                    if conf in blanket_ignores and stanza in blanket_ignores[conf]:
                                        continue
                                    else:
                                        if not conf in local_ignore:
                                            local_ignore[conf] = {}

                                        if not stanza in local_ignore[conf]:
                                            local_ignore[conf][stanza] = {}

                                        local_ignore[conf][stanza] = {
                                            param: True
                                        }
                                else:
                                    if not conf in local_ignore:
                                        local_ignore[conf] = {}

                                    local_ignore[conf][stanza] = True

                                    if not conf in blanket_ignores:
                                        blanket_ignores[conf] = {}

                                    if not stanza in blanket_ignores[conf]:
                                        blanket_ignores[conf][stanza] = {}
                        else:
                            local_ignore[conf] = True

                            if not conf in blanket_ignores:
                                blanket_ignores[conf] = {}

            event['ignore_local'] = json.dumps(local_ignore)

            event['app_title'] = self.package
            event['_raw'] = json.dumps(event)

            yield event

        if self.quack == 'localobjects':
            SPLUNK_HOME = os.environ.get('SPLUNK_HOME')

            local_objs = {}

            for root, dirs, files in os.walk(os.path.join(SPLUNK_HOME, 'etc', 'users')):
                user_dir = os.path.join(SPLUNK_HOME, 'etc', 'users')
                m = re.match(
                    re.escape(user_dir)
                    + re.escape(os.sep)
                    + "(?P<local_user>[^"
                    + re.escape(os.sep)
                    + "]+)"
                    + re.escape(os.sep)
                    + self.package
                    + re.escape(os.sep)
                    + 'metadata',
                root)

                if m:
                    local_user = m.group('local_user')

                    for file in files:
                        if file == 'local.meta':
                            private_meta = os.path.join(
                                SPLUNK_HOME,
                                'etc',
                                'users',
                                local_user,
                                self.package,
                                'metadata',
                                file
                            )

                            ignore_confs = ['history', 'ui-prefs', 'ui-tour']

                            with open(private_meta, 'r') as f:
                                meta = f.readlines()

                                for line in meta:
                                    s_match = re.match("\[(?P<stanza>[^\]]+)\]", line)

                                    if s_match:
                                        s_details = s_match.group('stanza').split('/')

                                        if s_details[0] in ignore_confs:
                                            continue

                                        if not local_user in local_objs:
                                            local_objs[local_user] = {}

                                        if not s_details[0] in local_objs[local_user]:
                                            local_objs[local_user][s_details[0]] = []

                                        local_objs[local_user][s_details[0]].append(s_details[1])

            for user, confs in local_objs.items():
                for conf, stanzas in confs.items():
                    for stanza in stanzas:
                        event = {}
                        event['_time'] = time.time()
                        event['user'] = user
                        event['conf'] = conf
                        event['stanza'] = stanza
                        event['_raw'] = json.dumps(event)

                        yield event
        if self.quack=='allfiles':
            all_files = []

            for root, dirs, files in os.walk(APP_HOME):
                pathparts = root.split(os.path.sep)

                hidden_dir = False

                for pathpart in pathparts:
                    if len(pathpart) > 1 and pathpart[0] == ".":
                        hidden_dir = True

                if hidden_dir:
                    continue

                for file in files:
                    if not file in all_files and file[0] != ".":
                        all_files.append(file)

            for file in all_files:
                event = {
                    "filename": file,
                    "_time": time.time()
                }

                event["_raw"] = json.dumps(event)

                yield event

dispatch(drake, sys.argv, sys.stdin, sys.stdout, __name__)
