import sys
import json
import os
import csv
import logging
from Utilities import KennyLoggins, Utilities
from vmware_edr_client import EDRAlertAction
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import multiprocessing.dummy as mp
from cbapi.response import BannedHash
from cbapi.errors import ServerError
import re

_APP_NAME = "TA-vmware_cb_edr_app_for_splunk"
_alert_name = "vmware-edr-ban-hash"
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))
kl = KennyLoggins()
logger = kl.get_logger(app_name=_APP_NAME, file_name=_alert_name, log_level=logging.INFO)

MD5SUM_RE = re.compile("[A-Fa-f0-9]{32}")
SHASUM_RE = re.compile("[A-Fa-f0-9]{64}")


class SplunkBannedHash(BannedHash):
    urlobject = "/api/v1/banning/blacklist"

    def __init__(self, *args, **kwargs):
        super(BannedHash, self).__init__(*args, **kwargs)

    def get_info(self):
        return self._info


class VmwareBanHash(EDRAlertAction):
    def __init_(self, setting, action_name):
        try:
            EDRAlertAction.__init__(self, settings=settings, action_name=_alert_name,
                                          filename=_alert_name,
                                          stanza="global_{}_configuration".format(_alert_name))

        except Exception as e:
            self._catch_error(e, action_name)

    def _catch_error(self, e, action_name="undefined_alert"):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = " " \
                    "error_message=\"{}\" " \
                    "error_type=\"{}\" " \
                    "error_arguments=\"{}\" " \
                    "error_filename=\"{}\" " \
                    "error_line_number=\"{}\" " \
                    "action_name=\"{}\" " \
            .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, action_name)
        self._log.error(error_msg)

    def main(self):
        try:
            self._log.debug("action=start")
            self.setup()
            edr_clients = self.clients_by_org_key()
            self._log.info("edr_client={}".format(edr_clients))
            with self._load_results("rt") as fh:
                self._log.debug("file_handler={}".format(fh))
                p = mp.Pool(10)

                def do_threaded_result(num, result):
                    try:
                        self._log.debug("processing result number result={}".format(num))
                        result.setdefault('rid', str(num))
                        for key in ["host", "sourcetype", "source"]:
                            if key in result:
                                result["orig_{}".format(key)] = result[key]
                                del result[key]
                        delete_result_keys = [key for key in result if '_mv' in key]
                        for key in delete_result_keys:
                            if key in result:
                                del result[key]
                        self._log.debug("getting hash value id field result={}".format(num))
                        hash_value = result.get(self._configuration.get("hash_field", None), None)
                        dryrun = self._configuration.get("dryrun", "0")
                        self._log.debug("checking fields result={} hash_value={} ".format(num,
                                                                                         hash_value))
                        if hash_value is None:
                            msg = "action=cannot_complete_action hash_value={} hash_field={} ".format(
                                hash_value, self._configuration.get("hash_value_field", None))
                            self._log.warn(msg)
                            self._log.debug("{}".format(json.dumps(self._configuration)))
                            self.addevent(msg, "vmware:cb:edr:alert_action:{}:error".format(_alert_name))
                            return
                        result["hash_value"] = hash_value
                        org_name = result["orig_host"]
                        try:
                            dryrun = int(dryrun)
                        except:
                            dryrun = 1
                        self._log.debug("action=checking_dryrun dryrun_processed={} dryrun_raw={}".format(
                            dryrun, self._configuration.get("dryrun", "not_set")
                        ))
                        if dryrun == 1:
                            self._log.warn("Dry run: would have banned hash {0}.".format(hash_value))
                            self.addevent("dryrun=1 hash={} org_name=\"{}\"".format(hash_value, org_name),
                                          sourcetype="vmware:cb:edr:alert_action:{}".format(_alert_name))
                            return True
                        # Where can be one of: ip, hostname, groupid
                        # hostname = "name:{}".format(hash_value)
                        self._log.debug("hash_value={} org_name={}".format(hash_value, org_name))
                        if SHASUM_RE.match(hash_value):
                            result["result"] = "SHA256 not currently supported. {}".format(hash_value)
                            self.addevent(json.dumps(dict(result)),
                                          sourcetype="vmware:cb:edr:alert_action:{}".format(_alert_name))
                            self._log.warn("action=not_supported match=sha256 hash_value={} org_name={}".format(hash_value, org_name))
                            return True
                        if not MD5SUM_RE.match(hash_value):
                            result["result"] = "That string is not currently supported. {}".format(hash_value)
                            self._log.warn(
                                "action=not_supported match=not_md5_not_sha256 hash_value={} org_name={}".format(hash_value,
                                                                                                     org_name))
                            self.addevent(json.dumps(dict(result)),
                                          sourcetype="vmware:cb:edr:alert_action:{}".format(_alert_name))
                            return True
                        try:
                            new_ban = edr_clients[org_name].create(BannedHash)
                            new_ban.md5hash = hash_value
                            new_ban.text = "Banned from Splunk: {}".format(_alert_name)
                            new_ban.enabled = True
                            new_ban.save()
                            result["result"] = "Hash {0} now banned".format(hash_value)
                        except KeyError:
                            result["alert_action_exception"] = "Unable to find API config for host \"{}\"".format(
                                org_name)
                            self.addevent(json.dumps(dict(result)),
                                          sourcetype="vmware:cb:edr:alert_action:{}:error".format(_alert_name))
                            self._log.warn("action=cannot_find_host host={}".format(org_name))
                            return
                        except ServerError as ex:
                            if ex.error_code == 409:
                                self._log.info("BannedHash already exists for Hash {0}".format(hash_value))
                                existing_ban = edr_clients[org_name].select(SplunkBannedHash, hash_value)
                                existing_ban.text = "Banned from Splunk"
                                existing_ban.enabled = True
                                existing_ban.save()
                                self._log.info("Enabled existing BannedHash for Hash {0}".format(hash_value))
                                result["result"] = "Enabled existing BannedHash for Hash {0}".format(hash_value)
                                self.addevent(json.dumps(dict(result)),
                                              sourcetype="vmware:cb:edr:alert_action:{}".format(_alert_name))
                            else:
                                raise
                        else:
                            result["result"] = "Hash {0} now banned.".format(hash_value)
                            self.addevent(json.dumps(dict(result)),
                                          sourcetype="vmware:cb:edr:alert_action:{}".format(_alert_name))
                            return True
                    except Exception as lre:
                        self._catch_error(lre, self._action_name)
                matrix = [(num, result) for num, result in enumerate(csv.DictReader(fh))]
                p.starmap(do_threaded_result, matrix)
                p.close()
                p.join()

        except Exception as me:
            self._catch_error(me, self._action_name)


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.fatal("FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
    modaction = None
    try:
        logger.info("instantiating {}".format(_alert_name))
        modaction = VmwareBanHash(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evtidx("vmware_cb_edr_action_index")
        logger.info("action=found_eventtype class=alert_action_index alert_action_index=\"{}\"".format(evttype))
        modaction.writeevents(index=evttype,
                              fext='vmware_cb_edr_alert_action_st',
                              sourcetype="vmware:cb:edr:alert_action:{}".format(_alert_name),
                              source="vmware:cb:edr:alert_action:{}:{}".format(_alert_name,
                                                                            modaction.payload["search_name"].replace(" ","_")))
    except Exception as e:
        try:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, _alert_name)
            logger.error(error_msg)
        except Exception as e:
            logger.critical(e)
        sys.exit(3)

