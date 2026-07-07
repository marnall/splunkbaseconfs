#!/bin/bash
# DNS Word Score - Aspell Dictionary Creator
# Version 1.2.0
# Stuart Hopkins (shopkins@splunk.com)
#
# This script will create a compatible word-list from the installed aspell dictionaries.
# Only the english dictionaries are used at this time


# VARIABLE: Dictionary prefix (change to a different language if required)
DICT_PREFIX='^en_'

# VARIABLE: Required commands
REQ_CMDS="aspell grep sed xargs"

# VARIABLE: Script name (for dictionary creation)
SCRIPT_CREATE="dnsws_createdict.py"

# VARIABLE: Script dir (for later reference)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# VARIABLE: Script dir for the custom app (if present)
SCRIPT_DIR_CUSTOM="${SCRIPT_DIR}/../../TA-dnswordscore_lists/bin"

# VARIABLE: Temp files to use
TMP_FILE_S1="/tmp/dict_creator_$$_$(date +%s 2>/dev/null).stage1"
TMP_FILE_S2="/tmp/dict_creator_$$_$(date +%s 2>/dev/null).stage2"

# VARIABLE: Version
VERSION="1.2.0"


# FUNCTION: Handle an error gracefully
die() {
  echo "ERROR: ${1}"
  [ -f "${TMP_FILE_S1}" ] && rm -f "${TMP_FILE_S1}"
  [ -f "${TMP_FILE_S2}" ] && rm -f "${TMP_FILE_S2}"
  exit 1
}

# FUNCTION: Show the help/usage
show_usage() {
  echo "Usage: ${0} -n dictionary_name"
  echo "Note: The dictionary name can only contain a-z and 0-9"
  exit 2
}


# Begin
echo "DNS Word Score - Aspell Dictionary Creator - Version ${VERSION}"

# Check that the creation script exists
[ -f "${SCRIPT_DIR}/${SCRIPT_CREATE}" ] || die "The ${SCRIPT_CREATE} script is missing"

# Check the required commands are present
for cmd in ${REQ_CMDS} ; do
  command -v "${cmd}" >/dev/null 2>&1 || die "The ${cmd} command was not found"
done

# Determine the python executable to use
cmd_python=
command -v python2.7 >/dev/null 2>&1 && cmd_python="python2.7"
command -v python2 >/dev/null 2>&1 && cmd_python="python2"
command -v python3 >/dev/null 2>&1 && cmd_python="python3"
command -v python >/dev/null 2>&1 && cmd_python="python"
[ -n "${cmd_python}" ] || die "Failed to determine Python version"
echo "Python Cmd: ${cmd_python}"

# Parse the CLI args
list_name=""
while [ -n "${1}" ] ; do
  case "${1}" in
    "-h") show_usage ;;
    "-n") shift ; list_name="${1}" ;;
    *) die "Unknown option: ${1}"
  esac
  shift
done

# Check that a dictionary name was provided
[ -n "${list_name}" ] || show_usage

# Check that the dictionary name is valid
echo -n "${list_name}" 2>/dev/null | grep '[^a-z0-9]' >/dev/null 2>&1 && \
  die "Invalid word-list name provided: ${list_name}"

# Check if the dictionary name already exists
[ ! -d "${SCRIPT_DIR}/../wordlists/${list_name}" ] || \
  die "The specified word-list name already exists"
[ ! -d "${SCRIPT_DIR_CUSTOM}/../wordlists/${list_name}" ] || \
  die "The specified word-list name already exists"

# Check for compatible dictionaries
echo "Checking for compatible dictionaries"
dict_list=$(aspell dump dicts 2>/dev/null |\
  grep "${DICT_PREFIX}" 2>/dev/null |\
  sed -e '/-/d' 2>/dev/null |\
  xargs 2>/dev/null)
[ -n "${dict_list}" ] || die "No compatible dictionaries were found"

# Loop through each dictionary name and export it to the temp file
for dict in ${dict_list} ; do
  echo "Exporting dictionary: ${dict}"
  aspell -d "${dict}" dump master 2>/dev/null |\
  tr '[:upper:]' '[:lower:]' 2>/dev/null |\
  sed -e "/[^a-z]/d" 2>/dev/null |\
  sort -u >>"${TMP_FILE_S1}" 2>/dev/null || die "Failed to export ${dict} dictionary"
  wordcount=$(wc -l "${TMP_FILE_S1}" 2>/dev/null | awk '{print($1)}' 2>/dev/null)
  [ -n "${wordcount}" ] || die "Failed to determine wordcount for dict ${dict}"
  echo "- Wordcount: ${wordcount}"
done

# Clean up the original temp file
echo "Creating finalised word-list"
sort -u <"${TMP_FILE_S1}" >"${TMP_FILE_S2}" 2>/dev/null || \
  die "Failed to created finalised word-list"

# Remove the stage-1 temp file
rm -f "${TMP_FILE_S1}" || die "Failed to remove ${TMP_FILE_S1} file"

# Create the new dictionary
echo "Creating processed dictionary"
"${cmd_python}" "${SCRIPT_DIR}/${SCRIPT_CREATE}" --file "${TMP_FILE_S2}" --name "${list_name}" || \
  die "Failed to create dictionary"

# Remove the stage-2 temp file
rm -f "${TMP_FILE_S2}" || die "Failed to remove ${TMP_FILE_S2} file"

# Finished
echo "Creation Finished"
exit 0
