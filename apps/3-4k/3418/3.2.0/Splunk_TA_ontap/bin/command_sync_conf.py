import json
import logging
from logging.handlers import RotatingFileHandler
import splunk.rest as rest
import splunk.entity as entity
import splunk.Intersplunk as intersplunk
from splunk.clilib.bundle_paths import make_splunkhome_path
from os import path
import sys
import shutil
from datetime import datetime

app_name = "Splunk_TA_ontap"
owner = 'nobody'
CONF_WEB = 'configs/conf-web'
url = "https://{}/servicesNS/nobody/Splunk_TA_ontap/{}?output_mode=json"
old_properties_list = [
        "perf_whitelist", "realm", "target","username",
        "connection_validation", "credential_validation",
        "per_target_connection_validation",
        "per_target_credential_validation"
    ]
    
COLLECTION_CONF_PATH = make_splunkhome_path([
    'etc', 'apps', 'Splunk_TA_ontap', 'local', 'ta_ontap_collection.conf'])

now = datetime.now().strftime("%d%m%Y-%H%M%S")
BACKUP_FILE_NAME = "ta_ontap_collection-" + now + ".conf.bak"

COLLECTION_CONF_BACKUP_PATH = make_splunkhome_path([
    'etc', 'apps', 'Splunk_TA_ontap', 'local', BACKUP_FILE_NAME])

logger = None
def setup_logger():
    """
    Setup a logger for the search command
    """

    global logger
    logger = logging.getLogger('netapp_syncconf')

    # Prevent the log messages from being duplicated in the python.log file
    logger.propagate = False
    logger.setLevel(logging.INFO)
    file_handler = RotatingFileHandler(make_splunkhome_path(
        ['var', 'log', 'splunk', 'netapp_syncconf.log']))
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)


def getsessionkey():
    '''
        Get the Session Key
        ARGS:
            None
        
        RETURNS
            Session key of the current instance
    '''
    _, _, settings = intersplunk.getOrganizedResults()
    session_key = settings['sessionKey']
    return session_key


def delete_stanza(delete_url, session_key):
    '''
        Deletes the stanza
        ARGS:
            delete_url - The url for making the request of deleting the stanza
            session_key - The Session Key

        RETURNS:
            True if deletion was successful or False if there was error making request 
    '''
    response, content = rest.simpleRequest(
            delete_url,
            sessionKey=session_key,
            method='DELETE',
            raiseAllErrors=True
        )
    if response['status'] == "200":
        return True
    else:
        return False


def insert_stanza(stanza_url, insert_url, stanza, source_data, session_key):
    '''
        Insert the new stanza to ta_ontap_collection.conf
        ARGS:
            stanza_url - The url for making the stanza
            insert_url - The url for making the request of inserting the data in stanza
            stanza - The name of stanza where the data is to be inserted
            source_data - The data to be added in stanza
            session_key - The Session Key

        RETURNS:
            True if insertion was successful or False if there was error making request
    '''
    payload_stanza = '__stanza=' + stanza
    response, content = rest.simpleRequest(
            stanza_url,
            sessionKey=session_key,
            jsonargs=payload_stanza,
            method='POST',
            raiseAllErrors=True
        )
    if response["status"] == "201":
        insert_data = {}
        for data in source_data:
            if "perf_whitelist" in data:
                insert_data["perf_includelist"] = source_data["perf_whitelist"]
            else:
                insert_data[data] = source_data[data]
        payload_insert_data = ""
        for data in insert_data:
            payload_insert_data = payload_insert_data + data + "=" + insert_data[data] + "&"
        payload_insert_data = payload_insert_data[:-1]
        response, content = rest.simpleRequest(
                insert_url,
                sessionKey=session_key,
                jsonargs=payload_insert_data,
                method='POST',
                raiseAllErrors=True
            )
        if response['status'] == "200":
            logger.debug("Successfully saved parameters to stanza: {}".format(stanza))
            return True
        else:
            logger.error("An issue occurred while saving parameters to the stanza: {}".format(stanza))
            return False
    else:
        logger.error("An issue occurred while creating the stanza: {}".format(stanza))
        return False


def get_old_data(get_old_data_url, session_key):
    '''
        Get the old data of particular stanza from ta_ontap_collection.conf
        ARGS:
            get_old_data_url - The url for making the request of 
                               getting the data from stanza
            session_key - The Session Key

        RETURNS:
            The dictionary of data or False if there was error making request
    '''
    local_data = {}
    response, content = rest.simpleRequest(
        get_old_data_url,
        sessionKey=session_key,
        method='GET',
        raiseAllErrors=True,
    )
    if response["status"] == "200":
        data = json.loads(content)
        for property in old_properties_list:
            if property in data["entry"][0]["content"]:
                local_data[property] = data["entry"][0]["content"][property]
        return local_data
    else:
        return False


def get_old_stanza(get_data_url, session_key):
    '''
        Get the list of stanzas that are stored in ta_ontap_collection.conf
        ARGS:
            get_data_url - The url for making the request of getting the list of stanzas
            session_key - The Session Key

        RETURNS:
            The list of stanzas or False if there was error making request
    '''
    stanza_list = []
    response, content = rest.simpleRequest(
        get_data_url,
        sessionKey=session_key,
        method='GET',
        raiseAllErrors=True,
    )
    if response["status"] == "200":
        data = json.loads(content)
        for value in data["entry"]:
            stanza = value["name"]
            if "uigen" in stanza:
                stanza_list.append(stanza)
        return stanza_list
    else:
        return False


def updateconf(splunkd_uri, session_key):
    '''
        Update the ta_ontap_collection.conf with the updated parameter perf_includelist
        ARGS:
            splunkd_uri - The uri for accessing the endpoint of splunkd
            session_key - The Session Key

        RETURNS:
            The list of messages if there is data to be updated or returns a string 
    '''
    global logger
    message = []
    stanza_url = url.format(splunkd_uri, "properties/ta_ontap_collection")
    stanza_list = get_old_stanza(stanza_url,session_key)
    logger.debug("Retrieved the list of stanzas in the ta_ontap_collection.conf file. Total stanzas: {}".format(len(stanza_list)))
    if stanza_list:
        for i in range(len(stanza_list)):
            config_data_url = url.format(splunkd_uri,"configs/conf-ta_ontap_collection/"
                                        + stanza_list[i])

            source_data = get_old_data(config_data_url,session_key)
            if source_data:
                if "perf_whitelist" in source_data:
                    delete = delete_stanza(config_data_url, session_key)
                    if delete:
                        insert_url = url.format(
                                splunkd_uri,
                                "properties/ta_ontap_collection/"+stanza_list[i]
                                )
                        insert = insert_stanza(
                            stanza_url, insert_url, stanza_list[i], source_data , session_key
                        )
                        if insert:
                            message_string = "Successfully updated stanza " + stanza_list[i]
                            message.append(message_string)
                        else:
                            message_string = "There was a problem while adding new data to stanza " \
                                + stanza_list[i]
                            message.append(message_string)
                            continue
                    else:
                        message_string = "There was a problem deleting stanza "+stanza_list[i]
                        message.append(message_string)
                        continue
                else:
                    message_string = "Stanza " +stanza_list[i]+" is already updated."
                    message.append(message_string)
                    continue
            else:
                if source_data == False:
                    message_string = "There has been error in getting the old data from stanza : " \
                        + stanza_list[i] 
                else:
                    message_string = "There is no data in stanza " \
                        + stanza_list[i] 
                message.append(message_string)
                continue
        return message
    else:
        if stanza_list == False:
            message_string = "There has been an error reading the stanzas of ta_ontap_collection.conf" 
        else:
            message_string = "There are no stanzas in ta_ontap_collection.conf to be updated " 
        return message_string

def main():
    global logger
    setup_logger()
    results = []
    if not path.exists(COLLECTION_CONF_PATH):
        error_message = "ta_ontap_collection.conf does not exists in the local directory. "\
            "Aborting the upgrade script."

        result = {
            'Task': 'Sync Conf',
            'Result': error_message
        }
        logger.error(error_message)
        results.append(result)
        intersplunk.outputResults(results)
        sys.exit()

    try:
        shutil.copyfile(COLLECTION_CONF_PATH, COLLECTION_CONF_BACKUP_PATH)
        logger.debug("{} file successfully backed up at {}".format(COLLECTION_CONF_PATH, COLLECTION_CONF_BACKUP_PATH))
        
    except Exception as e:
        error_message = "Error while taking the backup of ta_ontap_collection.conf"
        result = {
            'Task': 'Sync Conf',
            'Result': error_message
        }
        logger.error("Error occurred while taking backup of ta_ontap_collection.conf file. Error: {}".format(str(e)))
        results.append(result)
        intersplunk.outputResults(results)
        sys.exit()

    try:
        session_key = getsessionkey()
        splunkd_uri = entity.getEntity(
                        CONF_WEB,
                        'settings',
                        sessionKey=session_key,
                        namespace=app_name,
                        owner=owner
                    ).get('mgmtHostPort', '127.0.0.1:8089')
        message = updateconf(splunkd_uri,session_key)
        result = {
            'Task': 'Sync Conf',
            'Result': message
        }
        logger.info("Response from updateconf: {}".format(str(message)))
        results.append(result)
    except Exception:
        import traceback
        stack = traceback.format_exc()
        results = intersplunk.generateErrorResults(
                "Error occurred while updating the ta_ontap_collection.conf file. Please check netapp_syncconf.log file for more details."
            )
        logger.error("Error occurred while updating the ta_ontap_collection.conf file. Error: {}".format(str(stack)))

    intersplunk.outputResults(results)

if __name__ == "__main__":
    main()
