#!/usr/bin/env python

# Program name: create_agent.py
# Compatibility: Python 2x
# Purpose - Create a customized version of the TA-metricator-for-nmon
# Licence:

# Copyright 2018 Guilhem Marchand

import sys
import os
import tarfile
import glob
import fnmatch
import argparse
import shutil

version = '2.0.0'

####################################################################
#############           Arguments Parser
####################################################################

# Define Arguments

parser = argparse.ArgumentParser()

parser.add_argument('-f', action='store', dest='INFILE',
                    help='Name of the tgz archive file')

parser.add_argument('--agentname', action='store', dest='TARGET',
                    help='Define the TA Agent name and root directory')

parser.add_argument('--version', action='version', version='%(prog)s ' + version)

parser.add_argument('--debug', dest='debug', action='store_true')

parser.set_defaults(debug=False)

args = parser.parse_args()

# Set debug
if args.debug:
    debug = True

####################################################################
#############           Functions
####################################################################

# String replacement function
# Can be called by:
# findreplace(path, string_to_search, replace_by, file_extension)

def findreplace(directory, find, replace, filepattern):
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in fnmatch.filter(files, filepattern):
            filepath = os.path.join(path, filename)

            # Prevents binaries modification
            if "bin/linux" in filepath:
                if debug:
                    print("file " + str(filename) + " is binary or binary related")
            elif "bin/sarmon" in filepath:
                if debug:
                    print("file " + str(filename) + " is binary or binary related")
            else:
                with open(filepath) as f:
                    s = f.read()
                s = s.replace(find, replace)
                with open(filepath, "w") as f:
                    f.write(s)


####################################################################
#############           Main Program
####################################################################

# Check Arguments
if len(sys.argv) < 2:
    print("\n%s" % os.path.basename(sys.argv[0]))
    print("\nThis utility had been designed to allow creating customized agents for the TA-metricator-for-nmon" \
          " please follow these instructions:\n")
    print("- Download the current release of the technical add-on")
    print("- Ensure to have this Python script and the TGZ archive in the same directory")
    print("- Run the tool: ./create_agent.py and check for available options")
    print("- After the execution, a new agent package will have been created in the resources directory")
    print("- Extract its content to your Splunk deployment server, configure the server class, associated clients and" \
          " deploy the agent")
    print("- Don't forget to set the application to restart splunkd after deployment\n")
    print("\nRun this tool such as:\n")
    print("./create_agent.py -f TA-metricator-for-nmon_xxx.tgz --agentname TA-metricator-for-nmon-custom \n")

    sys.exit(0)

# Will expect in first Argument the name of the tgz Archive of the Application to be downloaded in Splunk Base
if not args.INFILE:
    print("\nERROR: Please provide the tgz Archive file with -f statement\n")
    sys.exit(1)
else:
    infile = args.INFILE

# If the root directory of the TA-nmon is not defined, exit and show message
if not args.TARGET:
    print("ERROR: You must specify the name of the agent package you want to create, and it must be different from" \
          " the default package: TA-metricator-for-nmon")
    sys.exit(0)
else:
    ta_root_dir = args.TARGET

# Avoid naming the TA ascore application
if not "TA-" in ta_root_dir:
    print("ERROR: The TA package name should always start by TA_ as good Splunk practice.")
    sys.exit(1)

# Verify tgz Archive file exists
if not os.path.exists(infile):
    print ('ERROR: invalid file, could not find: ' + infile)
    sys.exit(1)

# Ensure the same package name does not already exist in current directory
if os.path.exists(ta_root_dir):
    print ('ERROR: A directory named ' + ta_root_dir + ' already exist in current directory, please remove it and'
                                                       ' restart')
    sys.exit(1)
elif os.path.exists(ta_root_dir + ".tgz"):
    print ('ERROR: A tgz archive named ' + ta_root_dir + ".tgz" + ' already exist in current directory, please'
                                                                  ' remove it and restart')
    sys.exit(1)

# Extract Archive
tar = tarfile.open(infile)
msg = 'Extracting tgz Archive: ' + infile
print (msg)
tar.extractall()
tar.close()

# Operate

# Get current directory
curdir = os.getcwd()

# Extract the TA-nmon default package in current directory

print ('INFO: Extracting Agent tgz resources Archives')

tgz_files = 'TA-metricator-for-nmon*.tgz'
for tgz in glob.glob(str(tgz_files)):
    tar = tarfile.open(tgz)
    tar.extractall()
    tar.close()

# Rename the TA directory to match agent name

msg = 'INFO: Renaming TA-metricator-for-nmon default agent to ' + ta_root_dir
print (msg)

shutil.copytree('TA-metricator-for-nmon', ta_root_dir)

################# STRING REPLACEMENTS #################

# Replace the old agent name in files

# Achieve string replacements

print ('Achieving files transformation...')

search = 'TA-metricator-for-nmon'
replace = ta_root_dir
findreplace(ta_root_dir, search, replace, "*.sh")
findreplace(ta_root_dir, search, replace, "*.py")
findreplace(ta_root_dir, search, replace, "*.pl")
findreplace(ta_root_dir, search, replace, "*.conf")

print ('Done.')

# Don't use "with" statement in tar creation for Python 2.6 backward compatibility
tar_file = ta_root_dir + '.tgz'
out = tarfile.open(tar_file, mode='w:gz')

try:
    out.add(ta_root_dir)
finally:
    msg = 'INFO: ************* Tar creation done of: ' + tar_file + ' *************'
    print (msg)
    out.close()

# remove Agent directory
if os.path.isdir(ta_root_dir):
        shutil.rmtree(ta_root_dir)

print ('\n*** Agent Creation terminated: To install the agent: ***\n')
print (' - Upload the tgz Archive ' + tar_file + ' to your Splunk deployment server')
print (' - Extract the content of the TA package in $SPLUNK_HOME/etc/deployment-apps/')
print (' - Configure the Application (set splunkd to restart), server class and associated clients to push the new'
       ' package to your clients\n')

# END
print ('Operation terminated.\n')
sys.exit(0)
