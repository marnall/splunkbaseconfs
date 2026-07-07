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

def get_indexer_ip_port():
    try:
        fp = open("../local/indexerip.conf")
        contents = fp.read()
        content_list = contents.split("\n")
        return content_list[0]
    except Exception as excp:
        return ""

try:

    index_name = get_index_name()
    indexer_ip_port = get_indexer_ip_port()
    json_list = []
    d= {}

    if indexer_ip_port != "":
        indexer_ip = indexer_ip_port.split(":")[0]
        receiving_port = indexer_ip_port.split(":")[1]
    else:
        indexer_ip = "Not Configured"
        receiving_port = "Not Configured"

    d["IndexerIP"] = indexer_ip
    # d["ReceivingPort"] = receiving_port

    d["ReceivingPort"] = receiving_port

    if index_name == "":
        d['IndexName'] = "Not Configured"
    else:
        d['IndexName'] = index_name

    json_list.append(d)
    splunk.Intersplunk.outputResults(json_list)

except Exception as excp:
    fp = open('internal_log.txt','a')
    fp.write(str(excp) + '\n')
