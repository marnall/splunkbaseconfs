import struct
import base64
import json
import requests
import binascii
import sys
from asn1crypto.core import Sequence
from urllib import quote
from OpenSSL.crypto import load_certificate,FILETYPE_ASN1
from datetime import datetime

# Copyright 2018 Jorrit Folmer
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

class CTL2Splunk:
    """ This class:
        - gets Certificate Transparency Logs from a given log url
        - decodes the certificates in the MerkleTreeLeafs
        - and saves the certificate metadata as events to Splunk """

    def __init__(self, helper, ew, log_url):
        # Instance variables:
        self.helper    = helper
        self.log_url   = log_url if log_url[-1]=='/' else "{}/".format(log_url)
        self.ew        = ew
        self.tree_size = 0

    def decode_leaf(self, leaf, counter):
        """ Decodes a given raw leaf entry 
            and returns a hash with leaf and leaf certificate metadata """
        leaf_out = dict()
        format = ">BBQHBBB%ds" % (len(base64.b64decode(leaf))-15)
        try:
            version,merkleleaftype,timestamp,logentrytype,s3,s2,s1,entry=struct.unpack(format,base64.b64decode(leaf))
        except Exception, e:
            print("decode_leaf: unpack of entry %d failed with %s" % (counter, str(e)))
        else:
            leaf_out['LeafIndex'] = counter
            leaf_out['Timestamp'] = timestamp
            leaf_out['LogEntryType'] = logentrytype
            if logentrytype == 0:
                 size = s1+(s2*256)+(s3*65536)
                 if size > len(base64.b64decode(leaf))-15:
                     print("decode_leaf: declared size of leaf cert (%d) is larger than the actual leaf certificate (%d)" % (size, len(base64.b64decode(leaf))-15))
                 else:
                     der = entry[0:size]
                     leaf_out['LeafCertificate'] = self.decode_x509(der, counter)
            else:
                 print("decode_leaf: ignoring unsupported entry_type %d" % logentrytype)
        return leaf_out

    def decode_subjectaltname(self, data, counter):
        """ Decodes given ASN1 encoded subjectaltname data
            and returns an array of url strings """
        result = []
        parsed = Sequence.load(data)
        for i in range(0,len(parsed)):
            try:
                subjectaltname = parsed[i].native
            except Exception, e:
                print("decode_subjectaltname: exception in %s entry %d (%s): %s" % (self.log_url, counter, parsed[i], str(e)))
            else:
                if isinstance(subjectaltname, (long,int)):
                    subjectaltname =  binascii.unhexlify('%x' % subjectaltname)
                elif isinstance(subjectaltname, basestring):
                    subjectaltname = subjectaltname
                else:
                    print("decode_subjectaltname: Unknown instance type %s found in entry %d. ASN1 data for debugging: %s" % type(subjectaltname), counter, binascii.hexlify(data))
                    subjectaltname = ''
                try:
                    subjectaltname.decode('utf8')
                except Exception,e:
                    print("decode_subjectaltname: exception in entry %d: %s. ASN1 data for debugging: %s" % (counter, str(e), binascii.hexlify(data)))
                else:
                    result.append(subjectaltname)
        return result
 
    def decode_x509(self, der, counter):
        """ Decodes a given certificate 
            and returns a hash with certificate metadata """
        cert = dict()
        try:
            x509=load_certificate(FILETYPE_ASN1, der)
        except Exception, e:
            print("decode_x509: exception in entry %d: %s" % (counter, str(e)))
        else:
            cert['issuer'] = ''
            cert['subject'] = ''
            for key,value in x509.get_issuer().get_components():
                cert['issuer'] += "%s=%s, " %(key, value)
            cert['issuer'] = cert['issuer'][:-2]
            for key,value in x509.get_subject().get_components():
                cert['subject'] += "%s=%s, " %(key, value)
            cert['subject'] = self.fix_string_encoding(cert['subject'][:-2])
            cert['serial'] = ':'.join(["%02x" % (x509.get_serial_number() >> i & 0xff) for i in (152, 144, 136, 128, 120, 112, 104, 96, 88, 80, 72, 64, 56, 48, 40, 32, 24, 16, 8, 0)])
            cert['validity'] = dict()
            cert['validity']['notafter'] = datetime.strptime(x509.get_notAfter(),"%Y%m%d%H%M%SZ").isoformat(" ") + "+00:00"
            cert['validity']['notbefore'] = datetime.strptime(x509.get_notBefore(),"%Y%m%d%H%M%SZ").isoformat(" ") + "+00:00"
            cert['public_key'] = dict()
            cert['public_key']['bits'] = x509.get_pubkey().bits()
            cert['public_key']['type'] = x509.get_pubkey().type()
            cert['signature_algorithm'] = x509.get_signature_algorithm()
            cert['version'] = x509.get_version()
            cert['x509_extensions'] = dict()
            try:
                for i in range(0,x509.get_extension_count()):
                    name = x509.get_extension(i).get_short_name()
                    if name == 'subjectAltName':
                        data = x509.get_extension(i).get_data()
                        subjectaltname = self.decode_subjectaltname(data, counter)
                        cert['x509_extensions'][name] = subjectaltname
            except Exception, e:
                print("decode_x509 in extension retrieval of entry %d: %s" % (counter, str(e)))
        return cert

    def get_entries(self, start, end):
        """ Fetches entries from the log
            and returns an array of raw leaf_inputs
            (extra_data is currently ignored) """
        leafs = []
        try:
            r = requests.get('https://{}ct/v1/get-entries?start={}&end={}'.format(self.log_url,start,end), timeout=20)
        except Exception, e:
            print("get_entries: %s, status %s, %s" %  (r.url, r.status_code, str(e)))
        else:
            if r.status_code == 200:
                print("get_entries: %s, status %s" %  (r.url, r.status_code))
                log = json.loads(r.text)
                for leaf in log['entries']:
                    leafs.append(leaf['leaf_input'])
            else:
                print("get_entries: %s, status %s" %  (r.url, r.status_code))
            return leafs

    def get_tree_size(self):
        """ Fetches the current tree_size from the given log_url instance variable
            and returns the size as an integer """
	try:
            r = requests.get('https://{}ct/v1/get-sth'.format(self.log_url), timeout=10)
	except Exception, e:
            print("get_tree_size(): %s exception %s" %  (self.log_url, str(e)))
            return False
        else:
            if r.status_code == 200:
                sth = json.loads(r.text)
                return sth['tree_size']
            else:
                print("get_tree_size(): %s, http status %s" %  (r.url, r.status_code))
                return False

    def leaf2splunk(self, leaf, tree_size):
        """ For the given leaf
            push an event to splunk
            and update the previous_tree_size for the log_url """
        print leaf

    def fix_string_encoding(self, s):
        encodings = ['utf-8', 'windows-1252', 'utf16']
        result = None
        for e in encodings:
            try:
                result = s.decode(e).encode('utf-8')
            except Exception, e:
                print("fix_string_encoding: exception %s when decoding %s" % (str(e), s))
            else:
                print("fix_string_encoding: decoded with %s: %s" % (e, s))
                break
        return result

    def process_log(self, start):
        """ For the given log_url instance variable
            process the MerkleTreeLeaves 
            into Splunk events """
        # TODO: determine fetch_size for a given log_url
        # A fetch_size of 64 is barely enough to keep up with argon2018
        fetch_size = 1
	if start>0:
            previous_tree_size = start
            tree_size = start+1
            print("process_log: starting %s tree_size: %d, previous_tree_size: %d" % (self.log_url, tree_size, previous_tree_size))
            counter = previous_tree_size
            for i in range(previous_tree_size, tree_size, fetch_size):
                leaf_inputs = self.get_entries(i, i+fetch_size-1)
                counter = i
                for leaf in leaf_inputs:
                     leaf = self.decode_leaf(leaf, counter)
                     if len(leaf)>0:
                         self.leaf2splunk(json.dumps(leaf), counter)
                     counter=counter+1
            print("process_log: finished %s at %d" % (self.log_url, counter))
        else:
            print("process_log: finished without processing entries because tree_size was %s" % tree_size)


total = len(sys.argv)
if total == 3:
    source = str(sys.argv[1])
    position = str(sys.argv[2])
    obj = CTL2Splunk(None, None, source)
    obj.process_log(int(position)) 
else:
    print("Usage: %s source position" % str(sys.argv[0]))
