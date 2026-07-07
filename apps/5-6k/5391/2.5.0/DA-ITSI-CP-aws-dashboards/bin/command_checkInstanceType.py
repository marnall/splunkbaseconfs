import json
import splunk.rest as rest
import splunk.entity as entity
import splunk.Intersplunk as intersplunk
from dao.kvstore_access_object import KVStoreAccessObject
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import os
import xml.etree.ElementTree as ET
import cp_aws_bin.utils.app_util as util

logger = util.get_logger()

instance_url = "https://{}/services/server/info/server-info?output_mode=json"
INSTANCE_KVSTORE_NAMESPACE = "aws_instance_type_kvstore"


def getsessionkey():
    """
    Get the Session Key
    """
    logger.info("Getting session key")
    results, dummyresults, settings = intersplunk.getOrganizedResults()
    session_key = settings["sessionKey"]
    user = settings["owner"]
    logger.info("Got session key sucessfully")
    return user, session_key


def check_instance_type(splunkd_uri, user, session_key):
    check_instance_url = instance_url.format(splunkd_uri)
    response, content = rest.simpleRequest(
        check_instance_url,
        sessionKey=session_key,
        method="GET",
        raiseAllErrors=True,
    )
    if response.status == 200:
        data = json.loads(content)
        instance_type = data["entry"][0]["content"].get("instance_type")
        if instance_type == None:
            logger.info(
                "instance_type key does not exists in server. Setting instance_type as on-prem"
            )
            instance_type = "on-prem"
        else:
            logger.info(
                "instance_type key exists in server. Setting instance_type as cloud"
            )
        instance_kao = KVStoreAccessObject(
            INSTANCE_KVSTORE_NAMESPACE, session_key
        )
        instance_kao.insert_single_item(
            {"_key": "instance_type", "value": instance_type}
        )
        return instance_type


def main():
    app_name = "DA-ITSI-CP-aws-dashboards"
    owner = "nobody"
    CONF_WEB = "configs/conf-web"
    try:
        logger.info(
            "Started updating navigation menu as per the Instance type On-prem/Cloud"
        )
        user, session_key = getsessionkey()
        instance_type = KVStoreAccessObject(
            INSTANCE_KVSTORE_NAMESPACE, session_key
        )
        lookup_value = instance_type.query_items({"_key": "instance_type"})
        lookup_value = json.loads(lookup_value)
        if len(lookup_value) != 0:
            logger.info(
                "Exiting script as lookup is already filled with value {}".format(
                    lookup_value
                )
            )
            intersplunk.outputResults([{"value": lookup_value[0]["value"]}])
            exit()
        splunkd_uri = entity.getEntity(
            CONF_WEB,
            "settings",
            sessionKey=session_key,
            namespace=app_name,
            owner=owner,
        ).get("mgmtHostPort", "127.0.0.1:8089")
        instance_type = check_instance_type(splunkd_uri, user, session_key)
        intersplunk.outputResults([{"value": instance_type}])

    except Exception as e:
        import traceback

        stack = traceback.format_exc()
        errorMsg = intersplunk.generateErrorResults(
            "Something went wrong. Try again later\n Error : Traceback: "
            + str(stack)
        )
        intersplunk.outputResults(errorMsg)


if __name__ == "__main__":
    main()