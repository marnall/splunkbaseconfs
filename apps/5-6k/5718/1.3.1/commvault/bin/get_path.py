import splunk.Intersplunk
try:
    fp = open("../local/software.conf","r")
    contents = fp.read()
    fp.close()
    content_list = contents.split("\n")
    json_list = []
    i = 0
    unix_flag = False
    windows_flag = False
    while(i < len(content_list)-1):
        temp = {}
        if "unix" in content_list[i].lower():
            unix_flag = True
        else:
            windows_flag = True
        os_content = content_list[i].split("[")[1]
        os_content = os_content.split("]")[0]
        temp['os'] = os_content
        temp['path'] = content_list[i+1]
        json_list.append(temp)
        i = i + 2

    if not unix_flag:
        temp = {'os' : 'Unix','path' : 'Unconfigured'}
        json_list.append(temp)
    if not windows_flag:
        temp = {'os' : 'Windows','path' : 'Unconfigured'}
        json_list.append(temp)

    splunk.Intersplunk.outputResults(json_list)
except Exception as excp:
    json_list = [{'os':'Windows','path':'Unconfigured'},{'os':'Unix','path':'Unconfigured'}]
    splunk.Intersplunk.outputResults(json_list)
