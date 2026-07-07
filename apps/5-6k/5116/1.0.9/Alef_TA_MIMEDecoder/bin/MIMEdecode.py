#!/usr/bin/env python

##########################################################################
#  Copyright (C) 2020 ALEF NULA a.s.
#  
#  Authors: 
#  Brian Kirk @ Splunk universe
#  Tomas Moser, tomas.moser@alef.com
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#  See the GNU General Public License for more details.
#
#  A copy of the GNU General Public License is provided in the LICENSE 
#  file. If not, see <http://www.gnu.org/licenses/> for additional detail.
##########################################################################

import csv
import sys
import email
import re
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from email.header import Header, decode_header
from splunklib.searchcommands import dispatch, StreamingCommand, Option, Configuration, validators
import six

""" An MIMEDecoder that takes CSV as input, performs a email.header.decode_header
    on the field, then returns the decoded text in CSV results
"""

def getmailheader(header_text, default="ascii"):
    """Decode header_text if needed.  
       Note: This function works by itself but if there are multiple strings that 
             need decoded you get encoding in the middle of the results"""
    try:
        headers=email.header.decode_header(header_text)
    except email.errors.HeaderParseError:
    # If the string doesn't decode correctly try stripping a few end characters
        header_len=len(header_text)
        if header_len>10:
            try:
                headers=email.header.decode_header(header_text[0:header_len-3]+'?=')
            except email.errors.HeaderParseError:
                try:
                    headers=email.header.decode_header(header_text[0:header_len-4]+'?=')
                except email.errors.HeaderParseError:
                    try:
                        headers=email.header.decode_header(header_text[0:header_len-5]+'?=')
                    except email.errors.HeaderParseError:
                    # If all else fails return ***CORRUPTED***
                        return "***CORRUPTED***"
        for i, (text, charset) in enumerate(headers):
            try:
                headers[i]=six.text_type(text, charset or default, errors='replace')
            except LookupError:
            # if the charset is unknown, force default
                headers[i]=six.text_type(text, default, errors='replace')
        return u"".join(headers)
    else:
        for i, (text, charset) in enumerate(headers):
            try:
                headers[i]=six.text_type(text, charset or default, errors='replace')
            except LookupError:
            # if the charset is unknown, force default
                headers[i]=six.text_type(text, default, errors='replace')
        return u"".join(headers)

def decode_subject( subject ):
    """Decode subject string if needed.  
       Note: This function splits each segment that might need decoded and calls 
             getmailheader for each part merging the results all together"""
    decoded = ''
    pointer = 0
    length = len(subject)
    while pointer < length:
        try:
            beginning = subject.index('=?', pointer)
            if beginning > pointer:
            # If we are not currently at the pointer then concatenate string as is to results.
                decoded += subject[pointer:beginning]
            try:
            # Move the point past the character set and encoding.
                pointer = subject.index('?B?', pointer + 2) + 3
            except ValueError:
                try:
                    pointer = subject.index('?b?', pointer + 2) + 3
                except ValueError:
                    try:
                        pointer = subject.index('?Q?', pointer + 2) + 3
                    except ValueError:
                        try:
                            pointer = subject.index('?q?', pointer + 2) + 3
                        except ValueError:
                            pointer += 2
            try:
            # Find the end of the encoded text
                ending = subject.index('?=', pointer)
                pointer = ending + 2
                decoded += getmailheader(subject[beginning:ending + 2])
            except ValueError:
            # If found no end string, add end string and decode the rest field to results and return
                pointer = length
                decoded += getmailheader(subject[beginning:length] + '?=')
        except ValueError:
        # Found no beginning string, add the rest field to the results and return
            decoded += subject[pointer:length]
            pointer = length
    return decoded

def main(message_subject):
    MIMEEncode = message_subject
 
    # only the MIMEEcode was provided, preform decoding where needed
    if MIMEEncode.find("=?") == -1:
        # If the field does not appear to contain encoded data return original field 
        MIMEDecode = MIMEEncode
    else:
    # Else remove extra charaters not part of the encoding and decode the field 
	# remove extra space after '?Q?' as it breaks decoding function later
        MIMEEncode = re.sub(r'(\?[qQ]\?)\s*', r'\1', MIMEEncode)
	# remove the rest as per else statement
        MIMEDecode = MIMEEncode.replace('??','')
        MIMEDecode = MIMEDecode.replace('? ','')
        MIMEDecode = decode_subject(MIMEDecode)
        #result[MIMEDecode] = getmailheader(result[MIMEEncode])
    if MIMEDecode:
        # If successfully decoded then return results 
        return MIMEDecode

# Splunk SDK skeleton
@Configuration()

class decodemimeCommand(StreamingCommand):
    def stream(self, records):
        # get the argument - fieldname with mime-encoded string
        field_in = self.fieldnames[0]
        field_out = self.fieldnames[1]
        for record in records:
            if field_in in record:
                record[field_out] = main(record[field_in])
                yield record
    
if __name__ == "__main__":
    dispatch(decodemimeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
