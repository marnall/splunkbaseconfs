from splunk.persistconn.application import PersistentServerConnectionApplication

import os
import sys
import json

app_lib_folder = os.path.join(os.path.dirname(__file__), "..", "lib")
sys.path.insert(0, app_lib_folder)

from sa_littlehelper import Target, Bundle, BoolEnum, parse_enum_query, RESTException, SHCConfig, SHCStatus, splunk_json_get
from sa_littlehelper import setup_logging, SplunkClientFactory
from sa_littlehelper import SPLUNK_HOME, LocalBundleWalker

class LHBundleREST(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super().__init__()
        self.logger = setup_logging("littlehelper_bundle_rest", "littlehelper_rest.log")
        self.client_factory = SplunkClientFactory()

    def handle(self, in_string):
        data = json.loads(in_string)
        try:
            system_token = data.get('system_authtoken', None)
            if not system_token:
                raise RESTException(status=500, message="Missing credential to talk to Splunk. "
                                                        "Ensure passSystemAuth = true in restmap.conf")
            user_token = data.get('session', {}).get('authtoken')
            if not user_token:
                raise RESTException(status=500, message="Missing credential to talk to Splunk. "
                                                        "Ensure passSession = true in restmap.conf")
            if not SPLUNK_HOME:
                raise RESTException(status=500, message="Missing $SPLUNK_HOME... How the heck is this running?")

            # If a path other than the root... Not Found 404
            if data.get('path_info'):
                raise RESTException(status=404, message=f"Unknown path {data['path_info']}")
            # If a method other than GET/HEAD ... Method Not Allowed 405
            if data.get('method') not in ["GET", "HEAD"]:
                raise RESTException(status=405, message=f"There is no {data['method']} only Zuuul. I mean GET")
            # If explicitly asking for output mode that isn't json... Not Acceptable 406
            if data.get('output_mode') != "json" and data.get('output_mode_explicit'):
                raise RESTException(status=406, message="JSON is the one true content-type in this house.")

            (values, errors) = parse_enum_query(data.get('query', []), target=Target.CAPTAIN, bundle=Bundle.LATEST, skip_local=BoolEnum.NO)

            if errors:
                raise RESTException(
                    status=400,
                    message="Errors parsing request",
                    errors=errors,
                    available_params=dict(
                        target=dict(cardinality="[0,1]", default=Target.CAPTAIN, values=list(Target)),
                        bundle=dict(cardinality="[0,1]", default=Bundle.LATEST, values=list(Bundle))
                    ))

            server_info = data['server']
            client = self.client_factory.create_client(server_info['rest_uri'], system_token)

            target = values['target']
            bundle = values['bundle']
            skip_local = bool(values['skip_local'])

            hostname = server_info['servername']

            targets = []
            messages = []

            def message_writer(level,message):
                messages.append( (level, f"[{hostname}] {message}") )

            try:
                if not SHCConfig(client).enabled:
                    targets.append(client)
                elif target == Target.LOCAL:
                    targets.append(client)
                elif target == Target.CAPTAIN:
                    shc_status = SHCStatus(client)
                    if shc_status.captain.id == server_info['guid']:
                        targets.append(client)
                    else:
                        targets.append(self.client_factory.create_client(shc_status.captain.mgmt_uri, user_token))
                elif target == Target.ALL:
                    shc_status = SHCStatus(client)
                    for (guid, peer) in shc_status.peers.items():
                        if guid == server_info['guid']:
                            targets.append(client)
                        else:
                            targets.append(self.client_factory.create_client(peer.mgmt_uri, user_token))
                else:
                    message_writer("ERROR", f"Target {target} not implemented")

            except:
                msg = "Error discovering SHC members"
                self.logger.exception(msg)
                message_writer("ERROR", msg)
                targets.append(client)

            results = []

            for target in targets:
                if target is client:
                    if not skip_local:
                        walker = LocalBundleWalker(target, Target.LOCAL, message_writer, self.logger)
                        results.extend(walker.walk(bundle))
                else:
                    try:
                        walker = splunk_json_get(client=target,path=f"/services{data['rest_path']}", bundle=bundle, target=Target.LOCAL)
                        messages.extend(walker['messages'])
                        results.extend(walker['results'])
                    except:
                        msg = f"Error communicating to SHC member {target.authority}"
                        message_writer("ERROR", msg)
                        self.logger.exception(msg)

            return dict(status=200, payload=dict(messages=messages, results=results))

        except RESTException as err:
            return dict(status=err.status, payload=err.payload)
