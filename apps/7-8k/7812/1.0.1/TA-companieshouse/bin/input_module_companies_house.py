
# encoding = utf-8

import os
import sys
import time
import datetime
import re
import zipfile
import shutil
import urllib.request
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

output_dir = splunk_lib_util.make_splunkhome_path(['var', 'log','companieshouse'])

# Ensure the output directory is writable
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
 

def get_latest_file_link(helper,r1,r2):
    url = "https://download.companieshouse.gov.uk/en_output.html"
    
    with urllib.request.urlopen(url) as response:
        html = response.read().decode('utf-8')

    # Define regex patterns
    zip_file_pattern = r'href="('+r1+')"'
    date_pattern = r'\s*<strong>Last Updated:</strong>\s*('+r2+')'

    # Find the ZIP file link
    match = re.search(zip_file_pattern, html)
    zip_link = f"https://download.companieshouse.gov.uk/{match.group(1)}" if match else None
    # Find the Last Updated date
    date_match = re.search(date_pattern, html)
    last_updated_date = date_match.group(1) if date_match else "Unknown"

    return zip_link, last_updated_date


def download_file(helper,url):
    try:
        name = url.split("/")[-1]
        filename = splunk_lib_util.make_splunkhome_path(['var', 'log','companieshouse', name]) 
        helper.log_info(f"Downloading {filename} from {url}...")
        urllib.request.urlretrieve(url, filename)
        helper.log_info(f"File downloaded successfully: {filename}")
        return filename
    except Exception as e:
        helper.log_error(f"Error downloading file: {e}")
        return None


def extract_csv_from_zip(helper,zip_filename):
    extracted_csv = None
    try:
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            # Find the first CSV file in the ZIP archive
            for file in zip_ref.namelist():
                if file.endswith('.csv'):
                    extracted_csv = file
                    zip_ref.extract(file, path=output_dir)
                    helper.log_info(f"Extracted CSV: {file}")
                    break
    except Exception as e:
        helper.log_error(f"Error extracting CSV: {e}")

    return extracted_csv

def process_csv_and_send_to_splunk(helper,csv_filename,ew, cur_time, batch_size=1000):
    csv_path = os.path.join(output_dir, csv_filename) 
    helper.log_info(f"event_time: {cur_time}")
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            i=0
            for line in f:
                if i==0:   # Skip header row
                    i=i+1
                    continue
                # i=i+1
                # if i >= 10000:
                #   break
                event = helper.new_event(data=line, time=cur_time, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
                ew.write_event(event)
    else:
        helper.log_error("CSV file not found.")


def clear_output_directory(helper,directory_path):
    helper.log_info("cleanup started")
    if os.path.exists(directory_path):
        shutil.rmtree(directory_path)  # Deletes entire directory and its contents
        helper.log_info(f"Deleted: {directory_path}")
    else:
        helper.log_info("Output directory does not exist.")


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # company_data_as_one_file = definition.parameters.get('company_data_as_one_file', None)
    # last_updated = definition.parameters.get('last_updated', None)
    pass

def collect_events(helper, ew):
    
    opt_company_data_as_one_file = helper.get_arg('company_data_as_one_file')
    opt_last_updated = helper.get_arg('last_updated')

    helper.log_info("input started")
    zip_link, last_updated_date = get_latest_file_link(helper,opt_company_data_as_one_file,opt_last_updated)
    
    if zip_link==None:
        helper.log_error("Company data as one file didn't match with given regex. Please update the regex in configurations page")
        return
    
    if last_updated_date=="Unknown":
        helper.log_error("Last Updated date didn't match with given regex. Please update the regex in configurations page")
        return
      
    # Need to comment below line after test
    # helper.delete_check_point("companieshouse_checkpoint")
    
    # Initial checkpoint logic    
    data_checkpoint = helper.get_check_point("companieshouse_checkpoint")
    if data_checkpoint != last_updated_date:
        # Download the file
        zip_filename = download_file(helper,zip_link)
        if zip_filename:
            # Extract CSV from ZIP
            csv_filename = extract_csv_from_zip(helper,zip_filename)
            if csv_filename:
                # Read CSV content and ingest in splunk
                cur_time=time.time()
                helper.save_check_point("companieshouse_checkpoint", last_updated_date)
                process_csv_and_send_to_splunk(helper,csv_filename,ew,cur_time)
                clear_output_directory(helper,output_dir)
    else:
        helper.log_info("No new updates.")
        return
