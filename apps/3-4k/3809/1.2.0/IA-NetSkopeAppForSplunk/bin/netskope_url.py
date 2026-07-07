import sys
import os
from Utilities import KennyLoggins
from netskope_client import netskope_client
from AlertAction import CreateAlertModularAction
from json import dumps
import logging
import csv
import hashlib
import re

_app_name = "NetSkopeAppForSplunk"
kl = KennyLoggins()
logger = kl.get_logger(app_name=_app_name, file_name="netskope_url", log_level=logging.INFO)


class netskope_url(CreateAlertModularAction):
    def __init__(self, settings, action_name):
        CreateAlertModularAction.__init__(self, settings, app_name=_app_name, action_name=action_name,
                                          global_configuration={"filename": "netskope",
                                                                "stanza": "global_netskope_configuration"})
        self.column_name = self.payload["configuration"].get("column_name", "url")
        self.default_column_name = "url"

    def add_url(self, urls, existing):
        new_lookup = []
        [new_lookup.append(x) for x in existing if x.get(self.default_column_name) not in urls]
        [new_lookup.append({self.default_column_name: x, "_key": self.make_key(x)}) for x in urls]
        return new_lookup

    def make_key(self, s):
        return hashlib.sha256(b"{}".format(s)).hexdigest()

    def remove_url(self, urls, existing):
        for x in existing:
            if x.get(self.default_column_name) not in urls:
                x["delete"] = False
            else:
                x["delete"] = True
        return existing

    def main(self):
        try:
            self._log.debug("function=main action=start")
            urls = []
            with self._load_results() as fh:
                for num, result in enumerate(csv.DictReader(fh)):
                    try:
                        self._log.debug("processing result number {}".format(num))
                        result.setdefault('rid', str(num))
                        self._log.debug("function=main marker=result result={}".format(dumps(result)))
                        single_result = {k: v for k, v in result.iteritems()
                                         if not k.startswith('__') and k != "rid"}
                        self._log.debug("single_result={}".format(single_result))
                        urls.append(single_result.get(self.column_name, ""))
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self._log.error(
                            "function=main action=fatal_error exception_line={} file={}  message={}".format(
                                exc_tb.tb_lineno,
                                fname, e))
            self._log.debug("action=urls urls={}".format(urls))
            uniq_urls = set(urls)
            l = self._load_kvstore("aa_netskope_url")
            self._log.debug("action=load_kvstore kvstore={}".format(l))
            # Do Add or Remove to Lookup
            updated_list = l
            action = self.payload["configuration"].get("action", "unknown")
            self._log.debug("action=get_action act={}".format(action))
            if action == "remove":
                updated_list = self.remove_url(uniq_urls, l)
            elif action == "add":
                updated_list = self.add_url(uniq_urls, l)
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
                updated_urls = [x.get(self.default_column_name) for x in updated_list if
                                x.get(self.default_column_name) is not None and x.get(
                                    self.default_column_name) is not ""
                                and not x.get("delete")]
                self._log.info("updated_urls={} len_list={} list_name={}".format({}, len(updated_urls),
                                                                                  self.list_name))

                if len(updated_urls) < 1:
                    result["status"] = "nothing_to_do"
                    return
                r = RC.updateUrlList(updated_urls, self.list_name)
                if "errors" in r:
                    self._log.info("updateUrlResponse={}".format(r))
                    raise Exception("action=update_url_list status=\"{}\" reason=\"{}\" error_code=\"{}\"".format(
                        r["status"],
                        ", ".join(r["errors"]),
                        r["errorCode"]))
                else:
                    self._save_kvstore("aa_netskope_url", "url", [{"_key": x.get("_key",
                                                                          self.make_key(
                                                                              x.get(self.default_column_name))),
                                                                  "value": x.get(self.default_column_name)} for x in
                                                                 updated_list if
                                                                 x.get(self.default_column_name) is not None and x.get(
                                                                     self.default_column_name) is not ""])
                    self._delete_kvstore_items("aa_netskope_url", [{"_key": x.get("_key",
                                                                          self.make_key(
                                                                              x.get(self.default_column_name)))} for
                                                                         x in
                                                                         updated_list if
                                                                         x.get(
                                                                             self.default_column_name) is not None and x.get(
                                                                             self.default_column_name) is not "" and x.get(
                                                                             "delete")])
                    result["status"] = r
                self._log.info("action=sending_adaptive_response_framwork_ack")
            except Exception as e:
                self._log.error("Error on updateUrlList: {}".format(e))
                excep = "{}".format(e)
                # (\w+)="([^"]+)"
                result["exception_status"] = excep
                pat = re.compile('(\w+)="([^"]+)"')
                updict = {"exception_{}".format(x): y for x, y in pat.findall(excep)}
                result.update(updict)
            result.update(self.payload.get("result", {}))
            self.update(result)
            self.invoke()

            self.addevent(dumps(result),
                          sourcetype="netskope:alertaction:url")
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error(
                "function=main action=fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno, fname, e))


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
    modaction = None
    try:
        modaction = netskope_url(sys.stdin.read(), 'netskope_url')
        modaction.main()
        modaction.writeevents(index="notable", source='netskope_url_alertaction')
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
