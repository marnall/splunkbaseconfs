#!/usr/bin/env python
"""
    DNS Word Score - List
    Version 1.2.0
    Stuart Hopkins (shopkins@splunk.com)

    This script will determine which dictionaries are present, determine their size, and return info
"""
# pylint: disable=broad-except,wildcard-import,unused-wildcard-import

from __future__ import print_function
import logging
import sys
from dnsws_shared import *
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration()
class DNSWordScoreListCommand(GeneratingCommand):
    """ The core class that will be called when the script is executed """
    log_debug = Option(
        doc='Enable debug logging',
        require=False,
        default=False,
        validate=validators.Boolean()
    )
    max_length = Option(
        doc='The maximum permitted length of a word',
        require=False,
        default=WORD_LEN_MAX,
        validate=validators.Integer()
    )
    min_length = Option(
        doc='The minimum permitted length of a word (minimum of 2)',
        require=False,
        default=WORD_LEN_MIN,
        validate=validators.Integer()
    )
    use_plurals = Option(
        doc='Use a plural (trailing s) to finish a word',
        require=False,
        default=True,
        validate=validators.Boolean()
    )
    use_singles = Option(
        doc='Use single characters (specifically a and i)',
        require=False,
        default=True,
        validate=validators.Boolean()
    )
    wordlist = Option(
        doc='The word-list(s) to use (comma-separated), or "all" to use all available',
        require=False,
        default='all')
    # Note: You can't directly reference the options here, they aren't set yet
    #       Instead you must reference them in the generate function

    def die(self, msg, exit_code=1):
        """ Handle an error gracefully """
        self.logger.error(str(msg))
        # Log the message to the console otherwise it wont show in the Splunk UI
        print('ERROR: %s' % str(msg))
        sys.exit(exit_code)

    def warn(self, msg):
        """ Handle a warning gracefully """
        self.logger.warning(str(msg))
        # Log the message to the console otherwise it wont show in the Splunk UI
        print('WARNING: %s' % str(msg), file=sys.stderr)

    def generate(self):
        """ Generate the informational events """
        # Enable debug logging if requested
        if self.log_debug:
            self.logger.setLevel(logging.DEBUG)
        self.logger.debug('DNS Word Score Starting - Version %s', str(VERSION))
        # Create the dict to hold all of the loaded words
        words = dict()
        words[0] = list()
        # Load the word-lists
        self.logger.debug('Beginning word-list load')
        word_lists = dnsws_load_wordlists(self, words, is_fatal=False)
        # Create clean lists of word-list names
        all_lists = list()
        csv_list = list()
        raw_list = list()
        for list_name in word_lists['csv']:
            list_name_clean = os.path.basename(list_name)
            all_lists.append(list_name_clean)
            csv_list.append(list_name_clean)
        for list_name in word_lists['raw']:
            list_name_clean = os.path.basename(list_name)
            all_lists.append(list_name_clean)
            raw_list.append(list_name_clean)
        # Return the word-lists loaded
        yield {
            'category': 'lists-loaded-all', 'subcategory': 'count',
            'value': len(all_lists)
        }
        yield {
            'category': 'lists-loaded-all', 'subcategory': 'names',
            'value': sorted(all_lists)
        }
        yield {
            'category': 'lists-loaded-csv', 'subcategory': 'count',
            'value': len(csv_list)
        }
        yield {
            'category': 'lists-loaded-csv', 'subcategory': 'names',
            'value': csv_list
        }
        yield {
            'category': 'lists-loaded-raw', 'subcategory': 'count',
            'value': len(raw_list)
        }
        yield {
            'category': 'lists-loaded-raw', 'subcategory': 'names',
            'value': raw_list
        }
        # Return the total number of words per length, and calculate the total number of words
        words_total = 0
        for word_len in sorted(words.keys()):
            # Skip zero-length (bad words)
            if not word_len:
                continue
            words_by_len = 0
            for word_pfx in words[word_len]:
                words_by_len += len(words[word_len][word_pfx])
            # Add the total words by prefix to the overall word total
            words_total += words_by_len
            # Return the number of words for this prefix
            yield {
                'category': 'wordcount-by-len', 'subcategory': word_len,
                'value': words_by_len
            }
        # Return the total number of words (good and bad)
        yield {
            'category': 'wordcount-total', 'subcategory': 'good', 'value': words_total
        }
        yield {
            'category': 'wordcount-total', 'subcategory': 'bad', 'value': len(words[0])
        }
        # Return the stats for each word-list (CSV)
        for list_name in sorted(word_lists['stats-csv'].keys()):
            list_name_clean = os.path.basename(list_name)
            yield {
                'category': 'list-stats-csv-%s' % list_name_clean,
                'subcategory': 'loaded',
                'value': word_lists['stats-csv'][list_name]['loaded']
            }
            yield {
                'category': 'list-stats-csv-%s' % list_name_clean,
                'subcategory': 'error',
                'value': word_lists['stats-csv'][list_name]['error']
            }
            yield {
                'category': 'list-stats-csv-%s' % list_name_clean,
                'subcategory': 'count_added',
                'value': word_lists['stats-csv'][list_name]['count_added']
            }
            yield {
                'category': 'list-stats-csv-%s' % list_name_clean,
                'subcategory': 'count_skipped',
                'value': word_lists['stats-csv'][list_name]['count_skipped']
            }
        # Return the stats for each word-list (RAW)
        for list_name in sorted(word_lists['stats-raw'].keys()):
            list_name_clean = os.path.basename(list_name)
            yield {
                'category': 'list-stats-raw-%s' % list_name_clean,
                'subcategory': 'loaded',
                'value': word_lists['stats-raw'][list_name]['loaded']
            }
            yield {
                'category': 'list-stats-raw-%s' % list_name_clean,
                'subcategory': 'error',
                'value': word_lists['stats-raw'][list_name]['error']
            }
            yield {
                'category': 'list-stats-raw-%s' % list_name_clean,
                'subcategory': 'count_added',
                'value': word_lists['stats-raw'][list_name]['count_added']
            }
            yield {
                'category': 'list-stats-raw-%s' % list_name_clean,
                'subcategory': 'count_skipped',
                'value': word_lists['stats-raw'][list_name]['count_skipped']
            }
        # Finished processing all records
        self.logger.debug('DNS Word Score Ending')


if __name__ == '__main__':
    dispatch(DNSWordScoreListCommand, sys.argv, sys.stdin, sys.stdout, __name__)
