# Copyright (C) 2011-2025 Sideview LLC.  All Rights Reserved.

import sys
import os
import json
import traceback
import csv
import logging
import logging.handlers
import time

import splunk
import splunk.rest
import splunk.entity as en

from urllib.parse import quote


APP = "cisco_cdr"
SPLUNK_HOME = os.environ["SPLUNK_HOME"]

def setup_logging(log_level):
    """the app uses its own log file.  we also sneak in a runid=%s guid for the events logged from
    this script. """

    LOG_FILE_PATH = os.path.join(SPLUNK_HOME, "var", "log", "splunk", APP + ".log")
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - runid=%(runid)s %(message)s"

    our_logger = logging.getLogger(APP + "_setup")
    our_logger.propagate = False
    if not our_logger.handlers:

        our_logger.setLevel(log_level)

        handler = logging.handlers.RotatingFileHandler(LOG_FILE_PATH, mode="a")
        handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        our_logger.addHandler(handler)

        extra = {"runid": int(time.time())}
        return logging.LoggerAdapter(our_logger, extra)
    return our_logger

logger = setup_logging(logging.INFO)

def get_rest_api_response(uri, session_key):
    """ simple wrapper around simpleRequest to return just the json response """
    getargs = {
        "output_mode":"json",
        "count":0
    }
    uri = quote(uri)
    _response, content = splunk.rest.simpleRequest(uri, sessionKey=session_key, method="GET",
                                                   raiseAllErrors=True, getargs=getargs)
    return json.loads(content)


def get_app_version(session_key):
    """ try and get the app's version number from REST. """
    uri = "/servicesNS/nobody/%s/configs/conf-app/launcher" % APP
    response = get_rest_api_response(uri, session_key)
    entry = response.get("entry")
    return entry[0]["content"]["version"]


def optimistically_run_search(session_key, spl, is_async=True):
    """ these are simple inputlookup searches that at least in cases so far,
    are going to be on relatively small lookup files.  So we don't actually
    care enough to check whether they error unexpectedly, nor do we wait
    politely until they complete.
    """
    uri = "/servicesNS/nobody/%s/search/jobs/" % APP
    postargs = {
        "search":spl
    }
    # Yes this looks stupid.  Stepping back, it's possible for customers to
    # add workload management rules that cause searches to fail if no
    # timerange is submitted.   Well meaning though this is,  there are no
    # guardrails on that to prevent it from blocking GENERATING searches so...
    # #thisisfine
    if spl.lstrip("| ").find("inputlookup") == 0:
        postargs["earliest_time"] = "-24h"
        postargs["latest_time"] = "now"

    if not is_async:
        postargs["exec_mode"] = "blocking"

    response, _content = splunk.rest.simpleRequest(uri,
                                                   postargs=postargs,
                                                   getargs={},
                                                   raiseAllErrors=True,
                                                   sessionKey=session_key)

    if "status" in response:
        status = int(response["status"])
        #print(spl)
        #print(status)
        if 200 <= status < 300:
            logger.debug("Success. Status %s returned from ( %s ).", status, spl)
            return True
        logger.error("Failure. Status %s returned from ( %s ).", status, spl)
    else:
        logger.error("Failure. No status code returned at all from our POST ( %s ).", spl)
    return False


def find_existing_lookup_files(lookup_dir):
    """ don't comb the desert, just our little part of it """
    lookups_we_have = []
    mysteriously_empty_lookups = []



    for file_name in os.listdir(lookup_dir):

        if file_name.endswith(".csv") and not file_name.endswith(".default.csv"):

            lookup_path = os.path.join(SPLUNK_HOME, "etc", "apps", APP, "lookups", file_name)
            with open(lookup_path, 'r') as lookup_file:

                try:
                    lookup_file_reader = get_reader(lookup_file)
                    #logger.info("looking at header row of %s" % name)
                    #_header_row = next(lookup_file_reader)
                    lookups_we_have.append(file_name.replace(".csv", ""))
                except StopIteration:
                    mysteriously_empty_lookups.append(file_name.replace(".csv", ""))


    return lookups_we_have, mysteriously_empty_lookups


def repair_quality_lookup(session_key):
    """ in 6.3.5 we changed call_quality_to_qos.csv  to call_quality_thresholds.csv
    and there was a really misguided "migration" that ended up just creating a
    thresholds file that had rows for the qos levels, but null thresholds on
    every row.   Here we try and detect that from a PRIOR migration failure
    and replace it with the default.
    """

    lookup_name = "call_quality_thresholds"
    logger.info("checking to see if we need to repair %s", lookup_name)
    lookup_path = os.path.join(SPLUNK_HOME, "etc", "apps", APP, "lookups", lookup_name + ".csv")

    with open(lookup_path, 'r') as lookup_file:
        lookup_file.seek(0)
        reader = csv.DictReader(lookup_file, delimiter=',')
        has_any_populated_rows = False
        has_any_empty_rows = False
        for row in reader:
            if row.get("field", "") != "" and row.get("quality", "") != "" and row.get("min", "") != "" and row.get("max", "") != "":
                has_any_populated_rows = True
            else:
                has_any_empty_rows = True
        if has_any_populated_rows and has_any_empty_rows:
            logger.warning("this is strange, but %s has some empty rows and some populated rows", lookup_name)
        elif not has_any_populated_rows:
            logger.warning("no populated rows were seen in %s.csv. This means a prior migration created an unusable version. Resetting the file to default values. ", lookup_name)
            spl = "| inputlookup call_quality_thresholds_default | outputlookup create_empty=false override_if_empty=false call_quality_thresholds"
            if optimistically_run_search(session_key, spl, False):
                logger.info("damaged %s.csv was detected and successfully reset to default", lookup_name)
            else:
                logger.error("something went wrong when we tried to repair %s.csv", lookup_name)


def get_correct_field_order(session_key, lookup_name):
    """
    A simple utility that gets the lookups "default"" stanza in transforms,
    goes to the actual filename it refers to
    and fishes out the header row, returning it as an array.
    """
    uri = "/servicesNS/nobody/%s/configs/conf-transforms/%s_default" % (APP, lookup_name)
    response = get_rest_api_response(uri, session_key)
    content = response.get("entry")[0].get("content")
    filename = content.get("filename")
    lookup_path = os.path.join(SPLUNK_HOME, "etc", "apps", APP, "lookups", filename)
    field_list = []
    with open(lookup_path, "r") as f:
        field_list = f.readline().strip()
        field_list = field_list.split(",")
    return field_list





def create_missing_lookups(session_key, lookups_we_need):
    """
    we can't ship the actual files of file-based lookups because then all
    local changes would be clobbered on every update.
    So we ship foo.default.csv and then here we copy those files over to make
    the foo.csv if there isn't one there.
    """

    lookup_dir = os.path.join(SPLUNK_HOME, "etc", "apps", APP, "lookups")
    lookups_we_created = []
    mysteriously_empty_lookup_files = []
    try:
        lookups_we_have, mysteriously_empty_lookup_files = find_existing_lookup_files(lookup_dir)
    except Exception:
        logger.error("Unexpected exception while trying to look on disk for what lookup files we have. \n%s", traceback.format_exc())

    for required_lookup in lookups_we_need:
        if required_lookup in mysteriously_empty_lookup_files:
            logger.warning("We found a %s.csv lookup file that was entirely empty. This is an error state but we will fix by replacing its contents with the contents of the corresponding default csv file.", required_lookup)

        if required_lookup in lookups_we_have:
            logger.debug("we have a lookup file already generated on disk for %s.csv", required_lookup)
        else:


            logger.info("%s.csv is missing (or empty) but we will create one from the corresponding default file.", required_lookup)

            # wouldn't it be nice if we could just do $things$ here, and
            # then tell SHC hey we did $things$ can you please replicate them?
            # well,  we sort of can.
            # POST to /services/replication/configuration/lookup-update-notify w/ app= user= and filename=
            # except.... this seems like "you can probably fly a 747 - try it and see"


            # we go the extra mile and fill the file with the exact same canonical field order,
            # cause it's ugly when all customer lookups have their columns sorted alphabetically.
            # (and outputlookup has no keepcolorder=true option boo)

            field_order = get_correct_field_order(session_key, required_lookup)

            field_expression = ""
            if len(field_order) > 0:
                field_expression = "| fields %s *" % " ".join(field_order)
            spl = "| inputlookup %s_default %s | outputlookup create_empty=false override_if_empty=false %s" % (required_lookup, field_expression, required_lookup)


            #logger.info(spl)
            if optimistically_run_search(session_key, spl, False):
                logger.info("%s.csv was created using the default %s csv file.", required_lookup, required_lookup)
                lookups_we_created.append(required_lookup)
            else:
                logger.error("our search to generate the %s.csv lookup ( %s ) failed.", required_lookup, spl)


    return lookups_we_have, lookups_we_created

def populate_clusters_lookup(session_key):
    """ this does it all.
    - If clusters.csv is empty and there is no indexed CDR data, it will populate it using
      clusters_default
    - If clusters.csv has rows but there are clusters in the indexed data (-90d) that are NOT in
      the lookup, it will add them.
    - If clusters.csv has rows that are NOT in the indexed data it will leave them alone.
    - If clusters.csv has rows with the long-dead clusterName and clusterGroup fields, it will
      migrate them to name, group.
    """
    spl = """
| tstats count as events WHERE `custom_index` earliest_time="-90d" GROUPBY globalCallId_ClusterID
| rename globalCallId_ClusterID as clusterId
| inputlookup clusters append=t
| inputlookup clusters_default append=t
| streamstats count as row
| search NOT (group="PLACEHOLDER_GROUP" row>1) NOT clusterId="globalCallId_ClusterID"
| eval name=if(isnull(clusterName),name,clusterName)
| eval group=if(isnull(clusterGroup),group,clusterGroup)
| reverse
| dedup clusterId
| reverse
| fillnull locale value="US"
| fillnull axlHost value="*"
| fields clusterId name group locale axlHost
| outputlookup create_empty=false override_if_empty=false clusters
    """
    if optimistically_run_search(session_key, spl):
        logger.info("Any new clusters seen in the last 90 days were added to clusters.csv")
    else:
        logger.error("something went wrong when we tried to add new clusters to the clusters lookup")

def devices_lookup_fillnull_clusterId_lastUpdated(session_key):
    """ If the columns are actually different at startup, the migration actually runs
    and it will have fillnulled clusterId.
    however.... this is here for the cases where the columns are NOT different and someone
    just made a mistake... we just sneak in the * values if clusterId is blank.
    """
    field_expression = ""
    try:
        lookup_path = os.path.join(SPLUNK_HOME, "etc", "apps", APP, "lookups", "devices.7.8.default.csv")
        with open(lookup_path, "r") as f:
            field_list = f.readline()
            if field_list:
                field_expression = "| fields " + field_list
    except Exception as e:
        logger.warning("something went wrong when we tried to write the new devices lookup with the right field order")
        field_expression = ""

    things_cleaned_up = 0
    spl = """
        | inputlookup devices
        | fillnull clusterId value="*"
        | fillnull lastUpdated value=""
        %s
        | outputlookup create_empty=false override_if_empty=false devices
    """ % field_expression
    if optimistically_run_search(session_key, spl):
        logger.info("We made sure the devices lookup had no null values of clusterId")
        things_cleaned_up = 1
    else:
        logger.error("something went wrong when we tried to fillnull the clusterId field on the devices lookup.")
    return things_cleaned_up


def get_reader(lookup_file):
    """ deal with whatever python2 and python3 gremlins, and given a file pointer,
    give back a working csv reader instance"""
    lookup_file.seek(0)
    #try:
    #    reader = csv.reader(codecs.iterdecode(lookup_file, 'utf-8'), delimiter=',')
    #except Exception:
    return csv.reader(lookup_file, delimiter=',')


def migrate_lookup(session_key, lookup_name, correct_columns, migration_search):
    """
    returns False if it did nothing.   True if it actually ran the migration_search.
    """

    lookup_path = os.path.join(SPLUNK_HOME, "etc", "apps", APP, "lookups", lookup_name + ".csv")

    with open(lookup_path, 'r') as lookup_file:

        lookup_file_reader = get_reader(lookup_file)

        try:
            header_row = next(lookup_file_reader)
        except StopIteration:
            logger.error("WARN - while checking %s.csv for migration cases, we discovered it is actually an empty file.", lookup_name)
            return False
        if set(header_row) == set(correct_columns):
            logger.info("The %s lookup has the correct fields and does not need to be migrated", lookup_name)
        else:
            logger.info("The %s.csv lookup has columns matching an old convention and is about to be migrated", lookup_name)
            logger.info("The %s.csv lookup has columns of %s whereas it should have columns of %s", lookup_name, ",".join(header_row), ",".join(correct_columns))

            if optimistically_run_search(session_key, migration_search):
                logger.info("It appears that our search to migrate %s.csv was successful",  lookup_name)
                return True
            logger.error("Unfortunately our search to migrate %s.csv seems to have failed. ( %s )", lookup_name, migration_search)
    return False

def run_migration_and_ftr_checks(session_key):
    """ time to make the donuts"""

    try:
        version = get_app_version(session_key)
    except Exception:
        logger.error("Unexpected exception. what should have been a straightforward request to get the app version hit an exception \n%s", traceback.format_exc())
        version = "unknown"

    logger.info("Splunk must have restarted. app=%s version=%s. Migration and first-time-run checks are about to run.", APP, version)

    #clusters is populated and/or migrated and/or appended-to separately from the others.
    try:
        populate_clusters_lookup(session_key)
    except Exception:
        logger.error("Unexpected exception while trying to populate the clusters lookup. \n%s", traceback.format_exc())


    # we have to give Splunk a moment to think about things or else the lookup isn't actually on disk yet
    time.sleep(3)

    try:
        lookups_we_had, lookups_we_created = create_missing_lookups(session_key, ["groups", "cidr", "devices", "call_quality_thresholds" ,"data_types"])
    except Exception:
        logger.error("Unexpected exception while trying to create missing lookups. \n%s", traceback.format_exc())
        lookups_we_had = []
        lookups_we_created = []

    # if it was already there prior, it wont be in lookups_we_created, and it means it was
    # created in some prior app upgrade.   Hence we check for the damage that migration
    # used to do from 6.3.5 through 6.3.7  (this code was added in 6.3.8)
    if "call_quality_thresholds" in lookups_we_had:
        try:
            repair_quality_lookup(session_key)
        except Exception:
            logger.error("Unexpected exception while checking the call_quality_thresholds lookup for a migration problem that might have occurred from 6.3.5 to 6.3.7.\n%s" , traceback.format_exc())



    # if we just created it,  it won't be an old one that needs any migration.
    to_try_migrating = {}
    for lookup in ["cidr", "devices", "groups", "call_quality_thresholds"]:
        if lookup not in lookups_we_created:
            to_try_migrating[lookup] = 1


    migration_cases = {
        "groups": {
            "correct_columns":["number", "name", "group", "subgroup", "subgroup2", "subgroup3", "subgroup4"],
            "lookup_file":"groups",
            "migration_search": """
    | inputlookup groups | fillnull value="" subgroup2 subgroup3 subgroup4
    | append [
      | stats count | fields - count | eval number="_PLACEHOLDER" | eval name="PLACEHOLDER NAME" | eval group="PLACEHOLDER GROUP" | eval subgroup="PLACEHOLDER SUBGROUP"
    ]
    | dedup number
    | streamstats count
    | search (number="_PLACEHOLDER" AND count="1") OR NOT name="PLACEHOLDER_NAME"
    | fields number name group subgroup subgroup2 subgroup3 subgroup4
    | outputlookup create_empty=false override_if_empty=false groups
        """
        },

        "devices": {
            "correct_columns":["name", "productName", "department", "description", "className", "subclassName", "devicePool", "mailId", "userFullName", "userId", "callingSearchSpaceName", "protocol", "securityProfileName", "directoryNumber", "clusterId", "lastUpdated"],
            "lookup_file":"devices",
            "migration_search": """
    | inputlookup devices
    | search NOT name="PLACEHOLDER_DEVICE"
    | eval name=if(isnotnull(deviceName),deviceName,name)
    | eval devicePool=case(isnotnull(devicePoolName),devicePoolName,isnotnull(devicepool),devicepool,true(),devicePool)
    | eval mailId=if(isnotnull(mailid),mailid,mailId)
    | eval userFullName=if(isnotnull(userfullname),userfullname,userFullName)
    | eval userId=if(isnotnull(userid),userid,userId)
    | fields - deviceName devicePoolName mailid userfullname userid
    | inputlookup devices_default append=t
    | streamstats count
    | search (name="PLACEHOLDER_DEVICE" AND count="1") OR NOT name="PLACEHOLDER_DEVICE"
    | fields name productName department description className subclassName devicePool mailId userFullName userId callingSearchSpaceName protocol securityProfileName directoryNumber clusterId lastUpdated
    | fillnull clusterId value="*"
    | outputlookup create_empty=false override_if_empty=false devices
                """
        },
        "cidr": {
            "correct_columns":["subnet", "site_name", "country", "subnet_description", "lat", "long"],
            "lookup_file":"cidr",
            "migration_search": """
    | inputlookup cidr
    | eval site_name=if(isnull(site_name),location,site_name)
    | fields subnet site_name country subnet_description lat long
    | outputlookup create_empty=false override_if_empty=false cidr
    """
        },
        "call_quality_thresholds": {
            "correct_columns":["field", "min", "max", "quality"],
            "lookup_file":"call_quality_thresholds",
            "migration_search": """
    | inputlookup call_quality_thresholds
    | eval already_existing=1
    | inputlookup append=t call_quality_thresholds_default
    | fillnull already_existing value=0
    | eventstats max(already_existing) as some_rows_already_exist
    | where already_existing=some_rows_already_exist
    | eval quality=if(isnotnull(quality),quality,qos)
    | fields field min max quality
    | outputlookup create_empty=false override_if_empty=false call_quality_thresholds
        """
        },
    }

    """
    CLUSTERS
    -- old header was clusterId, clusterName, clusterGroup
    -- then it had clusterId,name,group,locale
    -- then in early 2024 we added axlHost so it was   clusterId,name,group,locale,axlHost



    DEVICES
    -- oldest header was callingSearchSpaceName,description,deviceName,devicePoolName,protocol,securityProfileName
       (then we changed deviceName to name,   devicePoolName to devicepool and added department mailid userfullname userid)
    -- older header was name department description devicepool mailid userfullname userid callingSearchSpaceName protocol securityProfileName
       (then we put devicepool mailid userfullname and userid to proper camel case)
    -- old header was name,department,description,devicePool,mailId,userFullName,userId,callingSearchSpaceName,protocol,securityProfileName
       (then we added productName)
    -- NEW Header is name,productName,department,description,devicePool,mailId,userFullName,userId,callingSearchSpaceName,protocol,securityProfileName
    -- (at some point we added className, subclassName and directoryNumber)
    -- early 2024 we also added a clusterId which starts out with value="*", and also lastUpdated.
       name,productName,department,description,className,subclassName,devicePool,mailId,userFullName,userId,callingSearchSpaceName,protocol,securityProfileName,directoryNumber,clusterId,lastUpdated



    SITES
    -- older header was subnet,location,lat,long.
    -- old   header was subnet site_name country subnet_description lat long

    """
    actually_migrated = {}

    for lookup_name in to_try_migrating:
        try:

            if migrate_lookup(
                    session_key,
                    migration_cases[lookup_name]["lookup_file"],
                    migration_cases[lookup_name]["correct_columns"],
                    migration_cases[lookup_name]["migration_search"]
            ):
                actually_migrated[lookup_name] = 1
        except Exception:
            logger.error("Unexpected exception while trying to migrate the %s lookup. \n%s", lookup_name, traceback.format_exc())


    if "devices" not in lookups_we_created:
        try:
            things_cleaned_up = devices_lookup_fillnull_clusterId_lastUpdated(session_key)
        except Exception:
            things_cleaned_up = 0
            logger.error("Unexpected exception while trying to fillnull the clusterId and lastUpdated fields in the devices lookup. \n%s", traceback.format_exc())

    if things_cleaned_up == 0 and not bool(actually_migrated) and not lookups_we_created:
        logger.info("No first-time-run or migration checks were hit so we did nothing.")

    logger.info("completed app_setup script success=True")

def is_rest_api_responding(session_key):
    """ scripted inputs like this execute not AFTER splunkd has completely restarted but kind of
    AS it is restarting.  Here we check whether we can hit the app endpoint.
    If so, we return true yay.
    if not we sleep and retry up to 20 times.
     """
    for x in range(0, 30):  # try 20 times
        try:
            get_app_version(session_key)
            return True
        except splunk.SplunkdConnectionException:
            if x < 10:
                logger.warning("splunk started our scripted input before splunkd had the rest api up.  We have learned that this happens though, so this script is going to wait 2 seconds and try again.")
                time.sleep(2)
            else:
                logger.error("we tried and retried, but the splunk REST API just seems DOA so our first-time-run checks and migration checks did not run. Exiting.")
                break
        except splunk.AuthenticationFailed:
            logger.error("the session key provided to this scripted input wasn't accepted by Splunkd. This should never happen. Exiting.")
            logger.error(traceback.format_exc())
            break


        except Exception:
            logger.error("something unexpected went wrong during our retries to see if Splunk REST API was up. Exiting.")
            logger.error(traceback.format_exc())
            break

    return False
