def check_if_file_exists(filename):
    try:
        fp = open("../local/"+filename,"r")
        fp.close()
        return True
    except Exception as excp:
        return False

def delete_entry_from_forwarder_details(client_list, commserve):
    fp = open("../local/forwarder_details.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    fp.close()

    i = 0
    with open("../local/forwarder_details.conf","w") as fp:
        while(i < len(content_list)-1):
            webserver = content_list[i].split("]")[0]
            webserver = webserver.split("[")[1]
            client_name = content_list[i+1].split(":")[1]
            if webserver == commserve and client_name in client_list:
                i = i + 7
            else:
                for j in range(0,7):
                    fp.write(content_list[i+j] + '\n')
                i = i + 7

def delete_entry_from_software_status(client_list, commserve):
    fp = open("../local/software_status.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    fp.close()

    i = 0
    with open("../local/software_status.conf","w") as fp:
        while(i < len(content_list)-1):
            webserver = content_list[i].split("]")[0]
            webserver = webserver.split("[")[1]
            client_name = content_list[i+1].split(":")[1]
            if webserver == commserve and client_name in client_list:
                i = i + 3
            else:
                fp.write(content_list[i] + '\n')
                fp.write(content_list[i+1] + '\n')
                fp.write(content_list[i+2] + '\n')
                i = i + 3

def delete_entry_from_forwarder(client_list, commserve):
    fp = open("../local/forwarder.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    fp.close()

    i = 0
    with open("../local/forwarder.conf","w") as fp:
        while(i < len(content_list)-1):
            webserver = content_list[i].split("]")[0]
            webserver = webserver.split("[")[1]
            client_name = content_list[i+1].split(":")[1]
            if webserver == commserve and client_name in client_list:
                i = i + 4
            else:
                for j in range(0,4):
                    fp.write(content_list[i+j] + '\n')
                i = i + 4

def delete_entry_from_client(client_list, commserve):
    with open("../local/client.conf","r") as fp:
        lines = fp.readlines()

    i = 0
    with open("../local/client.conf","w") as fp:
        while i < len(lines):
            ip = lines[i]
            webserver = ip.split("]")[0]
            webserver = webserver.split("[")[1]
            fp.write(lines[i])
            i = i + 1
            if commserve == webserver:
                while(i < len(lines) and lines[i] != "[end]"):
                    if(lines[i].strip("\n") not in client_list):
                        fp.write(lines[i])
                        i = i + 1
                    else:
                        i = i + 1
            else:
                while(i < len(lines) and lines[i] != "[end]"):
                    fp.write(lines[i])
                    i = i + 1
            if(i < len(lines) and lines[i] == "[end]"):
                fp.write(lines[i])
            i = i + 1

def delete_from_new_client(client_list, commserve):
    with open("../local/new_client.conf","r") as fp:
        lines = fp.readlines()

    i = 0
    with open("../local/new_client.conf","w") as fp:
        while i < len(lines):
            ip = lines[i]
            webserver = ip.split("]")[0]
            webserver = webserver.split("[")[1]
            fp.write(lines[i])
            i = i + 1
            if commserve == webserver:
                while(i < len(lines) and lines[i] != "[end]"):
                    if(lines[i].strip("\n") not in client_list):
                        fp.write(lines[i])
                        i = i + 1
                    else:
                        i = i + 1
            else:
                while(i < len(lines) and lines[i] != "[end]"):
                    fp.write(lines[i])
                    i = i + 1
            if(i < len(lines) and lines[i] == "[end]"):
                fp.write(lines[i])
            i = i + 1

def clean(client_name, commserve):
    if check_if_file_exists("forwarder_details.conf"):
        delete_entry_from_forwarder_details([client_name], commserve)

    if check_if_file_exists("software_status.conf"):
        delete_entry_from_software_status([client_name], commserve)

    if check_if_file_exists("forwarder.conf"):
        delete_entry_from_forwarder([client_name], commserve)

    if check_if_file_exists("client.conf"):
        delete_entry_from_client([client_name], commserve)

    if check_if_file_exists("new_client.conf"):
        delete_from_new_client([client_name], commserve)
