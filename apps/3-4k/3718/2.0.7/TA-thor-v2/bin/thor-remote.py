#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -*- coding: utf-8 -*-
#
# DISCLAIMER - USE AT YOUR OWN RISK.
#
# Florian Roth

__version__ = "0.3.0"

import sys
import os
from datetime import datetime
import traceback
import re
import ConfigParser
import argparse
import fnmatch
from subprocess import check_output

# Functions ###################################################################

def check_schedule(thor_schedule):

    # System Name
    this_system = os.environ['COMPUTERNAME']
    if args.debug:
        print "DEBUG: Evaluated system name: %s" % this_system

    # Check Schedule
    try:
        with open(thor_schedule) as f:
            content = f.readlines()

        for line in content:

            line = line.rstrip("\n")

            # Skip other lines
            if line.count(";") != 1 or line.startswith("#"):
                if args.debug:
                    print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: Skipping line because of missing " \
                          "';' symbol or '#' at start LINE: %s" % line
                continue

            try:
                # Split line
                ( system_pattern, schedule ) = line.split(";")
                if args.debug:
                    print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: Read schedule entry SYSTEM: %s " \
                          "SCHEDULE: %s" % ( system_pattern, schedule )

                ( min, hour, day, mon, dow ) = re.split('[\s\t]+', schedule)[:5]

                # Not this system
                if fnmatch.fnmatch(this_system, system_pattern):
                    if args.debug:
                        print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: System name does not match " \
                              "the local value"
                    continue

                # Minute will be handled in a special way
                if not check_sched_elem("min", min):
                    if args.debug:
                        print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: Minute value does not match " \
                              "requirements - Defined is: %s" % min
                    continue
                if not check_sched_elem("hour", hour):
                    if args.debug:
                        print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: Hour value does not match " \
                              "requirements - Defined is: %s" % hour
                    # print "no hour"
                    continue
                if not check_sched_elem("day", day):
                    if args.debug:
                        print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: Day value does not match " \
                              "requirements - Defined is: %s" % day
                    # print "no day"
                    continue
                if not check_sched_elem("mon", mon):
                    if args.debug:
                        print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: Month value does not match " \
                              "requirements - Defined is: %s" % mon
                    # print "no mon"
                    continue
                if not check_sched_elem("dow", dow):
                    if args.debug:
                        print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: DayofWeek value does not " \
                              "match requirements - Defined is: %s" % dow
                    # print "no dow"
                    continue

                if args.debug:
                    print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: All schedule elements matched!"
                # If all schedule elements match - return true to start THOR run
                return True

            except Exception:
                if args.debug:
                    print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: Invalid scheduler line: %s" % line
                    traceback.print_exc()
                # Corrupt line
                pass

        # No schedule element matches
        return False

    except:
        traceback.print_exc()


def check_sched_elem(date_elem, value):
    # Split the values if separated by '/'
    values = value.split("/")
    # Now
    now = datetime.now()

    for value in values:
        if value == "*":
            return True
        # Minute
        # Special handling for minute definitions
        if date_elem == "min":
            if int(value) < now.minute:
                return True
        # Hour
        if date_elem == "hour":
            if int(value) == now.hour:
                return True
        # Day
        if date_elem == "day":
            if int(value) == now.day:
                return True
        # Month
        if date_elem == "mon":
            if int(value) == now.month:
                return True
        # Weekday
        if date_elem == "dow":
            # Correction
            if int(value) == 0:
                cor_value = 7
            else:
                cor_value = int(value)
            # Now check
            if cor_value == now.isoweekday():
                return True

    # Else return False
    return False


def is_thor_running():
    result = check_output(r'tasklist /FI "IMAGENAME eq thor.exe"', shell=True)
    if "thor.exe" in result:
        if args.debug:
            print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: THOR is already running. " \
                  "Won't start another scan run."
        return True
    else:
        if args.debug:
            print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: THOR is not running. Clear to go."
    return False


def run_thor(thor_exe, thor_params):
    # Run Thor
    if args.debug:
        print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: Running THOR '%s' %s" % (thor_exe, thor_params)
    os.system(r'"%s" %s' % (thor_exe, thor_params))


def get_application_path():
    try:
        application_path = ""
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)
        if application_path != "":
            # Working directory change skipped due to the function to create TXT, CSV and HTML file on the local file
            # system when thor is started from a read only network share \\server\thor\thor.exe
            # os.chdir(application_path)
            pass
        if application_path == "":
            application_path = os.path.dirname(os.path.realpath(__file__))

        if args.debug:
            print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: Application Path = %s" %application_path
        return application_path

    except Exception, e:
        traceback.print_exc()


# MAIN ########################################################################
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='THOR Remote Executor for Splunk')
    parser.add_argument('--debug', action='store_true', default=False, help='Debug output')

    args = parser.parse_args()

    # Init
    # Default
    application_path = get_application_path()
    # Option 1
    if not os.path.exists(os.path.join(application_path, 'thor-remote.conf')):
        application_path = os.path.expandvars(r'%APP_HOME%\bin')
    # Option 2
    if not os.path.exists(os.path.join(application_path, 'thor-remote.conf')):
        application_path = os.path.expandvars(r'%SPLUNK_HOME%\etc\app\TA-thor-v2\bin')

    # Config
    thor_remote_config = os.path.join(application_path, 'thor-remote.cfg')

    # Parse Config
    config = ConfigParser.ConfigParser()
    try:
        config.read(thor_remote_config)
        thor_location = config.get('general', 'thor_location')
        thor_schedule = config.get('general', 'thor_schedule')
        thor_params = config.get('general', 'thor_params')
        asgard_server = config.get('general', 'asgard_server')  # not yet used - only 'Enterprise' license type supported
    except Exception as e:
        traceback.print_exc()
        print "Cannot find thor-remote.cfg config file in expected location: %s" % thor_remote_config
        sys.exit(1)

    # Schedule.csv
    if not os.path.exists(thor_schedule):
        thor_schedule = os.path.join(application_path, thor_schedule)
    # Thor Executable
    if not os.path.exists(thor_location):
        thor_location = os.path.join(application_path, thor_location)

    if args.debug:
        print "ThorLauncher: Debug: MODULE: ThorRemoteLauncher MESSAGE: Running launcher - using executable '%s', " \
              "using config '%s', using schedule '%s'" % (thor_location, thor_remote_config, thor_schedule)

    # Check and Run
    if check_schedule(thor_schedule):
        if not is_thor_running():
            run_thor(thor_location, thor_params)