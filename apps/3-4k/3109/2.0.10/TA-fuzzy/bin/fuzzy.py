#!/usr/bin/env python
import os, sys, re
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators


APPDIR = 'TA-fuzzy'

# make sure the directory storing the fuzzy wuzzy library can be imported
LIBDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
# LIBDIR = os.path.join(os.path.join(os.environ.get('SPLUNK_HOME')), 'etc', 'apps', APPDIR, 'bin', 'lib')
if not LIBDIR in sys.path:
    sys.path.append(LIBDIR)

# Import the library
try:
    from fuzzywuzzy import fuzz
except ImportError as ex1:
    raise Exception('Unable to import required fuzzywuzzy library. Exception: {}'.format(ex1))

#@Configuration(local=True)
@Configuration()
class FuzzyCommand(StreamingCommand):
    """
    ##Syntax
     | fuzzy wordlist="svchost.exe,wininit.exe" compare_field="myfield" output_prefix="output_" type="type" delims="(\\\\|/|\s+|;|-)"

    ##Description
    Implements a fuzzy search based on the fuzzywuzzy library which is an implementation of the levenshtein algorithm
    to determine the commonality between two words.

    """
    # Options that can be set when a user runs the search
    # wordlist, compare_field, output_prefix, match_type, 
    wordlist = Option(require=True, name='wordlist')
    compare_field = Option(require=False, name='compare_field', default='_raw')
    output_prefix = Option(require=False, name='output_prefix', default='fuzzyout_')
    match_type = Option(require=False, name='type', default='simple')
    delims = Option(require=False, name='delims', default='(\\\\|/|\s+|;|-)')

    def get_matches_from_data(self, data, cregex):
        try:
            if cregex is not None:
                return cregex.split(data)
            else:
                return re.split(self.delims, data)
        except:
            # Basically, trying to fail open here.
            return []

    def stream(self, events):
        # Try to compile the regex which may show some modest performance gains
        try:
            compiled_regex = re.compile(str(self.delims).strip())
        except:
            self.logger.warning('Provided regex did not compile. Comparison will attempt to continue but may produce unexpected results.')
            compiled_regex = None

        # Expecting a single word or comma separated word list - split it up into a list of words
        words = [x.strip() for x in self.wordlist.split(',')]

        # set output field names for consistency
        fn_max_match_word = self.output_prefix + 'max_match_word'
        fn_max_match_ratio = self.output_prefix + 'max_match_ratio'

        # Make a reference to the matching type requested
        mt = str(self.match_type).lower()
        fuzzymatch = None
        if mt == 'partial':
            fuzzymatch = fuzz.partial_ratio
        elif mt == 'token_sort':
            fuzzymatch = fuzz.token_sort_ratio
        elif mt == 'token_set':
            fuzzymatch = fuzz.token_set_ratio
        else:
            fuzzymatch = fuzz.ratio

        # start the horribly nested parsing loop of death
        for single_event in events:
            single_event[fn_max_match_ratio] = ''
            single_event[fn_max_match_word] = ''

            single_event_keys = list(single_event.keys())

            # Basically, make the assumption that if the user provided a wordlist value that matches an existing event key;
            # the user must want to split up that key for comparison purposes.
            if self.wordlist in single_event_keys:
                words = [x.strip() for x in single_event[self.wordlist].split(',')]

            if self.compare_field in single_event_keys:
                matches = []

                #try:
                if type(single_event[self.compare_field]) == list:
                    for i in single_event[self.compare_field]:
                        m = self.get_matches_from_data(i, compiled_regex)
                        if type(m) == list:
                            matches = matches + m
                        else:
                            matches.append(m)
                else:
                    matches = self.get_matches_from_data(single_event[self.compare_field], compiled_regex)
                        

               # except:
                #    raise Exception('Attempting to split input with the given regex failed. Assuming a bad regex and bailing out.')

                for match in matches:
                    for word in words:
                        # Get a ratio from word A to word B
                        ratio = fuzzymatch(word, match)

                        # If the event does not have a ratio already stored, assume this is the first match
                        if single_event[fn_max_match_ratio] == '':
                            single_event[fn_max_match_ratio] = ratio
                            single_event[fn_max_match_word] = str(word + '/' + match)
                      
                        # If the event has something in this field, it must have been parsed already and not found a 100% match
                        else: 
                            if single_event[fn_max_match_ratio] < ratio:
                                single_event[fn_max_match_ratio] = ratio
                                single_event[fn_max_match_word] = str(word + '/' + match)

                        # Goal here is to stop parsing the event if the ratio reaches 100 because you can't get any better
                        if ratio == 100:
                            yield single_event

            else:
                self.logger.warning('Event provided for parsing but key %s does not exist. Ignoring.' % str(self.compare_field))
                single_event[fn_max_match_ratio] = ''
                single_event[fn_max_match_word] = ''
            
            yield single_event
            


dispatch(FuzzyCommand, sys.argv, sys.stdin, sys.stdout, __name__)
