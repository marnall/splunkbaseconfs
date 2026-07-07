import sys,re
import json
import pyWhat.what_call
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration

name_pull = re.compile("\"Name\":(.*), \"Regex\"")
match_pull = re.compile("\"Matched\":(.*), \"Regex Pattern\"")
n = 1

@Configuration()
class whatthis(StreamingCommand):
  def stream(self, records):
    for record in records:
        message = ""
        try:
            message = self.fieldnames[0]
        except:
            message = '_raw'
        json_list = pyWhat.what_call.export_cli({record[message]})
        json_str_list = (json.dumps(json_list)).split("},")
        record['what_raw'] = json_list
        n = 1
        for json_str in json_str_list:
            full_string = ""
            name_string = name_pull.findall(json_str)
            match_string = match_pull.findall(json_str)
            full_string = full_string + str(name_string) + ":" + str(match_string) +","
            record["found_what_" + str(n) ] =  full_string
            n = n + 1
        yield record


if __name__ == "__main__":
  dispatch(whatthis, sys.argv, sys.stdin, sys.stdout, __name__)
