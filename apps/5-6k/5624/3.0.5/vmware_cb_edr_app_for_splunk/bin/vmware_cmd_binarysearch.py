import sys
import logging
from Utilities import KennyLoggins, Utilities
from vmware_edr_client import EDRCommand
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import multiprocessing.dummy as mp
import os
import time

_APP_NAME = "vmware_cb_edr_app_for_splunk"
_cmd_name = "edrbinarysearch"
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))
from splunklib.searchcommands import Configuration, GeneratingCommand, Option, validators, dispatch
from cbapi.response import Binary

kl = KennyLoggins()


class SplunkBinary(Binary):

    def __init__(self, *args, **kwargs):
        super(SplunkBinary, self).__init__(*args, **kwargs)

    def get_info(self):
        return self._info


@Configuration(type='events')
class VMwareEDRBinarySearchCommand(GeneratingCommand):
    """ %(synopsis)
    ##Syntax
    %(syntax)
    ##Description
    %(description)
    """
    query = Option(name="query", require=False)
    sort = Option(name="sort", require=False)
    _clients = {}
    _log = kl.get_logger(app_name=_APP_NAME, file_name=_cmd_name, log_level=logging.INFO)
    _cmd_name = _cmd_name
    _results = []

    def threaded_action(self, org_name, cb_url, c):
        try:
            self._log.info("action=thread_start org_name={} cb_url={} query={}".format(org_name, cb_url, self.query))
            query = c.select(SplunkBinary)
            if self.query is not None:
                query = query.where(self.query)
            if self.sort is not None:
                query = query.sort(self.sort)
            [self._results.append(self.squash_data(result, cb_url)) for result in query]
        except Exception as e:
            errobj = {"{}".format(type(e)): "{}".format(e)}
            self._log.error("ThreatedAction {}".format(self.squash_error_data(errobj, cb_url)))
            self._results.append(self.squash_error_data(errobj, cb_url))
            self._catch_error(e, self._cmd_name)


    def _catch_error(self, e, cmd_name="undefined_alert"):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = " " \
                    "error_message=\"{}\" " \
                    "error_type=\"{}\" " \
                    "error_arguments=\"{}\" " \
                    "error_filename=\"{}\" " \
                    "error_line_number=\"{}\" " \
                    "action_name=\"{}\" " \
            .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, cmd_name)
        self._log.error(error_msg)

    def squash_error_data(self, ret_dict, cb_url="Unknown"):
        try:
            self._log.info("action=squash_error_data")
            return {'sourcetype': 'vmware:cb:edr:cmd:binarysearch:error', '_time': time.time(),
                    'source': cb_url, '_raw': ret_dict}
        except Exception as e:
            self._catch_error(e)

    def squash_data(self, data_dict, cb_url="Unknown"):
        try:
            if data_dict is None:
                self._log.warning("action=squash_data data_dict=None data_dict_raw={}".format(data_dict))
                return {'sourcetype': 'vmware:cb:edr:cmd:binarysearch', '_time': time.time(),
                        'source': cb_url, '_raw': {"action": "no_data"}}
            self._log.info("action=squash_data")
            ret_dict = {}
            for x in data_dict._info:
                self._log.info("x={}".format(x))
                v = data_dict.get(x)
                ret_dict[x] = str(v)
            return {'sourcetype': 'vmware:cb:edr:cmd:binarysearch', '_time': time.time(),
                    'source': cb_url, '_raw': ret_dict}
        except Exception as e:
            self._catch_error(e)

    def generate(self):
        """
        Splunk requires generate function to behave as main, upon search command
        trigger the generate function will be called with the arguments provided
        by the command issuer (The VMware EDR App UI or the search GUI)
        """
        try:
            session_key = "{}".format(self.metadata.searchinfo.session_key)
            edr_client = EDRCommand(_cmd_name, session_key)
            edr_client.setup()
            self._clients = edr_client.clients_as_array()
            if any([x is None for x in self._clients]):
                yield {'sourcetype': 'vmware:cb:edr:cmd:processsearch:error', '_time': time.time(),
                       'source': 'custom_command', '_raw': {
                        "error": "Authentication hosts not assigned. Please configure the search command for authentication."}}
            else:
                p = mp.Pool(2)
                matrix = [(client["org_name"], client["url"], client["cb"]) for client in self._clients]
                p.starmap(self.threaded_action, matrix)
                p.close()
                p.join()
                for evt in self._results:
                    yield evt
        except Exception as e:
            self._catch_error(e, _cmd_name)
            self.write_error("{}".format(e), type(e))


dispatch(VMwareEDRBinarySearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
