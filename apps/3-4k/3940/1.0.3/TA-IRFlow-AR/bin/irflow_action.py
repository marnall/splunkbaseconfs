## Minimal set of standard modules to import
import csv      ## Result set is in CSV format
import gzip     ## Result set is gzipped
import json     ## Payload comes in JSON format
import logging  ## For specifying log levels
import sys      ## For appending the library path

from irflow_common.irflow_client import IRFlowClient

## Importing the cim_actions.py library
## A.  Import make_splunkhome_path
## B.  Append your library path to sys.path
## C.  Import ModularAction from cim_actions
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "TA-Irflow", "lib"]))
from cim_actions import ModularAction

## Retrieve a logging instance from ModularAction
## It is required that this endswith _modalert
logger = ModularAction.setup_logger('irflow_action_modalert')

default_mapping = {
    '_raw': 'logEntry',
    'sourcetype': 'logSource',
    'host': 'sourceHostname',
}


class CreateAlertModularAction(ModularAction):

    def dowork(self, result):
        user = self.configuration.get('api_user')
        key = self.configuration.get('api_key')
        address = self.configuration.get('address')

        irfc = IRFlowClient(config_args={'address': address,
                                         'api_user': user,
                                         'api_key': key,
                                         'protocol': 'https',
                                         'debug': False})

        logger.info(json.dumps(result))

        alert_fields = self.map_fields(result)
        culled_json = {}

        for k, v in result.iteritems():
            if not k.startswith('__'):
                culled_json[k] = v

        logger.info(json.dumps(culled_json, indent=2))

        culled_json['splunkRawJson'] = json.dumps(culled_json)

        response = irfc.create_alert(culled_json, 'Splunk Correlation Search Result', 'Splunk AR Action',
                                     suppress_missing_field_warning=True)
        logger.info(json.dumps(response, indent=2))

        if response['success']:
            self.message('Successfully submitted alert to IR-Flow', status='success')
        elif response['errorCode'] is not None:
            self.message('Unable to submit alert to IR-Flow',
                         status='failure',
                         status_code=response['errorCode'])

    def map_fields(self, result):
        mapped_fields = {}
        for k, v in result.iteritems():
            if v != "":
                if k in default_mapping:
                    mapped_fields[default_mapping[k]] = v
        return mapped_fields


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)

    try:
        modaction = CreateAlertModularAction(sys.stdin.read(), logger, 'irflow_create_alert')

        with gzip.open(modaction.results_file, 'rb') as fh:
            for num, result in enumerate(csv.DictReader(fh)):
                result.setdefault('rid', str(num))
                modaction.update(result)
                modaction.invoke()
                modaction.dowork(result)
                break

        modaction.writeevents(index='irflow_action', source='irflow_action')

    except Exception as e:
        try:
            modaction.message(e, status='failure', level=logging.CRITICAL)
        except:
            logger.critical(e)
        print >> sys.stderr, "ERROR Unexpected err: %s" % e
        sys.exit(3)

