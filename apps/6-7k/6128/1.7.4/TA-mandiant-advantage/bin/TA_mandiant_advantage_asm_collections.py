import requests
import import_declare_test  # noqa: F401

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "..", "common")))

import splunk.admin as admin

from common.utility import read_conf_file
import common.log as log
import common.proxy as pro

from common.api.asm.client import AsmApiClient

logger = log.get_logger(__file__)


def get_asm_accounts(conf_details):
    """Returns a list of advantage accounts from conf."""
    account_list = []
    for account_name, account_details in conf_details.items():
        if account_details.get('account_type') == 'mandiant_attack_surface_management':
            account_list.append(account_name)
    return account_list


class AdvantageAccountDisplaying(admin.MConfigHandler):
    """Get the advantage account names."""

    def setup(self):
        """To setup the variables to access in account."""
        pass

    def handleList(self, conf_info):
        """Populate the accounts in singleselect dropdown."""
        # set splunk context vars
        try:
            conf_file = read_conf_file(self.getSessionKey(), "ta_mandiant_advantage_account")
            asm_account = get_asm_accounts(conf_file)
            asm_url = None
            access_key = None
            secret_key = None

            for account in asm_account:
                asm_url = f"https://{conf_file.get(account).get('endpoint_url')}"
                access_key = conf_file.get(account).get("access_key")
                secret_key = conf_file.get(account).get("secret_key")
                verify_ssl = conf_file.get(account).get('validation_verify_ssl')
                if verify_ssl == '0':
                    verify_ssl = False
                else:
                    verify_ssl = True

            if conf_file.get(account).get("proxy_enabled") != "1":
                proxy_settings = None
            else:
                logger.info(f"Proxy settings found, creating config...")
                proxy_config = {}
                proxy_config["proxy_enabled"] = conf_file.get(account).get("proxy_enabled")
                proxy_config["proxy_port"] = conf_file.get(account).get("proxy_port")
                proxy_config["proxy_type"] = conf_file.get(account).get("proxy_type")
                proxy_config["proxy_url"] = conf_file.get(account).get("proxy_url")
                proxy_config["proxy_username"] = conf_file.get(account).get("proxy_username")
                proxy_config["proxy_password"] = conf_file.get(account).get("proxy_password")
                proxy_settings = pro.transform_proxy_config(proxy_config=proxy_config)

            asm_client = AsmApiClient(access_key, secret_key, asm_url, verify_ssl, proxy_settings, "input_settings")

            projects = asm_client.get_projects(logger)
            logger.info(f"Projects returned")

            collections = []
            for project in projects:
                project_id = str(project.get('id'))
                logger.info(f"Found Project ID: {project_id}")
                for collection in asm_client.get_collections(project_id, logger):
                    collections.append(collection)

            for collection in collections:
                project_name = collection.get("project_name")
                collection_name = collection.get("printable_name")
                conf_info[f"{project_name} ==>> {collection_name}"]

        except Exception as e:
            logger.error(
                "message:error occured while getting ASM Collections | "
                "The following error occured while getting ASM collections."
                "ERROR: {}".format(e)
            )


if __name__ == "__main__":
    """Driving function."""
    admin.init(AdvantageAccountDisplaying, admin.CONTEXT_NONE)
