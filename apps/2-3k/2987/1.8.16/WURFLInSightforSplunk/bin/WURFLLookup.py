

import csv
import sys
import logging
from subprocess import check_output
from ast import literal_eval
import tempfile
import os
""" Lookup Search Script for the Command wurfl_lookup
    Synatx: lookup wurfl_lookup user_agent
    Process the Events, which are flushed to instream in CSV form
    Interacts with the java process by flushing the useragents to java input stream and retreive the device ids and required_capabilities
    Flush the useragents and their corresponding device id and required_capabilities to the OutStream in CSV format
    Logger is maintained and level is set to ERROR
"""

logging.basicConfig(filename='WURFLLookup.log',level=logging.ERROR, format='[%(asctime)s] %(levelname)s: %(message)s')



def main():
    	
    logging.debug("main started: ")
    """ Storing the useragent field name to useragent variable
    """
    useragent = sys.argv[1]
    args=""
    logging.debug("useragent: %s ", useragent)
    """ Storing the capabilities configured fieldnames along with device id to args variable
    """
    for i in range(2,len(sys.argv)):
        if i==2 :
            args=""+sys.argv[i]+""
        else :
            args=args+","+sys.argv[i]+""
    logging.debug("args: %s", args)	
    
    logging.debug("getting infile and outfile: ")
    """ Connecting to the input and output streams for reading the input and writing the output
    """
    infile = sys.stdin
    outfile = sys.stdout
    logging.debug("infile: %s", infile)
    logging.debug("outfile: %s", outfile)
    logging.debug("infile: %s", infile)
    """ Reading the CSV formatted input using DictReader and get fieldnames to header variable
    """
    r = csv.DictReader(infile)
    header = r.fieldnames
    logging.debug("header: %s", header)
    """ Creating the ouput in CSV formatted using DictWriter with the fieldnames from header variable
        Write the headers to the first line
    """
    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()
    logging.debug("r: %s", r)
    input=args
    try:
        """ Storing the each useragent field to input variable by escaping the escape character and seperated each useragent with a new line and enclosed with in double quotes
        """
        for result in r:
            """logging.debug("Result : %s", (result))"""
            for i in range(1,len(sys.argv)):
                if i == 1:
                   if result[sys.argv[i]].endswith("\\") :
                      input = input+"\n\""+result[sys.argv[i]]+"\\\""
                   else :
                      input = input+"\n\""+result[sys.argv[i]]+"\""
                else :
                   input = input+","+result[sys.argv[i]]
        """logging.info("input : %s \n fieldnames: %s ", input, r.fieldnames)"""
        """ Invoking the java process and Flushing the 'input' to the java process input stream so that the java process reads the input and 
            processes the useragents and retrieves the device ids along with the required_capabilities and flushes them as python readable format
        """
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(input)
        f.close()
        logging.debug("Temp File name is %s", f.name)	
        op_list = []
        opt = check_output(['java', '-jar', 'WURFLInSightForSplunkExternalLookup.jar', f.name, useragent, args], universal_newlines=True)
        """ Reading the output from java process and convert to dict type and writes each row to output stream
        """
        op_list = opt.splitlines()
        for line in op_list:
            op1 = "{"+line.rstrip()+"}"
            row = (literal_eval(op1))
            ua = row[useragent]
            if ua.endswith("\\\\"):
               row[useragent] = ua[0:(len(ua)-3)]+"\\"
            w.writerow(row)
        os.unlink(f.name)
        logging.debug("Temp file is deleted successfully")		
    except Exception as e:
        exc = e
        logging.exception("Error in Processing Results %s", e)	
        logging.exception("op1 %s", op1)	
    logging.debug("done output")

main()
