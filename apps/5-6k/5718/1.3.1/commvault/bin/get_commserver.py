import splunk.Intersplunk

fp = open("../local/commcell.conf","r")
contents = fp.read()
content_list = contents.split("\n")
processed_commcell = []
output_list = []

for i in range(0,len(content_list)-1,4):
    commcell_name = content_list[i+1].split("=",1)[1]
    if commcell_name not in processed_commcell:
        results = {"commserve":commcell_name}
        output_list.append(results)
        processed_commcell.append(commcell_name)

splunk.Intersplunk.outputResults(output_list)
