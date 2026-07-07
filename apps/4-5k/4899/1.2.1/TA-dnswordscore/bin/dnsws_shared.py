#!/usr/bin/env python
"""
    DNS Word Score - Shared Code
    Version 1.2.0
    Stuart Hopkins (shopkins@splunk.com)

    This script contains shared values/code referenced by other scripts.
"""
# pylint: disable=broad-except

import csv
import gzip
import os
import re

# Values indicating true/false (for csv ingest)
BOOL_VAL_FALSE = ['f', 'false', 'n', 'no', '0']
BOOL_VAL_TRUE = ['t', 'true', 'y', 'yes', '1']

# CSV columns
CSV_COLUMN_WORD = 'word'
CSV_COLUMN_ENABLED = 'enabled'
CSV_COLUMNS_REQUIRED = [CSV_COLUMN_ENABLED, CSV_COLUMN_WORD]

# Folders (within this TA) that contains the word-lists
# Note: Raw files are in a separate folder to avoid confusing Splunk with incompatible files
FOLDER_CUSTOMAPP = 'TA-dnswordscore_lists'
FOLDER_LOOKUPS = 'lookups'
FOLDER_WORDLISTS = 'wordlists'

# Compiled regular expressions
RE_EXCLUDE = re.compile(r'_exclude\.csv$', re.IGNORECASE)
RE_FNAME_PARTS = re.compile(r'_(\d+)_([a-z]{2})\.txt\.gz$')
RE_LIST_NAME = re.compile(r'[^a-z._]+')
RE_PUNCT_SPLIT = re.compile(r'[^a-z0-9]+')
RE_PUNCT_CLEAN = re.compile(r'[^a-z]+')
RE_TLD_1PART = re.compile(r'\.[a-z]{3}$')
RE_TLD_2PART = re.compile(r'\.[a-z]{1,3}\.[a-z]{2}$')
RE_TLD_ARPA = re.compile(r'\.in-addr\.arpa$')
RE_TLD_EC2 = re.compile(r'^ec2-\d{1,3}-\d{1,3}-\d{1,3}-\d{1,3}\.')
RE_TLD_IP = re.compile(r'^\d{1,3}-\d{1,3}-\d{1,3}-\d{1,3}\.')
RE_TLD_LOCAL = re.compile(r'_(?:tcp|udp)\.local$')
RE_TLD_WWW = re.compile(r'^www\.')

# Version
VERSION = '1.2.0'

# Word settings
# Note: No english word comes close to the limit, so there is no need to change
WORD_LEN_MIN = 2
WORD_LEN_MAX = 50


def dnsws_create_subpart_dict(order, remain=''):
    """ Create the subpart-compatible dict for searching """
    subpart = dict()
    subpart['order'] = order
    subpart['matched_chars'] = 0
    subpart['matched_words'] = list()
    subpart['remains'] = remain
    subpart['remains_len'] = len(subpart['remains'])
    if subpart['remains']:
        subpart['remains_pfx'] = str(remain[:2])
    else:
        subpart['remains_pfx'] = ''
    return subpart


def dnsws_find_wordlist(self, list_name):
    """ Find the specified word-list, and return its type/path """
    self.logger.debug('Attempting to find word-list: %s', list_name)
    # Define the base paths to check (for csv and raw)
    base_paths = [
        os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'),
        os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', FOLDER_CUSTOMAPP)
    ]
    # Loop through each base path and check for compatible word-lists
    for base_path in base_paths:
        self.logger.debug('Checking for matching word-list in path: %s', base_path)
        # Check for a raw match (local)
        path_raw = os.path.join(base_path, FOLDER_WORDLISTS, list_name)
        if os.path.isdir(path_raw):
            # Match found
            self.logger.debug('Raw word-list found: %s', list_name)
            return 'raw', path_raw
        # Check for a CSV match
        path_csv = os.path.join(base_path, FOLDER_LOOKUPS, list_name)
        if os.path.isfile(path_csv):
            # Match found
            self.logger.debug('CSV word-list found: %s', list_name)
            return 'csv', path_csv
    # No match at this point
    return None, None


def dnsws_find_wordlists(self, word_lists):
    """ Find all compatible word-lists and store their names """
    self.logger.debug('Attempting to find all compatible word-lists')
    # Define the base paths to check (for csv and raw)
    base_paths = [
        os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'),
        os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', FOLDER_CUSTOMAPP)
    ]
    # Loop through each base path and check for compatible word-lists
    for base_path in base_paths:
        self.logger.debug('Checking for word-lists in path: %s', base_path)
        # Raw lists
        self.logger.debug('Checking for raw word-lists')
        # Check the required folder exists
        path_raw = os.path.join(base_path, FOLDER_WORDLISTS)
        if os.path.isdir(path_raw):
            # Folder exists, check for lists within
            for name in sorted(os.listdir(path_raw)):
                # Skip anything that isn't a folder
                path_raw_list = os.path.join(path_raw, name)
                if not os.path.isdir(path_raw_list):
                    continue
                # Folder found, add it to the list
                self.logger.debug('Found raw word-list: %s', name)
                word_lists['raw'].append(str(path_raw_list))
        # All raw lists in the base path added at this point
        # CSV lists
        self.logger.debug('Checking for csv word-lists')
        # Check the required folder exists
        path_csv = os.path.join(base_path, FOLDER_LOOKUPS)
        if os.path.isdir(path_csv):
            # Folder exists, check for lists within
            for name in sorted(os.listdir(path_csv)):
                # Skip anything that isn't a file
                path_csv_list = os.path.join(path_csv, name)
                if not os.path.isfile(path_csv_list):
                    continue
                # File found, check its a csv
                if not path_csv_list.endswith('.csv'):
                    continue
                # CSV found, add it to the list
                self.logger.debug('Found csv word-list: %s', name)
                word_lists['csv'].append(str(path_csv_list))
        # All csv lists in the base path added at this point
    # Finished finding word-lists
    self.logger.debug('Finished detecting compatible word-lists')


def dnsws_load_wordlist_csv(self, word_lists, words, list_path):
    """ Load the specified csv word-list into RAM """
    self.logger.debug('Loading csv word-list: %s', list_path)
    # Create the stats entry for this list
    word_lists['stats-csv'][list_path] = dict()
    word_lists['stats-csv'][list_path]['count_added'] = 0
    word_lists['stats-csv'][list_path]['count_skipped'] = 0
    word_lists['stats-csv'][list_path]['error'] = None
    word_lists['stats-csv'][list_path]['loaded'] = False
    # Determine if this is an exclusion list or not
    if RE_EXCLUDE.search(list_path):
        self.logger.debug('- List is an exclusion list')
        is_excludes = True
    else:
        self.logger.debug('- List is not an exclusion list')
        is_excludes = False
    # Open the CSV file for reading
    try:
        with open(list_path, 'rt') as csv_obj:
            self.logger.debug('CSV word-list opened, creating CSV reader')
            try:
                csv_reader = csv.DictReader(csv_obj, delimiter=',', quotechar='"')
            except Exception as exc:
                self.logger.error('Failed to create CSV reader: %s', str(exc))
                raise
            # Check the correct columns exist
            self.logger.debug('Checking for required columns')
            try:
                for field_name in CSV_COLUMNS_REQUIRED:
                    if field_name not in csv_reader.fieldnames:
                        self.warn('Required column %s is missing in %s' % (field_name, list_path))
                        return
            except Exception as exc:
                self.logger.error('Failed to check for required columns: %s', str(exc))
                raise
            # Loop through each row
            self.logger.debug('Reading each CSV row')
            try:
                for row in csv_reader:
                    # Clean the word
                    word = str(row[CSV_COLUMN_WORD]).strip().lower()
                    # Calculate the length of the word
                    word_len = len(word)
                    # Check if the word is long enough
                    if word_len < self.min_length:
                        word_lists['stats-csv'][list_path]['count_skipped'] += 1
                        continue
                    # Check if the word is short enough
                    if word_len > self.max_length:
                        word_lists['stats-csv'][list_path]['count_skipped'] += 1
                        continue
                    # Check if the word is enabled for use
                    if str(row[CSV_COLUMN_ENABLED]).lower() not in BOOL_VAL_TRUE:
                        word_lists['stats-csv'][list_path]['count_skipped'] += 1
                        continue
                    # Check for unsupported characters
                    if RE_PUNCT_CLEAN.search(word):
                        self.logger.debug('Found unsupported word in %s: %s', list_path, str(word))
                        word_lists['stats-csv'][list_path]['count_skipped'] += 1
                        continue
                    # Handle if this is an excluded word
                    if is_excludes:
                        # Check if the word is already in the excludes list
                        if word in words[0]:
                            word_lists['stats-csv'][list_path]['count_skipped'] += 1
                            continue
                        # Add the word to the exclusion list
                        word_lists['stats-csv'][list_path]['count_added'] += 1
                        words[0].append(word)
                    else:
                        # Get the first two characters of the word
                        word_pfx = word[:2]
                        # Create the entry in the dict if it doesn't already exist
                        if word_len not in words:
                            words[word_len] = dict()
                        if word_pfx not in words[word_len]:
                            words[word_len][word_pfx] = list()
                        # Check if the word already exists
                        if word in words[word_len][word_pfx]:
                            word_lists['stats-csv'][list_path]['count_skipped'] += 1
                            continue
                        # Store the word
                        word_lists['stats-csv'][list_path]['count_added'] += 1
                        words[word_len][word_pfx].append(word)
                # Finished processing all entries
            except Exception as exc:
                self.logger.error('Failed to parse CSV rows: %s', str(exc))
                raise
        # Finished word-list processing
        word_lists['stats-csv'][list_path]['loaded'] = True
        self.logger.debug('Added %i word(s), skipped %i word(s)',
                          word_lists['stats-csv'][list_path]['count_added'],
                          word_lists['stats-csv'][list_path]['count_skipped'])
        self.logger.debug('Finished loading csv word-list')
    except Exception as exc:
        self.logger.error('Failed to open/parse CSV: %s (%s)', list_path, str(exc))
        word_lists['stats-csv'][list_path]['error'] = str(exc)


def dnsws_load_wordlist_raw(self, word_lists, words, list_path):
    """ Load the specified raw word-list into RAM """
    self.logger.debug('Loading raw word-list: %s', list_path)
    # Create the stats entry for this list
    word_lists['stats-raw'][list_path] = dict()
    word_lists['stats-raw'][list_path]['count_added'] = 0
    word_lists['stats-raw'][list_path]['count_skipped'] = 0
    word_lists['stats-raw'][list_path]['error'] = None
    word_lists['stats-raw'][list_path]['loaded'] = True
    # Loop through every file/folder in the word-list path
    for name in sorted(os.listdir(list_path)):
        file_name = os.path.join(list_path, name)
        # Skip anything that isn't a file
        if not os.path.isfile(file_name):
            continue
        # Check for the correct file extension
        if not name.endswith('.txt.gz'):
            continue
        # Split the name to determine the lengths and the prefix
        name_split = RE_FNAME_PARTS.search(name)
        # Skip invalid filenames
        if not name_split:
            self.warn('Found file with incorrect fields: %s' % name)
            continue
        if name_split.lastindex != 2:
            self.warn('Incorrect split-parts: %s (%s)' % (name, str(name_split)))
            continue
        # Store the split groups separately for performance
        list_len = int(name_split.group(1))
        list_pfx = str(name_split.group(2))
        # Check if the words are long enough
        if list_len < self.min_length:
            word_lists['stats-raw'][list_path]['count_skipped'] += 1
            continue
        if list_len > self.max_length:
            word_lists['stats-raw'][list_path]['count_skipped'] += 1
            continue
        # Create the entry in the dict if it doesn't already exist
        if list_len not in words:
            words[list_len] = dict()
        if list_pfx not in words[list_len]:
            words[list_len][list_pfx] = list()
        # Open the compressed file for reading
        try:
            # Note: Must be opened in rt mode as binary wont work correctly
            with gzip.open(file_name, 'rt') as file_obj:
                # Process each entry
                for line in file_obj:
                    # Create a clean version of the word
                    word = str(line).rstrip().lower()
                    # Check if the entry already exists (as multiple lists are supported)
                    if word in words[list_len][list_pfx]:
                        word_lists['stats-raw'][list_path]['count_skipped'] += 1
                        continue
                    # Add the entry to the list
                    word_lists['stats-raw'][list_path]['count_added'] += 1
                    words[int(name_split.group(1))][str(name_split.group(2))].append(word)
            word_lists['stats-raw'][list_path]['loaded'] = True
        except Exception as exc:
            word_lists['stats-raw'][list_path]['loaded'] = False
            self.logger.error('Failed to open/parse RAW: %s (%s)', file_name, str(exc))
            word_lists['stats-raw'][list_path]['error'] = str(exc)
    # Finished word-list processing
    self.logger.debug('Added %i word(s), skipped %i word(s)',
                      word_lists['stats-raw'][list_path]['count_added'],
                      word_lists['stats-raw'][list_path]['count_skipped'])
    self.logger.debug('Finished loading raw word-list')


def dnsws_load_wordlists(self, words, is_fatal=True):
    """ Load the specified word-list(s) """
    self.logger.debug('Loading specified word-lists: %s', str(self.wordlist))
    # Create the holder for the lists to load and their stats
    word_lists = dict()
    word_lists['csv'] = list()
    word_lists['raw'] = list()
    word_lists['stats-csv'] = dict()
    word_lists['stats-raw'] = dict()
    # Check the specified word-list exists (folder)
    if not self.wordlist:
        self.die('No word-list(s) specified')
    # Check if specific lists were specified
    if str(self.wordlist) == 'all':
        # All lists specified, determine the available names
        dnsws_find_wordlists(self, word_lists)
    else:
        # Split the list and check each one exists
        lists_split = str(self.wordlist).split(',')
        # Loop through all split entries
        for list_name in lists_split:
            # Clean the name
            list_name = str(list_name).strip().lower()
            if not list_name:
                self.warn('Empty list name provided')
                continue
            # Check the name is valid
            if RE_LIST_NAME.search(list_name):
                self.warn('Invalid list name provided: %s' % str(list_name))
                continue
            # Find the list in the defined folders
            list_type, list_path = dnsws_find_wordlist(self, list_name)
            if not list_type:
                self.warn('Specified list does not exist: %s' % str(list_name))
            # Add the list-name for processing
            word_lists[list_type].append(list_path)
    # Load the word-list(s) into RAM
    for list_name in word_lists['raw']:
        dnsws_load_wordlist_raw(self, word_lists, words, list_name)
    for list_name in word_lists['csv']:
        dnsws_load_wordlist_csv(self, word_lists, words, list_name)
    # Log the number of excluded words
    self.logger.debug('Number of excluded words: %i', len(words[0]))
    # Remove any excluded words from the final list
    for word in words[0]:
        # Calculate the length of the word
        word_len = len(word)
        # Check if there is a dict for words this length
        if word_len not in words:
            continue
        # Get the first two characters of the word
        word_pfx = word[:2]
        # Check if there is a list entry for the first two characters
        if word_pfx not in words[word_len]:
            continue
        # Check if the entry is in the list
        if word in words[word_len][word_pfx]:
            self.logger.debug('Removing word from final list: %s', word)
            words[word_len][word_pfx].remove(word)
    # Check at least one file was loaded
    if not words and is_fatal:
        self.die('No compatible word-lists files were found')
    # Return the word-list info
    return word_lists
