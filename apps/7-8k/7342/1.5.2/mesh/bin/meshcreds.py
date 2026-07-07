#!/usr/bin/env python

import base64
import io
import json
import os
import re
import sys
import tarfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(local=True)
class meshcreds(GeneratingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """

    action = Option(require=True, validate=None)
    package = Option(require=False, validate=None)

    def generate(self):
            upload_rex = re.compile('data:(?P<data_type>[^;]+);(?P<data_encoding>[^,]+),(?P<data_string>.*)')
            upload_match = upload_rex.match(self.package)

            matches = upload_match.groupdict()

            if not 'data_encoding' in matches:
                yield self.error('Data encoding not present in package.')
                return

            if matches['data_encoding'] != 'base64':
                yield self.error('Incorrect data encoding.')
                return

            if not 'data_type' in matches:
                yield self.error('Filetype not present in package.')
                return

            if matches['data_type'] != 'model/mesh' and matches['data_type'] != 'application/octet-stream':
                yield self.error('Incorrect filetype.')
                return

            if not 'data_string' in matches:
                yield self.error('Credential data not present in package.')
                return

            filebytes = base64.b64decode(matches['data_string'])

            files = {}

            with tarfile.open(fileobj=io.BytesIO(filebytes), mode='r:gz', encoding='utf-8') as tar:
                for item in tar:
                    files[item.name] = tar.extractfile(item.name).read().decode('utf-8')

            if not 'mesh.crt' in files or not 'mesh.key' in files or not 'mesh.token' in files:
                yield self.error('Credential package is incomplete.')
                return

            with open(os.path.join(sys.path[0], '..', 'auth', 'mesh.crt'), 'w') as cert_file:
                cert_file.write(files['mesh.crt'])

            with open(os.path.join(sys.path[0], '..', 'auth', 'mesh.key'), 'w') as key_file:
                key_file.write(files['mesh.key'])

            certificate_keyfile = os.path.join(sys.path[0], '..', 'auth', 'mesh.key')

            storage_passwords = self.service.storage_passwords

            credential_name = "mesh:mesh:"

            credential = False

            for storage_password in storage_passwords.list():
                if storage_password.name == credential_name:
                    credential = storage_password

            if not credential:
                credential = storage_passwords.create(files['mesh.token'], "mesh", "mesh")
            else:
                credential.update(password=files['mesh.token'])	

            confs = self.service.confs
            mesh_confs = confs.get(name='app', app="mesh", owner="nobody", sharing="app")

            conf_debug = []

            for conf in confs.iter():
                if conf.name == 'app':
                    app_config = conf
                    break

            for stanza in app_config.iter():
                if stanza.name == 'install':
                    stanza.update(is_configured=1)

            # install_config = app_config.install
            # install_config.update(is_configured=1)

            event = {
                'result': 'success',
            }

            event['_raw'] = json.dumps(event)
            event['_time'] = time.time()

            yield event

    def error(self, message):
        event = {
            "result": "fail",
            "reason": message
        }

        event['_raw'] = json.dumps(event)
        event['_time'] = time.time()

        return event

dispatch(meshcreds, sys.argv, sys.stdin, sys.stdout, __name__)
