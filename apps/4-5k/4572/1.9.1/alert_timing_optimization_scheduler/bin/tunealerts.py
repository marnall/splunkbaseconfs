import re,sys,time
import splunk.Intersplunk
import os, fnmatch
import traceback
import gzip
from zipfile import ZipFile
import string
from io import open
from six.moves import range



alert_settings = {}
alert_unique_dictionary = {}

alerts_array_dict = []

# This list will hold the final alert values as { 'heading ' : 'value', heading2 : value2 ... }
parsed_final_alert = []


process_alert_name = "First Alert Not Processed"
process_alert = False

def process_alert_timing(array_of_dict_alerts):
    
    local_dict = {}
    alerts_count = 0
    try:
    

        for d in array_of_dict_alerts:
        
            alerts_count = alerts_count + 1
            local_dict = {'CRON' : d['cron_schedule']}

            parsed_final_alert.append(local_dict) 

    except:
            tracestack = traceback.format_exc()
            splunk.Intersplunk.generateErrorResults(tracestack)
            #print "except === exited"
            exit(0)
        
    finally:
        pass
    
   
    
    
    
    months = [0] * 1000
    day_of_week = [0] * 1000
    day_of_month = [0] * 1000
    hours = [0] * 1000
    minutes = [0] * 1000
   
    # Pass #1
    # Scan for repeating searches with a */n where n is a number.
    
    for d in parsed_final_alert:
        cron_string = d['CRON']
        cron_items = cron_string.split()
        
        
        # if * * * * * is present - then add 1 to all minute slots and skip the rest of the checks
        
        if (cron_items[0] == "*") and (cron_items[1] == "*") and (cron_items[2] == "*") and (cron_items[3] == "*") and (cron_items[4] == "*"):
            for j in range(0, 60):
                minutes[j] = minutes[j] + 1
                
        # now check if we are limited by months, days of month, weeks, hours or minutes.
        # break out of the longest period as this will limit the alert to run at the longest period setting.
        
        elif ("*/" in cron_items[3]): # month in year
            for j in range(1, 12, int(cron_items[3][2:])):
                months[j] = months[j] + 1
        elif ("*/" in cron_items[2][2:]): # day of month
            for j in range(1, 31, int(cron_items[2][2:])):
                day_of_month[j] = day_of_month[j] + 1
        elif ("*/" in cron_items[4]): # day_of_week
            for j in range(0, 6, int(cron_items[4][2:])):
                day_of_week[j] = day_of_week[j] + 1
        elif  ("*/" in cron_items[1]): # hour
            for j in range(0, 23, int(cron_items[1][2:])):
                hours[j] = hours[j] + 1
        elif  ("*/" in cron_items[0]):
            for j in range(0, 59, int(cron_items[0][2:])):
                minutes[j] = minutes[j] + 1
            
    # Pass #2 
    # look for m-m like 1-4 or so       
            
    for d in parsed_final_alert:
        cron_string = d['CRON']
        cron_items = cron_string.split()
        
        if ("-" in cron_items[3]): # month in year
            dash_terms = cron_items[3].split("-")
            for j in range(int(dash_terms[0]), int(dash_terms[1])+1):
                j = int(j)
                months[j] = months[j] + 1
        elif ("-" in cron_items[2]): # day in month
            dash_terms = cron_items[2].split("-")
            for j in range(int(dash_terms[0]), int(dash_terms[1])+1):
                j = int(j)
                day_of_month[j] = day_of_month[j] + 1
        elif ("-" in cron_items[4]): # day_of_week
            dash_terms = cron_items[4].split("-")
            for j in range(int(dash_terms[0]), int(dash_terms[1])+1):
                j = int(j)
                months[j] = months[j] + 1
        elif  ("-" in cron_items[1]): # hour in day
            dash_terms = cron_items[1].split("-")
            for j in range(int(dash_terms[0]), int(dash_terms[1])+1):
                j = int(j)
                hours[j] = hours[j] + 1   
        elif  ("-" in cron_items[0]):
            dash_terms = cron_items[0].split("-")
            for j in range(int(dash_terms[0]), int(dash_terms[1])+1):
                j = int(j)
                minutes[j] = minutes[j] + 1
     
    # Pass #3
    # Get non-decorated plain integars frmo cron fields
    
    for d in parsed_final_alert:
        cron_string = d['CRON']
        cron_items = cron_string.split()
        
        if not ( ("-" in cron_items[3] ) or ("*" in cron_items[3])): # month in year
            i = int(cron_items[3])
            months[i] = months[i] + 1
        elif not ( ("-" in cron_items[2] ) or ("*" in cron_items[2])): # day in month
            i = int(cron_items[2])
            day_of_month[i] = day_of_month[i] + 1
        elif not ( ("-" in cron_items[4] ) or ("*" in cron_items[4])): # week in month
            i = int(cron_items[4])
            day_of_week[i] = day_of_week[i] + 1
        elif   not ( ("-" in cron_items[1] ) or ("*" in cron_items[1])): # hour in day
            i = int(cron_items[1])
            hours[i] = hours[i] + 1   
        elif  not ( ("-" in cron_items[0] ) or ("*" in cron_items[0])):
            i = int(cron_items[0])
            minutes[i] = minutes[i] + 1
            
    
    
     
     
        alerts_schedule = []
     
     
            
    for i in range(1, 999):
        if( minutes[i] != 0):
            alerts_schedule.append( {'alerts' : minutes[i], 'runs at minute' : i} )
            
    for i in range(1, 999):
        if( hours[i] != 0):
            alerts_schedule.append( {'alerts' : hours[i], 'runs at hour' : i} )
           
    for i in range(1, 999):
        if( day_of_month[i] != 0):
            alerts_schedule.append( {'alerts' : day_of_month[i], 'runs at day of month' : i} )
            
            
    for i in range(1, 999):
        if( day_of_week[i] != 0):
            alerts_schedule.append( {'alerts' : day_of_week[i], 'runs at day of week' : i} )
           
    for i in range(1, 999):
        if( months[i] != 0):
            alerts_schedule.append( {'alerts' : months[i], 'runs at month' : i} )
           
    
    return(alerts_count, alerts_schedule)
         
             

def find_paths(fileList):
    
    inDIR = '../..'
    pattern = 'savedsearches.conf'
    #filelist = []
    
    
    #walk t hru directory
    for dName, sdname, fList in os.walk(inDIR):   
            
            
        for fileName in fList:
            if fnmatch.fnmatch(fileName, pattern): # Match namwe string
                if ((not "splunk_archiver" in dName) and (not "splunk_monitoring_console" in dName) and (not "splunk_instrumentation" in dName) and (not "search/default" in dName)):
                    fileList.append({'path to savedsearch.conf' : os.path.join(dName, fileName)})
    
    return (fileList)


def schedule_alerts(num_alerts, path_to_savedsearches_file):
    
    try:
    
        cron_strings = []
    
        orig_config = open(path_to_savedsearches_file, "r")
    
        new_config =  open("../appserver/static/new_config_files/savedsearches.conf", "w")
        
    
    
        new_saved_searches_file = []
    
        if (num_alerts < 60):
            alert_spacing = int(60/num_alerts)
            alerts_processed = 0
            i = 0
            while (alerts_processed < num_alerts):
                cron_string = str(i) + " * * * *"
                cron_strings.append(cron_string)
                i = i + alert_spacing
                alerts_processed = alerts_processed + 1
        
        else: # greater than 60 alerts
            alerts_processed = 0
            i = 0
            while (alerts_processed < num_alerts):
                cron_string = str(i) + " * * * *\n"
                cron_strings.append(cron_string)
                i = i + 1
                if i >=60:
                    i = 0
                alerts_processed = alerts_processed + 1
    
             
    #print cron_strings
    
    # Add the cron_strings to the original savedsearches.conf file. 
        for original_line in orig_config:
        
            if ("cron_schedule" in original_line):
                new_config.write("cron_schedule = " + cron_strings.pop(0))
                
            else:
                new_config.write(original_line)
                
            
        new_config.close()
        orig_config.close()
    
        # gzip the savedsearches.conf file
    
        f_in = open("../appserver/static/new_config_files/savedsearches.conf","r")
        f_out = gzip.open("../appserver/static/new_config_files/savedsearches.conf.gz", "w")
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()
        
        
        contents = open("../appserver/static/new_config_files/savedsearches.conf").read()
       
        open("../appserver/static/new_config_files/savedsearches.conf.dos","w").write(string.replace(contents, '\n', '\r\n'))
        
    
        os.rename("../appserver/static/new_config_files/savedsearches.conf.dos", "../appserver/static/new_config_files/savedsearches.conf")
        
        # zip the savedsearches.conf file
        
        os.chdir("../appserver/static/new_config_files")
        ZipFile("savedsearches.conf.zip", "w").write("savedsearches.conf")
    
    
        return(new_saved_searches_file)
    
    except: 
        tracestack = traceback.format_exc()
        splunk.Intersplunk.generateErrorResults(tracestack)
        exit(0) 




path_to_savedsearches_conf = ""        

try:
    keywords,options = splunk.Intersplunk.getKeywordsAndOptions()
    defaultval = options.get('default', None)
    field = options.get('field', '_raw')
    
    if len(keywords) != 1:
            splunk.Intersplunk.generateErrorResults('Requires exactly one argument. either the word "list" or "help" or a relative path to the savedsearches.conf file')
            exit(0)
            
    if (keywords[0] == "list"):
        saved_searches = []     
        saved_searches = find_paths(saved_searches)  
        splunk.Intersplunk.outputResults(saved_searches)
        exit(0) 
        
    if ((keywords[0] == "help") or (keywords[0] == "?")):
            
        help_line = []
        help_line.append({ 'help' : '--------------------- Help for Alert_Timing_Optimization_Scheduler app -------------------'})
        help_line.append({ 'help' : ' '})
        help_line.append({ 'help' : 'Use this app to view a summary of your current saved searches timing schedule'})
        help_line.append({ 'help' : ' '})
        help_line.append({ 'help' : 'The savedsearches.conf file presented in the search will be analyzed and the number of alerts running each'})
        help_line.append({ 'help' : 'minute, hour, day, week, month and year will be presented as tabulated search results'})
        help_line.append({ 'help' : 'In addition a new savedsearches.conf file is generated for all your alerts which may be downloaded from this app'})
        help_line.append({ 'help' : 'The new savedsearches.conf file will have your alerts now running hourly and balanced around the hour'})
        help_line.append({ 'help' : 'This is necessary if you have many alerts and are seeing skipped alerts'})
        help_line.append({ 'help' : ' '})
        help_line.append({ 'help' : 'Workflow steps for creating a csv file of your current alert timings and creating a new balances savedsearches.conf file'})
        help_line.append({ 'help' : '1) Issue this command: | tunealerts list'})
        help_line.append({ 'help' : 'This will give you a list of user defined alert directory paths on Splunk cloud or your on-prem splunk instance'})
        help_line.append({ 'help' : 'Example of directory listing: ../../search/local/savedsearches.conf which is a relative path to your saved searches'})
        help_line.append({ 'help' : ' '})
        help_line.append({ 'help' : 'Now highlight the relative directory path: ../../search/local/savedsearches.conf and right click the mouse and do a copy or use control C in windows'})
        help_line.append({ 'help' : 'in the search bar now simply type: | tunealerts ../../search/local/savedsearches.conf by pasting in the path and hit enter'})
        help_line.append({ 'help' : ' '})
        help_line.append({ 'help' : 'At this point one should see search results of saved search and alert timings presented below'})
        help_line.append({ 'help' : 'The app has also created a new savedsearches.conf file for you with your alerts and saved searches balanced and running hourly'})
        help_line.append({ 'help' : 'Now you can save the search timing results to a csv file or you can download a new balanced savedsearches.conf file'})
        help_line.append({ 'help' : ' '})
        help_line.append({ 'help' : 'Workflow steps for downloading a csv file of your current alert timings:'})
        help_line.append({ 'help' : 'This app is now showing a schedule of your current alerts as given in the savedsearches.conf file you supplied'})
        help_line.append({ 'help' : '2) In the top right use SAVE As to save this search as a REPORT. Name the report some name you choose'})
        help_line.append({ 'help' : '3) In the upper right of the Alert Timing Optimization Scheduler app is a dropdown showing "Default Views"'})
        help_line.append({ 'help' : '4) Use the drop-down arrow and select "REPORTS"'})
        help_line.append({ 'help' : '5) Find the report you just created - find the name you used...'})
        help_line.append({ 'help' : '6) You will see all your alerts below. Now find the Export arrow far upper right. Arrow points to a horizonal line. Hover over and see "Export"'})
        help_line.append({ 'help' : '7) In the dialogue box keep CSV. Name the file. Leave Number of results blank. The alert timings CSV file will now download to your downloads folder'}) 
        help_line.append({ 'help' : '8) Open the .csv file with Excel or Apple Numbers or app of your choice. Enjoy.'})
        help_line.append({ 'help' : 'Support- email devopsjeffreyfall@gmail.com send any errors or any comments'})
        help_line.append({ 'help' : ' '})
        help_line.append({ 'help' : 'Workflow steps for downloading a new balanced savedsearches.conf file which you can use in your Splunk installation:'})
        help_line.append({ 'help' : '1) Click the DASHBOARDS tab upper left with black background'})
        help_line.append({ 'help' : '2) Choose the "Download new balanced savedsearches.conf file" Dashboard'})
        help_line.append({ 'help' : '3) Click the button for "Download savedsearches.conf.zip" OR "download savedsearches.conf.gz"'})
        help_line.append({ 'help' : '4) uncompress the savedsearches.zip or savedsearches.gz in your Downloads folder'})
        help_line.append({ 'help' : '5) Make a backup of your current savedsearches.conf file'})
        help_line.append({ 'help' : '6) Copy the new savedsearches.conf file to the proper location on your Splunk server'})
        help_line.append({ 'help' : '7) Restart splunk'})
        help_line.append({ 'help' : 'Your alerts are now balanced across an hour. If you had 60 alerts you will have an alert running once a minute'})
        help_line.append({ 'help' : 'If you had 600 alerts your alerts are now balanced to run 10 alerts each minute'})
        help_line.append({ 'help' : 'This will make the saved searches and alerts run in the most balanced and consistent manner by spreading the saved searches load'})
        help_line.append({ 'help' : 'In one minute search slots around the hour'})
       
        splunk.Intersplunk.outputResults(help_line)
        exit(0)
    
    else:
        if (not "savedsearches.conf" in keywords[0]):
            splunk.Intersplunk.generateErrorResults('the path you entered does not contain the string "savedsearches.conf". Nope - no snooping other files allowed out of context. Try again. use | exportalerts list or | exportalerts help')
            exit(0)
            
        path_to_savedsearches_conf = keywords[0]
        

finally:
    pass

  ################################################################################################################################
  # Process savedsearches.conf file
  ################################################################################################################################
 


filehandle = open(path_to_savedsearches_conf, "r")
for item in filehandle:
    first = item[:1]
    
    if (first == "#"):
        break
    
    if (first == "["): # Here we have a valid alert
       
        if (process_alert_name == "First Alert Not Processed"):
            saved_search_name=item[item.find("[")+1:item.find("]")]
            process_alert_name="First Alert Now Processed..."
            #print "first alert processed"
        elif (process_alert_name  != "First Alert Not Processed"):
            process_alert_name = saved_search_name
            saved_search_name=item[item.find("[")+1:item.find("]")]
            process_alert = True                  
    
    else:
        try:
            special_case = item[0:8]
            if (special_case == "search ="):
                value = item[8:]
                alert_settings['search'] = value.strip()
                alert_unique_dictionary['search'] = value.strip()
            else:
                item = item.strip()
                my_pair = item.split("=",1)
                
                if (len(my_pair) == 2 ):
                
                    my_field = my_pair[0]
                    my_value = my_pair[1]
                
                    my_field = my_field.strip()
                    my_value = my_value.strip()
                
                    alert_settings[my_field] = my_value
                    alert_unique_dictionary[my_field] = my_value
          
        except:
            tracestack = traceback.format_exc()
            splunk.Intersplunk.generateErrorResults(tracestack)
            exit(0)
        
  
  
    if (process_alert == True):
        
        alert_settings['alert_name'] = process_alert_name.strip()
        alerts_array_dict.append(alert_settings)
        
        
        process_alert = False
        alert_settings = {}

        
alert_settings['alert_name'] = saved_search_name.strip()
alert_unique_dictionary['alert_name'] = saved_search_name.strip()
alerts_array_dict.append(alert_settings)



num_alerts, alerts_schedule_to_print = process_alert_timing(alerts_array_dict)


schedule_alerts(num_alerts, path_to_savedsearches_conf)


splunk.Intersplunk.outputResults(alerts_schedule_to_print)
