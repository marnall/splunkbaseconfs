import logging
import json
import sys
import threading
import os
from splunk.clilib import cli_common
import splunk.entity as entity
import mes_request
import config
import kvstore_handler as kv


def get_passwords(app):
    """Retrieve the user's API keys from Storage/Passwords"""

    try:
        sessionKey = sys.stdin.readline().strip()
        # list all credentials
        entities = entity.getEntities(
            ["storage", "passwords"],
            namespace=app,
            owner="nobody",
            sessionKey=sessionKey,
        )
    except Exception as e:
        raise Exception(
            "Could not get %s passwords from storage. Error: %s" % (app, str(e))
        )

    # # return set of credentials
    pwd_dict = {}
    for i, c in entities.items():
        try:
            pwd_dict[c["username"]] = c["clear_password"]
        except Exception as e:
            logging.error("---------Exception in Clear password Info Block---------")
            logging.error(str(c))
            logging.error(str(e))
            logging.error("---------End---------")

    return pwd_dict
    # raise Exception("No credentials have been found")


def get_credentials(app):
    """Retrieve the user's credentials from conf file"""
    api_key = None
    try:
        # Fetch Storage/Password list
        password_list = get_passwords(app)
        logging.info("Password read from encrypted storage system")

        api_credentials = cli_common.getConfStanza(config.app, "apiconfig")
        splunk_username = api_credentials.get("splunkUsername")

        splunk_password = ""
        if "splunkPassword" in password_list.keys():
            splunk_password = password_list["splunkPassword"]
        else:
            logging.error(
                "No Splunk Password found in Storage. Please save Splunk Username/Password using Setup Page or Manage Tenant page."
            )

        http_proxy = api_credentials.get("httpProxy")
        https_proxy = api_credentials.get("httpsProxy")
        inputCount = api_credentials.get("inputCount")

        api_key = password_list.get("apiKey", "")
        ent = api_credentials.get("ent")
        # TODO: https://lookoutsecurity.jira.com/browse/EMM-8441
        stream_pos = str(api_credentials.get("streamPosition", "0"))

        # Loop through added keys and verify in store
        count = 0
        keys_obj = []
        ent_list = [ent]
        keys_obj.append({"api_key0": api_key, "ent0": ent, "stream0": stream_pos})

        while int(inputCount) > 0 and count < int(inputCount):
            index = count + 1
            if password_list["key_" + str(count)]:
                keys_obj.append(
                    {
                        "api_key" + str(index): password_list["key_" + str(count)],
                        "ent" + str(index): api_credentials.get("ent" + str(count)),
                        "stream"
                        + str(index): str(
                            api_credentials.get(("streamPosition" + str(count)), "0")
                        ),
                    }
                )
                ent_list.append(api_credentials.get("ent" + str(count)))
            count += 1

    except Exception as e:
        # TODO: use constant value for app name
        logging.error(
            "Error in reading Lookout_Mobile_Security_Splunk_App.conf, either file is missing or Setup is not completed yet."
        )
        logging.error(
            "Could not get %s credentials from lookout conf. Error: %s" % (app, str(e))
        )
        raise Exception(
            "Could not get %s credentials from lookout conf. Error: %s" % (app, str(e))
        ) from None

    if not api_key:
        logging.error("No API key have been found")
        raise Exception("No API key have been found") from None
    return (
        splunk_username,
        splunk_password,
        http_proxy,
        https_proxy,
        keys_obj,
        ent_list,
    )


def single_ent_events(
    ent=None,
    api_key=None,
    http_proxy=None,
    https_proxy=None,
    kv_handler=None,
    is_valid=True,
):
    """Handle the tasks for each thread"""
    logging.info("Thread starting for ent %s..." % ent)
    if not is_valid:
        logging.info(
            "Please check API key, We got Invalid Client error in last attempt for ent %s..."
            % ent
        )
        return
    else:
        mes = mes_request.MESRequest(
            config.api_url, api_key, http_proxy, https_proxy, kv_handler
        )

        events = mes.get_events()
        for event in events:
            event["entName"] = ent
            print(json.dumps(event) + "\r\n")
        else:
            logging.info("No new events")


def main():
    log_name = os.path.join(config.app_log_path, "mes_events.log")

    # Create log folder if not exists
    try:
        if not os.path.exists(config.app_log_path):
            os.makedirs(config.app_log_path)
    except Exception as e:
        log_name = os.path.join(config.app_root_path, "bin", "mes_events.log")

    logging.basicConfig(
        level=logging.INFO,
        filename=log_name,
        format="%(asctime)s %(levelname)-8s %(threadName)s %(message)s",
        datefmt="%m-%d %H:%M",
    )
    logging.info("Application starting")

    username, password, http_proxy, https_proxy, keys_obj, ent_list = get_credentials(
        config.app
    )

    if ent_list and len(ent_list) > 0:
        logging.info(
            "Tenant with API key found in conf file, Total : {}".format(len(ent_list))
        )

        # get dict of everything stored in the kvstore as a baseline
        app_data = kv.KVStoreHandler.get_all_entries(username, password)

        same_keys = True
        for position, enterprise_obj in enumerate(keys_obj):
            # compare key from kvstore and from file
            file_ent = enterprise_obj["ent" + str(position)]
            file_key = enterprise_obj["api_key" + str(position)]
            file_sp = str(enterprise_obj["stream" + str(position)])

            if (
                file_ent not in app_data
                or file_key != app_data[file_ent]["application_key"]
                or (
                    str(app_data[file_ent]["startPosition"])
                    and file_sp != str(app_data[file_ent]["startPosition"])
                )
            ):
                same_keys = False

                # kv.KVStoreHandler.clear_kvstore(username, password)
                if file_ent in app_data:
                    logging.info(
                        "Data mismatch for ENT %s, Deleting KV Store Row and Setup again !!"
                        % file_ent
                    )
                    kv.KVStoreHandler.delete_entry(
                        username, password, app_data[file_ent]["_key"]
                    )

                updated_app_data = kv.KVStoreHandler.setup_kvstore(
                    username, password, file_key, file_ent, file_sp
                )

                logging.info("KV Store Row created for ENT %s " % file_ent)

            elif (
                file_ent in app_data and str(app_data[file_ent]["startPosition"]) == ""
            ):
                # save file sp as start position
                logging.info(
                    "Update Start Position for ENT %s, as it is blank !!" % file_ent
                )
                kv.KVStoreHandler.enc_kvstore_row(
                    username,
                    password,
                    app_data[file_ent]["access_token"],
                    app_data[file_ent]["refresh_token"],
                    app_data[file_ent]["streamPosition"],
                    file_sp,
                    app_data[file_ent]["application_key"],
                    file_ent,
                    app_data[file_ent]["_key"],
                )

        # fetch updated KV store and initialize threads in case if
        if not same_keys:
            app_data = kv.KVStoreHandler.get_all_entries(username, password)

        threads = []

        for index, ent in enumerate(app_data):
            values = app_data[ent]
            # Check for Data Encryption, If plain data exists from older version, Update it in KV Store
            if not values["is_updated"]:
                kv.KVStoreHandler.enc_kvstore_row(
                    username,
                    password,
                    values.get("access_token", ""),
                    values.get("refresh_token", ""),
                    values.get("streamPosition", ""),
                    values.get("startPosition", ""),
                    values["application_key"],
                    ent,
                    values.get("_key", ""),
                )

            # check if ENT stored in KV still exists in file otherwise delete it
            if ent in ent_list:
                opts = {
                    "ent": ent,
                    "api_key": values["application_key"],
                    "http_proxy": http_proxy,
                    "https_proxy": https_proxy,
                    "kv_handler": kv.KVStoreHandler(
                        username,
                        password,
                        values.get("access_token", ""),
                        values.get("refresh_token", ""),
                        values.get("streamPosition", ""),
                        values.get("_key", ""),
                    ),
                    "is_valid": values.get("is_valid", True),
                }

                thread = threading.Thread(
                    target=single_ent_events, kwargs=opts, args=()
                )
                thread.start()
                threads.append(thread)
            else:
                # Delete ent from KV store which is no more exists in file
                kv.KVStoreHandler.delete_entry(
                    username, password, values.get("_key", "")
                )
                logging.info(
                    "ENT not exists in conf file, Deleteing ENT from KV Store : %s "
                    % ent
                )

        # clean up threads
        for thread in threads:
            thread.join()


if __name__ == "__main__":
    main()
