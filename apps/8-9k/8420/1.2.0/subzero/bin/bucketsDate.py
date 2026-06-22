import os
import csv
import glob
#get the SPLUNK_HOME environment variable
SPLUNK_HOME = os.environ.get('SPLUNK_HOME')
#define lookup file location
lookup_file = (f"{SPLUNK_HOME}/etc/apps/subzero/lookups/myindexes.csv")
#define where to write output files
new_lookup_location = (f"{SPLUNK_HOME}/etc/apps/subzero/lookups/")
#define the function
def process_csv(lookup_file):
#open the csv
	with open(lookup_file, mode='r', newline='', encoding='utf-8') as file:
#read each row of the csv defining variables for each item
		csv_reader = csv.reader(file, delimiter=',')
		next(csv_reader) #skip header
		for row in csv_reader:
			if row:
				#this defines the indexname variable
				var1 = row[0]
				#this defines the frozenpath variable
				var2 = row[1]
				#this defines the pattern the files must match
				pattern = 'db_*'
				#this defines the path to look at for files that match the pattern
				files = glob.glob(os.path.join(var2, pattern), recursive=False)
				#create files named by index
				with open(f"{new_lookup_location}{var1}.csv", "w", newline='') as csvfile:
					#write the header into each file
					csvfile.write("bucket,start,end"+'\n')
					#loop through each file in the listed directory
					for file_path in files:
						#strip out the path and store the filename only
						filename = os.path.basename(file_path)
						#split the filename into multiple variables
						a, b, c, d = filename.split('_')
						#write the filename and its cooresponding variables to the index csv
						csvfile.write(filename + "," + c + "," + b + '\n')
#call the function
process_csv(lookup_file)
