import splunk.Intersplunk
import configparser
import os

args, kwargs = splunk.Intersplunk.getKeywordsAndOptions()

# The path to cluster indexes config
CONFIG_PATH = '../../../master-apps/_cluster/local/indexes.conf'

if len(args) == 4:
    index_name = args[0]
    max_size = args[1]
    retention = args[2]
    tsidx_retention = args[3]

    config = configparser.RawConfigParser()
    config.optionxform = str
    
    # 1. Read existing config to check for duplicates
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)
    
    # 2. Check if index name already exists (case-insensitive check)
    existing_indexes = [section.lower() for section in config.sections()]
    if index_name.lower() in existing_indexes:
        splunk.Intersplunk.outputResults([{"result": "error", "message": "Index already exists. Choose a different name."}])
    else:
        # 3. Create a NEW config object for the append operation 
        # (to avoid rewriting the whole file, which can mess up formatting/comments)
        new_entry = configparser.RawConfigParser()
        new_entry.optionxform = str
        new_entry.add_section(index_name)

        new_entry.set(index_name, 'homePath', '$SPLUNK_DB/{}/db'.format(index_name.lower()))
        new_entry.set(index_name, 'coldPath', '$SPLUNK_DB/{}/colddb'.format(index_name.lower()))
        new_entry.set(index_name, 'thawedPath', '$SPLUNK_DB/{}/thaweddb'.format(index_name.lower()))
        new_entry.set(index_name, 'maxTotalDataSizeMB', max_size)
        new_entry.set(index_name, 'frozenTimePeriodInSecs', retention)
        
        if int(tsidx_retention) > 0:
            new_entry.set(index_name, 'enableTsidxReduction', 'true')
            new_entry.set(index_name, 'timePeriodInSecBeforeTsidxReduction', tsidx_retention)
        
        new_entry.set(index_name, 'repFactor', 'auto')

        # 4. Append to file
        with open(CONFIG_PATH, 'a') as configfile:
            configfile.write('\n') # Ensure there is a newline before the new section
            new_entry.write(configfile)
        
        splunk.Intersplunk.outputResults([{"result": "ok", "message": "Index created."}])

else:
    splunk.Intersplunk.outputResults([{"result": "error", "message": "Incorrect parameter count."}])
