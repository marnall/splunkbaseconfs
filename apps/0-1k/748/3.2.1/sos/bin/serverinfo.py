import splunk.Intersplunk as si
from common import get_sos_server
import time
import socket
import subprocess
import os
import sys
import multiprocessing
import re

try:
    import ctypes
except:
    pass

_time=time.time()
sos_server=get_sos_server()


####################################
# meminfo(): returns the amount of physical and virtual memory present in GB
####################################
def meminfo():

  TotalPhys = "Could not be determined"

  if os.name == 'posix':

      if sys.platform.startswith("linux"):
          try:
              TotalPhys_re = re.compile(r'^MemTotal:\s+(\d+)\s')

              for line in open("/proc/meminfo"):
                  TotalPhys_match = TotalPhys_re.match(line)
                  if TotalPhys_match:
                      TotalPhys = int(round(float(TotalPhys_match.group(1))/1024**2))
          except:
              pass

      if sys.platform.startswith("darwin"):
          try:
              # if this is OSX, we won't have /proc/meminfo instead we'll need to execute system_profiler SPHardwareDataType
              pseudohandle = subprocess.Popen(["system_profiler", "SPHardwareDataType"], shell=False, stdout=subprocess.PIPE)
              stdout, stderr = pseudohandle.communicate()

              TotalPhys_re = re.compile(r'^\s+Memory\:\s+(\d+)\s+GB')

              for line in stdout.splitlines():
                  TotalPhys_match = TotalPhys_re.match(line)
                  if TotalPhys_match:
                      TotalPhys = TotalPhys_match.group(1)
          except:
              pass

      if sys.platform.startswith("sun"):
          try:
              pseudohandle = subprocess.Popen(["prtconf"], shell=False, stdout=subprocess.PIPE)
              stdout, stderr = pseudohandle.communicate()
              TotalPhys_re = re.compile(r'^Memory size\:\s+(\d+)\s+Megabytes')

              for line in stdout.splitlines():
                  TotalPhys_match = TotalPhys_re.match(line)
                  if TotalPhys_match:
                      TotalPhys = int(round(float(TotalPhys_match.group(1))/1024))
          except:
              pass


  if os.name == 'nt':

      try:
          class MEMORYSTATUSEX(ctypes.Structure):
              _fields_ = [("dwLength", ctypes.c_uint),
              ("dwMemoryLoad", ctypes.c_uint),
              ("ullTotalPhys", ctypes.c_ulonglong),
              ("ullAvailPhys", ctypes.c_ulonglong),
              ("ullTotalPageFile", ctypes.c_ulonglong),
              ("ullAvailPageFile", ctypes.c_ulonglong),
              ("ullTotalVirtual", ctypes.c_ulonglong),
              ("ullAvailVirtual", ctypes.c_ulonglong),
              ("sullAvailExtendedVirtual", ctypes.c_ulonglong),]

              def __init__(self):
                  # have to initialize this to the size of MEMORYSTATUSEX
                  self.dwLength = 2*4 + 7*8     # size = 2 ints, 7 longs
                  return super(MEMORYSTATUSEX, self).__init__()

          stat = MEMORYSTATUSEX()
          ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
          TotalPhys = round(float(stat.ullTotalPhys)/1024**3,2)

      except:
          TotalPhys = "not available"

  return(TotalPhys)


def cpuinfo():
    cpu_count = "Could not be determined"

    try:
        cpu_count = multiprocessing.cpu_count()
    except:
        pass

    return(cpu_count)


####################################
# main function
####################################
if __name__ == '__main__':
    try:
        keywords,options = si.getKeywordsAndOptions()
        if len(keywords) > 0:
            si.generateErrorResults('This command takes no arguments.')
            exit(0)
        conffile = ' '.join(keywords)

        results = []
        results.append({
            "host_fqdn" : socket.getfqdn(socket.gethostname()),
            "cpu_count" : cpuinfo(),
            "total_phys_mem_gb" : meminfo(),
            "_time" : _time,
            "sos_server" : sos_server,
            "source" : "serverinfo",
            "sourcetype" : "serverinfo"})
        si.outputResults(results)

    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))


