from __future__ import absolute_import, print_function
import os,sys,splunk,glob,re,errno,time,datetime,csv,gzip,subprocess,shutil
import log,logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.modularinput import *
import splunklib.client as client
from splunklib.modularinput import Argument
from splunklib.modularinput import Script
from splunklib.modularinput import Event
from splunklib.modularinput import Scheme
from datetime import datetime, timedelta
import splunklib.six as six
import splunk.clilib.cli_common as cli
from subprocess import Popen, PIPE
from sys import platform as platform_str
from time import gmtime, strftime
## Global Variables and defaults
logger = log.Log().get_logger("sample_data")
base_path=os.path.dirname(os.path.abspath(__file__))
parentDir = os.path.dirname(base_path)
bin_fldr = os.path.join(parentDir,'bin')
data_fldr = os.path.join(parentDir,'logs/data')
lkp_fldr = os.path.join(parentDir,'lookups')
## Get List of data sample template files to perform the date update to, if enabled
sample_list_file = os.path.join(lkp_fldr,'vjm_sample_data_list.csv')
tgt_time=""
hour_counter=0
today = datetime.now()

class VJMInput(Script):
    def get_scheme(self):
        scheme = Scheme("VJ-SampleData")
        scheme.description = "Loads Sample Data for the Value Journey for Splunk application. Verify Index Setting before Enabling."
        scheme.use_external_validation = True
        scheme.use_single_instance = True
        target_date_type_arg = Argument(
            name="target_date_type",
            title="Date Type",
            description="Enter 0 for Loading Todays and Tomorrows Sample Data. Enter 1 for Only Loading Tomorrow's Sample Data.  After the target data is loaded, the input will be set to 1 to load tomorrows data once every 24hrs.",
            data_type=Argument.data_type_number,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(target_date_type_arg)
        last_load_status_arg = Argument(
            name="last_load_status",
            title="Last Load Status",
            description="No Entry required: Holder for the Status of the last attmpeted Sample Data Load.",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(last_load_status_arg)
        last_load_date_arg = Argument(
            name="last_load_date",
            title="Date for Last Data Load",
            description="No Entry required: Holder for the date period of the Last Succesful Sample Data Load.",
            data_type=Argument.data_type_number,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(last_load_date_arg)
        next_load_time_arg = Argument(
            name="next_load_time",
            title="Scheduled Time for Next Load",
            description="No Entry required: Holder for when the next sample data load is scheduled.",
            data_type=Argument.data_type_number,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(next_load_time_arg)     
        return scheme
    def validate_input(self, v):
    	try:
        	target_date_type = int(v.parameters["target_date_type"])
        	if target_date_type > 2:
        		raise ValueError(' Invalid Entry - Must Enter 0 for indexing Sample data with Today and Tomorrow date, 1 for only Tomorrow Only date or 2 for Today Only.')
        except Exception as e:
        	raise ValueError(' Invalid Entry - Must Enter 0 for indexing Sample data with Today and Tomorrow date, 1 for only Tomorrow Only date or 2 for Today Only.')
        target_index = str(v.parameters["index"])
        if target_index =="main":
        	raise ValueError(' Invalid Index Entry in More Settings - The Default(Main) Index cannot be used. Create a new index that is seperated from production data, either with the name vj_ex or a custom one.')

    def stream_events(self, inputs, ew):
		for input_name, input_item in inputs.inputs.iteritems():
			session_key = self._input_definition.metadata["session_key"]
			args = {'token':session_key}
			service = client.connect(**args)
			kind, input_name = input_name.split("://")
			item = service.inputs.__getitem__((input_name, kind))
			tgt_input_name = "input_vjm_sample_data://"+input_name
			err_stat=""
			err_stat_msg=""
			tgt_d_l_date = ""
			tgt_last_type = 0
			script_dur = 0
			global tgt_idx_name
			tgt_idx_name = str(input_item['index'])
			global tgt_d_type
			tgt_d_type = int(input_item['target_date_type'])
			if tgt_d_type == '':
				tgt_d_type = 0
			tgt_d_l_date = str(input_item['last_load_date'])
			log_scrpt_settings= "input_name="+tgt_input_name+",target_date_type="+str(tgt_d_type)+",tgt_index="+tgt_idx_name
			logger.info('status=start,' + str(log_scrpt_settings))
			while tgt_d_type < 2:
				s_time = time.time()
				tgt_time_val=set_time_val(tgt_d_type)
				prev_l_date = str(tgt_time_val.strftime("%m/%d/%y"))
				if tgt_d_type == 0:
					tgt_d_label = "Today Date"
				else:
					tgt_d_label = "Tomorrow Date"
				if tgt_d_l_date == prev_l_date:
					logger.info('status=skipped,message=Data Load skipped because data has been already loaded,target_date_label=' + tgt_d_label + ',target_date=' + format(prev_l_date))
					tgt_d_type = tgt_d_type + 1
					break
				else:
					times = {
						'TmWday': tgt_time.strftime("%A"),
						'TmabrWday': tgt_time.strftime("%a"),
						'Tmday': tgt_time.strftime("%d"),
						'Tmyear': tgt_time.strftime("%Y"),
						'Tmabryear': tgt_time.strftime("%y"),
						'TmabrMnth': tgt_time.strftime("%b"),
						'TmfullMnth': tgt_time.strftime("%B"),
						'TmMnth': tgt_time.strftime("%m")
					}
					try:
						os.chdir(data_fldr)
						cur_dir_files = os.listdir(os.getcwd())
						with open(sample_list_file) as csvfile:
							readCSV = csv.reader(csvfile, delimiter=',')
							for row in readCSV:
								data_file=os.path.join(parentDir,'logs/data/'+row[5])
								v_enabled=str(row[0])
								logfile=str(row[1])
								v_host=str(row[2])
								v_src_type=str(row[3])
								v_src=str(row[4])
								if v_enabled=="TRUE":
									if logfile in cur_dir_files:
										orig_content = read_file(logfile)
										temp_content = orig_content
										lg_det=" - Log File ("+logfile+") src_type ("+v_src_type+") index ("+tgt_idx_name+")"
										if temp_content != '':
											try:
												temp_content = re.sub('#UNIX_TIME\((\d+)\)#', unix_replacement, temp_content)
												for key in times.keys():
													temp_content = re.sub("#" + key + "#", times[key], temp_content, flags=re.M)
											except IOError as e:
												logger.error('status=failure,message=Part 1 - Unable to update Time Variables,details=' + format(lg_det))
												logger.error('status=failure,message=Part 2 - Unable to update Time Variables,details=' + format(e))
												err_stat="Error"
												err_stat_msg="Failed Data Load: Review 'VJM - Sample Data Load Analysis' dashboard"
												break
											excellent_event = Event(
												data="%s" % temp_content,
												stanza="input_vjm_sample_data",
												host=v_host,
												index=tgt_idx_name,
												source=v_src,
												sourcetype=v_src_type,
												done=True,
												unbroken=True
											)
											try:
												ew.write_event(excellent_event)
											except Exception as e:
												logger.error('status=failure,message=Part 1 - Writing Event Data,details=' + format(lg_det))
												logger.error('status=failure,message=Part 2 - Writing Event Data,details=' + format(e))
												err_stat="Error"
												err_stat_msg="Failed Data Load: Review 'VJM - Sample Data Load Analysis' dashboard"
												break
											err_stat="success"
										else:
											logger.error('status=Warning,message=Sample Log File is not in vjm_splunk/logs/data directory,details=' + format(logfile))
								elif v_enabled=="FALSE":
									logger.info('status=disabled,message=Sample Log File is Disabled and will be skipped,details=' + format(str(row[1])))
						e_time = time.time()
						script_dur += e_time - s_time
						tgt_last_type = str(tgt_d_type)
						tgt_d_type = tgt_d_type + 1
						if tgt_d_type > 1:
							script_dur = '' + str(script_dur)
							logger.info('status=' + err_stat + ',duration=' + str(script_dur) + ',target_date_label=' + tgt_d_label + ',target_date=' + tgt_d_l_date)
							update_cur_mod_input(tgt_input_name,tgt_last_type,tgt_idx_name,err_stat,err_stat_msg,tgt_d_l_date)
					except Exception as e: # pylint: disable=broad-except
						logger.error('status=failure,message=Trouble Accessing vjm_sample_data_list.csv file,details=' + format(e))
						break

# Check for target Directory to update inputs.conf
def check_and_listdir(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return os.listdir(path)
# Set Date Parameters that will be used to update sample data matching variables.
def set_time_val(set_time):
	global tgt_time
	tomorrow = today + timedelta(days = 1)
	if set_time==0:
		tgt_time = today	
	elif set_time==1:
		tgt_time = tomorrow
	return tgt_time
# Read target file for updating and outputting updated events.
def read_file(path): 
    contents = ''
    try:
    	with gzip.open(path, 'r') as f:
    		contents = f.read()
    except Exception as e:
    	msg = path+" - Error: "+e
    	logger.error('status=failure,message=An error occurred reading log file,details=' + format(msg))
    return contents
# Update holder settings in the local/inputs.conf file with new values.  Copy from default if there isn't an inputs.conf file already there
def update_cur_mod_input(tgt_input,tgt_date,tgt_index,e_stat,e_stat_msg,e_prev_date):
	src_file = parentDir + "/default/inputs.conf"
	dest_path = parentDir + "/local/"
	dest_file = dest_path + "inputs.conf"
	local_files = check_and_listdir(dest_path)
	tgt_load_stat = ""
	tgt_input_disabled = ""
	tgt_input_index = tgt_index
	tgt_next_load = today + timedelta(days = 1)
	if e_stat == "success":
		tgt_load_stat = "Success: Sample Data Loaded"
		tgt_load_date = str(tgt_time.strftime("%m/%d/%y"))
		tgt_next_load = str(tgt_next_load.strftime("%m/%d/%y %I:%M %p"))
		tgt_load_date_type = "1"
		tgt_load_interval = "86460"
		tgt_input_disabled = "false"
	else:
		tgt_load_stat = e_stat_msg
		tgt_load_date = ""
		tgt_next_load = ""
		tgt_load_date_type = str(tgt_date)
		tgt_load_interval = ""
		tgt_input_disabled = "true"
	if not 'inputs.conf' in local_files:
		try:
			shutil.copyfile(src_file, dest_file)
		except Exception as e:
			logger.info('status=' + e_stat + ',message=No Inputs.conf exist in default directory,details=' + format(e))
	try:
		conf_file = cli.readConfFile(dest_file)
		conf_file[tgt_input].update({'interval': tgt_load_interval})
		conf_file[tgt_input].update({'disabled': tgt_input_disabled})
		conf_file[tgt_input].update({'target_date_type': tgt_load_date_type})
		conf_file[tgt_input].update({'last_load_status': tgt_load_stat})
		conf_file[tgt_input].update({'last_load_date': tgt_load_date})
		conf_file[tgt_input].update({'next_load_time': tgt_next_load})
		conf_file[tgt_input].update({'index': tgt_input_index})
		inp_msg='\n[' + tgt_input + ']\ninterval = ' + tgt_load_interval + '\ndisabled = ' + tgt_input_disabled + '\ntarget_date_type = ' + tgt_load_date_type + '\nlast_load_status = ' + tgt_load_stat + '\nlast_load_date = ' + tgt_load_date + '\nnext_load_time = ' + tgt_next_load + '\nindex = ' + tgt_input_index
		logger.info('status=' + e_stat + ',message=New Input Settings,input_settings="' + format(inp_msg) + '"')
		cli.writeConfFile(dest_file, conf_file)
	except Exception as e:
		logger.error('status=failure,message=Unable to Update data input in the Inputs.conf,details=":"')
		logger.error(format(e))

# Replace unix timestamps with the current datetime for the correct hour
def unix_replacement(match):
    timestamp = datetime.utcfromtimestamp(float(match.group(1)))
    new_ts = datetime(tgt_time.year, tgt_time.month, tgt_time.day, int(hour_counter), timestamp.minute, timestamp.second, timestamp.microsecond)
    return new_ts.strftime("%s")

if __name__ == "__main__":
	sys.exit(VJMInput().run(sys.argv))