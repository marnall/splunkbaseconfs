#!/usr/bin/env python
import sys, re
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators


#@Configuration(local=True)
@Configuration()
class LuhnCommand(StreamingCommand):
    """
    ##Syntax
    

    ##Description
    Implements a LUHN algorithm for searching Splunk data for potential credit card numbers with higher accuracy than a simple regex check.

    """

    # Command options
    disable_extraction = Option(require=False, name='disable_extraction', default='no')
    output_prefix = Option(require=False, name='output_prefix', default='ta_luhn_')
    input_field = Option(require=False, name='input_field', default='_raw')
    extraction_regex = Option(require=False, name='regex', default='(\d[\d\-\s]{13,30})')
    ccpattern_regex = Option(require=False, name='cc_regex', default='(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|(?:2131|1800|35\d{3})\d{11})')

    # Reference: http://en.wikipedia.org/wiki/Luhn_algorithm
    # Reference: https://stackoverflow.com/questions/21079439/implementation-of-luhn-formula
    def luhn_checksum(self, card_number):
        def digits_of(n):
            return [int(d) for d in str(n)]

        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = 0
        checksum += sum(odd_digits)
        
        for d in even_digits:
            checksum += sum(digits_of(d*2))
        
        return checksum % 10
     
    def is_luhn_valid(self, card_number):
        return self.luhn_checksum(card_number) == 0

    def normalize_str_to_bool(self, val):
        val = str(val).lower()
        if val == '1' or val == 'true' or val == 'yes':
            return True
        else:
            return False

    def normalize_bool_to_str(self, val):
        if type(val) == bool:
            if val:
                return 'True'
            else:
                return 'False'
        else:
            return val

    def do_cc_check(self, data, ccpattern_compiled, extraction_compiled = None):
        if extraction_compiled is not None:
            ## create chunks of data, loop through all of them.
            chunks = extraction_compiled.findall(data)
            if len(chunks) == 0:
                return {'result': False, 'data': []}
            else:
                return_data = []
                return_result = False
                for chunk in chunks:
                    potential_match = str(''.join(c for c in chunk if c.isdigit()))
                    if ccpattern_compiled.match(potential_match):
                        if self.is_luhn_valid(potential_match):
                            return_data.append(potential_match)

                if len(return_data) > 0:
                    return_result = True
       
                return {'result': return_result, 'data': return_data}            

        else:
            ## only do the cc regex + luhn check on the whole data chunk
            if ccpattern_compiled.match(data):
                if self.is_luhn_valid(data):
                    return {'result': True, 'data': [data]}
            else:
                return {'result': False, 'data': []}


    def stream(self, events):
        luhn_check_result_return = self.output_prefix + 'check'
        luhn_check_result_values = self.output_prefix + 'matches'

        if not self.normalize_str_to_bool(self.disable_extraction):
            # try to compile the regex and, if unable to do so, error out
            try:
                extraction_compiled = re.compile(self.extraction_regex)
            except:
                raise Exception('Unable to compile the provided extraction regex. Ending execution.')
        else:
            extraction_compiled = None

        # try to compile the ccpattern regex, error out if it fails
        try:
            ccpattern_compiled = re.compile(self.ccpattern_regex)
        except:
            raise Exception('Unable to compile the provided ccpattern regex. Ending execution.')


        # start parsing events
        for single_event in events:
            # make sure the input field exists, if it doesn't - don't bother parsing stuff
            if self.input_field in list(single_event.keys()):
                # handle multivalue inputs
                if type(single_event[self.input_field]) == list:
                    single_event[luhn_check_result_values] = []
                    for i in single_event[self.input_field]:
                        x = self.do_cc_check(i, ccpattern_compiled, extraction_compiled)

                        if x['result']:
                            single_event[luhn_check_result_return] = x['result']
                            single_event[luhn_check_result_values] = single_event[luhn_check_result_values] + x['data']

                else:
                    x = self.do_cc_check(single_event[self.input_field], ccpattern_compiled, extraction_compiled)

                    single_event[luhn_check_result_return] = x['result']
                    single_event[luhn_check_result_values] = x['data']

            else:
                self.logger.debug('Event provided for parsing but key %s does not exist. Ignoring.' % str(self.input_field))
                single_event[luhn_check_result_return] = False
                single_event[luhn_check_result_values] = []

            # Just in case, make sure we set the fields.
            if luhn_check_result_return not in list(single_event.keys()):
                single_event[luhn_check_result_return] = 'False'

            single_event[luhn_check_result_return] = self.normalize_bool_to_str(single_event[luhn_check_result_return])

            # Some cleanup; if the result is False, return None values. 
            # If the result is 1, return a single value
            # Otherwise, just leave it alone as a multivalue list
            if single_event[luhn_check_result_return] == 'False':
                single_event[luhn_check_result_values] = None
            elif len(single_event[luhn_check_result_values]) == 1:
                x = single_event[luhn_check_result_values]
                single_event[luhn_check_result_values] = x[0]


            yield single_event


dispatch(LuhnCommand, sys.argv, sys.stdin, sys.stdout, __name__)
