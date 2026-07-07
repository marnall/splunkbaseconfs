#!/usr/bin/env python3

import re

RE_IP_FRAGMENT = re.compile(r'^\d+(?:\.\d+)*$')
PROTOCOL_TRANSLATIONS = {
    'http': 'hXXp',
    'https': 'hXXps',
    'ftp': 'fXp',
}

def defang_protocol(proto):
    return PROTOCOL_TRANSLATIONS.get(proto.lower(), '({0})'.format(proto))

RE_URLS = re.compile(
    r'((?:(?P<protocol>[-.+a-zA-Z0-9]{1,12})://)?'
    r'(?P<auth>[^@\:]+(?:\:[^@]*)?@)?'
    r'((?P<hostname>'
    r'(?!(?:10|127)(?:\.\d{1,3}){3})'
    r'(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})'
    r'(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})'
    r'(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])'
    r'(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}'
    r'(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))'
    r'|'
    r'(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)'
    r'(?:\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*'
    r')(?P<tld>\.(?:[a-z\u00a1-\uffff]{2,}))'
    r'))'
    r'(?::\d{2,5})?'
    r'(?:/\S*)?',
    re.IGNORECASE
)


def _is_ip_fragment(hostname):
    '''
    For some reason, there is a bug where the URL regex matches on the first
    half of an IP address. This double checks that and skips the match if so.
    '''
    return bool(RE_IP_FRAGMENT.match(hostname))






def _defang_match(match, all_dots=False, colon=False):
    '''
    Defangs a single regex match.

    :param SRE_Match match: the regex match on the URL, domain, ip, or subdomain
    :param bool all_dots: whether to defang all dots in the URIs
    :param bool colon: whether to defang the colon in the protocol
    :return: a string of the defanged input
    '''
    clean = ''
    if match.group('protocol'):
        clean = defang_protocol(match.group('protocol'))
        if colon:
            clean += '[:]//'
        else:
            clean += '://'
    if match.group('auth'):
        clean += match.group('auth')
    if all_dots:
        fqdn = match.group('hostname') + match.group('tld')
        clean += fqdn.replace('.', '[.]')
    else:
        clean += match.group('hostname')
        clean += match.group('tld').replace('.', '[.]')
    return clean


def defang(line, all_dots=False, colon=False, zero_width_replace=False):
    '''
    Defangs a line of text.

    :param str line: the string with URIs to be defanged
    :param bool all_dots: whether to defang all dots in the URIs
    :param bool colon: whether to defang the colon in the protocol
    :param bool zero_width_replace: inserts a zero width character after every character
    :return: the defanged string
    '''
    if zero_width_replace:
        return ZERO_WIDTH_CHARACTER.join(line)
    for match in RE_URLS.finditer(line):
        if _is_ip_fragment(match.group('hostname')):
            continue
        cleaned_match = _defang_match(match, all_dots=all_dots, colon=colon)
        line = line.replace(match.group(1), cleaned_match, 1)
    return line


def defanger(infile):

    clean_line = defang(infile)
  #  print("this is the clean file" +clean_line)
    output = clean_line
    return output

if __name__ == '__main__':
    this_sam = "http://google.com"
    defanger(this_sam)
