#!/usr/bin/env python
"""
    DNS Word Score - Parser
    Version 1.2.0
    Stuart Hopkins (shopkins@splunk.com)

    This script will parse each passed entry (in the specified field) and check for valid words.
    Statistics for each entry will be returned, including the words matched.
"""
# pylint: disable=broad-except,wildcard-import,unused-wildcard-import

from __future__ import print_function
import logging
import sys
from dnsws_shared import *
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class DNSWordScoreParseCommand(StreamingCommand):
    """ The core class that will be called when the script is executed """
    field = Option(
        doc='The field containing the string to score',
        require=False,
        default='query',
        validate=validators.Fieldname())
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
    #       Instead you must reference them in the stream function

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

    @staticmethod
    def _populate_record(names, record, data):
        """ Populate the return fields in the provided record """
        # Holders for the stats
        total_chars = 0
        len_max = 0
        len_min = 0
        # Check data was provided
        if data:
            # Loop through each word that was matched to calculate the stats
            for word in data['words_matched']:
                total_chars += len(word)
                len_word = len(word)
                if len_word > len_max:
                    len_max = len_word
                if len_word < len_min:
                    len_min = len_word
            # Add the stats to the record
            if data['words_matched']:
                record[names['avg']] = round(total_chars / len(data['words_matched']), 1)
            else:
                record[names['avg']] = 0.0
            record[names['min']] = len_min
            record[names['max']] = len_max
            record[names['score']] = data['score']
            record[names['words']] = data['words_matched']
        else:
            # No data, add zero values to the record
            record[names['avg']] = 0
            record[names['min']] = 0
            record[names['max']] = 0
            record[names['score']] = 0
            record[names['words']] = None

    def _process_string(self, words, val):
        """ Process the provided string (pre-split) and return the score """
        self.logger.debug('Starting processing string: %s', val)
        # Create the holder for the values
        string = dict()
        string['chars_total'] = 0
        string['chars_matched'] = 0
        string['score'] = 0
        string['words_matched'] = list()
        # Lowercase the value and strip it
        string['word'] = str(val).strip().lower()
        self.logger.debug('- Lowercased: %s', string['word'])
        # Determine the length of the unsplit/unmodified version
        string['word_len'] = len(string['word'])
        self.logger.debug('- Length: %i', string['word_len'])
        # Remove common domain extensions from it (regex match)
        string['word'] = RE_TLD_2PART.sub('', string['word'], count=1)
        self.logger.debug('- 2 Part: %s', string['word'])
        if len(string['word']) == string['word_len']:
            # Two-part match didnt work, try a single-part
            string['word'] = RE_TLD_1PART.sub('', string['word'], count=1)
            self.logger.debug('- 1 Part: %s', string['word'])
        string['word'] = RE_TLD_WWW.sub('', string['word'], count=1)
        self.logger.debug('- WWW: %s', string['word'])
        string['word'] = RE_TLD_EC2.sub('', string['word'], count=1)
        self.logger.debug('- EC2: %s', string['word'])
        string['word'] = RE_TLD_IP.sub('', string['word'])
        self.logger.debug('- IP: %s', string['word'])
        # Split by punctuation
        string['split'] = RE_PUNCT_SPLIT.split(string['word'])
        # If no parts, its an invalid word so return 0 for the score
        if not string['split']:
            self.warn('Word has no parts: %s' % str(string['word']))
            return string
        self.logger.debug('- Split: %s', ','.join(string['split']))
        # Loop through each part of the string
        for part in string['split']:
            self.logger.debug('Processing part: %s', part)
            self._process_string_part(words, string, part)
        # Processing loop has finished, the string has been processed
        self.logger.debug('Calculating total score')
        self.logger.debug('- Total characters: %i', string['chars_total'])
        self.logger.debug('- Matched characters: %i', string['chars_matched'])
        # Determine the total score per character matched
        string['char_score_val'] = round(float(100 / float(string['chars_total'])), 2)
        self.logger.debug('- Score per character: %f', string['char_score_val'])
        # Determine the total score
        string['score'] = int(round(string['char_score_val'] * string['chars_matched']))
        self.logger.debug('- Total score: %i', string['score'])
        # Return the string dict
        self.logger.debug('Finished processing string')
        return string

    def _process_string_part(self, words, string, string_part):
        """ Process the passed portion of the string (post-split) """
        self.logger.debug('Starting string part processing')
        # Create the holder for the values
        part = dict()
        part['part'] = string_part
        part['part_len'] = len(part['part'])
        self.logger.debug('- Part: %s', part['part'])
        self.logger.debug('- Part Length: %i', part['part_len'])
        # Add it to the total chars
        string['chars_total'] += part['part_len']
        self.logger.debug('- Total chars: %i', string['chars_total'])
        # Remove any non-az characters
        part['clean'] = RE_PUNCT_CLEAN.sub('', part['part'])
        self.logger.debug('- Clean: %s', part['clean'])
        # Determine the length of the cleaned version
        part['clean_len'] = len(part['clean'])
        self.logger.debug('- Clean Length: %i', part['clean_len'])
        # Handle single characters (a and i)
        if part['clean_len'] == 1:
            if part['clean_len'] in ('a', 'i'):
                self.logger.debug('- Single character match')
                string['chars_matched'] += part['clean_len']
                string['words_matched'].append(str(part['clean']))
                return
        # Get the first two characters (for speed matching)
        part['clean_pfx'] = part['clean'][:2]
        self.logger.debug('- Clean Prefix: %s', str(part['clean_pfx']))
        # Check if its length matches the dict (for a full match)
        if part['clean_len'] in words:
            # Check if the words with a matching prefix are known
            if part['clean_pfx'] in words[part['clean_len']]:
                # Check for a full match
                if part['clean'] in words[part['clean_len']][part['clean_pfx']]:
                    # Full match
                    self.logger.debug('- Full match found')
                    string['chars_matched'] += part['clean_len']
                    string['words_matched'].append(str(part['clean']))
                    return
            else:
                # No list found for this prefix
                self.logger.debug('- No list found for this prefix')
        else:
            # No dictionary for this length of word
            self.logger.debug('- No dictionary found for this length of word')
        # No full match at this point, start looking for partial matches
        self.logger.debug('- No full match found, switching to partial matching')
        # Process in both directions (highest score wins)
        results_ltr = self._process_string_partial_l_to_r(words, part)
        self.logger.debug('- Results (LTR): %s', str(results_ltr))
        results_rtl = self._process_string_partial_r_to_l(words, part)
        self.logger.debug('- Results (RTL): %s', str(results_rtl))
        # Return which ever result-set had the highest character match
        if results_ltr['matched_chars'] >= results_rtl['matched_chars']:
            # LTR wins
            self.logger.debug('- LTR matching wins')
            string['chars_matched'] += results_ltr['matched_chars']
            string['words_matched'].extend(results_ltr['matched_words'])
        else:
            # RTL wins
            self.logger.debug('- RTL matching wins')
            string['chars_matched'] += results_rtl['matched_chars']
            string['words_matched'].extend(results_rtl['matched_words'])
        # Part processing finished
        self.logger.debug('Finished string part processing')

    def _process_string_partial_l_to_r(self, words, part):
        """ Process the passed part of the string for partial matches (L-to-R) """
        self.logger.debug('Starting string part partial processing (L-to-R)')
        # Create the holder for the values
        subpart = dnsws_create_subpart_dict('l_to_r', part['clean'])
        # Loop until there are no remaining usable characters left
        while len(subpart['remains']) >= self.min_length:
            self.logger.debug('- Remains loop begin')
            self.logger.debug('- Remains: %s', subpart['remains'])
            # Set the matched flag (new loop)
            matched = False
            # Get the first two characters (for speed matching)
            # Note: This is calculated again as it will be truncated on each loop
            subpart['remains_pfx'] = subpart['remains'][:2]
            self.logger.debug('- Remains Prefix: %s', subpart['remains_pfx'])
            # Determine the length of the remaining characters
            # Note: This is calculated again as the length will change on each loop
            subpart['remains_len'] = len(subpart['remains'])
            self.logger.debug('- Remains Length: %s', subpart['remains_len'])
            # Loop through the possible lengths in reverse order (biggest matches first)
            for key in range(subpart['remains_len'], 1, -1):
                self.logger.debug('- Testing against length %i', key)
                # The key might not exist if no words match that length
                if key not in words:
                    self.logger.debug('- Key not found in word-lists')
                    continue
                # Check if words with a matching prefix are known
                if subpart['remains_pfx'] not in words[key]:
                    self.logger.debug('- Prefix not found in word-list')
                    continue
                # Go through each word and check for a startswith match
                self.logger.debug('- Looping through words in %i/%s', key, subpart['remains_pfx'])
                for list_word in words[key][subpart['remains_pfx']]:
                    if subpart['remains'].startswith(list_word):
                        # Partial match found
                        self.logger.debug('- Partial match found: %s', list_word)
                        # Check if this is a plural match to the end of of the string
                        if not list_word[:-1] == 's' and (
                                subpart['remains_len'] == len(list_word) + 1):
                            self.logger.debug('- Possible plural match to end of text (s)')
                            if subpart['remains'] == '%ss' % list_word:
                                # Plural match as the remainder (s)
                                if self.use_plurals:
                                    self.logger.debug('- Plural match found (s)')
                                    matched = True
                                    subpart['matched_chars'] += len(list_word) + 1
                                    subpart['matched_words'].append('%ss' % str(list_word))
                                    subpart['remains'] = ''
                                    break
                                else:
                                    self.logger.debug('- Plural match found (s) but usage is disabled')
                        if not list_word[:-2] == 'ss' and (
                                subpart['remains_len'] == len(list_word) + 2):
                            self.logger.debug('- Possible plural match to end of text (es)')
                            if subpart['remains'] == '%ses' % list_word:
                                # Plural match as the remainder (es)
                                if self.use_plurals:
                                    self.logger.debug('- Plural match found (es)')
                                    matched = True
                                    subpart['matched_chars'] += len(list_word) + 2
                                    subpart['matched_words'].append('%ses' % str(list_word))
                                    subpart['remains'] = ''
                                    break
                                else:
                                    self.logger.debug('- Plural match found (es) but usage is disabled')
                        # Not a plural match at this point, so handle differently
                        matched = True
                        subpart['matched_chars'] += len(list_word)
                        subpart['matched_words'].append(str(list_word))
                        subpart['remains'] = subpart['remains'][len(list_word):]
                        break
                    # No match found
                # Check if a match was found
                if matched:
                    # Break this loop so the process is started again on the remainder
                    self.logger.debug('- Match found, breaking out of word-check loop')
                    break
            # All words have been checked at this point
            # If a match was found, continue so the process is started again on the remainder
            if matched:
                self.logger.debug('- Match found, breaking out of key loop')
                continue
            # No match found, strip the first character from the remainder ready for the next try
            self.logger.debug('- No match found, checking for usable vowel')
            if subpart['remains'][:1] in ['a', 'i']:
                # Usable vowel found (as there was no word match)
                if self.use_singles:
                    self.logger.debug('- Usable vowel found')
                    subpart['matched_chars'] += 1
                    subpart['matched_words'].append(subpart['remains'][:1])
                else:
                    self.logger.debug('- Usable vowel found but using them is disabled')
                subpart['remains'] = subpart['remains'][1:]
            else:
                self.logger.debug('- No match found, removing first character of remaining text')
                subpart['remains'] = subpart['remains'][1:]
        # Processing loop has finished
        self.logger.debug('Finished string part partial processing')
        return subpart

    def _process_string_partial_r_to_l(self, words, part):
        """ Process the passed part of the string for partial matches (R-to-L) """
        self.logger.debug('Starting string part partial processing (R-to-L)')
        # Create the holder for the values
        subpart = dnsws_create_subpart_dict('r_to_t', part['clean'])
        # Loop until there are no remaining usable words left
        while len(subpart['remains']) >= self.min_length:
            self.logger.debug('- Remains loop begin')
            self.logger.debug('- Remains: %s', subpart['remains'])
            # Set the matched flag
            matched = False
            # Determine the length of the remaining characters
            # Note: This is calculated again as the length will change on each loop
            subpart['remains_len'] = len(subpart['remains'])
            self.logger.debug('- Remains Length: %s', subpart['remains_len'])
            # Loop through the possible lengths in reverse order (biggest matches first)
            for key in range(subpart['remains_len'], 1, -1):
                self.logger.debug('- Testing against length %i', key)
                # The key might not exist if no words match that length
                if key not in words:
                    self.logger.debug('- Key not found in word-lists')
                    continue
                # Calculate the initial characters to skip
                skip_len = subpart['remains_len'] - key
                self.logger.debug('- Skip length: %i', skip_len)
                # Determine the partial string to match
                partial = subpart['remains'][skip_len:]
                self.logger.debug('- Cut word: %s', partial)
                # Get the first two characters of this portion (for speed matching)
                partial_pfx = partial[:2]
                self.logger.debug('- Cut Prefix: %s', partial_pfx)
                # Check if words with a matching prefix are known
                if partial_pfx not in words[key]:
                    self.logger.debug('- Prefix not found in word-list')
                    continue
                # Go through each word and check for an endswith match
                self.logger.debug('- Looping through words in %i/%s', key, partial_pfx)
                for list_word in words[key][partial_pfx]:
                    if partial.endswith(list_word):
                        # Partial match found
                        self.logger.debug('- Partial match found: %s', list_word)
                        matched = True
                        subpart['matched_chars'] += len(list_word)
                        subpart['matched_words'].append(str(list_word))
                        subpart['remains'] = subpart['remains'][:-len(list_word)]
                        break
                    # No match found
                # Check if a match was found
                if matched:
                    # Break this loop so the process is started again on the remainder
                    self.logger.debug('- Match found, breaking out of word-check loop')
                    break
            # All words have been checked at this point
            # If a match was found, continue so the process is started again on the remainder
            if matched:
                self.logger.debug('- Match found, breaking out of key loop')
                continue
            # No match found, strip the last character from the remainder ready for the next try
            self.logger.debug('- No match found, checking for usable vowel')
            if subpart['remains'][-1:] in ['a', 'i']:
                # Usable vowel found (as there was no word match)
                if self.use_singles:
                    self.logger.debug('- Usable vowel found')
                    subpart['matched_chars'] += 1
                    subpart['matched_words'].append(subpart['remains'][-1:])
                else:
                    self.logger.debug('- Usable vowel found but using them is disabled')
                subpart['remains'] = subpart['remains'][:-1]
            else:
                self.logger.debug('- No match found, removing last character of remaining text')
                subpart['remains'] = subpart['remains'][:-1]
        # Reverse the order of the list (so the word ordering is correct
        subpart['matched_words'].reverse()
        # Processing loop has finished
        self.logger.debug('Finished string part partial processing')
        return subpart

    def stream(self, records):
        """ Process the incoming data stream """
        # Enable debug logging if requested
        if self.log_debug:
            self.logger.setLevel(logging.DEBUG)
        self.logger.debug('DNS Word Score Starting - Version %s', str(VERSION))
        # Check the min/max values are usable
        if self.min_length < WORD_LEN_MIN or self.min_length > WORD_LEN_MAX:
            self.die('Invalid minimum length specified: %i' % self.min_length)
        if self.max_length < WORD_LEN_MIN or self.max_length > WORD_LEN_MAX:
            self.die('Invalid maximum length specified: %i' % self.max_length)
        # Log the input field
        self.logger.debug('Input field: %s', str(self.field))
        # Define the field names for the output (based on the input)
        field_names = dict()
        field_names['score'] = '%s_score' % str(self.field)
        field_names['words'] = '%s_words' % str(self.field)
        field_names['avg'] = '%s_words_avglen' % str(self.field)
        field_names['min'] = '%s_words_minlen' % str(self.field)
        field_names['max'] = '%s_words_maxlen' % str(self.field)
        self.logger.debug('Output fields: %s', str(field_names))
        # Create the dict to hold all of the loaded words
        words = dict()
        words[0] = list()
        # Load the word-lists
        self.logger.debug('Beginning word-list load')
        _ = dnsws_load_wordlists(self, words)
        # Loop through each record
        self.logger.debug('Beginning record processing')
        count = 0
        for record in records:
            # Increment the count
            count += 1
            # Some records may not have the required field, so check first
            if str(self.field) not in record:
                self.logger.debug('Record %i is missing the %s field', count, self.field)
                self._populate_record(field_names, record, None)
                yield record
                continue
            # An empty record doesn't get scored either
            if not record[self.field]:
                self.logger.debug('Record %i is has an empty value', count)
                self._populate_record(field_names, record, None)
                yield record
                continue
            # PTR queries aren't supported (in-addr.arpa)
            if RE_TLD_ARPA.search(record[self.field]):
                self.logger.debug('Record %i was an ARPA request', count)
                self._populate_record(field_names, record, None)
                yield record
                continue
            # Local queries aren't supported (_tcp.local)
            if RE_TLD_LOCAL.search(record[self.field]):
                self.logger.debug('Record %i was an local request', count)
                self._populate_record(field_names, record, None)
                yield record
                continue
            # The record contains the required field, process it and return
            self.logger.debug('Processing record %i: %s', count, record[self.field])
            word = self._process_string(words, record[self.field])
            self._populate_record(field_names, record, word)
            yield record
            continue
        # Finished processing all records
        self.logger.debug('DNS Word Score Ending')


if __name__ == '__main__':
    dispatch(DNSWordScoreParseCommand, sys.argv, sys.stdin, sys.stdout, __name__)
