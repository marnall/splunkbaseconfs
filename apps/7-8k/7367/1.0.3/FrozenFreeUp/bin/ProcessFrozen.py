
__authors__ = "Dr. Simily Joseph, Subin N"
__copyright__ = "Copyright 2024"
__version__ = "1.0.0"
__maintainer__ = "Subin N"
__status__ = "Production"

import os
import csv
import datetime
import subprocess
import socket
import configparser
import logging
import logging.handlers
# import win32api
import platform

platform = platform.system()

if platform == 'Windows':
    splunk_path = os.getenv('SPLUNK_HOME', 'C:\\Program Files\\Splunk\\')
else:
    splunk_path = os.getenv('SPLUNK_HOME', '/opt/splunk')


def setuplogging():
    scriptpath = os.path.dirname(os.path.abspath(__file__))
    logpath = os.path.join(scriptpath, 'data/log', 'frozen.log')
    # os.chmod(os.path.join(scriptpath, 'data/log'), 0o777)
    logging.basicConfig(level=logging.DEBUG, filename=logpath, filemode="a",
                        format="%(asctime)s %(levelname)s %(message)s")
    logging.info("logging configured", exc_info=True)


config_dict = {}
frozenpath = ""
AgeingRb = 0
Ageing = -1


def IntializeCofig():
    try:
        global frozenpath,AgeingRb,config_dict
        config = configparser.ConfigParser()
        scriptpath = os.path.dirname(os.path.abspath(__file__))
        confpath = os.path.join(scriptpath, 'data/config', 'frozen.conf')
        config.read_file(open(confpath))
        frozenpath = config.get('Frozen_Path', 'Path_frozen')
        Ageingstr = config.get('Frozen_Path', 'Ageing_db_Index')
        try:
            AgeingRb = int(config.get('Frozen_Path', 'Ageing_rb'))
        except Exception as ex:
            AgeingRb = -1

        for keyvalue in Ageingstr.split(";"):
            key, value = keyvalue.split("=")
            config_dict[key] = value

    except Exception as e:
        logging.error('Exception occurred - Configuration ' + str(e), exc_info=True)
        exit()


def ProcessFrozendata():
    try:
        global Ageing
        path = frozenpath
        status = "False"
        bucketlist = []
        directories = os.listdir(path)
        # Iterating bucket directories
        for dirct in directories:
            # arraying index directory name
            isdirct = os.path.join(path, dirct)
            if os.path.isdir(isdirct):
                # invoking frozendb to as per Splunk configuration
                path_idx = path + dirct + "/"
                subdir = os.listdir(path_idx)
                # Iterating the index folders
                for diridx in subdir:
                    isdirctsub = os.path.join(path_idx, diridx)
                    if os.path.isdir(isdirctsub):
                        path_sub = path_idx + diridx + "/"
                        subdirct = os.listdir(path_sub)
                        # Check whether the folder name contains rb_ or db_
                        for dbdir in subdirct:
                            path_file = path_sub + dbdir + "/"
                            if "rb_" in str(dbdir):
                                bucketlist = str(dbdir).split('_')
                                startdate = datetime.datetime.fromtimestamp(int(bucketlist[2])).strftime('%Y-%m-%d')
                                strdat = datetime.datetime.strptime(startdate, '%Y-%m-%d')
                                enddate = datetime.datetime.fromtimestamp(int(bucketlist[1])).strftime('%Y-%m-%d')
                                now = datetime.datetime.now()
                                diff = (now - strdat).days
                                if 0 < AgeingRb < diff:
                                    os.rmdir(path_file)
                                    logging.info("rb buckets removed=%s", str(path_file))
                                    # remove the replicated buckets
                            elif "db_" in str(dbdir):
                                bucketlist = str(dbdir).split('_')
                                startdate = datetime.datetime.fromtimestamp(int(bucketlist[2])).strftime('%Y-%m-%d')
                                strdat = datetime.datetime.strptime(startdate, '%Y-%m-%d')
                                enddate = datetime.datetime.fromtimestamp(int(bucketlist[1])).strftime('%Y-%m-%d')
                                now = datetime.datetime.now()
                                diff = (now - strdat).days

                                for key, value in config_dict.items():
                                    Ageing = -1
                                    if key in str(diridx):
                                        try:
                                            Ageing = int(value)
                                        except Exception as e:
                                            continue
                                        if 0 < Ageing < diff:
                                            os.rmdir(path_file)
                                            logging.info("db buckets removed=%s", str(path_file))
                                            # remove the buckets aged
                                    else:
                                        if '*' in key:
                                            try:
                                                Ageing = int(value)
                                            except Exception as e:
                                                continue
                                            if 0 < Ageing < diff:
                                                os.rmdir(path_file)
                                                logging.info("db buckets removed=%s", str(path_file))
                                                # remove the buckets aged
                        status = True
        if status:
            logging.info("process Completed", exc_info=True)

    except Exception as e:
        logging.error("Exception occurred " + str(e), exc_info=True)


if __name__ == "__main__":
    # Setting up logging
    setuplogging()
    # Read configuration
    IntializeCofig()
    # Process frozen buckets
    ProcessFrozendata()
