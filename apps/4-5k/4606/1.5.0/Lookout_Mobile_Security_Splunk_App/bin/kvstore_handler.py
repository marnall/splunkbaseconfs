"""
Module KVStoreHandler to handle all requests to Splunk's Key-Value Store.
"""
import json
import sys
import logging
import requests
import config
import os
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from Crypto.Cipher import AES


# TODO: https://lookoutsecurity.jira.com/browse/EMM-8422
# Refactor all of this
def encrypt_val(clear_text):
    if clear_text:
        try:
            enc_secret = AES.new(config.random_id[:32].encode("utf-8"), AES.MODE_ECB)
            tag_string = (
                str(clear_text)
                + (AES.block_size - len(str(clear_text)) % AES.block_size) * "\0"
            )
            cipher_text = base64.b64encode(
                enc_secret.encrypt(tag_string.encode("utf-8"))
            ).decode("utf-8")
            return cipher_text
        except Exception as e:
            logging.error("Error in Encryption of Value. Error: %s" % str(e))
            return clear_text
    else:
        return clear_text


def decrypt_val(enc_text):
    if enc_text:
        try:
            dec_secret = AES.new(config.random_id[:32].encode("utf-8"), AES.MODE_ECB)
            raw_decrypted = dec_secret.decrypt(base64.b64decode(enc_text))
            clear_val = raw_decrypted.decode("utf-8").rstrip("\0")
            return clear_val
        except Exception as e:
            logging.error("Error in Decryption of Value. Error: %s" % str(e))
            # FIXME
            return enc_text
    else:
        return enc_text


class KVStoreHandler:
    """
    Class KVStoreHandler containing public methods to interact with Splunk's Key-Value Store.
    """

    def __init__(
        self,
        username,
        password,
        access_token,
        refresh_token,
        stream_position,
        kvstore_key,
    ):
        """Create an interface for persistent data for one ent."""
        self.username = username
        self.password = password
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.stream_position = stream_position
        self.kvstore_key = kvstore_key

    @staticmethod
    def get_all_entries(username, password):
        """
        Retrieve and return all contents of the kvstore for this app.
        This method is static and is only used to initially set up the kvstore,
        and should not be called from any of the worker threads.
        """
        response = requests.get(
            config.kvstore_location, verify=False, auth=(username, password)
        )

        # if kvstore is still initializing, no point in continuing during this run
        if response.status_code != requests.codes.ok:
            logging.error("KVStore is not connecting via REST API, May be intializing")
            try:
                logging.error("KVStore Response Code :" + str(response.status_code))
                logging.error("KVStore Response :" + str(response.text))
            except Exception as e:
                pass

            sys.exit()

        # FIXME
        response_content = json.loads(response.text)
        app_data = {}
        if isinstance(response_content, (list,)) and response_content:
            for entry in response_content:
                # use .get() here in case the kvstore schema has been changed

                is_valid_key = True
                if "is_valid" in entry and entry.get("is_valid"):
                    is_valid_key = entry.get("is_valid")

                # check for encrypted data
                if "is_updated" in entry and entry.get("is_updated") == True:
                    app_data[decrypt_val(entry.get("ent"))] = {
                        "application_key": decrypt_val(entry.get("application_key")),
                        "access_token": decrypt_val(entry.get("access_token")),
                        "refresh_token": decrypt_val(entry.get("refresh_token")),
                        "streamPosition": decrypt_val(entry.get("streamPosition")),
                        "startPosition": decrypt_val(entry.get("startPosition", "")),
                        "is_updated": True,
                        "is_valid": is_valid_key,
                        "_key": entry.get("_key"),
                    }
                else:
                    app_data[entry.get("ent")] = {
                        "application_key": entry.get("application_key"),
                        "access_token": entry.get("access_token"),
                        "refresh_token": entry.get("refresh_token"),
                        "streamPosition": entry.get("streamPosition"),
                        "startPosition": entry.get("startPosition", ""),
                        "is_updated": False,
                        "is_valid": is_valid_key,
                        "_key": entry.get("_key"),
                    }

        return app_data

    @staticmethod
    def setup_kvstore(username, password, application_key, ent, stream_position):
        """
        Set up the kvstore for this app for the
        first time if it has not been set up yet.
        - The app_data argument is a dict of dicts, keyed by ent.
          Each ent's value is a dict of {field_name: field_value} for
          all the relevant persistent data for this app
        """
        initial_entry = {
            "access_token": "",
            "refresh_token": "",
            "streamPosition": encrypt_val(stream_position),
            "startPosition": encrypt_val(stream_position),
            "application_key": encrypt_val(application_key),
            "ent": encrypt_val(ent),
            "is_updated": True,
            "is_valid": True,
        }
        logging.info(
            "Storing Keys in KV store for ENT %s stream position %s"
            % (ent, str(stream_position))
        )

        post_response = requests.post(
            config.kvstore_location,
            data=json.dumps(initial_entry),
            headers={"accept": "application/json", "content-type": "application/json"},
            verify=False,
            auth=(username, password),
        )
        # log the ents and the beginning of each application key
        logging.info(" Key for Ent:" + ent)
        app_data = {ent: {}}
        app_data[ent]["_key"] = post_response.json()["_key"]
        app_data[ent]["application_key"] = application_key

        return app_data

    @staticmethod
    def clear_kvstore(username, password):
        """Clear the contents of the kvstore for this app."""
        response = requests.delete(
            config.kvstore_location, verify=False, auth=(username, password)
        )
        if response.status_code != requests.codes.ok:
            logging.error(
                "Failed to clear KVStore with status code " + str(response.status_code)
            )
        else:
            logging.info("Successfully cleared KVStore")

    def get_this_ent(self, enc_mode=None):
        """Get the kvstore entry for this object's ent."""
        response = requests.get(
            config.kvstore_location + self.kvstore_key,
            verify=False,
            auth=(self.username, self.password),
        )
        response_content = json.loads(response.text)

        if response_content["is_updated"] and not enc_mode:
            response_content["access_token"] = decrypt_val(
                response_content["access_token"]
            )
            response_content["refresh_token"] = decrypt_val(
                response_content["refresh_token"]
            )
            response_content["streamPosition"] = decrypt_val(
                str(response_content["streamPosition"])
            )
            if (
                response_content["startPosition"] == ""
                or not response_content["startPosition"]
            ):
                response_content["startPosition"] = "0"
            else:
                response_content["startPosition"] = decrypt_val(
                    str(response_content["startPosition"])
                )
            response_content["application_key"] = decrypt_val(
                str(response_content["application_key"])
            )

        # TODO: https://lookoutsecurity.jira.com/browse/EMM-8441
        if (
            response_content["startPosition"] == ""
            or not response_content["startPosition"]
        ):
            response_content["startPosition"] = "0"

        self.access_token = response_content["access_token"]
        self.refresh_token = response_content["refresh_token"]
        self.stream_position = response_content["streamPosition"]
        self.start_position = response_content["startPosition"]
        self.kvstore_key = response_content["_key"]

        return response_content

    def store_in_kvstore(self, key, value):
        """Store a key-value pair in a collection in Splunk's KVStore."""
        current_data = {}
        current_data = self.get_this_ent(True)
        if key != "is_valid":
            current_data[key] = encrypt_val(str(value))
        else:
            current_data[key] = str(value)

        del current_data["_key"]

        post_response = requests.post(
            config.kvstore_location + self.kvstore_key,
            data=json.dumps(current_data),
            headers={"content-type": "application/json"},
            verify=False,
            auth=(self.username, self.password),
        )
        try:
            contents = json.loads(post_response.text)
        except (AttributeError, ValueError):
            pass

    @staticmethod
    def delete_entry(username, password, key):
        response = requests.delete(
            config.kvstore_location + key, verify=False, auth=(username, password)
        )
        if response.status_code != requests.codes.ok:
            logging.error(
                "Failed to delete KVStore row with status code "
                + str(response.status_code)
            )
        else:
            logging.info("Successfully deleted KVStore row")

    @staticmethod
    def enc_kvstore_row(
        username,
        password,
        access_token,
        refresh_token,
        stream_position,
        start_position,
        application_key,
        ent,
        key,
    ):
        """
        Set up the updated kvstore for this app for the
        first time if it is not encrypted, update it.
        """
        updated_entry = {
            "access_token": encrypt_val(access_token),
            "refresh_token": encrypt_val(refresh_token),
            "streamPosition": encrypt_val(stream_position),
            "startPosition": encrypt_val(start_position),
            "application_key": encrypt_val(application_key),
            "ent": encrypt_val(ent),
            "is_updated": True,
            "is_valid": True,
        }
        logging.info("Encrypting data in KV store for ENT %s " % ent)

        post_response = requests.post(
            config.kvstore_location + key,
            data=json.dumps(updated_entry),
            headers={"accept": "application/json", "content-type": "application/json"},
            verify=False,
            auth=(username, password),
        )

        # log the ents and the beginning of each application key
        logging.info("Data Encrypted for Ent:" + ent)
        app_data = {ent: {}}
        app_data[ent]["_key"] = post_response.json()["_key"]
        app_data[ent]["application_key"] = application_key

        return app_data
