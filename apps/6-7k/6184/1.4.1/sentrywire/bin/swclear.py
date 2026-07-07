import os
import sys
import time

try:
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration
except ImportError as e:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "lib"))
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration

PCAP_DIRECTORY = os.getenv("SPLUNK_HOME") + "/etc/apps/sentrywire/appserver/static/pcaps/"

def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


@Configuration()
class SentrywireClearCommand(StreamingCommand):

    def stream(self, events):
        size = 0
    
        try:
            for f in os.listdir(PCAP_DIRECTORY):
                size += os.path.getsize(os.path.join(PCAP_DIRECTORY, f))
                os.remove(os.path.join(PCAP_DIRECTORY, f))
                
            file_size = sizeof_fmt(size)
            yield {'_time': time.time(), 'event_no': 0,
                   '_raw': 'Local PCAP storage cleared.'}
            yield {'_time': time.time(), 'event_no': 0,
                   '_raw': 'Cleared ' + str(file_size)}
        except Exception as e:
            yield {'_time': time.time(), 'event_no': 0,
                   '_raw': 'Error: ' + str(e)}


try:
    dispatch(SentrywireClearCommand, sys.argv, sys.stdin, sys.stdout, __name__)
except Exception as e:
    sys.stderr.write(str(e))
