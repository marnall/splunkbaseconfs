from __future__ import absolute_import
import os
import logging as logger
from datetime import datetime
import json
import time
import csv
import sys
import gzip
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from ModularInput import ModularInput
from RESTClient import RESTClient
from Utilities import Utilities, KennyLoggins
from netskope_client import netskope_client

GLOBALLOGLEVEL = logger.DEBUG
__author__ = 'ksmodular_inputth'

_modular_input_APP_NAME = 'Netskope Web Transactions Modular Input'
_APP_NAME = 'IA-NetSkopeAppForSplunk'
_SPLUNK_HOME = make_splunkhome_path([""])

kl = KennyLoggins()
log = kl.get_logger(app_name=_APP_NAME, file_name="web_transactions_modularinput", log_level=GLOBALLOGLEVEL)


class netskope_webtransactions(ModularInput):
    def _validate_arguments(self, val_data):
        """
        :param val_data: The data that requires validation.
        :return:
        RAISE an error if the arguments do not validate correctly. The default is just "True".
        """

        if len(val_data["tenanturl"]) > 255:
            raise Exception("TenantURL cannot be longer than 255 characters.")

        if "proxy_name" in val_data:
            if len(val_data["proxy_name"]) > 255:
                raise Exception("Proxy name cannot be longer than 255 characters.")

        return True


class NetskopeWTClient(RESTClient):

    def _build_url(self, endpoint):
        return "https://{}/txnlogs/api/v1/{}".format(self._hostname, endpoint)

    def _call(self, **kwargs):
        url_args = kwargs.copy()
        fullUrl = "{}?{}".format(self._build_url(url_args["endpoint"]), url_args.get("parameters", ""))
        self._log.debug("action=calling_url url={}".format(fullUrl))
        return self._read(fullUrl, payload=None)

    def _file_read(self, url, payload=None, **kwargs):
        try:
            self._log.debug("starting {} read from url".format(self._version))
            self._lastUrl = url
            r = None
            if payload is not None:
                if "headers" in kwargs:
                    self._log.debug("custom_headers={}".format(kwargs["headers"]))
                    kwargs["headers"]["User-Agent"] = self._user_agent
                    self._session.headers.update(kwargs["headers"])
                else:
                    self._log.debug("no_custom_headers")
                    self._session.headers.update({"Content-Type": "application/x-www-form-urlencoded",
                                                  "Content-Length": len(payload),
                                                  "User-Agent": self._user_agent,
                                                  "Host": self._hostname,
                                                  "Accept-Encoding": "*"
                                                  })
                if not self._useproxy:
                    self._log.debug("not using the proxy")
                    r = self._session.post(url, verify=self._verifyCertificate, data=payload)
                else:
                    self._log.debug("using the proxy")
                    r = self._session.post(url, verify=self._verifyCertificate, data=payload, proxies=self.proxies)
            else:
                self._session.headers.update({"User-Agent": self._user_agent})
                if not self._useproxy:
                    r = self._session.get(url, verify=self._verifyCertificate)
                else:
                    r = self._session.get(url, verify=self._verifyCertificate, proxies=self.proxies)
            if r.status_code == 200:
                return r.content
            else:
                self._log.error(
                    " action=read api_version={} status={}".format(self._version, r.status_code))
                self._raise_for_status(r)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = {"msg": str((e)),
                      "exception_type": "{}".format(type(e).__name__),
                      "exception_arguments": "{}".format(e),
                      "filename": fname,
                      "exception_line": exc_tb.tb_lineno
                      }
            self.error(self._build_string(myJson), e)

    def _file_call(self, **kwargs):
        url_args = kwargs.copy()
        fullUrl = "{}?{}".format(self._build_url(url_args["endpoint"]), url_args.get("parameters", ""))
        self._log.debug("action=calling_url url={}".format(fullUrl))
        return self._file_read(fullUrl, payload=None)

    def get_bucket_list(self, date=None):
        if date is None:
            date = "Today"
        buckets = self._call(endpoint="bucketlist")
        self._log.debug("action=got_buckets buckets={}".format(json.dumps(buckets)))
        return buckets.get("ListAllMyBucketResult", {"Buckets": {}}).get("Buckets", {"Bucket": {}}).get("Bucket", [])

    def list_bucket(self, bucket_name=None):
        if bucket_name is None:
            raise Exception("No Bucket Name Passed")
        buckets = self._call(endpoint="bucket", parameters="bucket_name={}".format(bucket_name))
        self._log.debug("action=got_bucket bucket_items={}".format(json.dumps(buckets)))
        return buckets.get("ListBucketResult", [])

    def get_file(self, bucket_name=None, file_name=None):
        if bucket_name is None:
            raise Exception("No Bucket Name Passed")
        if file_name is None:
            raise Exception("No File name passed")
        # https://stackoverflow.com/questions/22676/how-do-i-download-a-file-over-http-using-python
        return self._file_call(endpoint="transaction", parameters="bucket_name={}&obj_name={}".format(bucket_name, file_name))


# NET-33 : Updated Configuration to define proxy_name and use_proxy to not be required.
modular_input = netskope_webtransactions(_APP_NAME, {
    "title": "Netskope Web Transactions",
    "description": "Modular Input for web transactions from Netskope",
    "args": [
        {"name": "tenanturl",
         "description": "The URL provided by Netskope for your instance.",
         "title": "Tenant URL",
         "required": True
         },
        {"name": "token",
         "description": "The authorization Token generated by Netskope",
         "title": "Token"
         },
        {"name": "proxy_name",
         "description": "The stanza name for a configured proxy.",
         "title": "Proxy Name"
         }
    ]
})


def run():
    log.debug("action=setting_debug_notification")
    modular_input.start()
    try:
        modular_input.config()
        use_proxy = False
        proxy_name = modular_input.get_config("proxy_name")
        log.info("proxy_name={}".format(proxy_name))
        if proxy_name is not None:
            if len(proxy_name) > 0 and proxy_name != "not_configured":
                use_proxy = True
        else:
            log.info("action=variable_check use_proxy={} skipping test")
        log.info("action=variable_check use_proxy={}".format(use_proxy))

        utils = Utilities(app_name=_APP_NAME, session_key=modular_input.get_config("session_key"))

        modular_input.host(modular_input.get_config("tenanturl"))
        modular_input.info("action=start logic=modular_input")
        modular_input.source(modular_input.get_config("name"))

        args_dict = {"token": utils.get_credential(_APP_NAME, modular_input.get_config("token")),
                     "tenanturl": modular_input.get_config("tenanturl"),
                     "verify": modular_input.get_config("verify")}
        if args_dict.get("verify") is None:
            args_dict["verify"] = ""
        RESTConfig = {
            "auth":
                {"type": "basic",
                 "username": args_dict["tenanturl"],
                 "password": args_dict["token"]
                 },
            "hostname": modular_input.get_config("tenanturl"),
            "verify_certificate": True if args_dict.get("verify", "false").lower() in ["1", "true"] else False
        }

        if use_proxy:
            RESTConfig["proxy"] = utils.get_proxy_configuration(modular_input.get_config("proxy_name"))

        rest_client = NetskopeWTClient("{}".format(_APP_NAME), RESTConfig)
        current_execution_time = int(time.time())
        log.debug("support=NET-114 action=make_checkpoint evt_type=ModInput new_checkpoint_created={}".format(
            current_execution_time))

        # Setup Checkpoint
        for b in rest_client.get_bucket_list():
            try:
                bucket_name = b.get("Name")
                today = datetime.today()
                today_format = today.strftime("%Y%m%d")
                my_checkpoint = "bucket_{}".format(today_format)
                checkpoint = modular_input._get_checkpoint(my_checkpoint)
                if checkpoint is None:
                    checkpoint = {"last_time": current_execution_time, "items": []}
                checkpoint["checkpoint_name"] = my_checkpoint
                checkpoint["modular_input"] = _APP_NAME
                log.debug(
                    "support=NET-114 today={} today_format={}".format(today, today_format))

                bucket_items = rest_client.list_bucket(bucket_name)
                log.debug("support=NET-114 action=list_buckets bucket_items={}".format(len(bucket_items)))
                my_sourcetype = "netskope:web_transactions"
                modular_input.sourcetype(my_sourcetype)
                for bi in bucket_items:
                    log.debug("bi={}".format(json.dumps(bi)))
                    bucket_item_name = bi.get("Contents").get("Name")
                    if bucket_item_name not in checkpoint["items"]:
                        modular_input.source("netskope:web_transactions:{}".format(bucket_item_name))
                        log.debug("support=NET-114 action=not_found_in_checkpoint bi_name={}".format(bucket_item_name))
                        file_object = rest_client.get_file(bucket_name, bucket_item_name)
                        file_location = make_splunkhome_path(["etc", "apps", _APP_NAME, "bin", "downloads", bucket_item_name])
                        # Extract Tar Information
                        open(file_location, 'wb').write(file_object)
                        log.debug("support=NET-114 action=got_object location={} object={}".format(file_location,
                                                                                                   type(file_object)))
                        with gzip.open(file_location, 'rb') as f:
                            def do_process(l):
                                return {g: l[g] for g in l if "{}".format(g) != "{}".format(l[g])}
                            reader = csv.reader(f)
                            headers = [h.strip() for h in next(reader)[0].replace("#Fields: ", "").split(" ")]
                            csv.register_dialect('NetskopeWebTransactionLogs', quotechar='"', skipinitialspace=True,
                                                 delimiter=' ', strict=True)
                            dict_reader = csv.DictReader(f, fieldnames=headers, dialect="NetskopeWebTransactionLogs")
                            lines = [do_process(x) for x in dict_reader]
                            modular_input.print_multiple_events(lines, time_field="x-cs-timestamp")
                            log.debug("support=NET-114 action=dict_object file_name={} headers={} data={}".format(bucket_item_name, headers, lines))
                        os.remove(file_location)
                        checkpoint["items"].append(bucket_item_name)
                        modular_input._set_checkpoint(my_checkpoint, object=checkpoint)
                    else:
                        log.info("support=NET-114 action=found_in_checkpoint bi_name={}".format(bucket_item_name))

            except Exception, e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                msg = 'message="{}" exception_type="{}" exception_arguments="{}" filename="{}" exception_line={} input={}' \
                    .format(str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, modular_input.get_config("name"))

                log.error("Error occurred in bucket : {} {}".format(bucket_name, e, msg))
                modular_input.print_error(msg)

    except Exception, e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        msg = 'message="{}" exception_type="{}" exception_arguments="{}" filename="{}" exception_line={} input={}' \
            .format(str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, modular_input.get_config("name"))

        log.error("Error occured making REST API call : {} {}".format(e, msg))
        modular_input.print_error(msg)
    modular_input.info("action=stop logic=modular_input input={}".format(modular_input.get_config("name")))
    modular_input.stop()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            modular_input.scheme()
        elif sys.argv[1] == "--validate-arguments":
            modular_input.validate_arguments()
        elif sys.argv[1] == "--test":
            print('No tests for the scheme present')
        else:
            print('You giveth weird arguments')
    else:
        run()

    sys.exit(0)
