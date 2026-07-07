#!/usr/bin/env python

import csv
import sys
import email
from email.header import Header, decode_header

""" An MIMEDecoder that takes CSV as input, performs a email.Header.decode_header
    on the field, then returns the decoded text in CSV results
"""

def getmailheader(header_text, default="ascii"):
    """Decode header_text if needed.  
       Note: This function works by itself but if there are multiple strings that 
             need decoded you get encoding in the middle of the results"""
    try:
        headers=email.Header.decode_header(header_text)
    except email.Errors.HeaderParseError:
    # If the string doesn't decode correctly try stripping a few end characters
        header_len=len(header_text)
        if header_len>10:
            try:
                headers=email.Header.decode_header(header_text[0:header_len-3]+'?=')
            except email.Errors.HeaderParseError:
                try:
                    headers=email.Header.decode_header(header_text[0:header_len-4]+'?=')
                except email.Errors.HeaderParseError:
                    try:
                        headers=email.Header.decode_header(header_text[0:header_len-5]+'?=')
                    except email.Errors.HeaderParseError:
                    # If all else fails return ***CORRUPTED***
                        return "***CORRUPTED***"
        for i, (text, charset) in enumerate(headers):
            try:
                headers[i]=unicode(text, charset or default, errors='replace')
            except LookupError:
            # if the charset is unknown, force default
                headers[i]=unicode(text, default, errors='replace')
        return u"".join(headers)
    else:
        for i, (text, charset) in enumerate(headers):
            try:
                headers[i]=unicode(text, charset or default, errors='replace')
            except LookupError:
            # if the charset is unknown, force default
                headers[i]=unicode(text, default, errors='replace')
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



def main():
    if len(sys.argv) != 3:
        print "Usage: python MIMEDecoder.py [MIME Encoded field] [MIME Decoded field]"
        sys.exit(1)

    MIMEEncode = sys.argv[1]
    MIMEDecode = sys.argv[2]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for result in r:
        if result[MIMEEncode] and result[MIMEDecode]:
        # both fields were provided, just pass it along
            w.writerow(result)

        elif result[MIMEEncode]:
        # only the MIMEEcode was provided, preform decoding where needed
            if result[MIMEEncode].find("=?") == -1:
            # If the field does not appear to contain encoded data return original field 
                result[MIMEDecode] = result[MIMEEncode]
            else:
            # Else remove extra charaters not part of the encoding and decode the field 
                result[MIMEDecode] = result[MIMEEncode].replace('??','')
                result[MIMEDecode] = result[MIMEDecode].replace('? ','')
                result[MIMEDecode] = decode_subject(result[MIMEDecode])
                #result[MIMEDecode] = getmailheader(result[MIMEEncode])
            if result[MIMEDecode]:
            # If successfully decoded then write results 
                w.writerow(result)


main()