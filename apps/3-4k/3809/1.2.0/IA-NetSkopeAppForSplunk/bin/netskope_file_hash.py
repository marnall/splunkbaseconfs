import sys
import os
from Utilities import KennyLoggins
from netskope_client import netskope_client
from AlertAction import CreateAlertModularAction
from json import dumps
import logging
import csv
import re

_app_name = "NetSkopeAppForSplunk"
kl = KennyLoggins()
logger = kl.get_logger(app_name=_app_name, file_name="netskope_file_hash", log_level=logging.info)


class netskopeFileHash(CreateAlertModularAction):
    def __init__(self, settings, action_name):
        CreateAlertModularAction.__init__(self, settings, app_name=_app_name, action_name=action_name,
                                          global_configuration={"filename": "netskope",
                                                                "stanza": "global_netskope_configuration"})
        self.column_name = self.payload["configuration"].get("column_name", "file_hash")
        self.default_column_name = "file_hash"

    def add_hash(self, hashes, existing):
        new_lookup = []
        [new_lookup.append(x) for x in existing if x.get(self.default_column_name) not in hashes]
        [new_lookup.append({self.default_column_name: x, "_key": x}) for x in hashes]
        return new_lookup

    def remove_hash(self, hashes, existing):
        for x in existing:
            if x.get(self.default_column_name) not in hashes:
                x["delete"] = False
            else:
                x["delete"] = True
        return existing

    def main(self):
        try:
            self._log.debug("function=main action=start using_field={}".format(self.column_name))
            hashes = []
            with self._load_results() as fh:
                for num, result in enumerate(csv.DictReader(fh)):
                    try:
                        self._log.debug("processing result number {}".format(num))
                        self._log.debug("function=main marker=result result={}".format(dumps(result)))
                        single_result = {k: v for k, v in result.iteritems()
                                         if not k.startswith('__') and k != "rid"}
                        self._log.debug("single_result={}".format(single_result))
                        hashes.append(single_result.get(self.column_name, ""))
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self._log.error(
                            "function=main action=fatal_error exception_line={} file={}  message={}".format(
                                exc_tb.tb_lineno,
                                fname, e))
            self._log.debug("action=hashes hashes={}".format(hashes))
            uniq_hashes = set(hashes)
            l = self._load_kvstore("aa_netskope_file_hash")
            self._log.debug("action=load_kvstore kvstore={}".format(l))
            # Do Add or Remove to Lookup
            updated_list = l
            action = self.payload["configuration"].get("action", "unknown")
            self._log.debug("action=get_action act={}".format(action))
            if action == "remove":
                updated_list = self.remove_hash(uniq_hashes, l)
            elif action == "add":
                updated_list = self.add_hash(uniq_hashes, l)
            else:
                raise Exception("Invalid Action Found action={}".format(action))
            # Update Netskope Lookup
            self._log.debug("updated_list={}".format(updated_list))
            credential_token = self.utils.get_credential(_app_name, "global_netskope_aa_credential")
            use_proxy = False
            proxy_name = self.proxy_name
            self._log.info("proxy_name={}".format(proxy_name))
            if proxy_name is not None:
                if len(proxy_name) > 0 and proxy_name != "not_configured":
                    use_proxy = True
            else:
                self._log.info("action=variable_check use_proxy={} skipping test")
            self._log.info("action=variable_check use_proxy={}".format(use_proxy))

            RESTConfig = {
                "auth":
                    {"type": "token",
                     "token": credential_token,
                     "authorization_string": "%s"
                     },
                "hostname": self.tenanturl,
                "verify_certificate": False
            }

            if use_proxy:
                RESTConfig["proxy"] = self.utils.get_proxy_configuration(self.proxy_name)
            RC = netskope_client(_app_name, RESTConfig)
            result = {"rid": "{}".format(self.current_milli_time()),
                      "search_name": self.payload.get("search_name", ""),
                      "app": self.payload.get("app", ""),
                      "owner": self.payload.get("owner", "")
                      }
            try:
                hashes_update = [x.get(self.default_column_name) for x in updated_list if
                                 x.get(self.default_column_name) is not None and x.get(
                                     self.default_column_name) is not ""
                                 and not x.get("delete")]
                self._log.info("hashes_update={} len_list={} list_name={}".format(hashes_update, len(hashes_update),
                                                                                  self.list_name))
                if len(hashes_update) < 1:
                    self._log.info("")
                    result["status"] = "nothing_to_do"
                    return
                r = RC.updateFileHashList(hashes=hashes_update, name=self.list_name)
                if "errors" in r:
                    self._log.info("updateFileHashListResponse={}".format(r))
                    raise Exception("action=update_filehash_list status=\"{}\" reason=\"{}\" error_code=\"{}\"".format(
                        r["status"],
                        ", ".join(r["errors"]),
                        r["errorCode"]))
                else:
                    self._save_kvstore("aa_netskope_file_hash", "file_hash", [{"_key": x.get(self.default_column_name),
                                                                  "value": x.get(self.default_column_name)} for x in
                                                                 updated_list if
                                                                 x.get(self.default_column_name) is not None and x.get(
                                                                     self.default_column_name) is not ""])
                    self._delete_kvstore_items("aa_netskope_file_hash", [{"_key": x.get(self.default_column_name),
                                                                          "value": x.get(self.default_column_name)} for
                                                                         x in
                                                                         updated_list if
                                                                         x.get(
                                                                             self.default_column_name) is not None and x.get(
                                                                             self.default_column_name) is not "" and x.get(
                                                                             "delete")])
                    result["status"] = r["status"]
                    self._log.info("action=sending_adaptive_response_framwork_ack")
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                self._log.error(
                    "Error on updateFileHashList: {} exception_line={} file={}".format(e, exc_tb.tb_lineno, fname))
                excep = "{}".format(e)
                # (\w+)="([^"]+)"
                result["exception_status"] = excep
                pat = re.compile('(\w+)="([^"]+)"')
                # updict = {s.split('=', 1)[0]: s.split('=', 1)[1] for s in excep.split() if len(s.split('=', 1)) > 1}
                updict = {"exception_{}".format(x): y for x, y in pat.findall(excep)}
                result.update(updict)
            result.update(self.payload.get("result", {}))
            self.update(result)
            self.invoke()
            self.addevent(dumps(result), sourcetype="netskope:alertaction:file_hash")
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error(
                "function=main action=fatal_error exception_line={} file={}  message={}".format(exc_tb.tb_lineno, fname,
                                                                                                e))


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
    modaction = None
    try:
        modaction = netskopeFileHash(sys.stdin.read(), 'netskope_file_hash')
        modaction.main()
        modaction.writeevents(index="notable", source='netskope_file_hash_alertaction')
    except Exception as e:
        try:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error(
                "function=__main__ action=fatal_error exception_line={} file={}  message={}".format(exc_tb.tb_lineno,
                                                                                                    fname, e))
        except Exception, e:
            logger.critical(e)
        print >> sys.stderr, "ERROR Unexpected err: %s" % e
        sys.exit(3)
