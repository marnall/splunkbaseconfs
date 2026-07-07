import config
import pandas as pd


def csv_to_json(in_file_path, out_file_path):
    df = pd.read_csv(in_file_path)
    df.columns = df.columns.str.replace(config.TIMESTAMP_FIELD, 'timestamp', case=False)
    df.to_json(out_file_path, orient='records')


def xlsx_to_json(in_file_path, out_file_path):
    df = pd.read_excel(in_file_path)
    df.columns = df.columns.str.replace(config.TIMESTAMP_FIELD, 'timestamp', case=False)
    df.to_json(out_file_path, orient='records')


def xml_to_json(in_file_path, out_file_path):
    df = pd.read_xml(in_file_path)
    df.columns = df.columns.str.replace(config.TIMESTAMP_FIELD, 'timestamp', case=False)
    df.to_json(out_file_path, orient='records')


def json_to_json(in_file_path, out_file_path):
    df = pd.read_json(in_file_path)
    df.columns = df.columns.str.replace(config.TIMESTAMP_FIELD, 'timestamp', case=False)
    df.to_json(out_file_path, orient='records')

