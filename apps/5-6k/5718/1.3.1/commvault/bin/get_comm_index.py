import splunk.Intersplunk
import splunklogger as SL

def get_index_name():
    try:
        fp = open("../local/commindex.conf","r")
        contents = fp.read()
        content_list = contents.split("\n")
        return content_list[0]
    except Exception as excp:
        return ""

d = {}
json_list = []
d["Index"] = get_index_name()
json_list.append(d)
splunk.Intersplunk.outputResults(json_list)
