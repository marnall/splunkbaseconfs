import re
import os
import csv
from splunk.clilib import cli_common as cli


def is_csv_file_name(file_name):
    # csv file name pattern
    pattern = r'^[\w]+\.csv$'

    # Check if the file name matches the pattern
    if re.match(pattern, file_name):
        return True
    else:
        return False


def get_file_name(s3_path):
    """
    get csv filename /dataset/train/input_data.csv
    """
    if s3_path.endswith(".csv"):
        return os.path.basename(s3_path)


def check_if_exists_tmp(file_path):
    try:
        if not os.path.exists(file_path):
            os.makedirs(file_path)
    except OSError as e:
        message = "Encountered an error while trying to create _tmp: %s" % (str(e))


def csv_to_json(csvFilePath):
    """
    csv to json return
    """
    jsonArray = []
    
    with open(csvFilePath, encoding='utf-8') as f: 
        csvReader = csv.DictReader(f) 
        for row in csvReader: 
            # self.logger.fatal(f"This is a row , {row}")
            jsonArray.append(row)
            
    return jsonArray


def getMellerikatConf(confStanza, confFile="mellerikatinfo"):
    cfg = cli.getConfStanza(confFile, confStanza)
    return cfg


if __name__ == "__main__":
    cfg = getMellerikatConf("mellerikat:model_name1")
    print(cfg)
    print(cfg['train_bucket_name'])