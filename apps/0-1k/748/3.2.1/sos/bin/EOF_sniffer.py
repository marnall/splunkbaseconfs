#!/usr/bin/python

import sys
import os
import time
import md5
import collections

# The following list should be populated with the absolute paths of all files to sniff
monitored_filenames = [
                       '/opt/splunk/var/log/splunk/splunkd.log',
                       '/opt/splunk/var/log/splunk/splunkd_access.log']



# Set the interval of polling, in seconds
poll_interval = 1

# crc size for the data; typically this is 256 but other values are possible
crc_size = 256

# if you want more data than the crc chunk from the file end, set to a positive
# integer
larger_eof_readsize = None


# kludgy test data
if '--test' in sys.argv:
    monitored_filenames = [
                           'branches/ace/built/var/log/splunk/splunkd.log',
                           'branches/ace/built/var/log/splunk/splunkd_access.log']


def log_error(msg):
    sys.stderr.write(msg)

def silly_splunk_hash(data):
    hash_obj = md5.md5(data)
    hex_text = hash_obj.hexdigest()
    # We only use the first half of the hash.  Don't ask me why
    half_hex_text = hex_text[:16]
    return half_hex_text

def get_seek_and_content_info(filename):
    """determine and return file end location and file end contents 
    """
    f = open(filename, "rb")

    # get file size
    f.seek(0, os.SEEK_END)
    current_eof = f.tell()

    # if the file is smaller than our crc method wants, we can't honestly report
    # the contents
    if current_eof < crc_size:
        msg = "Oops; '%s' less than %i bytes, will keep trying.\n" % (filename , crc_size)
        log_error(msg)
        return None

    modtime = time.ctime(os.path.getmtime(filename))

    # record initial content
    f.seek(0)
    init_buf = f.read(crc_size)

    # record terminal content
    f.seek(current_eof-crc_size)
    seekptr_buf = f.read(crc_size)

    # want this close to the read as possible
    read_time = time.time()

    init_crc = silly_splunk_hash(init_buf)
    seekptr_crc = silly_splunk_hash(seekptr_buf)

    file_info = collections.OrderedDict( 
        (
        ('read_time', read_time), 
        ('filename', filename), 
        ('modtime', modtime), 
        ('init_text', init_buf), 
        ('init_crc', init_crc), 
        ('current_eof', current_eof), 
        ('seek_text', seekptr_buf), 
        ('seek_crc', seekptr_crc)
        )
    )

    if larger_eof_readsize:
        if current_eof < larger_eof_readsize:
            buf = "too_small"
        else:
            f.seek(current_eof-larger_eof_readsize)
            buf = f.read(larger_eof_readsize)
        file_info['large_seek_text'] = buf

    return file_info

def main():
    if len(sys.argv) < 2:
        print "usage: file_end_sniffer.py output_file"
        sys.exit()

    logfile = sys.argv[1]
    lf = open(logfile, "w", 1)

    while True:
        for monitored_filename in monitored_filenames:
            info = get_seek_and_content_info(monitored_filename)
            if info:
                lf.write(repr(info) + "\n")

        time.sleep(poll_interval)

if __name__ == "__main__":
    main()

