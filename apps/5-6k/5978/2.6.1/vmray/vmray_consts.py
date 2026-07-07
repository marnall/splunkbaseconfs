# File: vmray_consts.py
#
# Copyright (c) VMRay GmbH 2017-2025
#
# Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)
VMRAY_JSON_SERVER = "vmray_server"
VMRAY_JSON_API_KEY = "vmray_api_key"  # pragma: allowlist secret
VMRAY_JSON_DISABLE_CERT = "disable_cert_verification"
VMRAY_ERROR_SERVER_CONNECTION = "Could not connect to server. {}"
VMRAY_ERROR_CONNECTIVITY_TEST = "Connectivity test failed"
VMRAY_SUCC_CONNECTIVITY_TEST = "Connectivity test passed"
VMRAY_ERROR_UNSUPPORTED_HASH = "Unsupported hash"
VMRAY_ERROR_SAMPLE_NOT_FOUND = "Could not find sample"
VMRAY_ERROR_OPEN_ZIP = "Could not open zip file"
VMRAY_ERROR_ADD_VAULT = "Could not add file to vault"
VMRAY_ERROR_MULTIPART = "File is a multipart sample. Multipart samples are not supported"
VMRAY_ERROR_MALFORMED_ZIP = "Malformed zip"
VMRAY_ERROR_SUBMIT_FILE = "Could not submit file"
VMRAY_ERROR_GET_SUBMISSION = "Could not get submission"
VMRAY_ERROR_SUBMISSION_NOT_FINISHED = "Submission is not finished"
VMRAY_ERROR_NO_SUBMISSIONS = "Sample has no submissions"
VMRAY_ERROR_GET_VTIS = "Could not get VTIs"
VMRAY_ERROR_VTIS_NOT_FINISHED = "VTIs are not finished"
VMRAY_ERROR_GET_IOCS = "Could not get IOCs"
VMRAY_ERROR_IOCS_NOT_FINISHED = "IOCs are not finished"
VMRAY_ERROR_FILE_EXISTS = "File already exists"
VMRAY_ERROR_REST_API = "REST API Error"
VMRAY_ERROR_CODE_MSG = "Error code unavailable"
VMRAY_ERROR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
VMRAY_PARSE_ERROR_MSG = "Unable to parse the error message. Please check the asset configuration and|or action parameters"
VMRAY_ERROR_SERVER_RES = "Error processing server response. {}"
VMRAY_INVALID_INTEGER_ERROR_MSG = "Please provide a valid integer value in the {}"
VMRAY_NEGATIVE_INTEGER_ERROR_MSG = "Please provide a valid non-negative integer value in the {}"
VMRAY_ERROR_DOWNLOAD_FAILED = "Download of the files failed"
VMRAY_ERROR_EXTRACTING_SCREENSHOTS = "Extracting screenshots failed"

ACTION_ID_VMRAY_GET_FILE = "get_file"
ACTION_ID_VMRAY_DETONATE_FILE = "detonate_file"
ACTION_ID_VMRAY_DETONATE_URL = "detonate_url"
ACTION_ID_VMRAY_GET_VTIS = "get_vtis"
ACTION_ID_VMRAY_GET_IOCS = "get_iocs"
ACTION_ID_VMRAY_GET_REPORT = "get_report"
ACTION_ID_VMRAY_GET_INFO = "get_info"
ACTION_ID_VMRAY_GET_SCREENSHOTS = "get_screenshots"

VMRAY_DEFAULT_PASSWORD = b"infected"
DEFAULT_TIMEOUT = 60 * 10
INDEX_LOG_DELIMITER = "|"
INDEX_LOG_FILE_NAME_POSITION = 3

SAMPLE_TYPE_MAPPING = {
    "Apple Script": "apple script",
    "Archive": "archive",
    "CFB File": "compound binary file",
    "Email (EML)": "email",
    "Email (MSG)": "email",
    "Excel Document": "xls",
    "HTML Application": "html application",
    "HTML Application (Shell Link)": "html application",
    "HTML Document": "html document",
    "Hanword Document": "hanword document",
    "JScript": "jscript",
    "Java Archive": "jar",
    "Java Class": "java class",
    "macOS App": "macos app",
    "macOS Executable": "macos executable",
    "macOS PKG": "macos installer",
    "MHTML Document": "mhtml document",
    "MSI Setup": "msi",
    "Macromedia Flash": "flash",
    "Microsoft Access Database": "mdb",
    "Microsoft Project Document": "mpp",
    "Microsoft Publisher Document": "pub",
    "Microsoft Visio Document": "vsd",
    "PDF Document": "pdf",
    "PowerShell Script": "powershell",
    "PowerShell Script (Shell Link)": "powershell",
    "Powerpoint Document": "ppt",
    "Python Script": "python script",
    "RTF Document": "rtf",
    "Shell Script": "shell script",
    "URL": "url",
    "VBScript": "vbscript",
    "Windows ActiveX Control (x86-32)": "pe file",
    "Windows ActiveX Control (x86-64)": "pe file",
    "Windows Batch File": "batch file",
    "Windows Batch File (Shell Link)": "batch file",
    "Windows DLL (x86-32)": "dll",
    "Windows DLL (x86-64)": "dll",
    "Windows Driver (x86-32)": "pe file",
    "Windows Driver (x86-64)": "pe file",
    "Windows Exe (Shell Link)": "pe file",
    "Windows Exe (x86-32)": "pe file",
    "Windows Exe (x86-64)": "pe file",
    "Windows Help File": "windows help file",
    "Windows Script File": "windows script file",
    "Word Document": "doc",
}
