#!/nsm/splunk/bin/python
import sys
import datetime, time
import os
import csv
import splunk.Intersplunk as sis

def parseOptions():
    files = []
    for arg in sys.argv[1:]:
        files.append(arg)

    return files

def lsFilename(files):
    file_output = {}
    list_file_dicts = []
    # Loop through all the logs in the list and output file stats for each.
    timestamp_iso = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%dT%H:%M:%S")
    timestamp_epoch = int(time.time()) 
    #timestamp_epoch = int((datetime.datetime.today() - datetime.datetime(1970,1,1)).total_seconds())
    for file in files:
        try:
            s = os.stat(file)
            logChmod = oct(s.st_mode & 0777)[1:]
            list_file_dicts.append({'run_time_iso': timestamp_iso,
                                    'run_time_epoch': timestamp_epoch,
                                    'file_name': file,
                                    'log_chmod': logChmod,
                                    'log_ctime': s.st_atime,
                                    'log_mtime': s.st_mtime,
                                    'log_size': s.st_size})
        except:
            pass

    sis.outputResults(list_file_dicts)


def main():
    # Returns a list of filenames/paths
    files = parseOptions()
    # Pass list of filenames to lsFilename function
    lsFilename(files)


if __name__ == '__main__':
    main()

