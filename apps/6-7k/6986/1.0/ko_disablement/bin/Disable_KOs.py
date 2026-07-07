#### This script is copyright of Visicore Technologies, LLC.

import csv
import re
import os
import shutil
import zipfile

### Add any additional definitions for .conf files that require a disabled = 1 line within the object stanza to disable here
disable_dictionary = {
    "collections-conf": "collections.conf",
    "commands": "commands.conf",
    "conf-times": "times.conf",
    "eventtypes": "eventtypes.conf",
    "fvtags": "tags.conf",
    "global-banner": "global-banner.conf",
    "macros": "macros.conf",
    "modalerts": "alert_actions.conf",
    "savedsearch": "savedsearches.conf",
    "transforms-extract": "transforms.conf",
    "transforms-lookup": "transforms.conf",
    "visualizations": "visualizations.conf",
    "workflow-actions": "workflow_actions.conf",
    "event_renderers": "event_renderers.conf"
}
###

json_disable = {
    "datamodel": "datamodels.conf"
    }

removal_dictionary = {
    "props-extract": "props.conf",
    "props-lookup": "props.conf"
}

xml_deletion_dictionary = {
    "nav": "/data/ui/nav/",
    "panels": "/data/ui/panels/",
    "views": "/data/ui/views/",
}


#This Python script should live in "$SPLUNK_HOME/etc/apps/APP_NAME/bin/Disable_KOs.py
#These variables are set for the purposes of running the disable functionality through an alert action rather than taking command line arguments
splunkHome = os.environ.get("SPLUNK_HOME")
input_csv = splunkHome + "/etc/apps/ko_disablement/lookups/user_ko_disablement.csv" #Change this if path to reference csv file changes in ko_disablement applicaton 
output_path = splunkHome + "/etc/apps/ko_disablement/lookups/disableLog.csv" #Debug file output path

KO_list = []

try:
    with open(input_csv, 'r') as csvfile:
        for row in csv.DictReader(csvfile):
            KO_list.append(row)
except Exception as e:
    print(f"Unable to read csv file {input_csv} - Error {e}")

# Backup files first

def create_zip(source_directory, zip_file_path):
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_directory):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, source_directory)
                zipf.write(file_path, rel_path)

def find_app_directory(sharing_level, owner, app_name):
    splunk_home = os.environ.get("SPLUNK_HOME")
    app_directory_user = os.path.join(splunk_home, "etc", "users", owner, app_name)
    app_directory_app = os.path.join(splunk_home, "etc", "apps", app_name)

    if sharing_level == "user" and os.path.exists(app_directory_user):
        return app_directory_user
    elif sharing_level in ["app", "global"] and os.path.exists(app_directory_app):
        return app_directory_app
    else:
        return None

def backup_app(app_directory, backup_directory, owner, debug_file):
    app_name = os.path.basename(app_directory.rstrip("/"))
    owner_backup_dir = os.path.join(backup_directory, owner)
    os.makedirs(owner_backup_dir, exist_ok=True)

    zip_file_path = os.path.join(owner_backup_dir, f"{app_name}_backup.zip")

    try:
        create_zip(app_directory, zip_file_path)
        print(f"Zip file backup of {app_name} owned by {owner} created successfully at {zip_file_path}")
        debug_file.write(f"Zip file backup of {app_name} owned by {owner} created successfully at {zip_file_path}\n")
    except Exception as e:
        print(f"Backup of {app_name} owned by {owner} failed: {e}")
        debug_file.write(f"Backup of {app_name} owned by {owner} failed: {e}\n")

# Example usage
if __name__ == "__main__":
    csv_file = os.path.join(os.environ.get("SPLUNK_HOME"), "etc", "apps", "ko_disablement", "lookups", "user_ko_disablement.csv")
    backup_directory = os.path.join(os.environ.get("SPLUNK_HOME"), "etc", "apps", "ko_disablement", "tmp")

    debug_log = os.path.join(backup_directory, "debug_log.txt")
    with open(debug_log, 'w') as debug_file:
        with open(csv_file, newline='') as csvfile:
            app_reader = csv.DictReader(csvfile)
            for row in app_reader:
                sharing_level = row['sharing_level'].strip()
                owner = row['owner'].strip()
                app_name = row['app'].strip()

                app_directory = find_app_directory(sharing_level, owner, app_name)
                if app_directory:
                    backup_app(app_directory, backup_directory, owner, debug_file)
                else:
                    print(f"App directory for {app_name} with sharing level '{sharing_level}' and owner '{owner}' not found.")
                    debug_file.write(f"App directory for {app_name} with sharing level '{sharing_level}' and owner '{owner}' not found.\n")


# Build local path for private-level objects

def build_local_path(search_path, user_name, app, config_type):
    final_path = search_path + user_name + "/" + app + "/local/" + config_type
    return final_path

def build_global_path(search_path, app, localOrDefault, config_type):
    final_path = search_path + app + "/" + localOrDefault + "/" + config_type
    return final_path

def create_stanza_dict(config_list):
    pattern = re.compile("#*\[(.*?)\]")
    config_dict = {}
    for data in config_list:
        if pattern.match(data) is not None: #If line from conf file matches regex to only get [headers], that header becomes a key and the value is another dictonary that will contain the field:value pairs in .conf stanzas
            config_dict[data] = [] # Create list on stanza header key that will store the lines of the stanza to eventually add disabled = 1 line to
            current_header_switch = False
            for inner_loop_data in config_list:
                if current_header_switch:
                    if pattern.match(inner_loop_data) is not None:
                        break
                    else:
                        config_dict[data].append(inner_loop_data)
                if inner_loop_data == data:
                    current_header_switch = True
    return(config_dict) 


def open_file_to_list(file_path, readorwrite):
    file_contents = []
    with open(file_path, readorwrite, encoding="utf8") as f:
        for line in f:
            file_contents.append(line.rstrip())
    return file_contents

def comment_line(stanzaDictionary, csvObject, disableBoolean=bool):
    target_stanza = csvObject.split(" : ")[0]
    target_line = csvObject.split(" : ")[1]
    objectNotExists = True
    if disableBoolean:
        for header in stanzaDictionary:
            if header == f"[{target_stanza}]":
                for idx, object in enumerate(stanzaDictionary[header]):
                    if target_line == object.replace(" ", "").split("=", 1)[0] and object[0] != "#":
                        print(f"Disabling object {knowledge_object} from {objectPath}...")
                        stanzaDictionary[header][idx] = "#" + stanzaDictionary[header][idx]
                objectNotExists = False
        if objectNotExists:
            print(f"Object {knowledge_object} already disabled or not found in file {objectPath}")
            csv_output_list.append(["Failed", f"{csvObject} either already disabled or not found in file {objectPath}."])
    else:
        for header in stanzaDictionary:
            if header == f"[{target_stanza}]":
                for idx, object in enumerate(stanzaDictionary[header]):
                    if target_line == object.replace(" ", "").split("=", 1)[0].strip("#") and object[0] == "#":
                        print(f"Re-enabling object {knowledge_object} from {objectPath}...")
                        stanzaDictionary[header][idx] = stanzaDictionary[header][idx].strip("#")
                objectNotExists = False
        if objectNotExists:
            print(f"Object {knowledge_object} already disabled or not found in file {objectPath}")
            csv_output_list.append(["Failed", f"{csvObject} either already disabled or not found in file {objectPath}."])
    return stanzaDictionary

def comment_stanza(stanzaDictionary, targetHeader, disableBoolean=bool):
    noObject = True
    newStanzaDictionary = {}
    if disableBoolean:
        for header in stanzaDictionary:
            if header == f"[{targetHeader}]":
                newStanzaDictionary["#" + header] = stanzaDictionary[header]
                for idx, line in enumerate(stanzaDictionary[header]):
                    if line != '':
                        newStanzaDictionary["#" + header][idx] = '#' + newStanzaDictionary["#" + header][idx]
                noObject = False
            else:
                newStanzaDictionary[header] = stanzaDictionary[header]
        if noObject:
            print(f"Object {knowledge_object} already disabled or not found in file {objectPath}")
            csv_output_list.append(["Failed", f"{targetHeader} either already disabled or not found in file {objectPath}."])
    else:
        for header in stanzaDictionary:
            if header.strip("#") == f"[{targetHeader}]":
                newStanzaDictionary[header.strip("#")] = stanzaDictionary[header]
                for idx, line in enumerate(stanzaDictionary[header]):
                    if line != '':
                        newStanzaDictionary[header.strip("#")][idx] = stanzaDictionary[header][idx].strip("#")
                noObject = False
            else:
                newStanzaDictionary[header] = stanzaDictionary[header]
        if noObject:
            print(f"Object {knowledge_object} already disabled or not found in file {objectPath}")
            csv_output_list.append(["Failed", f"{targetHeader} either already disabled or not found in file {objectPath}."])
    return newStanzaDictionary

#Function to add disabled = 1 line to .conf file. If disabled = 0 exists already in stanza, rather than creating new line, code will replace the disabled = 0 with disabled = 1
def add_disabled_line(stanzaDictionary, csvObject):
    object_notExists = True
    for header in stanzaDictionary:
        if header == f"[{csvObject}]":
            object_notExists = False
            not_already_disabled = False #Flag to see if disabled = 1 currently exists in stanza. False = there is no disabled = 1 line in the stanza
            for object in stanzaDictionary[header]:
                if object.replace(" ", "") == "disabled=1": 
                    break
                elif object.replace(" ", "") != "disabled=1" and object == stanzaDictionary[header][-1]: #If this is last line of stanza and neither it nor any other lines of stanza equal 'disabled=1', then flip flag to True
                    not_already_disabled = True
            if not_already_disabled:
                disabledLineExists = False
                for idx, object in enumerate(stanzaDictionary[header]):
                    if object.replace(" ", "") == "disabled=0":
                        disabledLineExists = True
                        break
                if disabledLineExists:
                    print(f"Disabling {header} in file {objectPath}...")
                    stanzaDictionary[header][idx] = "disabled = 1"
                else:
                    if stanzaDictionary[header][-1] == '':
                        stanzaDictionary[header].insert(-1, "disabled = 1")
                    else:
                        stanzaDictionary[header].append("disabled = 1")
            else:
                print(f"Object {csvObject} already disabled.")
                csv_output_list.append(["Failed", f"Object {csvObject} is already disabled"])
    if object_notExists:
        print(f"Object {csvObject} Doesn't exist in file {objectPath}.")
        csv_output_list.append(["Failed", f"Object {csvObject} not found in file {objectPath}."])
    return stanzaDictionary


def write_new_conf(final_conf_dictionary, path):
    with open(path, "w", encoding="utf8") as n:
        #print(f"Disabled object in file (If not already disabled): {path}.")
        for header in final_conf_dictionary:
            n.write(f"{header}\n")
            for field in final_conf_dictionary[header]:
                n.write(f"{field}\n")


def enable_xml_object(inputPath, configurationType, appName, knowledgeObject, isGlobal, userID):
    if isGlobal:
        nothingEnabled = True # Create flag for outputting to debug csv if nothing is disabled upon the script attempting to disable a .xml file
        for localOrDefault in ['/local', '/default']:
            disabled_path = inputPath + appName + localOrDefault + xml_deletion_dictionary[configurationType] + knowledgeObject + ".xml" + ".bak"
            enable_path = os.path.splitext(disabled_path)[0]
            if os.path.exists(disabled_path):
                os.rename(disabled_path, enable_path)
                print(f"Re-enabled {disabled_path}...")
                nothingEnabled = False #Path was valid and object was disabled, set flag to false to indicate no debug error output needed
        if nothingEnabled: #If no file is disabled in either local or default, print to debug file
            print(f"No valid path for object {knowledgeObject} of config {configurationType} at in local or default directory in app {appName}. Scope: Global")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} of config {configurationType} in local or default app {appName}. Scope: Global"])
    else:
        disabled_path = inputPath + userID + "/" + appName + "/" + "local" + xml_deletion_dictionary[configurationType] + knowledgeObject + ".xml" + ".bak"
        enable_path = os.path.splitext(disabled_path)[0]
        if os.path.exists(disabled_path):
            os.rename(disabled_path, enable_path)
            print(f"Re-enabled {disabled_path}...")
        else:
            print(f"No valid path for object {knowledgeObject} at path {disabled_path}.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {disabled_path}"])

def delete_xml_object(inputPath, configurationType, appName, knowledgeObject, isGlobal, userID):
    if isGlobal:
        nothingDeleted= True
        for localOrDefault in ['/local', '/default']:
            delete_path = inputPath + appName + localOrDefault + xml_deletion_dictionary[configurationType] + knowledgeObject + ".xml"
            if os.path.exists(delete_path):
                os.remove(delete_path)
                print(f"Deleted {delete_path}...")
                nothingDeleted = False #Path was valid and object was deleted, set flag to false to indicate no debug error output needed
        if nothingDeleted: #If no file is disabled in either local or default, print to command line and append debug file
            print(f"No valid path for object {knowledgeObject} of config {configurationType} at in local or default directory in app {appName}. Scope: Global")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} of config {configurationType} in local or default app {appName}. Scope: Global"])
    else:
        delete_path = inputPath + userID + "/" + appName + "/" + "local" + xml_deletion_dictionary[configurationType] + knowledgeObject + ".xml"
        if os.path.exists(delete_path):
            os.remove(delete_path)
            print(f"Deleted {delete_path}...")
        else:
            print(f"No valid path for object {knowledgeObject} at path {delete_path}.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {delete_path}"])

#Disable xml objects by adding .bak file extension, preventing Splunk from reading the file
def disable_xml_object(inputPath, configurationType, appName, knowledgeObject, isGlobal, userID):
    if isGlobal:
        nothingDisabled = True # Create flag for outputting to debug csv if nothing is disabled upon the script attempting to disable a .xml file
        for localOrDefault in ['/local', '/default']:
            enabled_path = inputPath + appName + localOrDefault + xml_deletion_dictionary[configurationType] + knowledgeObject + ".xml"
            disabled_path = enabled_path + ".bak"
            if os.path.exists(enabled_path):
                os.rename(enabled_path, disabled_path)
                print(f"Disabled {enabled_path}...")
                nothingDisabled = False #Path was valid and object was disabled, set flag to false to indicate no debug error output needed
        if nothingDisabled: #If no file is disabled in either local or default, print to debug file
            print(f"No valid path for object {knowledgeObject} of config {configurationType} at in local or default directory in app {appName}. Scope: Global")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} of config {configurationType} in local or default app {appName}. Scope: Global"])
    else:
        enabled_path = inputPath + userID + "/" + appName + "/" + "local" + xml_deletion_dictionary[configurationType] + knowledgeObject + ".xml"
        disabled_path = enabled_path + ".bak"
        if os.path.exists(enabled_path):
            os.rename(enabled_path, disabled_path)
            print(f"Disabled {enabled_path}...")
        else:
            print(f"No valid path for object {knowledgeObject} at path {enabled_path}.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {enabled_path}"])

def enable_lookupFile(inputPath, appName, knowledgeObject, isGlobal, userID):
    if isGlobal:
        disabled_path = inputPath + appName + "/lookups/" + knowledgeObject + ".bak"
        enable_path = os.path.splitext(disabled_path)[0]
        if os.path.exists(disabled_path):
            os.rename(disabled_path, enable_path)
            print(f"Re-enabled {disabled_path}...")
        else:
            print(f"No valid path for object {knowledgeObject} at path {disabled_path}.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {disabled_path}"])
    else:
        disabled_path = inputPath + userID + "/" + appName + "/lookups/" + knowledgeObject + ".bak"
        enable_path = os.path.splitext(disabled_path)[0]
        if os.path.exists(disabled_path):
            os.rename(disabled_path, enable_path)
            print(f"Re-enabled {disabled_path}...")
        else:
            print(f"No valid path for object {knowledgeObject} at path {disabled_path}.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {disabled_path}"])

def delete_lookupFile(inputPath, appName, knowledgeObject, isGlobal, userID):
    if isGlobal:
        delete_path = inputPath + appName + "/lookups/" + knowledgeObject 
        if os.path.exists(delete_path):
            os.remove(delete_path)
            print(f"Deleted {delete_path}...")
        else:
            print(f"No valid path for object {knowledgeObject} at path {delete_path}.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {delete_path}"])
    else:
        delete_path = inputPath + userID + "/" + appName + "/lookups/" + knowledgeObject
        if os.path.exists(delete_path):
            os.remove(delete_path)
            print(f"Deleted {delete_path}...")
        else:
            print(f"No valid path for object {knowledgeObject} at path {delete_path}.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {delete_path}"])


#Disable csv objects by adding .bak file extension, preventing Splunk from reading the file
def disable_lookupFile(inputPath, appName, knowledgeObject, isGlobal, userID):
    if isGlobal:
        enabled_path = inputPath + appName + "/lookups/" + knowledgeObject
        disabled_path = enabled_path + ".bak"
        if os.path.exists(enabled_path):
            os.rename(enabled_path, disabled_path)
            print(f"Disabled {enabled_path}...")
        else:
            print(f"No valid path for object {knowledgeObject} at path {enabled_path}.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {enabled_path}"])
    else:
        enabled_path = inputPath + userID + "/" + appName + "/lookups/" + knowledgeObject
        disabled_path = enabled_path + ".bak"
        if os.path.exists(enabled_path):
            os.rename(enabled_path, disabled_path)
            print(f"Disabled {enabled_path}...")
        else:
            print(f"No valid path for object {knowledgeObject} at path {enabled_path}.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {enabled_path}"])

#Disable props.conf object by commenting out the object's line within the appropriate stanza by splitting the stanza/object up on the separating colon i.e. [Stanza_Name] : ObjectName 
def toggle_props(inputPath, configurationType, appName, knowledgeObject, isGlobal, userID, disableBoolean=bool):
    if isGlobal:
        target_header = knowledgeObject.split(" : ")[0]
        target_field = knowledgeObject.split(" : ")[1]
        nothingToggled = True # Create flag for outputting to debug csv if nothing is disabled upon the script attempting to disable a props.conf file object
        for localOrDefault in ['local', 'default']: 
            full_path = build_global_path(inputPath, appName, localOrDefault, removal_dictionary[configurationType]) # Build full path to users/user_id/app/local/config.conf to open and edit
            if os.path.exists(full_path):
                opened_file = open_file_to_list(full_path, "r")
                list_of_stanzas = create_stanza_dict(opened_file)
                if f"[{target_header}]" in list_of_stanzas.keys():
                    for field in list_of_stanzas[f"[{target_header}]"]:
                        if target_field == field.replace(" ", "").split("=", 1)[0].strip("#"):
                            updated_fileContent = comment_line(list_of_stanzas, knowledgeObject, disableBoolean) #True boolean disables object, False enables object
                            write_new_conf(updated_fileContent, full_path)
                            nothingToggled = False
        if nothingToggled:
            print(f"{knowledgeObject} of {configurationType} not found in either local or default directory in app {appName}. Scope: Global")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} of config {configurationType} at path local or default path in app {appName}. Scope: Global"])
    else:
        full_path = build_local_path(inputPath, userID, appName, removal_dictionary[configurationType]) # Build full path to users/user_id/app/local/config.conf to open and edit
        if os.path.exists(full_path):
            opened_file = open_file_to_list(full_path, "r")
            list_of_stanzas = create_stanza_dict(opened_file)
            updated_fileContent = comment_line(list_of_stanzas, knowledgeObject, disableBoolean) #True boolean disables object, False enables object
            write_new_conf(updated_fileContent, full_path)
        else:
            print(f"{full_path} not found in directory.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {full_path}"])

def delete_props(inputPath, configurationType, appName, knowledgeObject, isGlobal, userID):
    if isGlobal:
        target_header = knowledgeObject.split(" : ")[0]
        target_field = knowledgeObject.split(" : ")[1]
        nothingDeleted = True # Create flag for outputting to debug csv if nothing is disabled upon the script attempting to disable a props.conf file object
        for localOrDefault in ['local', 'default']: 
            full_path = build_global_path(inputPath, appName, localOrDefault, removal_dictionary[configurationType]) # Build full path to users/user_id/app/local/config.conf to open and edit
            if os.path.exists(full_path):
                opened_file = open_file_to_list(full_path, "r")
                list_of_stanzas = create_stanza_dict(opened_file)
                target_headerBracketed = "[" + target_header + "]"
                if target_headerBracketed in list_of_stanzas.keys():
                    for field in list_of_stanzas[target_headerBracketed]:
                        if target_field == field.replace(" ", "").split("=", 1)[0].strip("#"):
                            list_of_stanzas[target_headerBracketed].remove(field) #Remove targeted line from targeted stanza
                            write_new_conf(list_of_stanzas, full_path)
                            nothingDeleted = False
        if nothingDeleted:
            print(f"{knowledgeObject} of {configurationType} not found in either local or default directory in app {appName}. Scope: Global")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} of config {configurationType} at path local or default path in app {appName}. Scope: Global"])
    else:
        full_path = build_local_path(inputPath, userID, appName, removal_dictionary[configurationType]) # Build full path to users/user_id/app/local/config.conf to open and edit
        if os.path.exists(full_path):
            opened_file = open_file_to_list(full_path, "r")
            list_of_stanzas = create_stanza_dict(opened_file)
            target_headerBracketed = "[" + target_header + "]"
            for field in list_of_stanzas[target_headerBracketed]:
                if target_field == field.replace(" ", "").split("=", 1)[0].strip("#"):
                    list_of_stanzas[target_headerBracketed].remove(field) #Remove targeted line from targeted stanza
                    write_new_conf(list_of_stanzas, full_path)
        else:
            print(f"{full_path} not found in directory.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {full_path}"])


#Disable datamodels object by first commenting out entire stanza inside datamodels.conf, including stanza header and all fields. Then going to /data/models/ and adding .bak extension to appropriate .json object
def toggle_datamodels(inputPath, configurationType, appName, knowledgeObject, isGlobal, userID, disableObject=bool):
    if isGlobal:
        for localOrDefault in ['local', 'default']:
            full_path = build_global_path(inputPath, appName, localOrDefault, json_disable[configurationType]) #Define path for datamodels.conf file
            if disableObject:
                json_path = build_global_path(inputPath, appName, localOrDefault, "data/") + "models/" + knowledgeObject + ".json" #Define path for respective datamodels .json file
                renamed_json_path = json_path + ".bak"
            else:
                json_path = build_global_path(inputPath, appName, localOrDefault, "data/") + "models/" + knowledgeObject + ".json" + ".bak"
                renamed_json_path = os.path.splitext(json_path)[0]
            configNotToggled = True
            jsonNotToggled = True
            if os.path.exists(full_path):
                opened_file = open_file_to_list(full_path, "r") 
                list_of_stanzas = create_stanza_dict(opened_file)
                target_header = "[" + knowledgeObject + "]"
                if target_header in list_of_stanzas.keys(): #If object exists in the respective .conf file, comment out entire stanza for disablement and overwrite file
                    updated_fileContent = comment_stanza(list_of_stanzas, knowledgeObject, disableObject)
                    write_new_conf(updated_fileContent, full_path)
                    configNotToggled = False
            if os.path.exists(json_path): #Toggle .bak extension of .json file depending on disableObject boolean provided
                os.rename(json_path, renamed_json_path)
                jsonNotToggled = False
        if configNotToggled:
            print(f"{knowledgeObject} of type {configurationType} not found in local or default within app {appName}. Scope: {scope}")
            csv_output_list.append(["Failed", f"{knowledgeObject} of type {configurationType} not found in local or default within app {appName}. Scope: {scope}"])
        if jsonNotToggled:
            print(f"{knowledgeObject}.json for datamodels not found in local or default within app {appName}. Scope: {scope} {json_path}")
            csv_output_list.append(["Failed", f"{knowledgeObject}.json for datamodels not found in local or default within app {appName}. Scope: {scope}"])
    else:
        full_path = build_local_path(inputPath, userID, appName, json_disable[configurationType])
        if disableObject:
            json_path = build_local_path(inputPath, userID, appName, "data/") + "models/" + knowledgeObject + ".json"
            renamed_json_path = json_path + ".bak"
        else:
            json_path = build_local_path(inputPath, userID, appName, "data/") + "models/" + knowledgeObject + ".json" + ".bak"
            renamed_json_path = os.path.splitext(json_path)[0]
        if os.path.exists(full_path):
            opened_file = open_file_to_list(full_path, "r")
            list_of_stanzas = create_stanza_dict(opened_file)
            updated_fileContent = comment_stanza(list_of_stanzas, knowledgeObject, disableObject)
            write_new_conf(updated_fileContent, full_path)
            if os.path.exists(json_path):
                os.rename(json_path, renamed_json_path)
            else:
                csv_output_list.append(["Failed", f"No valid json file for {configurationType} {knowledgeObject} at path {json_path} to disable"])
        else:
            print(f"{full_path} not found in directory.")
            csv_output_list.append(["Failed", f"No valid path for {configurationType} {knowledgeObject} at path {full_path}"])

def delete_datamodels(inputPath, configurationType, appName, knowledgeObject, isGlobal, userID):
    if isGlobal:
        for localOrDefault in ['local', 'default']:
            full_path = build_global_path(inputPath, appName, localOrDefault, json_disable[configurationType]) #Define path for datamodels.conf file
            json_path = build_global_path(inputPath, appName, localOrDefault, "data/") + "models/" + knowledgeObject + ".json" #Define path for respective datamodels .json file
            disabled_json_path = json_path + ".bak"
            configNotDeleted = True
            jsonNotDeleted = True
            if os.path.exists(full_path):
                opened_file = open_file_to_list(full_path, "r") 
                list_of_stanzas = create_stanza_dict(opened_file)
                target_stanza = "[" + knowledgeObject + "]"
                for header in list_of_stanzas: #Delete stanza header from dictionary if found
                    if target_stanza == header.strip("#"):
                        list_of_stanzas.pop(header) #Delete entire target stanza from dictionary and write new updated file
                        write_new_conf(list_of_stanzas, full_path)
                        configNotDeleted = False
                        break
            for filePath in [json_path, disabled_json_path]: #Delete json file, in enabled or disabled form if either exist
                if os.path.exists(filePath):
                    os.remove(filePath)
                    jsonNotDeleted = False
        if configNotDeleted:
            print(f"{knowledgeObject} of type {configurationType} not found in local or default within app {appName}. Scope: {scope}")
            csv_output_list.append(["Failed", f"{knowledgeObject} of type {configurationType} not found in local or default within app {appName}. Scope: {scope}"])
        if jsonNotDeleted:
            print(f"{knowledgeObject}.json for datamodels not found in local or default within app {appName}. Scope: {scope} {json_path}")
            csv_output_list.append(["Failed", f"{knowledgeObject}.json for datamodels not found in local or default within app {appName}. Scope: {scope}"])
    else: #Private-level objects
        full_path = build_local_path(inputPath, userID, appName, json_disable[configurationType])
        json_path = build_local_path(inputPath, userID, appName, "data/") + "models/" + knowledgeObject + ".json"
        disabled_json_path = json_path + ".bak"
        if os.path.exists(full_path):
                opened_file = open_file_to_list(full_path, "r") 
                list_of_stanzas = create_stanza_dict(opened_file)
                target_stanza = "[" + knowledgeObject + "]"
                for header in list_of_stanzas: #Delete stanza header from dictionary if found
                    if target_stanza == header.strip("#"):
                        list_of_stanzas.pop(header) #Delete entire target stanza from dictionary and write new updated file
                        write_new_conf(list_of_stanzas, full_path)
                        break
        else:
            print(f"{full_path} not found in directory.")
            csv_output_list.append(["Failed", f"No valid path for {configurationType} {knowledgeObject} at path {full_path}"])
        jsonNotDeleted = True
        for filePath in [json_path, disabled_json_path]: #Delete json file, in enabled or disabled form if either exist
            if os.path.exists(filePath):
                os.remove(filePath)
                jsonNotDeleted = False
        if jsonNotDeleted:
            csv_output_list.append(["Failed", f"No valid json file for {configurationType} {knowledgeObject} at path {json_path} to disable"])

def enable_MostConfigurations(inputPath, configurationType, appName, knowledgeObject, isGlobal, userID):
    if isGlobal:
        full_path = build_global_path(inputPath, appName, "local", disable_dictionary[configurationType]) # Build full path to apps/app_name/local/config.conf to open and edit
        local_directory = full_path.rsplit("/", 1)[0]
        if os.path.exists(full_path):
            opened_file = open_file_to_list(full_path, "r")
            list_of_stanzas = create_stanza_dict(opened_file)
            knowledgeObjectHeader = "[" + knowledgeObject + "]"
            if knowledgeObjectHeader in list_of_stanzas.keys():
                for idx, field in enumerate(list_of_stanzas[knowledgeObjectHeader]):
                    if field.replace(" ", "").lower() == "disabled=1":
                        list_of_stanzas[knowledgeObjectHeader][idx] = "disabled = 0"
                write_new_conf(list_of_stanzas, full_path)
            else: #.conf file exists in local, but object is not in the local version of .conf, so have to add stanza and disabled = 1 line
                list_of_stanzas[f"[{knowledgeObject}]"] = ['disabled = 0']
                write_new_conf(list_of_stanzas, full_path)
        else: #.conf file doesn't exist in local. Will create a .conf containing only the currently referenced KO as header and add disabled = 0 line
            if(os.path.exists(local_directory) == False):
                os.mkdir(local_directory)
            config_dictionary = {}
            config_dictionary[f"[{knowledgeObject}]"] = ['disabled = 0']
            write_new_conf(config_dictionary, full_path)
    else:
        full_path = build_local_path(inputPath, userID, appName, disable_dictionary[configurationType]) # Build full path to users/user_id/app/local/config.conf to open and edit
        if os.path.exists(full_path):
            opened_file = open_file_to_list(full_path, "r")
            list_of_stanzas = create_stanza_dict(opened_file)
            knowledgeObjectHeader = "[" + knowledgeObject + "]"
            if knowledgeObjectHeader in list_of_stanzas.keys():
                for idx, field in enumerate(list_of_stanzas[knowledgeObjectHeader]):
                    if field.replace(" ", "").lower() == "disabled=1":
                        list_of_stanzas[knowledgeObjectHeader][idx] = "disabled = 0"
            write_new_conf(list_of_stanzas, full_path)
        else:
            print(f"{full_path} not found in directory.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {full_path}"])

def delete_MostConfigurations(inputPath, configurationType, appName, knowledgeObject, isGlobal, userID):
    if isGlobal:
        nothingDeleted = True
        for localOrDefault in ['local', 'default']:
            full_path = build_global_path(inputPath, appName, localOrDefault, disable_dictionary[configurationType]) # Build full path to apps/app_name/local/config.conf to open and edit
            if os.path.exists(full_path):
                opened_file = open_file_to_list(full_path, "r")
                list_of_stanzas = create_stanza_dict(opened_file)
                stanza_header = "[" + knowledgeObject + "]"
                if stanza_header in list_of_stanzas.keys():
                    list_of_stanzas.pop(stanza_header) #Remove entire target object stanza from dictionary
                    write_new_conf(list_of_stanzas, full_path)
                    nothingDeleted = False
        if nothingDeleted:
            print(f"{knowledgeObject} of {configurationType} not found in either local or default directory in app {appName}. Scope: Global")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} of config {configurationType} at path local or default path in app {appName}. Scope: Global"])
    else:
        full_path = build_local_path(inputPath, userID, appName, disable_dictionary[configurationType]) # Build full path to users/user_id/app/local/config.conf to open and edit
        if os.path.exists(full_path):
            opened_file = open_file_to_list(full_path, "r")
            list_of_stanzas = create_stanza_dict(opened_file)
            stanza_header = "[" + knowledgeObject + "]"
            if stanza_header in list_of_stanzas.keys():
                    list_of_stanzas.pop(stanza_header) #Remove entire target object stanza from dictionary
                    write_new_conf(list_of_stanzas, full_path)
        else:
            print(f"{full_path} not found in directory.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {full_path}"])

#Most configurations disabled by navigating to .conf file and adding disabled = 1 field to objects stanza
def disable_MostConfigurations(inputPath, configurationType, appName, knowledgeObject, isGlobal, userID):
    if isGlobal:
        full_path = build_global_path(inputPath, appName, "local", disable_dictionary[configurationType]) # Build full path to apps/app_name/local/config.conf to open and edit
        local_directory = full_path.rsplit("/", 1)[0]
        if os.path.exists(full_path):
            opened_file = open_file_to_list(full_path, "r")
            list_of_stanzas = create_stanza_dict(opened_file)
            if f"[{knowledgeObject}]" in list_of_stanzas.keys():
                updated_fileContent = add_disabled_line(list_of_stanzas, knowledgeObject)
                write_new_conf(updated_fileContent, full_path)
            else: #.conf file exists in local, but object is not in the local version of .conf, so have to add stanza and disabled = 1 line
                list_of_stanzas[f"[{knowledgeObject}]"] = ['disabled = 1']
                write_new_conf(list_of_stanzas, full_path)
        else: #.conf file doesn't exist in local. Will create a .conf containing only the currently referenced KO as header and add disabled = 1 line
            if(os.path.exists(local_directory) == False):
                os.mkdir(local_directory)
            config_dictionary = {}
            config_dictionary[f"[{knowledgeObject}]"] = ['disabled = 1']
            write_new_conf(config_dictionary, full_path)
    else:
        full_path = build_local_path(inputPath, userID, appName, disable_dictionary[configurationType]) # Build full path to users/user_id/app/local/config.conf to open and edit
        if os.path.exists(full_path):
            opened_file = open_file_to_list(full_path, "r")
            list_of_stanzas = create_stanza_dict(opened_file)
            updated_fileContent = add_disabled_line(list_of_stanzas, knowledgeObject)
            write_new_conf(updated_fileContent, full_path)
        else:
            print(f"{full_path} not found in directory.")
            csv_output_list.append(["Failed", f"No valid path for object {knowledgeObject} at path {full_path}"])


csv_output_list = [] # Create empty list to add actions performed by script for output/debugging

for line in KO_list:
    user = line['owner']
    scope = line['sharing_level']
    app = line['app']
    config_type = line['config']
    knowledge_object = line['title']
    operation = line['Pending_Status']
    objectGlobalScope = False
    objectPath = splunkHome + "/etc/users/"
    if scope.lower().strip() == "global" or scope.lower().strip() == "app":
        objectGlobalScope = True
        objectPath = splunkHome + "/etc/apps/"
    if operation.lower().strip() == "enable":
        if config_type in xml_deletion_dictionary.keys():
            enable_xml_object(objectPath, config_type, app, knowledge_object, objectGlobalScope, user)
        elif config_type == "lookup-table-files":
            enable_lookupFile(objectPath, app, knowledge_object, objectGlobalScope, user)
        elif config_type in removal_dictionary.keys():
            toggle_props(objectPath, config_type, app, knowledge_object, objectGlobalScope, user, False) #Passing False re-enables props object
        elif config_type in json_disable.keys():
            toggle_datamodels(objectPath, config_type, app, knowledge_object, objectGlobalScope, user, False) #Passing False re-enables datamodel object
        elif config_type in disable_dictionary.keys(): #If config is neither .xml nor lookup, add disabled = 1 to the object stanza within the respective .conf file
            enable_MostConfigurations(objectPath, config_type, app, knowledge_object, objectGlobalScope, user)
    elif operation.lower().strip() == "delete":
        if config_type in xml_deletion_dictionary.keys():
            delete_xml_object(objectPath, config_type, app, knowledge_object, objectGlobalScope, user)
        elif config_type == "lookup-table-files":
            delete_lookupFile(objectPath, app, knowledge_object, objectGlobalScope, user)
        elif config_type in removal_dictionary.keys():
            delete_props(objectPath, config_type, app, knowledge_object, objectGlobalScope, user, False) #Passing False re-enables props object
        elif config_type in json_disable.keys():
            delete_datamodels(objectPath, config_type, app, knowledge_object, objectGlobalScope, user, False) #Passing False re-enables datamodel object
        elif config_type in disable_dictionary.keys(): #If config is neither .xml nor lookup, add disabled = 1 to the object stanza within the respective .conf file
            delete_MostConfigurations(objectPath, config_type, app, knowledge_object, objectGlobalScope, user)
    elif operation.lower().strip() == "disable":
        if config_type in xml_deletion_dictionary.keys():
            disable_xml_object(objectPath, config_type, app, knowledge_object, objectGlobalScope, user)
        elif config_type == "lookup-table-files":
            disable_lookupFile(objectPath, app, knowledge_object, objectGlobalScope, user)
        elif config_type in removal_dictionary.keys():
            toggle_props(objectPath, config_type, app, knowledge_object, objectGlobalScope, user, True) #Passing True disables props object
        elif config_type in json_disable.keys():
            toggle_datamodels(objectPath, config_type, app, knowledge_object, objectGlobalScope, user, True) #Passing False re-enables datamodel object
        elif config_type in disable_dictionary.keys(): #If config is neither .xml nor lookup, add disabled = 1 to the object stanza within the respective .conf file
            disable_MostConfigurations(objectPath, config_type, app, knowledge_object, objectGlobalScope, user)

if output_path is not None:
    with open(output_path, "w", newline= '') as f:
        writer = csv.writer(f)
        writer.writerows(csv_output_list)
    print(f"Output csv written to {output_path}")
else:
    print("No output .csv written")

