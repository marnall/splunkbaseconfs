import ta_opseclea_import_declare
from builtins import str
from builtins import object

import os
from os import path, environ
import re
import logging
import subprocess
import uuid
import sys
PY_VERSION = sys.version_info[0]

import splunk.admin as admin
from splunk.clilib import bundle_paths

from splunktaucclib.rest_handler import base, validator
from splunktaucclib.rest_handler.error_ctl import RestHandlerError as RH_Err
from splunktalib.common import util

util.remove_http_proxy_env_vars()


def get_app_path():
    """
    Get path for this app.
    :return:
    """
    return bundle_paths.get_base_path()


class CertException(Exception):
    pass


class Cert(object):
    """
    Certification of the OPSEC Management Server
    """

    def __init__(self, host, app_name, password, cert_name):
        self.host = host
        self.app_name = app_name
        self.password = password
        self.cert_name = cert_name

    def check_path_len(self):
        """
        assert (OPSECDIR + "/" + opsec_app_name) < 255
        assert (OPSECDIR + "/" + cert_name) < 255
        """
        opsec_dir_len = len(environ.get("OPSECDIR", ""))

        sep_len = 1
        cert_len = opsec_dir_len + sep_len + len(self.cert_name)
        app_len = opsec_dir_len + sep_len + len(self.app_name)

        if cert_len > 255:
            raise CertException("Cert name is too long (>255 for full path).")
        elif app_len > 255:
            raise CertException("App name is too long (>255 for full path).")

    @property
    def shell_file(self):
        return './opsec-tools/opsec_pull_cert'

    def pull(self):
        """
        Pull the certification file from the OPSEC Management Server.
        :return:
        """

        # check path length
        try:
            self.check_path_len()
        except CertException as exc:
            RH_Err.ctl(
                400,
                msgx=exc,
                logLevel=logging.INFO
            )

        dir_name = os.path.dirname(os.path.realpath(__file__))
        os.environ["LD_LIBRARY_PATH"] = dir_name

        cert_name = self.cert_name + '_' + str(uuid.uuid4().fields[0]) + '.p12'

        cmd = [
            self.shell_file,
            '-h', self.host,
            '-n', self.app_name,
            '-p', self.password,
            '-o', '../certs/' + cert_name
        ]

        try:
            sub_proc = subprocess.Popen(
                cmd,
                env=dict(os.environ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except Exception:
            raise CertException("GNU C library (glibc.i686 32-bit and pam.i686) is missing.")

        output = sub_proc.communicate()[1]
        if PY_VERSION >= 3:
            output = output.decode('utf-8')
        output = output.lstrip()

        # regex for result of successfully running shell
        regex = "The\sfull\sentity\ssic\sname\sis:\n(?P<sic_name>[^\n]+)"
        regex = re.compile(regex, re.MULTILINE)
        m = re.match(regex, output)
        # Fail to pull
        if not m:
            authority_regex = ".*The referred entity does not exist in the Certificate Authority.*"
            authority_regex = re.compile(authority_regex, re.MULTILINE)
            glibc_regex = ".*bad\sELF\sinterpreter.*"
            glibc_regex = re.compile(glibc_regex, re.MULTILINE)
            pam_regex = ".*error\swhile\sloading\sshared\slibraries:\slibpam.so.0.*"
            pam_regex = re.compile(pam_regex, re.MULTILINE)

            if re.match(authority_regex, output):
                raise CertException("The referred entity does not exist in the Certificate Authority. "
                                    "Make sure you have provided the right application name and one-time password")

            if re.match(glibc_regex, output):
                raise CertException("GNU C library (glibc.i686 32-bit) is missing.")
            if re.match(pam_regex, output):
                raise CertException("PAM shared libraries (pam.i686 32-bit) is missing.")

            raise CertException("Failed to fetch the certificate from server")
        return m.groupdict().get('sic_name'), cert_name

    @staticmethod
    def get_entity_sic_name(server_type, sic_name, object_name):
        regex = re.compile('^CN=(?P<CN>[^,=]+),(?P<O>O=.+$)')
        m = re.match(regex, sic_name)
        if not m:
            raise CertException('Fail to extract "entity_sic_name" '
                                'due to unrecognized pattern of "sic_name".')

        if server_type == 'primary':
            cn = 'cp_mgmt'
        elif server_type == 'secondary':
            cn = 'cp_mgmt_%s' % object_name
        elif server_type == 'dedicated':
            cn = object_name
        else:
            cn = m.groupdict().get('CN')
        return 'CN=%s,%s' % (cn, m.groupdict().get('O'))


class OpsecCertModel(base.BaseModel):
    """
    REST endpoint model Endpoint of OPSEC Certification.
    """
    rest_prefix = 'ta_opsec'
    endpoint = "configs/conf-opseclea_connection"
    requiredArgs = {
        'lea_server_ip',
        'lea_server_auth_port',
        'lea_server_type',
        'fw_version',
        'certificate'
    }
    optionalArgs = {
        'lea_server_auth_type',
        'lea_object_name',
        'management_server_ip',
        'lea_app_name',
        'one_time_password',
        'opsec_sic_name',
        'cert_name',
        'lea_action_map'
    }
    defaultVals = {
        'lea_server_auth_type': 'sslca',
    }
    validators = {
        'lea_server_ip': validator.Host(),
        'lea_server_auth_port': validator.Port(),
        'lea_server_type': validator.Enum(
            ('primary', 'secondary', 'dedicated')
        ),
    }
    cap4endpoint = ''
    cap4get_cred = ''

    outputExtraFields = (
        'eai:acl',
        'acl',
        'eai:attributes',
        'eai:appName',
        'eai:userName',
        'opsec_sic_name',
        'opsec_entity_sic_name',
        'opsec_sslca_file',
        'cert_name'
    )


class OpsecCertHandler(base.BaseRestHandler):
    """
    REST endpoint handler Endpoint of OPSEC Certification.
    """
    # Ignore these args while saving to conf
    IGNORING_ARGS = ['one_time_password']

    def pull_cert(self, args):
        """
        Pull certification and update arguments.
        :param args:
        :return:
        """
        self.check_lea_object_name(
            args.get('lea_server_type'),
            args.get('lea_object_name', None)
        )
        # pull certification
        cert = Cert(
            args["management_server_ip"],
            args["lea_app_name"],
            args["one_time_password"],
            path.join(self.callerArgs.id)
        )
        opsec_sic_name, cert_name = cert.pull()

        # update arguments
        args = {key: val for key, val in args.items()
                if key not in OpsecCertHandler.IGNORING_ARGS}
        args['opsec_sic_name'] = opsec_sic_name
        args['cert_name'] = cert_name
        args['opsec_entity_sic_name'] = cert.get_entity_sic_name(
            args.get('lea_server_type'),
            opsec_sic_name,
            args.get('lea_object_name', None)
        )
        return args

    def check_lea_object_name(self, lea_server_type, lea_object_name):
        if lea_server_type in ('secondary', 'dedicated') and \
                not lea_object_name:
            RH_Err.ctl(
                400,
                msgx='"lea_object_name" is required '
                     'when "lea_server_type" is "%s".',
                logLevel=logging.INFO,
            )

    def handleCreate(self, confInfo):
        try:
            self.get(self.callerArgs.id)
        except:
            pass
        else:
            RH_Err.ctl(409,
                       msgx=('object=%s' % self.callerArgs.id),
                       logLevel=logging.INFO)

        # validate stanza name
        regex = re.compile("^[a-zA-Z0-9\-_\.]+$")
        m = re.match(regex, self.callerArgs.id)
        if not m:
            RH_Err.ctl(
                code=400,
                msgx="Only these character supported for stanza name: "
                     "[a-z A-Z 0-9 - _ .].",
                logLevel=logging.INFO,
            )

        try:
            args = self.encode(self.callerArgs.data)

            # Pull certificate
            if args.get('certificate') == 'pull_new_cert' and args.get('management_server_ip') and args.get('lea_app_name') and args.get('one_time_password'):
                del args['certificate']
                args = self.pull_cert(args)
            else:
                args['opsec_entity_sic_name'] = Cert.get_entity_sic_name(
                    args.get('lea_server_type'),
                    args.get('opsec_sic_name'),
                    args.get('lea_object_name', None)
                )
            self.create(self.callerArgs.id, **args)
            self.handleList(confInfo)
        except CertException as exc:
            RH_Err.ctl(400, msgx=exc, logLevel=logging.INFO)
        except Exception as exc:
            RH_Err.ctl(-1, msgx=exc, logLevel=logging.INFO)

    def handleEdit(self, confInfo):
        try:
            self.get(self.callerArgs.id)
        except Exception as exc:
            RH_Err.ctl(-1, msgx=exc, logLevel=logging.INFO)

        try:
            args = self.encode(self.callerArgs.data, setDefault=False)
            # Pull certificate
            if args.get('certificate') == 'pull_new_cert' and args.get('management_server_ip') and args.get('lea_app_name') and args.get('one_time_password'):
                args['certificate'] = ''
                args = self.pull_cert(args)
            elif self.callerArgs.id != args.get('certificate'):
                if args.get('lea_app_name'):
                    del args['lea_app_name']
                args['opsec_entity_sic_name'] = Cert.get_entity_sic_name(
                    args.get('lea_server_type'),
                    args.get('opsec_sic_name'),
                    args.get('lea_object_name', None)
                )

            self.update(self.callerArgs.id, **args)
            self.handleList(confInfo)
        except CertException as exc:
            RH_Err.ctl(400, msgx=exc, logLevel=logging.INFO)
        except Exception as exc:
            RH_Err.ctl(-1, msgx=exc, logLevel=logging.INFO)

    def handleRemove(self, confInfo):
        entity = self.get(self.callerArgs.id)
        base.BaseRestHandler.handleRemove(self, confInfo)
        if not entity.get('certificate'):
            dir_chars = re.compile(r"[\\/]+")
            cert_file = os.path.join('..', "certs", entity.get('cert_name'))
            if dir_chars.search(entity.get('cert_name')):
                RH_Err.ctl(400,
                           msgx="{} is not a valid cert_name.".format(
                               entity.get('cert_name')),
                           logLevel=logging.INFO)
                return
            if not os.path.exists(cert_file):
                RH_Err.ctl(400,
                           msgx="cert file {} doesn't exist.".format(cert_file),
                           logLevel=logging.INFO)
                return

            try:
                os.remove(cert_file)
            except:
                pass


if __name__ == "__main__":
    admin.init(
        base.ResourceHandler(OpsecCertModel, handler=OpsecCertHandler),
        admin.CONTEXT_APP_AND_USER
    )
