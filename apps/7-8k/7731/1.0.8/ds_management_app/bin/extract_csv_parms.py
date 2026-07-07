import csv,re, os,traceback
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
from ds_utils import log

main_csv_path = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ds_management_app", "lookups", "serverclass.csv"])
secoundary_csv_path = splunk_lib_util.make_splunkhome_path(["var", "run", "ds_management_app", "lookups", "serverclass.csv"])

def is_line_present(target_row):
    """
    Check if a row in the CSV matches the first three values of the given target row.
    
    :param csv_path: Path to the CSV file.
    :param target_row: List of the first three values to match (e.g., ["test-3", "-", "blacklist"]).
    :return: True if a matching row is found, False otherwise.
    """
    with open(main_csv_path, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[:3] == target_row:  # Compare only the first 3 elements
                
                return True,convert_to_int(row[-1])
    return False,None

def convert_to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return value

def make_path(path):
    if os.sep == "\\":
        if("/" in path):
            return
        else:
            return path.split(os.sep)
    elif os.sep == "/":
        if("\\" in path):
            return
        else:
            return path.split(os.sep)
    else:
        return path

def extrace_csv():
    
    
    if not os.path.exists(main_csv_path):
        with open(main_csv_path, mode='w') as main_csv_file:
            main_csv_file.write('Serverclass,App,Key,Value\n')
            
    os.makedirs(os.path.dirname(secoundary_csv_path), exist_ok=True) 
    
    with open(main_csv_path, mode='r') as main_csv_file:
        main_reader = csv.DictReader(main_csv_file)
        main_data = [row for row in main_reader]
    
    updated_rows= []
    
    # Iterate all rows from serverclass.csv at location - Lookup Directory
    for row in main_data:
        serverclass, app, key, value = row["Serverclass"], row["App"], row["Key"], row["Value"]

        if key == 'blacklist_from_pathname' or key =='whitelist_from_pathname':
            dest_csv_path = make_path(str(value))  # This is the path to the destination CSV
            if dest_csv_path == None:
                log("ERROR",f"CSV path: {str(value)} is incorrect for serverclass: {serverclass}. Please ensure you are using proper path seperator as per the OS.")
                continue
            else:
                dest_csv_path = splunk_lib_util.make_splunkhome_path(dest_csv_path)
                   
            method=str(key.split("_")[0])
            # Check for all ohter conditional parameters
            present_select_field_row,select_field_row_value=is_line_present([serverclass,app,method+"_select_field"])
            present_where_field_row,where_field_row_value=is_line_present([serverclass,app,method+"_where_field"])
            present_where_equals_row,where_equals_row_value=is_line_present([serverclass,app,method+"_where_equals"])
            
            # Make a list of where_equals parameter
            if where_equals_row_value != None:
                where_equals_row_value=str(where_equals_row_value).split(",")
                where_equals_row_value= [".*"+value[1:] if value.startswith("*") else value for value in where_equals_row_value]
                
            if select_field_row_value == None:
                select_field_row_value = 0
            
            # Read all lines from the destination CSV
            try:            
                with open(dest_csv_path, mode='r') as dest_csv_file:
                    dest_reader = csv.reader(dest_csv_file)
                    
                    header=True
                    if type(select_field_row_value)== int:
                        header = False
                    header_line=[]
                    
                    for line in dest_reader:
                        # For Header line of destination csv
                        if header:
                            header_line=line
                            header=False
                            
                            # Only for blacklist_from_pathname paramter
                            if present_select_field_row and not present_where_field_row:
                                if not type(select_field_row_value)== int:
                                    try:
                                        select_field_row_value=line.index(select_field_row_value) 
                                    except ValueError:
                                        select_field_row_value = None 
                            
                            #  blacklist_from_pathname and all other 2 parameters           
                            if present_select_field_row and present_where_field_row and present_where_equals_row:
                                if not type(where_field_row_value)== int:
                                    try:
                                        where_field_row_value=line.index(where_field_row_value)
                                    except ValueError:
                                        where_field_row_value=None    
                                if not type(select_field_row_value)== int:
                                    try:
                                        select_field_row_value=line.index(select_field_row_value) 
                                    except ValueError:
                                        select_field_row_value = None 
                               
                            # Parameter Validation Code
                            # select_field - Handle wrong select field int value                       
                            if present_select_field_row and type(select_field_row_value)== int and len(header_line) < select_field_row_value:
                                log("ERROR","Select field column does not present in csv")
                                break
                            # select_field - Handle wrong select field str value       
                            if present_select_field_row and select_field_row_value== None:
                                log("ERROR","Select Field name not present in csv")
                                break

                            # where_field - Handle wrong select field int value 
                            if present_where_field_row and type(where_field_row_value)== int and len(line) < where_field_row_value:
                                log("ERROR","Where field column does not present in csv")
                                break
                            # where_field - Handle wrong select field str value       
                            if present_where_field_row and where_field_row_value== None:
                                log("ERROR","Where Field name not present in csv")
                                break
                            
                            continue
                        
                        # where_field and where_equals present the filter hostname
                        if present_where_field_row and present_where_equals_row:
                            try:
                                if not any(re.match(pattern.strip(), line[where_field_row_value]) for pattern in where_equals_row_value):
                                    continue
                            except Exception as e:
                                log("ERROR","Error in where field filter: "+str(e))
                                continue
                        
                        # Make a row to insert in new file (./var/run/serverclass.csv)
                        try:
                            updated_rows.append({
                                "Serverclass": serverclass,
                                "App": app,
                                "Key": method,
                                "Value": line[select_field_row_value]
                            })
                        except Exception as e:
                            log("ERROR","Error in creating updated row: "+str(e))
                            continue
                main_data.remove(row)
            except FileNotFoundError:
                log("WARN",f"Destination CSV file not found: {dest_csv_path}")
            except Exception as e:
                log("ERROR", f"Error in csv extraction: {e}")
                log("ERROR",traceback.format_exc())
        else:
            updated_rows.append(row)
                
    # write data in - ./var/run/serverclass.csv        
    with open(secoundary_csv_path, mode='w', newline='') as secoundary_csv_file:
        fieldnames = ["Serverclass", "App", "Key", "Value"]
        writer = csv.DictWriter(secoundary_csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    log("INFO","CSV extraction is completed")