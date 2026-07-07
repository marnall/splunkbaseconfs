#!/usr/bin/env python
"""
    DNS Word Score - Dictionary Creator
    Version 1.2.0
    Stuart Hopkins (shopkins@splunk.com)

    This script will parse a singular word-list file and parse/store it ready for use.
    This involves filtering invalid words, removing duplicate entries, and storing in length/prefix-based indexes
"""

from __future__ import print_function
import os
import re
import sys
import argparse
import gzip

# Folder (within this TA) that contains the word-lists
FOLDER_WORDLISTS = 'wordlists'

# Compiled regular expressions
RE_GOOD_NAME = re.compile(r'[^a-z0-9]', re.IGNORECASE)
RE_GOOD_WORD = re.compile(r'^[a-z]+$')

# Version
VERSION = '1.2.0'


def create_files(args, word_lists):
    """ Create the output files """
    # Create the output folder if it doesn't exist
    file_prefix = str(args.name).lower().strip()
    folder_wl_all = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', FOLDER_WORDLISTS)
    folder_wl_this = os.path.join(folder_wl_all, file_prefix)
    if not os.path.isdir(folder_wl_all):
        print('Creating folder: %s' % folder_wl_all)
        os.mkdir(folder_wl_all)
    if not os.path.isdir(folder_wl_this):
        print('Creating folder: %s' % folder_wl_this)
        os.mkdir(folder_wl_this)
    # Loop through each word-length and then word-prefix
    print('Creating output files')
    for key in sorted(word_lists.keys()):
        for sub_key in sorted(word_lists[key].keys()):
            file_out = os.path.join(folder_wl_this, '%s_%i_%s.txt.gz' % (
                file_prefix, key, sub_key))
            with gzip.open(file_out, 'w') as file_obj:
                for word in word_lists[key][sub_key]:
                    file_obj.write('{}\n'.format(word).encode())


def die(msg, exit_code=1):
    """ Handle an error gracefully """
    print('ERROR: %s' % str(msg), file=sys.stderr)
    sys.exit(exit_code)


def parse_args():
    """ Parse any CLI args """
    parser = argparse.ArgumentParser(description='Process a dictionary file.')
    parser.add_argument('--file', dest='file', required=True,
                        help='Dictionary file to process')
    parser.add_argument('--name', dest='name', required=True,
                        help='The name for this wordlist (only a-z/0-9')
    args = parser.parse_args()
    if not os.path.isfile(args.file):
        die('Specified file does not exist')
    if RE_GOOD_NAME.search(args.name):
        die('Specified name contains invalid characters')
    return args


def parse_file(args, word_lists):
    """ Parse the dictionary file """
    # Open the file for reading
    with open(args.file, 'r') as file_obj:
        # Loop through each line
        loop_count = 0
        for line in file_obj:
            # Increment the count
            loop_count += 1
            # Status update
            if not loop_count % 10000:
                print('- Processing line %i' % loop_count)
            # Skip empty lines
            if not line:
                continue
            # Skip lines beginning with a hash (comment)
            if line.startswith('#'):
                continue
            # Strip and lowercase the line
            new_word = str(line).strip().lower()
            # Determine the length
            word_len = len(new_word)
            # Skip words that are less than two characters
            if word_len < 2:
                continue
            # Determine the first two characters (for performance)
            # Note: This reduces the search runtime from minutes to seconds
            word_pfx = new_word[:2]
            # Skip lines with bad characters
            if not RE_GOOD_WORD.match(new_word):
                print('WARNING: "%s" is not usable' % str(new_word), file=sys.stderr)
            # Check if the lists already exists, and if not, create them
            if word_len not in word_lists:
                word_lists[word_len] = dict()
            if word_pfx not in word_lists[word_len].keys():
                word_lists[word_len][word_pfx] = list()
            # Check if the word is already in the list (avoid duplicates)
            if new_word in word_lists[word_len][word_pfx]:
                print('WARNING: "%s" is already present (duplicate word)' %
                      str(new_word), file=sys.stderr)
            # Add the word to the list
            word_lists[word_len][word_pfx].append(new_word)
            # Finished with this line
        # Finished all lines
    # Finished parsing the file


def sort_lists(word_lists):
    """ Sort the word lists """
    for key in sorted(word_lists.keys()):
        for sec_key in sorted(word_lists[key].keys()):
            word_lists[key][sec_key].sort()


def main():
    """ Main execution """
    print('DNS Word Score - Dictionary Creator - Version %s' % VERSION)
    # Define the word-list dict
    word_lists = dict()
    # Parse the CLI args
    print('Processing CLI args')
    args = parse_args()
    # Parse the dictionary file
    print('Processing dictionary file')
    parse_file(args, word_lists)
    # Sort each list
    print('Sorting lists')
    sort_lists(word_lists)
    # Write each list to a compressed file
    create_files(args, word_lists)
    # Finished
    print('Processing complete')
    sys.exit(0)


if __name__ == '__main__':
    main()
