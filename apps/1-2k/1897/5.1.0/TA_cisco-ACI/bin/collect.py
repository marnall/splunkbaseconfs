from __future__ import print_function
import sys
import os
import json
import requests
import xml.sax.saxutils as xss
import splunk.entity as entity
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.clilib import cli_common as cli

import logger_manager

if sys.version_info < (3, 0, 0):
    from urllib import quote_plus
else:
    from urllib.parse import quote_plus

logger = logger_manager.get_logger("collect")

try:
    egg_directories = next(os.walk(os.path.dirname(os.path.realpath(__file__))))[1]
    for dir in egg_directories:
        if dir.endswith(".egg") or dir == "cert_lib":
            dirPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), dir)
            sys.path.extend([dirPath])
    from datetime import datetime
    from datetime import date, timedelta
except Exception as err:
    logger.error("ACI Error: Error importing the required python modules: %s" % err)
    raise

import acisession as aci

myapp = os.path.abspath(__file__).split(os.sep)[-3]

deployment_queries_file = make_splunkhome_path(["etc", "apps", myapp, "bin", "deployment_queries.json"])
cisco_aci_server_setup_local = make_splunkhome_path(["etc", "apps", myapp, "local", "cisco_aci_server_setup.conf"])

# Delete and create a file
global queries
with open(deployment_queries_file) as dep_queries:
    queries = json.load(dep_queries)
global pagelimit
pagelimit = 2000
global timeout_val
timeout_val = 180


def _getCredentials(apic_credentials, sessionKey):
    try:
        # list all credentials
        entities = entity.getEntities(
            ["admin", "passwords"],
            search="eai:acl.app=" + myapp,
            sessionKey=sessionKey,
            count=-1,
        )

        for i, c in list(entities.items()):
            host = str(xss.unescape(i.split(":")[0])).strip()
            user_detail = c["username"].split(",")

            if len(user_detail) == 4:
                if user_detail[0] == "mso" or user_detail[0] == "nd_auth":
                    continue

                if user_detail[0] == "apic":
                    user_detail = user_detail[1:]

            if "\\" in user_detail[1]:
                user_detail[1] = "apic#" + str(xss.unescape(user_detail[1]))

            if len(user_detail) == 3:
                port = user_detail[0]
                username = xss.unescape(user_detail[1])
                verify_ssl = user_detail[2]
            else:
                username = xss.unescape(user_detail[0])
                verify_ssl = user_detail[1]

            verify_ssl = verify_ssl.strip().upper()

            if verify_ssl in ("0", "FALSE", "F", "N", "NO", "NONE", ""):
                verify_ssl = "False"
            else:
                verify_ssl = "True"

            password = c["clear_password"]
            credential = []
            if port:
                host_list = host.split(",")
                port1 = ":" + port + ","
                host = port1.join(host_list)
                host = host + ":" + port

            credential = [username, password, verify_ssl]
            apic_credentials[host] = list(credential)

        # logger.error("ACI Error: Credentials Not Found through REST API")
        return apic_credentials
    except Exception as e:
        logger.error("ACI Error: Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))


# Function to print ACI object properties after converting it to tab separated values
def _printObjectPropertiesToTSV(data, apic_class, apic_host, **kwargs):
    global common_host
    events_ingested = 0
    for object_data in data:
        attribute_data = object_data[apic_class]["attributes"]
        resp = []
        currentTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")
        resp.append(currentTime)
        for keys in attribute_data:
            if attribute_data[keys]:
                resp.append(keys + "=" + attribute_data[keys])
        resp.append("apic_host=" + common_host)
        resp.append("actual_host=" + apic_host)
        resp.append("component=" + apic_class)
        if kwargs is not None:
            for key, value in list(kwargs.items()):
                if value:
                    resp.append(key + "=" + value)
        print("\t".join(resp))
        events_ingested += 1
        print("\n")

    return events_ingested


# Function to get general information for all the managed objects for given classes
def _getClassInfo(session, classes, apic_host):
    for apic_class in classes:
        events_ingested_count = 0
        if apic_class == "faultRecord" or apic_class == "aaaModLR" or apic_class == "eventRecord":
            try:
                events_ingested_count += _getBigDatasetResult(session, apic_class, apic_host)
            except Exception as e:
                logger.error(
                    "ACI Error: _getClassInfo Failed to fetch data from host: %s for class: %s. Error: %s. "
                    "Skipping this class." % (apic_host, apic_class, e)
                )
        elif apic_class == "fvCEp":
            _getStats(session, [apic_class], apic_host, component_type="_getClassInfo")
        else:
            page = 0
            counter = True
            while counter:
                query_url = "/api/node/class/%s.json?page=%s&page-size=%s" % (
                    apic_class,
                    page,
                    pagelimit,
                )
                try:
                    ret = session.get(query_url, timeout=timeout_val)
                except Exception as e:
                    logger.error(
                        "ACI Error: _getClassInfo Failed to fetch data from host: %s for class: %s. Error: %s. "
                        "Skipping this class." % (apic_host, apic_class, e)
                    )
                    break
                if ret.status_code != 200:
                    logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (query_url, ret.reason))
                    logger.error("ACI Error: Response Content:%s" % (ret.content))
                    logger.error("Error while collecting data for class: %s. Skipping this class." % (apic_class))
                    break
                page += 1
                data = ret.json()["imdata"]
                if data == []:
                    counter = False
                else:
                    events_ingested_count += _printObjectPropertiesToTSV(data, apic_class, apic_host)

        logger.info("Collected a total of %d events for %s class.", events_ingested_count, apic_class)


# Function to get information of the managed objects for classes which returns very big dataset.
# Ex: aaaSessionLR, aaaModLR, faultRecord usually have more than 2-3 lakh objects.
# REST has limit of 100k object count while quering once. Fetching only last 60 days data.
fd = None
fdupdate = None


def _getBigDatasetResult(session, apic_class, apic_host, host=None):
    scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
    fileName = apic_host + "_" + apic_class + "_LastTransactionTime.txt"
    filePath = os.path.join(scriptPath, fileName)
    global fd
    global fdupdate

    events_ingested_count = 0

    try:
        if os.path.isfile(filePath):
            logger.info("Starting to read the file: %s.", filePath)
            fd = open(filePath, "r")
            scaleStart = fd.read()
            fd.close()
            logger.info("File %s read successfully.", filePath)

            query_url = '/api/node/class/%s.json?query-target-filter=gt(%s.created,"%s")' % (
                apic_class,
                apic_class,
                quote_plus(scaleStart, safe=":"),
            )

            try:
                ret = session.get(query_url, timeout=timeout_val)
            except Exception as e:
                logger.error(
                    "ACI Error: _getBigDatasetResult Failed to fetch data from host: %s. "
                    "Query URL: %s. Error: %s" % (apic_host, query_url, e)
                )
                raise e
            if ret.status_code != 200:
                logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (query_url, ret.reason))
                logger.error("ACI Error: Response Content:%s" % (ret.content))
            else:
                data = ret.json()["imdata"]
                # logging.debug('response returned %s', data)
                if host:
                    events_ingested_count += _printObjectPropertiesToTSV(data, apic_class, apic_host, dest=str(host))
                else:
                    events_ingested_count += _printObjectPropertiesToTSV(data, apic_class, apic_host)

        else:
            # Storing current datetimestamp to a file
            # datetimestamp format: "created":"2016-01-07T10:06:32.622+00:00"
            query_url = "/api/node/mo/info.json"
            try:
                ret = session.get(query_url, timeout=timeout_val)
            except Exception as e:
                logger.error(
                    "ACI Error: _getBigDatasetResult Failed to fetch data from host: %s. "
                    "Query URL: %s. Error: %s" % (apic_host, query_url, e)
                )
                raise e
            if not ret.ok:
                logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (query_url, ret.reason))
                logger.error("ACI Error: Response Content:%s" % (ret.content))
                return events_ingested_count

            tdata = ret.json()["imdata"]
            # logging.debug('response returned %s', tdata)
            for tobject_data in tdata:
                for t in tobject_data:
                    attribute_data = tobject_data[t]["attributes"]

            datetime_stamp = attribute_data["currentTime"]
            logger.info("Starting to write to the file: %s.", filePath)
            fd = open(filePath, "w")
            fd.write(datetime_stamp)
            fd.close()
            logger.info("Updated the %s file successfully with the value: %s.", filePath, datetime_stamp)

            query_url = "/api/node/class/%s.json?rsp-subtree-include=count" % apic_class
            try:
                ret = session.get(query_url, timeout=timeout_val)
            except Exception as e:
                logger.error(
                    "ACI Error: _getBigDatasetResult Failed to fetch data from host: %s. "
                    "Query URL: %s. Error: %s" % (apic_host, query_url, e)
                )
                raise e
            if ret.status_code != 200:
                logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (query_url, ret.reason))
                logger.error("ACI Error: Response Content:%s" % (ret.content))
                return events_ingested_count

            data = ret.json()["imdata"]
            # logging.debug('response returned %s', data)
            for object_data in data:
                for k in object_data:
                    attribute_data = object_data[k]["attributes"]

            totalObjCount = int(attribute_data["count"])

            if totalObjCount < 99000:
                # Kept 99000 b'coz don't what to cut too close to 1 lakh objects
                query_url = "/api/node/class/%s.json" % apic_class
                try:
                    ret = session.get(query_url, timeout=timeout_val)
                except Exception as e:
                    logger.error(
                        "ACI Error: _getBigDatasetResult Failed to fetch data from host: %s. "
                        "Query URL: %s. Error: %s" % (apic_host, query_url, e)
                    )
                    raise e
                if ret.status_code != 200:
                    logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (query_url, ret.reason))
                    logger.error("ACI Error: Response Content:%s" % (ret.content))
                    return events_ingested_count
                else:
                    data = ret.json()["imdata"]
                    # logging.debug('response returned %s', data)
                    if host:
                        events_ingested_count += _printObjectPropertiesToTSV(
                            data, apic_class, apic_host, dest=str(host)
                        )
                    else:
                        events_ingested_count += _printObjectPropertiesToTSV(data, apic_class, apic_host)

            else:
                # Create datetimestamp i.e in format: "created":"2016-01-07T10:06:32.622+00:00"
                # time = datetime.now().strftime('T%H:%M:%S.%f')[:-3]
                onlytime = datetime_stamp.split("T")[1]

                timestamp = "T" + onlytime

                no_of_days = 1  # The interval period to get data is been kept as 1 day
                loop = 60  # Max of last 60 days records will be fetched.
                start = 0

                present = datetime.now().strftime("%Y-%m-%d")
                scaleEnd = present + timestamp

                previous = date.today() - timedelta(days=no_of_days)
                older = previous.strftime("%Y-%m-%d")
                scaleStart = older + timestamp

                while loop > start:
                    query_url = (
                        '/api/node/class/%s.json?query-target-filter=and(gt(%s.created,"%s"),lt(%s.created,"%s"))'
                        % (
                            apic_class,
                            apic_class,
                            quote_plus(scaleStart, safe=":"),
                            apic_class,
                            quote_plus(scaleEnd, safe=":"),
                        )
                    )
                    try:
                        ret = session.get(query_url, timeout=timeout_val)
                    except Exception as e:
                        logger.error(
                            "ACI Error: _getBigDatasetResult Failed to fetch data from host: %s."
                            "Query URL: %s. Error: %s" % (apic_host, query_url, e)
                        )
                        raise e
                    if ret.status_code != 200:
                        logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (query_url, ret.reason))
                        logger.error("ACI Error: Response Content:%s" % (ret.content))
                    else:
                        data = ret.json()["imdata"]
                        if host:
                            events_ingested_count += _printObjectPropertiesToTSV(
                                data, apic_class, apic_host, dest=str(host)
                            )
                        else:
                            events_ingested_count += _printObjectPropertiesToTSV(data, apic_class, apic_host)

                    scaleEnd = scaleStart
                    no_of_days = no_of_days + 1  # +1 day limit
                    previous = date.today() - timedelta(days=no_of_days)
                    older = previous.strftime("%Y-%m-%d")
                    scaleStart = older + timestamp

                    start = start + 1

        # Storing current datetimestamp to a file
        query_url = "/api/node/mo/info.json"
        try:
            ret = session.get(query_url, timeout=timeout_val)
        except Exception as e:
            logger.error(
                "ACI Error: _getBigDatasetResult Failed to fetch data from host: %s. Query URL: %s. Error: %s"
                % (apic_host, query_url, e)
            )
            raise e
        if not ret.ok:
            logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (query_url, ret.reason))
            logger.error("ACI Error: Response Content:%s" % (ret.content))
            return events_ingested_count

        tdata = ret.json()["imdata"]
        # logging.debug('response returned %s', tdata)
        for tobject_data in tdata:
            for t in tobject_data:
                attribute_data = tobject_data[t]["attributes"]

        datetime_stamp = attribute_data["currentTime"]
        logger.info("Starting to write to the file: %s.", filePath)
        fdupdate = open(filePath, "w")
        fdupdate.write(datetime_stamp)
        fdupdate.close()
        logger.info("Updated the %s file successfully with the value: %s.", filePath, datetime_stamp)
    except Exception as e:
        raise e
    finally:
        if fd is not None:
            fd.close()
        if fdupdate is not None:
            fdupdate.close()

    return events_ingested_count


# Function to get general information for all the managed objects for given classes
def _getAuthentication(session, classes, apic_host):
    for apic_class in classes:
        events_ingested_count = 0
        if apic_class == "aaaSessionLR":
            # this check is for aaaSessionLR class query may return more than 100k Objects
            try:
                events_ingested_count += _getBigDatasetResult(session, apic_class, apic_host, host=apic_host)
            except Exception as e:
                logger.error(
                    "ACI Error: _getAuthentication Failed to fetch data from host: %s for class: %s. "
                    "Error: %s. Skipping this class." % (apic_host, apic_class, e)
                )
        else:
            page = 0
            counter = True
            while counter:
                query_url = "/api/node/class/%s.json?page=%s&page-size=%s" % (
                    apic_class,
                    page,
                    pagelimit,
                )
                try:
                    ret = session.get(query_url, timeout=timeout_val)
                except Exception as e:
                    logger.error(
                        "ACI Error: _getAuthentication Failed to fetch data from host: %s for class: %s. "
                        "Error: %s. Skipping this class." % (apic_host, apic_class, e)
                    )
                    break
                if ret.status_code != 200:
                    logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (query_url, ret.reason))
                    logger.error("ACI Error: Response Content:%s" % (ret.content))
                    logger.error("Error while collecting data for class: %s. Skipping this class." % (apic_class))
                    break
                else:
                    page += 1
                    data = ret.json()["imdata"]
                    if data == []:
                        counter = False
                    else:
                        # logging.debug('response returned %s', data)
                        events_ingested_count += _printObjectPropertiesToTSV(data, apic_class, apic_host)

        logger.info("Collected a total of %d events for %s class.", events_ingested_count, apic_class)


def _printObjectsToTSV(modata, attribute_data, apic_class, apic_host):
    global common_host
    resp = []
    currentTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")
    resp.append(currentTime)
    events_ingested_count = 0
    if modata:
        for mo_object_data in modata:
            for mo_obj in mo_object_data:
                mo_attribute_data = mo_object_data[mo_obj]["attributes"]

                resp = []
                currentTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")
                resp.append(currentTime)

                for keys1 in mo_attribute_data:
                    if mo_attribute_data[keys1]:
                        resp.append(keys1 + "=" + mo_attribute_data[keys1])
                for keys2 in attribute_data:
                    if attribute_data[keys2]:
                        resp.append(keys2 + "=" + attribute_data[keys2])

                resp.append("apic_host=" + common_host)
                resp.append("actual_host=" + apic_host)
                resp.append("component=" + apic_class)
                print("\t".join(resp))
                events_ingested_count += 1
                print("\n")

    else:
        for keys2 in attribute_data:
            if attribute_data[keys2]:
                resp.append(keys2 + "=" + attribute_data[keys2])

        resp.append("apic_host=" + common_host)
        resp.append("actual_host=" + apic_host)
        resp.append("component=" + apic_class)
        print("\t".join(resp))
        events_ingested_count += 1
        print("\n")

    return events_ingested_count


# Function to get Health and Fault details for all the managed objects for given classes
def _getHealth(session, classes, apic_host):
    for apic_class in classes:
        page = 0
        counter = True
        events_ingested_count = 0
        while counter:
            query_url = "/api/node/class/%s.json?page=%s&page-size=%s" % (
                apic_class,
                page,
                pagelimit,
            )
            try:
                ret = session.get(query_url, timeout=timeout_val)
            except Exception as e:
                logger.error(
                    "ACI Error: _getHealth Failed to fetch data from host: %s for class: %s. "
                    "Error: %s. Skipping this class." % (apic_host, apic_class, e)
                )
                break
            page += 1
            if ret.status_code != 200:
                logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (query_url, ret.reason))
                logger.error("ACI Error: Response Content:%s" % (ret.content))
                logger.error("Error while collecting data for class: %s. Skipping this class." % (apic_class))
                break

            data = ret.json()["imdata"]
            if data == []:
                counter = False
                break
            # logging.debug('response returned %s', data)
            for object_data in data:
                for obj in object_data:
                    attribute_data = object_data[obj]["attributes"]
                    dn = attribute_data["dn"]

                    # Health Details
                    if apic_class == "fabricNode":
                        hquery_url = "/api/mo/%s/sys.json?rsp-subtree-include=health,no-scoped" % dn
                    else:
                        hquery_url = "/api/mo/%s.json?rsp-subtree-include=health,no-scoped" % dn

                    try:
                        healthret = session.get(hquery_url, timeout=timeout_val)
                        if healthret.status_code != 200:
                            logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (hquery_url, healthret.reason))
                            logger.error("ACI Error: Response Content:%s" % (healthret.content))
                        else:
                            healthdata = healthret.json()["imdata"]
                            # logging.debug('response returned %s', healthdata)
                            events_ingested_count += _printObjectsToTSV(
                                healthdata, attribute_data, apic_class, apic_host
                            )
                    except Exception as e:
                        logger.error(
                            "ACI Error: _getHealth Failed to fetch data from host: %s Query URL: %s. Error: %s"
                            % (apic_host, hquery_url, e)
                        )

                    # fault Detils
                    if apic_class == "fabricNode":
                        fquery_url = (
                            "/api/mo/%s/sys.json?rsp-subtree-include=faults,no-scoped&query-target=subtree" % dn
                        )
                    else:
                        fquery_url = "/api/mo/%s.json?rsp-subtree-include=faults,no-scoped&query-target=subtree" % dn

                    try:
                        faultret = session.get(fquery_url, timeout=timeout_val)
                        if faultret.status_code != 200:
                            logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (fquery_url, faultret.reason))
                            logger.error("ACI Error: Response Content:%s" % (faultret.content))
                        else:
                            faultdata = faultret.json()["imdata"]
                            # logging.debug('response returned %s', faultdata)
                            events_ingested_count += _printObjectsToTSV(
                                faultdata, attribute_data, apic_class, apic_host
                            )
                    except Exception as e:
                        logger.error(
                            "ACI Error: _getHealth Failed to fetch data from host: %s Query URL: %s. Error: %s"
                            % (apic_host, fquery_url, e)
                        )

        logger.info("Collected a total of %d events for %s class.", events_ingested_count, apic_class)


# Function to get statistical related information for all the managed objects of given classes
def _getStats(session, classes, apic_host, component_type="_getStats"):
    global common_host
    for apic_class in classes:
        events_ingested_count = 0
        page = 0
        counter = True
        if apic_class != "fvCEp":
            while counter:
                query_url = "/api/node/class/%s.json?page=%s&page-size=%s" % (
                    apic_class,
                    page,
                    pagelimit,
                )
                try:
                    ret = session.get(query_url, timeout=timeout_val)
                except Exception as e:
                    logger.error(
                        "ACI Error: _getStats Failed to fetch data from host: %s for class: %s. "
                        "Error: %s. Skipping this class." % (apic_host, apic_class, e)
                    )
                    break
                if ret.status_code != 200:
                    logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (query_url, ret.reason))
                    logger.error("ACI Error: Response Content:%s" % (ret.content))
                    logger.error("Error while collecting data for class: %s. Skipping this class." % (apic_class))
                    break

                data = ret.json()["imdata"]
                # logging.debug('response returned %s', data)
                page += 1
                if data == []:
                    counter = False
                else:
                    for object_data in data:
                        for obj in object_data:
                            attribute_data = object_data[obj]["attributes"]
                            dn = attribute_data["dn"]

                            moquery_url = "/api/mo/%s.json?rsp-subtree-include=stats,no-scoped" % dn
                            try:
                                moret = session.get(moquery_url, timeout=timeout_val)
                            except Exception as e:
                                logger.error(
                                    "ACI Error: _getStats Failed to fetch data from host: %s for Query URL: %s. "
                                    "Error: %s. Skipping this class." % (apic_host, moquery_url, e)
                                )
                                continue
                            if moret.status_code != 200:
                                logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (moquery_url, moret.reason))
                                logger.error("ACI Error: Response Content:%s" % (moret.content))
                            else:
                                modata = moret.json()["imdata"]
                                events_ingested_count += _printObjectsToTSV(
                                    modata, attribute_data, apic_class, apic_host
                                )
        else:
            while counter:
                if component_type == "_getStats":
                    query_url = (
                        "/api/node/class/%s.json?rsp-subtree=children&rsp-subtree-class=fvRsCEpToPathEp,fvIp"
                        "&page=%s&page-size=%s" % (apic_class, page, pagelimit)
                    )
                else:
                    query_url = (
                        "/api/node/class/%s.json?rsp-subtree=children&rsp-subtree-class=fvIp"
                        "&page=%s&page-size=%s" % (apic_class, page, pagelimit)
                    )
                try:
                    ret = session.get(query_url, timeout=timeout_val)
                except Exception as e:
                    logger.error(
                        "ACI Error: %s Failed to fetch data from host: %s for class: %s. "
                        "Error: %s. Skipping this class." % (component_type, apic_host, apic_class, e)
                    )
                    break
                page += 1
                if ret.status_code != 200:
                    logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (query_url, ret.reason))
                    logger.error("ACI Error: Response Content:%s" % (ret.content))
                    logger.error("Error while collecting data for class: %s. Skipping this class." % (apic_class))
                    break

                pdata = ret.json()["imdata"]
                if pdata == []:
                    counter = False
                else:
                    for pobject_data in pdata:
                        for pobj in pobject_data:
                            resp = []
                            currentTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")
                            resp.append(currentTime)

                            attribute_data = pobject_data[pobj].get("attributes", {})
                            cdata = pobject_data[pobj].get("children", [])
                            for attr_keys in attribute_data:
                                if attribute_data[attr_keys]:
                                    resp.append(attr_keys + "=" + attribute_data[attr_keys])
                            for cobject_data in cdata:
                                for cobj in cobject_data:
                                    children_data = cobject_data[cobj]["attributes"]
                                    if cobj == "fvIp":
                                        resp.append("addr=" + children_data.get("addr", ""))
                                    else:
                                        for keys1 in children_data:
                                            if children_data[keys1]:
                                                resp.append(keys1 + "=" + children_data[keys1])

                            resp.append("apic_host=" + common_host)
                            resp.append("actual_host=" + apic_host)
                            resp.append("component=" + apic_class)
                            print("\t".join(resp))
                            events_ingested_count += 1
                            print("\n")

        logger.info("Collected a total of %d events for %s class.", events_ingested_count, apic_class)


def _apicRedundancy(host, username, password, verify_ssl):
    global session
    try:
        for each in host:
            # Login from 2nd APIC
            if "apic#" in username:
                logger.info("Collecting data using Remote Based Authentication for the host: {0} ".format(host))
            else:
                logger.info("Collecting data using Password Based Authentication for the host: {0} ".format(host))
            try:
                each = each.strip()
                session = aci.Session("https://" + str(each), username, password, verify_ssl=verify_ssl, logger=logger)
                resp = session.login(timeout=timeout_val)
                if resp.ok:
                    return session, each
                logger.error("%% Could not login to APIC: {0}, Username: {1}".format(each, username))
            except Exception as err:
                logger.error("ACI Error: Not able to connect to %s Error: %s" % (each, err))
                if str(each) == str(host[-1]):
                    logger.error("%% Could not find other APICs to login:%s Username:%s" % (host, username))
                    return None, None
                continue
    except Exception:
        logger.error("%% Could not find other APICs to login:%s, Username:%s" % (host, username))


def getCtxDnObjects(ctxDn):
    """
    Parse ctxDn & appended like "related_<child-key>.

    sample data for ctxDn.
    ctxDn = "acct-[infra]/region-[us-east-1]/context-[overlay-1]-addr-[10.10.0.0/25]"
            "/cidr-[10.10.0.0/25]/subnet-[10.10.0.16/28]/ep-[eni-033a7e61e24a8639e]"
    ctxDn = "acct-[infra]/region-[us-east-1]/context-[overlay-1]-addr-[10.10.0.0/25]/csr-[ct_routerp_us-east-1_0:0]"
    ctxDn = "uni/tn-infra/ctxprofile-ct_ctxprofile_us-east-1/cidr-[10.10.0.0/25]"
    ctxDn = "uni/tn-infra/cloudapp-cloud-infra/cloudepg-infra-routers"
    """
    ctxDn_objects = []
    print_dict = {}
    if "acct" in ctxDn:
        split_dn1 = ctxDn.split("]/")
        if "]" in split_dn1[-1]:
            split_dn1[-1] = split_dn1[-1][:-1]
        for each in split_dn1:
            if "-[" in each and "]-" in each:
                split_dn_1 = each.split("]-")
                for items in split_dn_1:
                    if "-[" in items:
                        split_dn_2 = items.split("-[")
                        print_dict[split_dn_2[0]] = split_dn_2[1]
            elif "-[" in each:
                split_dn2 = each.split("-[")
                print_dict[split_dn2[0]] = split_dn2[1]
    elif "uni" in ctxDn:
        if "cidr" in ctxDn:
            cidr = ctxDn[::-1].split("-", 1)[0][::-1]
            print_dict["cidr"] = cidr[1:-1]
            ctxDn = ctxDn.split("cidr-")[0]
        split_dnA = ctxDn.split("/")
        for each in split_dnA:
            if "-" in each:
                if "[" in each.split("-", 1)[1]:
                    # print each.split('-',1)[1][1:]
                    each.split("-", 1)[1] = each.split("-", 1)[1][1:]
                print_dict[each.split("-", 1)[0]] = each.split("-", 1)[1]
    for key, value in list(print_dict.items()):
        if str(key) == "acct" or str(key) == "tn":
            key = "tenant"
        ctxDn_objects.append("related_" + str(key).capitalize() + "=" + str(value))
    return ctxDn_objects


def parse_deployment_query_response(deployment_resp, class_name, related_key, apic_host):
    """
    Print data in splunk.

    sample data:
        {
        "attributes": {
            "key": "value"
        },
        "children": [
        {
        "pconsCtrlrDeployCtx": {
            "attributes": {
                "deployStatus": "deployed",
                "key-val pairs"
            },
            "children": [
            {
                "pconsResourceCtx": {
                    "attributes": {
                        "childAction": "",
                        "ctxClass": "fvCtx",
                        "ctxDn": "uni/tn-infra/ctx-overlay-1",
                        "dn": "",
                        "status": ""
                    }
                }
            }
            ]
            }
        }
        ]
        }
    """
    currentTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")
    display_response = [
        str(currentTime),
        "apic_host=" + str(apic_host),
        "component=" + str(class_name),
        "related_component=" + str(related_key),
    ]
    events_ingested_count = 0

    for key, value in list(deployment_resp.items()):
        if str(key) == "attributes":
            for attribute_key, attribute_value in list(value.items()):
                if attribute_value:
                    display_response.append(str(attribute_key) + "=" + str(attribute_value))
    if "children" in list(deployment_resp.keys()):
        child_obj = deployment_resp.get("children", [{}])[0].get("pconsCtrlrDeployCtx", {})
        # child_obj = deployment_resp['children'][0]['pconsCtrlrDeployCtx']
        if str(child_obj.get("attributes", {}).get("deployStatus")) == "deployed" and "children" in child_obj:
            for each in child_obj.get("children", []):
                child_display = []
                for child_key, child_value in list(each.get("pconsResourceCtx", {}).get("attributes", {}).items()):
                    if child_value and str(child_key) == "ctxDn":
                        child_display = child_display + getCtxDnObjects(child_value)
                    # elif child_value:
                    child_display.append(str(child_key) + "=" + str(child_value))
                print_display = display_response + child_display
                print("\t".join(print_display))
                events_ingested_count += 1
                print("\n")
    else:
        print("\t".join(display_response))
        events_ingested_count += 1
        print("\n")

    return events_ingested_count


def query_mo_for_queries(session, result, class_name, apic_host):
    """
    Get the data of relatedObjects.

    It takes query parameters for relatedObjects of given class from deployment_queries.json file.
    """
    for each in result:
        attribute_data = each.get(class_name, {}).get("attributes", {})
        if "dn" not in list(attribute_data.keys()):
            continue

        deployment_queries = queries.get(class_name, {})
        # print deployment_queries['relatedObjects']
        for relatedKey, relatedOptions in list(deployment_queries.get("relatedObjects", {}).items()):
            events_ingested_count = 0
            for relatedOptions_query in relatedOptions:
                deployment_url = "/api/node/mo/%s.json?%s" % (
                    str(attribute_data.get("dn")),
                    str(relatedOptions_query),
                )
                try:
                    resp = session.get(deployment_url, timeout=timeout_val)
                except Exception as e:
                    logger.error(
                        "ACI Error: query_mo_for_queries, Failed to fetch data from host: %s for class: %s, "
                        "dn: %s, relatedKey: %s, relatedOptions_query: %s. Error: %s."
                        % (
                            apic_host,
                            class_name,
                            str(attribute_data.get("dn")),
                            relatedKey,
                            relatedOptions_query,
                            e,
                        )
                    )
                    continue

                if resp.status_code != 200:
                    logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (deployment_url, resp.reason))
                    logger.error("ACI Error: Response Content:%s" % (resp.content))
                    continue

                deployment_resp = resp.json()

                if deployment_resp and deployment_resp.get("imdata"):
                    if "error" not in list(deployment_resp.get("imdata", [{}])[0].keys()):
                        events_ingested_count += parse_deployment_query_response(
                            deployment_resp.get("imdata", [{}])[0].get(class_name, {}),
                            class_name,
                            relatedKey,
                            apic_host,
                        )
                    else:
                        logger.error(
                            "ACI Error: Could not Fetch response from CAPIC. Code= %s ,Message= %s"
                            % (
                                str(
                                    deployment_resp.get("imdata", [{}])[0]
                                    .get("error", {})
                                    .get("attributes", {})
                                    .get("code")
                                ),
                                str(
                                    deployment_resp.get("imdata", [{}])[0]
                                    .get("error", {})
                                    .get("attributes", {})
                                    .get("text")
                                ),
                            )
                        )
                else:
                    continue

            logger.info("Collected %d events for %s key.", events_ingested_count, relatedKey)


def _getCloudAPIC(session, classes, apic_host):
    """Get information for all the managed objects of given cloud-apic classes."""
    try:
        for apic_class in classes:
            query_url = "/api/node/class/%s.json" % (apic_class)
            try:
                response = session.get(query_url, timeout=timeout_val)
            except Exception as e:
                logger.error(
                    "ACI Error: _getCloudAPIC Failed to fetch data from host: %s for class: %s. "
                    "Error: %s. Skipping this class." % (apic_host, apic_class, e)
                )
                continue

            if response.status_code != 200:
                logger.error("ACI Error: HTTP Query=%s ERROR=%s" % (query_url, response.reason))
                logger.error("ACI Error: Response Content:%s" % (response.content))
                logger.error("Error while collecting data for class: %s. Skipping this class." % (apic_class))
                continue

            response_imdata = (response.json()).get("imdata")
            if not response_imdata:
                continue
            else:
                if "error" not in list(response_imdata[0].keys()):
                    query_mo_for_queries(session, response_imdata, apic_class, apic_host)
                else:
                    logger.error(
                        "ACI Error: Could not Fetch response from CAPIC. Code= %s ,Message= %s"
                        % (
                            str(response.get("imdata", [{}])[0].get("error", {}).get("attributes", {}).get("code")),
                            str(response.get("imdata", [{}])[0].get("error", {}).get("attributes", {}).get("text")),
                        )
                    )
    except Exception as e:
        logger.error("ACI Error:%s" % (e))
        sys.exit()


def _apicCertRedundancy(host_list, username, cert_name, cert_private_key_path, verify_ssl, argv, classes):
    global session
    for host in host_list:
        # Login from 2nd APIC
        host = host.strip()
        logger.info("Collecting data using Certificate Based Authentication for the host: {0} ".format(host))
        try:
            session = aci.Session(
                "https://" + str(host),
                username,
                cert_name=cert_name,
                key=cert_private_key_path,
                verify_ssl=verify_ssl,
                logger=logger,
            )
            _getDataArgs(argv, classes, host, session, username, "cert_based_auth")
            break
        except Exception as err:
            logger.error(
                "ACI Error: Failed to get data using Certificate Based Authentication from %s Error: %s" % (host, err)
            )
            if str(host) == str(host_list[-1]):
                logger.error("%% Could not find other APICs to login:%s Username:%s" % (host_list, username))
                return
            continue


def _getCertCredentials():

    apic_credentials = dict()
    username = ""
    cisco_aci_port = ""
    hostname = ""
    cert_name = ""
    cert_private_key_path = ""
    verify_ssl = ""

    try:
        if os.path.exists(cisco_aci_server_setup_local):
            credentials = cli.readConfFile(cisco_aci_server_setup_local)
            for stanza, settings in list(credentials.items()):
                if "cisco_aci_server_setup_settings" in stanza:
                    username = xss.unescape(settings.get("cisco_aci_username", ""))
                    cisco_aci_port = settings.get("cisco_aci_port", "")
                    hostname = xss.unescape(settings.get("cisco_aci_host", ""))
                    cert_name = xss.unescape(settings.get("cert_name", ""))
                    cert_private_key_path = settings.get("cert_private_key_path", "")
                    verify_ssl = settings.get("cisco_aci_ssl", "").strip().upper()

                    if verify_ssl in ("0", "FALSE", "F", "N", "NO", "NONE", ""):
                        verify_ssl = "False"
                    else:
                        verify_ssl = "True"

                    credential = []
                    if cisco_aci_port:
                        cisco_aci_port1 = ":" + cisco_aci_port + ","
                        hostname_list = hostname.split(",")
                        hostname = cisco_aci_port1.join(hostname_list)
                        hostname = hostname + ":" + cisco_aci_port

                    credential = [
                        username,
                        cert_name,
                        cert_private_key_path,
                        verify_ssl,
                    ]
                    apic_credentials[hostname] = credential
    except Exception as e:
        logger.error("Error while reading cisco_aci_server_setup.conf files %s" % (str(e)))
    return apic_credentials


# This function will check for cloud APIC and call functions based on value of arguments.
def _getDataArgs(*args):

    argv = args[0]
    classes = args[1]
    host = args[2]
    session = args[3]
    username = args[4]

    resp = []
    currentTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")
    resp.append(currentTime)
    cloud = False
    global common_host

    try:
        # check for C-APIC
        c_apic = session.get(
            '/api/node/class/fabricNode.json?query-target-filter=eq(fabricNode.role,"controller")',
            timeout=timeout_val,
        )
        if c_apic.status_code == 200:
            if not c_apic.json()["imdata"]:
                cloud = True
            elif str(c_apic.json()["imdata"][0]["fabricNode"]["attributes"]["nodeType"]) == "cloud":
                cloud = True
            else:
                cloud = False

    except requests.exceptions.ConnectionError:
        if "cert_based_auth" in args:
            raise

    except Exception as e:
        logger.error(
            "ACI Error: Could not verify APIC node type for cloud for host= " + str(host) + ", Error=" + str(e)
        )
        pass

    host_split_by_port = host[::-1].split(":", 1)
    host_without_port = host_split_by_port[1][::-1] if len(host_split_by_port) == 2 else host_split_by_port[0][::-1]
    if cloud:
        resp.append(
            "apic_host="
            + common_host
            + " actual_host="
            + host_without_port
            + " Username="
            + username
            + " component=credentials type=cloud"
        )
    else:
        resp.append(
            "apic_host="
            + common_host
            + " actual_host="
            + host_without_port
            + " Username="
            + username
            + " component=credentials"
        )
    print("\t".join(resp))
    print("\n")

    if argv[0] == "-health" or argv[0] == "-fex":
        if cloud:
            classes = classes + ["cloudApp", "cloudExtEPg", "cloudEPg", "fvCtx"]
        _getHealth(session, classes, host_without_port)
    elif argv[0] == "-stats":
        if cloud:
            classes = classes + ["fvCtx"]
        _getStats(session, classes, host_without_port)
    elif argv[0] == "-authentication":
        _getAuthentication(session, classes, host_without_port)
    elif argv[0] == "-classInfo" or argv[0] == "-microsegment":
        if cloud:
            classes = classes + [
                "cloudZone",
                "cloudCtxProfile",
                "vzBrCP",
                "cloudRegion",
                "hcloudCsr",
                "hcloudEndPoint",
                "hcloudInstance",
                "vnsAbsGraph",
                "cloudLB",
                "hcloudCtx",
            ]
        _getClassInfo(session, classes, host_without_port)
    elif argv[0] == "-cloud":
        if cloud:
            _getCloudAPIC(session, classes, host_without_port)
    else:
        logger.error(
            "ACI Error: Please use one of the following switches: "
            "-health, -stats, -authentication, -classInfo, -fex, -microsegment, -cloud"
        )
        sys.exit()
    session.close()


def main(argv):
    """Driver function and entry point of execution."""
    global logger
    classes = argv[1:]
    sessionKey = sys.stdin.readline().strip()

    input_class_name = argv[0]
    logger = logger_manager.get_logger(input_class_name.strip("-"))

    if len(sessionKey) == 0:
        logger.error(
            "ACI Error: Did not receive a session key from splunkd. "
            + "Please enable passAuth in inputs.conf for this "
            + "script\n"
        )
        sys.exit()

    apic_credentials = _getCertCredentials()
    apic_credentials = _getCredentials(apic_credentials, sessionKey)

    if not apic_credentials:
        logger.error(
            "Did not find any credentials configured for ACI. Please configure it first and then enable the scripts"
        )
        return

    global common_host
    for host_str, val in list(apic_credentials.items()):
        if len(val) == 3:
            username = apic_credentials[host_str][0]
            password = apic_credentials[host_str][1]
            verify_ssl = apic_credentials[host_str][2]

            host_list = host_str.split(",")
            host = host_list[0].strip()
            host_split_by_port = host[::-1].split(":", 1)
            # common_host variable consists of only apic_host and not port number
            common_host = host_split_by_port[1][::-1] if len(host_split_by_port) == 2 else host_split_by_port[0][::-1]
            apicUrl = "https://" + str(host)

            if "apic#" in username:
                logger.info("Collecting data using Remote Based Authentication for the host: {0} ".format(host))
            else:
                logger.info("Collecting data using Password Based Authentication for the host: {0} ".format(host))
            try:
                # Connect to the ACI REST interface and authenticate using the specified credentials

                session = aci.Session(apicUrl, username, password, verify_ssl=verify_ssl, logger=logger)
                response = session.login(timeout=timeout_val)
                if not response.ok:
                    logger.error("%% Could not login to APIC:%s, Username:%s" % (host, username))
                    if len(host_list) > 1:
                        session_host = _apicRedundancy(host_list[1:], username, password, verify_ssl)
                        if not session_host:
                            continue
                        else:
                            if not session_host[0]:
                                continue
                            else:
                                session = session_host[0]
                                host = session_host[1]
                    else:
                        continue
            except Exception as err:
                logger.error("ACI Error: Not able to connect to %s Error: %s" % (host, err))
                if len(host_list) > 1:
                    session_host = _apicRedundancy(host_list[1:], username, password, verify_ssl)
                    if not session_host:
                        continue
                    else:
                        if not session_host[0]:
                            continue
                        else:
                            session = session_host[0]
                            host = session_host[1]
                else:
                    continue

            try:
                _getDataArgs(argv, classes, host, session, username)
            except Exception as err:
                if "apic#" in username:
                    logger.error(
                        "ACI Error: Failed to get data using Remote Based Authentication from %s Error: %s"
                        % (host, err)
                    )
                else:
                    logger.error(
                        "ACI Error: Failed to get data using Password Based Authentication from %s Error: %s"
                        % (host, err)
                    )
                continue

        else:
            username = apic_credentials[host_str][0]
            cert_name = apic_credentials[host_str][1]
            cert_private_key_path = apic_credentials[host_str][2]
            verify_ssl = apic_credentials[host_str][3]

            host_list = host_str.split(",")
            host = host_list[0].strip()
            host_split_by_port = host[::-1].split(":", 1)
            # common_host variable consists of only apic_host and not port number
            common_host = host_split_by_port[1][::-1] if len(host_split_by_port) == 2 else host_split_by_port[0][::-1]
            apicUrl = "https://" + str(host)

            logger.info("Collecting data using Certificate Based Authentication for the host: {0} ".format(host))
            try:
                session = aci.Session(
                    apicUrl,
                    username,
                    cert_name=cert_name,
                    key=cert_private_key_path,
                    verify_ssl=verify_ssl,
                    logger=logger,
                )
                _getDataArgs(argv, classes, host, session, username, "cert_based_auth")
            except Exception as err:
                logger.error(
                    "ACI Error: Failed to get data using Certificate Based Authentication from %s Error: %s"
                    % (host, err)
                )
                if len(host_list) > 1:
                    _apicCertRedundancy(
                        host_list[1:],
                        username,
                        cert_name,
                        cert_private_key_path,
                        verify_ssl,
                        argv,
                        classes,
                    )
                continue


resp = []

if __name__ == "__main__":
    main(sys.argv[1:])
    logger.info("Data collection ended.")
