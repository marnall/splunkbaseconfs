import datetime

def make_entry(file_name, log_line):

    fp = open("../local/SplunkPlugin.log","a")
    date_time = datetime.datetime.now()
    fp.write(str(date_time) + " " + file_name  + " " + log_line + "\n")
    fp.close()
