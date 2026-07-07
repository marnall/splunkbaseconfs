import json
import traceback

import akamai_rest_import_guard as arig

import splunk.clilib.cli_common as scc
import splunk.admin as admin

import akamai_consts as ac
from splunktalib.common import log
logger = log.Logs(ac.splunk_ta_akamai).get_logger("custom_rest")

import splunktalib.common.pattern as scp
import splunktalib.kv_client as kc


class AkamaiCPCodeHandler(admin.MConfigHandler):
    alias_key = "alias"
    cp_code_key = "cp_code"
    collection = "akamai_cp_code"

    valid_params = [alias_key, cp_code_key]

    def setup(self):
        for param in self.valid_params:
            self.supportedArgs.addOptArg(param)

    @scp.catch_all(logger)
    def handleList(self, conf_info):
        logger.info("start listing CP code")
        kclient = kc.KVClient(scc.getMgmtUri(), self.getSessionKey())
        lookups = kclient.get_collection_data(
                self.collection, None, ac.splunk_ta_akamai)
        for account in lookups:
            d = conf_info[account['_key']]
            d.append(self.alias_key, account.get(self.alias_key))
            d.append(self.cp_code_key, account.get(self.cp_code_key))
        logger.info("end of listing CP code")

    @scp.catch_all(logger)
    def handleCreate(self, conf_info):
        logger.info("start creating CP code")
        self.handleEdit(conf_info)
        logger.info("end of creating CP code")

    @scp.catch_all(logger)
    def handleEdit(self, conf_info):
        logger.info("start editing CP code")
        if not self.callerArgs or not self.callerArgs.get(self.alias_key):
            logger.error("Missing CP code alias")
            raise Exception("Missing CP code alias")

        if not self.callerArgs or not self.callerArgs.get(self.cp_code_key):
            logger.error("Missing CP code")
            raise Exception("Missing CP code")

        key = self.callerArgs.get(self.cp_code_key)[0]
        alias = self.callerArgs.get(self.alias_key)[0]
        cp_code = key
        account = {
            '_key': key,
            self.alias_key: alias,
            self.cp_code_key: cp_code
        }

        kclient = kc.KVClient(scc.getMgmtUri(), self.getSessionKey())
        # We use update in batch mode just to have an upsert
        kclient.update_collection_data_in_batch(
                self.collection, [account], ac.splunk_ta_akamai)
        d = conf_info[account['_key']]
        d.append(self.alias_key, account.get(self.alias_key))
        d.append(self.cp_code_key, account.get(self.cp_code_key))
        logger.info("end of editing CP code")

    @scp.catch_all(logger)
    def handleRemove(self, conf_info):
        logger.info("start deleting CP code")
        key = self.callerArgs.id

        kclient = kc.KVClient(scc.getMgmtUri(), self.getSessionKey())
        try:
            kclient.delete_collection_data(
                    self.collection, key, ac.splunk_ta_akamai)
        except Exception:
            logger.error("Failed to delete CP code for key=%s, error=%s",
                         key, traceback.format_exc())
        logger.info("end of deleting CP code")


def main():
    admin.init(AkamaiCPCodeHandler, admin.CONTEXT_NONE)


if __name__ == "__main__":
    main()
