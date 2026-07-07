"""
Description:
    Assortment of spreadsheet(CSV) related utility functions to support the input scripts.

Authors:
    Peter Uys, Cylance Inc.
"""


import csv
import logging
import requests

from config import get_logger

g_cylogger = get_logger('cylance')


device_attributes = [
    'Device Name',
    'Serial Number',
    'OS Version',
    'Agent Version',
    'Policy',
    'Zones',
    'Mac Addresses',
    'IP Addresses',
    'Last Reported User',
    'Background Detection',
    'Created',
    'Files Analyzed',
    'Is Online',
    'Online Date',
    'Offline Date']

event_attributes = [
    'SHA256',
    'MD5',
    'Device Name',
    'Date',
    'File Path',
    'Event Status',
    'Cylance Score',
    'Classification',
    'Running',
    'Ever Run',
    'Detected By',
    'Serial Number' ]

indicator_attributes = [
    'SHA256',
    '16bitSubsystem',
    'AbnormalNetworkActivity',
    'Anachronism',
    'AntiVM',
    'AppendedData',
    'AutorunsPersistence',
    'Base64Alphabet',
    'BrowserInfoTheft',
    'CabinentUsage',
    'CodepageLookupImports',
    'CommandlineArgsImport',
    'ContainsBrowserString',
    'ContainsEmbeddedDocument',
    'CredentialProvider',
    'CryptoKeys',
    'CurrentUserInfoImports',
    'DebugCheckImports',
    'DebugStringImports',
    'DiskInfoImports',
    'DownloadFileImports',
    'EmbeddedPE',
    'EncodedPE',
    'EnumerateFileImports',
    'EnumerateModuleImports',
    'EnumerateNetwork',
    'EnumerateProcessImports',
    'EnumerateVolumeImports',
    'ExecuteDLL',
    'FakeMicrosoft',
    'FileDirDeleteImports',
    'FirewallModifyImports',
    'GinaImports',
    'HostnameSearchImports',
    'HTTPCustomHeaders',
    'HTTPCustomUserAgent',
    'InjectProcessImports',
    'InvisibleEXE',
    'IRCCommands',
    'KeystrokeLogImports',
    'ManifestMismatch',
    'MemoryExfiltrationImports',
    'MSCertStore',
    'MSCryptoImports',
    'MutexImports',
    'NetworkOutboundImports',
    'NontrivialDLLEP',
    'OpenSSLStatic',
    'OSInfoImports',
    'PipeUsage',
    'PossibleBAT',
    'PossibleDinkumware',
    'PossibleKeylogger',
    'PossibleLocker',
    'PossiblePasswords',
    'PrivEscalationCryptBase',
    'ProcessorInfoWMI',
    'ProtectionExamination',
    'RaiseExceptionImports',
    'RDPUsage',
    'RegistryManipulation',
    'ResourceAnomaly',
    'RPCUsage',
    'RWXSection',
    'SeBackupPrivilege',
    'SeDebugPrivilege',
    'SelfExtraction',
    'SeRestorePrivilege',
    'ServiceControlImports',
    'ServiceDLL',
    'SpawnProcessImports',
    'SuspiciousPDataSection',
    'SuspiciousRelocSection',
    'SystemDirImports',
    'TempFileImports',
    'TerminateProcessImports',
    'UserEnvInfoImports',
    'UserManagementImports',
    'UsesCompression',
    'VersionAnomaly',
    'VirtualAllocImports',
    'VirtualProtectImports' ]

threat_attributes = [
    'File Name',
    'File Status',
    'Cylance Score',
    'Signature Status',
    'AV Industry',
    'Global Quarantined',
    'Safelisted',
    'Signed',
    'Cert Timestamp',
    'Cert Issuer',
    'Cert Publisher',
    'Cert Subject',
    'Product Name',
    'Description',
    'File Version',
    'Company Name',
    'Copyright',
    'SHA256',
    'MD5',
    'Classification',
    'DeviceName',
    'Serial Number',
    'File Size (bytes)',
    'File Path',
    'Drive Type',
    'File Owner',
    'Create Time',
    'Modification Time',
    'Access Time',
    'Running',
    'Auto Run',
    'Ever Run',
    'First Found',
    'Last Found',
    'Detected By' ]

g_headers = {
    'devices' : ','.join(device_attributes),
    'events' : ','.join(event_attributes),
    'indicators' : ','.join(indicator_attributes),
    'threats' : ','.join(threat_attributes) }


def is_boolean(strval):
    return strval == 'False' or strval == 'True'


def is_yes_or_no(strval):
    return strval == 'Yes' or strval == 'No'


def is_int(strval):
    try:
        int(strval)
        return True
    except ValueError:
        return False


def validate_header(header, input_type):
    """ compare incoming header with expected header """

    # print(headers[input_type])
    if header == g_headers[input_type]:
        return True
    else:
        return False


def validate_row(row, input_type):
    """ check a sampling of fields for adherence to expected data format """
    if input_type ==  'devices':
        if not is_boolean(row['Background Detection']):
            return False
        if not is_int(row['Files Analyzed']):
            return False
    if input_type ==  'events':
        if not is_boolean(row['Running']):
            return False
        if (not is_int(row['Cylance Score'])) and (not len(row['Cylance Score']) == 0):
#        if not is_int(row['Cylance Score']):
            return False
    if input_type ==  'indicators':
        if not is_int(row['EnumerateFileImports']):
            return False
        if not is_int(row['VirtualProtectImports']):
            return False
    if input_type ==  'threats':
        if not is_yes_or_no(row['Global Quarantined']):
            return False
        if not is_yes_or_no(row['Safelisted']):
            return False

    return True


def format_row(row):
    for key, value in list(row.items()):
        if not value:
            row[key] = "N/A"
    return row


def read_csv_file(csv_absolute_filename, input_type):
    try:
        rows = []
        with open(csv_absolute_filename, 'rU') as csvfile:
            reader = csv.DictReader(csvfile)
            header = ','.join(reader.fieldnames)
            if not validate_header(header, input_type):
                msg = 'Invalid header format: {}.'
                raise ValueError(msg.format(header))
            for row in reader:
                if not validate_row(row, input_type):
                    # discard all if there is a single invalid row
                    msg = 'Invalid row format: {}.'
                    raise ValueError(msg.format(row))
                row = format_row(row)
                rows.append(row)
        return rows
    except Exception as exception:
        msg = 'Threat Data Report - failed to read from {}: {}.'
        g_cylogger.error(msg.format(csv_absolute_filename, exception))
        return []


def write_csv_file(csv_absolute_filename, tenant_download_url, input_type, threat_data_report_token):
    try:
        request = requests.get(tenant_download_url + '/' + input_type + '/' + threat_data_report_token)
    except Exception as exception:
        g_cylogger.error('Failed to download Threat Data Report: {}.'.format(exception))
        return False

    if not request.ok:
        msg = 'Failed to download Threat Data Report: {}'.format(request.status_code)
        g_cylogger.error(msg + '. Please check TDR URL and token.')
        return False

    try:
        with open(csv_absolute_filename, 'wb') as csv_file:
            first_chunk = True
            for chunk in request.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    if first_chunk and chunk[:3] == b'\xef\xbb\xbf':  # filter out BOM
                        csv_file.write(chunk[3:])
                        first_chunk = False
                    else:
                        csv_file.write(chunk)
                    csv_file.flush()
        return True
    except IOError as io_exception:
        logging.exception(io_exception)
        g_cylogger.error('Threat Data Report - failed to download and save.')
        return False
