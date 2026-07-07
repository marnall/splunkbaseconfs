import splunk.Intersplunk
import configparser
import os

results = list()

# The path to cluster indexes config
CONFIG_PATH = '../../../master-apps/_cluster/local/indexes.conf'

config = configparser.ConfigParser()
if os.path.exists(CONFIG_PATH):
    config.read(CONFIG_PATH)


def size_to_hr(num, suffix='B'):
    """
    Function to convert MB to human readable form with 2 decimal places,
    stripping trailing .00
    """
    if num == 0:
        return 'Unlimited'
    
    # num is in MB, convert it to B
    num = num * 1024 * 1024
    
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024:
            # round to 2 digits, then %g removes ".0" if it's a whole number
            return "%g %s%s" % (round(num, 2), unit, suffix)
        num /= 1024
        
    return "%g %s%s" % (round(num, 2), 'Y', suffix)


def seconds_to_hr(num, null_value='Unlimited'):
    if num == 0:
        return null_value
    
    # num is in seconds, convert it to days
    num /= 86400
    
    for unit in ['day', 'year']:
        if abs(num) < 365:
            # Round to 2 decimal places
            # .2g or :g removes trailing zeros automatically
            formatted_num = round(num, 2)
            suffix = 's' if formatted_num > 1 else ''
            
            # Use %g or f"{num:g}" to drop ".0"
            return "%g %s%s" % (formatted_num, unit, suffix)
        
        num /= 365
        
    return "%g years" % round(num, 2)


if len(config.sections()) > 0:
    for section in config.sections():
        # Set defaults
        maxtotaldatasizemb = 512000 # 500 GB
        frozentimeperiodinsecs = 189216000 # 4 years
        timeperiodinsecbeforetsidxreduction = 0 # disabled
        for (key, value) in config.items(section):
            if key.lower() == 'maxtotaldatasizemb':
                maxtotaldatasizemb = int(value)
            if key.lower() == 'frozentimeperiodinsecs':
                frozentimeperiodinsecs = int(value)
            if key.lower() == 'timeperiodinsecbeforetsidxreduction':
                timeperiodinsecbeforetsidxreduction = int(value)

        results.append({'Name': section, 'Size': size_to_hr(maxtotaldatasizemb), 'Lifetime': seconds_to_hr(frozentimeperiodinsecs), 'Tsidx reduction time': seconds_to_hr(timeperiodinsecbeforetsidxreduction, null_value='No reduction')})

else:
    results = [{'Name': 'No indexes created yet'}]

splunk.Intersplunk.outputResults(results)
