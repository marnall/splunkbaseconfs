import base64
import gzip
import re
import sys
import logging
import zipfile
import tarfile
from urllib.parse import urlencode
from splunk.util import normalizeBoolean
import zlib
from Utilities import KennyLoggins, Utilities
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import os
import json
import urllib.request
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl
import csv
import ftplib
from io import StringIO

_cmd_name = "getwatchlist"
app_path = make_splunkhome_path(["etc", "apps", _cmd_name])
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _cmd_name, "lib"]))
from splunklib.searchcommands import Configuration, GeneratingCommand, Option, validators, dispatch
from tld import get_tld

import pylightxl as xl

kl = KennyLoggins()


class CustomMessageError(Exception):
    pass


class GWUtilities(Utilities):
    def __init__(self, **kwargs):
        Utilities.__init__(self, **kwargs)

    def get_profiles(self):
        uri = self._build_endpoint_uri(
            ['configs', 'conf-getwatchlist'])
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"})
        entries = json.loads(server_content)["entry"]
        ret_entries = {}
        [ret_entries.update({"{}".format(x["name"]): x["content"]}) for x in entries if not x["content"]["disabled"]]
        return ret_entries

    def splunktime2iso(self, times, output_time_format="%Y-%m-%dT%H:%M:%SZ"):
        '''
        Returns splunk-parsed unix timestamps.  Accepts splunk relative time
        identifiers.
        Adapted from: appserver/mrsparkle/lib/times.py
        '''

        getargs = {'time': times, "output_mode": "json", "output_time_format": output_time_format}
        server_response, server_content = self._make_get_request('/search/timeparser', args=getargs)
        entries = json.loads(server_content)
        return entries

    def flatten_json(self, y):
        out = {}

        def flatten(x, name=''):
            if type(x) is dict:
                for a in x:
                    flatten(x[a], name + a + '_')
            elif type(x) is list:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + '_')
                    i += 1
            else:
                out[name[:-1]] = x

        flatten(y)
        return out


delimiter_mapping = {
    "comma": ",",
    "space": ' ',
    "tab": '\t',
    "pipe": '|'
}

_FILE_NOT_FOUND_STRING = "not_found.txt"


@Configuration()
class GetWatchlist(GeneratingCommand):
    """ %(synopsis)
    ##Syntax
    %(syntax)
    ##Description
    %(description)
    """
    default_profile_settings = {'url': '',
                                'delimiter': '\t',
                                'comment': '#',
                                'relevantFieldName': 'ip_address',
                                'relevantFieldCol': 0,
                                'categoryCol': -1,
                                'filetype': "txt",
                                'sheetIndex': 0,
                                'referenceCol': -1,
                                'dateCol': -1,
                                'authUser': '',
                                'authPass': '',
                                'ignoreFirstLine': False,
                                'autoExtract': False,
                                'fieldNames': "",
                                'proxyHost': '',
                                'proxyPort': '8080',
                                'expandObjects': False,
                                'dataKey': "",
                                'flattenJson': False,
                                'dictKeys': [],
                                'ignoreLines': 0,
                                'customFields': {},
                                'addCols': {},
                                'fileName': ""}

    log = None
    utils = None
    # Default to strictest self.settings - ie Splunk Cloud
    is_cloud = True
    settings = {}
    temp_data_location = make_splunkhome_path(["etc", "apps", _cmd_name, "lib", "temporary_data_location"])

    def __init__(self):
        GeneratingCommand.__init__(self)

    def get_saved_profile(self, profile_name):
        #
        # Read profile settings from getwatchlist.conf
        #
        scheme_matches = ['http', 'https', 'ftp']

        try:
            #
            # Check to see if profile contains a full web address and if so parse out the domain
            #
            if any(x in profile_name for x in scheme_matches):
                parsed_tld = get_tld(profile_name, as_object=True)
                parsed_profile_name = parsed_tld.domain
            else:
                parsed_profile_name = profile_name

            profiles = self.utils.get_profiles()
            self.log.debug("profiles={}".format(profiles))
            self.log.debug("profile_name={}, profile_keys={}".format(parsed_profile_name, profiles.keys()))
            update_default_profile = self.default_profile_settings
            if parsed_profile_name in profiles.keys():
                self.log.debug("profile_found={}".format(parsed_profile_name))
                for k, v in profiles[parsed_profile_name].items():
                    if k != "disabled" and k != "eai:acl" and k != "eai:appName" and k != "eai:userName":
                        if v is not None:
                            fixed = self.fix_values(k, v, update_default_profile)
                            self.log.debug("fixed_value={} value={} key={}".format(fixed, v, k))
            else:
                self.log.warn(
                    "action=check_profile_name_in_profiles, msg=profile {} is not found in getwatchlist.conf".format(
                        parsed_profile_name))
                # sys.exit()

            settings = {**self.default_profile_settings, **update_default_profile}
            self.log.debug("action=settings_combined settings={}".format(settings))
            if settings['url'] == '':
                settings['url'] = parsed_profile_name
            if settings['delimiter'] in list(delimiter_mapping.keys()):
                settings['delimiter'] = delimiter_mapping[settings['delimiter']]
            return settings
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)


    def process_args(self):
        try:
            self.log.debug("fieldnames={}".format(self.fieldnames))
            t_args = self.metadata.searchinfo.args
            local_fieldnames = t_args[2:]
            # local_fieldnames = self.fieldnames
            self.log.debug("fieldnames={} tagrs={}".format(self.fieldnames, local_fieldnames))
            # non_profile_fields = self.fieldnames[1:]
            # self.log.debug("fieldnames={} non_profile_fields={}".format(self.fieldnames, non_profile_fields))
            # DICT KEYS dictKeys NEEDS TO PULL THE DICT VALUE INTO TOP LEVEL RESPONSE FIELDS TODO
            t = [self.fix_values_arg(f) for f in local_fieldnames]
            self.log.debug("t={}".format(t))
            result = {}
            for f in [x for x in t if x is not None]:
                self.log.debug("f={}".format(f))
                for key, value in f.items():
                    self.log.debug("key={} value={}".format(key, value))
                    result[key] = value
            self.log.debug("result={}".format(result))
            if result.get("delimiter", "") in list(delimiter_mapping.keys()):
                result["delimiter"] = delimiter_mapping[result.get("delimiter", "")]
            self.log.debug(f"action=check_arg_values args={t_args} result={result}")
            return result
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)

    def fix_values_arg(self, arg):
        try:
            result = {}
            t = arg.split("=", 1)
            fixed = result
            self.log.debug(f"action=check_values arg={arg} t={t} result={result} fixed={fixed}")
            try:
                fixed = self.fix_values(t[0], t[1], result)
                self.log.debug(f"action=check_values_after arg={arg} t={t} result={result} fixed={fixed}")
            except IndexError:
                self.log.warn(f"action=fix_values_arg_not_split arg={arg} t={t}")
            self.log.debug(f"action=fix_values result={result} t={t} fixed={fixed}")
            return result
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)

    def _render_url_datetime(self, url, repl_match, action_match, action, modifier, form):
        # Format: {{dt:<time_modifier>:<strftime_format>}}
        modifier_conversion = {
            "now": "-1s",
            "yesterday": "-1d@d",
            "today": "@d",
            "tomorrow": "+1d@d"
        }
        if modifier in list(modifier_conversion.keys()):
            modifier = modifier_conversion[modifier]
        parsed_time = self.utils.splunktime2iso(modifier, output_time_format=form)[modifier]
        self.log.debug(f'action=calling_splunk_for_time_parse url="{url}" action_match="{action_match}" action="{action}" modifier="{modifier}" format="{form}" parsed_time="{parsed_time}"')
        return re.sub(repl_match, parsed_time, url)

    def render_url(self, url_string):
        valid_actions = {"dt": self._render_url_datetime}
        url_out = url_string
        var_rex = re.compile(r'(\{\{([^\}]+)\}\})')
        my_matches = var_rex.findall(url_out)
        if len(my_matches) > 0:
            self.log.debug(f"action=checking_matches matches={my_matches}")
            for matches in my_matches:
                full_match, action_match = matches
                at = action_match.split(":")
                self.log.debug(f"action=checking_valid_action test_value={at[0]} valid_actions={list(valid_actions.keys())} length={len(at)} test_result={at[0] in list(valid_actions.keys())}")
                if len(at) > 0 and at[0] in list(valid_actions.keys()):
                    url_out = valid_actions[at[0]](url_out, full_match, action_match, *at)
                    self.log.debug(f"action=rendered_match_final match={at} url=\"{url_out}\"")
        self.log.debug(f"action=rendered_url url=\"{url_out}\"")
        return url_out

    def fix_values(self, key, value, result):
        try:
            if not isinstance(value, bool):
                value = value.replace('\'', '')
                value = value.replace('"', '')
                value = value.strip()
                try:
                    value = json.loads(value)
                except:
                    pass
            lowkey = key.lower()
            is_string = ["delimiter", "url", "comment", "relevantfieldname", "authuser", "authpass", "proxyhost",
                         "proxyport", "filetype", "fieldnames", "datakey", "filename", "credential"]
            is_number = ["ignorelines"]
            multiple_strings = ["dictkeys"]
            is_bool = ["ignorefirstline", "autoextract", "expandobjects", "flattenjson"]
            minus_one = ["relevantfieldcol", "categorycol", "referencecol", "datecol", "sheetindex"]
            self.log.info(f"action=check lowkey={lowkey} key={key} value={value} result={result}")
            if lowkey in is_bool:
                result[key] = normalizeBoolean(value)
                self.log.info(f"action=is_bool lowkey={lowkey} key={key} value={value} type={type(result[key])}")
            elif lowkey in is_number:
                result[key] = int(value)
                self.log.info(f"action=is_number lowkey={lowkey} key={key} value={value} type={type(result[key])}")
            elif lowkey in is_string:
                result[key] = str(self.render_url(value)) if lowkey == "url" else str(value)
                self.log.debug(f"action=is_string lowkey={lowkey} key={key} value={value} type={type(result[key])}")
            elif lowkey in minus_one:
                result[key] = int(value) - 1
                self.log.info(f"action=minus_one lowkey={lowkey} key={key} value={value} type={type(result[key])}")
            elif lowkey in multiple_strings:
                result[key] = value.split(",")
                self.log.info(
                    f"action=multiple_strings lowkey={lowkey} key={key} value={value} type={type(result[key])}")
            else:
                if lowkey.isdigit():
                    self.log.info(
                        f"action=is_digit lowkey={lowkey} key={key} value={value} type={type(value)} result={result}")
                    if "addCols" not in result:
                        result["addCols"] = {}
                    result['addCols'][int(key)] = value
                else:
                    self.log.info(
                        f"action=is_not_digit lowkey={lowkey} key={key} value={value} type={type(value)} result={result}")
                    if "customFields" not in result:
                        result["customFields"] = {}
                    result['customFields'][key] = value
            return result
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)

    def _catch_error(self, e):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = " " \
                    "error_message=\"{}\" " \
                    "error_type=\"{}\" " \
                    "error_arguments=\"{}\" " \
                    "error_filename=\"{}\" " \
                    "error_line_number=\"{}\" " \
            .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno)
        self.log.error(error_msg)
        return error_msg

    def gz_str_to_str(self, si):
        try:
            # si = ByStrIO(compressed_str)
            return self.gunzip_stream_to_str(si)
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)

    def gunzip_stream_to_str(self, gz_stream):
        try:
            unzipped_str = ''
            for part in self.gunzip_stream(gz_stream):
                self.log.debug(f"action=part len={len(part)} part={part}")
                part = part.decode()
                unzipped_str += part
            return unzipped_str
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)

    def gunzip_stream(self, gz_stream):
        try:
            dec = zlib.decompressobj(32 + zlib.MAX_WBITS)
            for chunk in gz_stream:
                uz = dec.decompress(chunk)
                self.log.debug(f"action=chunk len={len(chunk)} max={zlib.MAX_WBITS} uztf8={chunk} uz={uz}")
                if uz:
                   yield uz
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)

    def get_watchlist(self):
        try:
            self.settings['url'] = urllib.parse.unquote(self.settings.get('url', ""))
            l_url = self.settings['url']
            parsed_url = urlparse(l_url)
            url_scheme = parsed_url.scheme
            self.log.debug("action=check_params scheme={} url={}".format(url_scheme, parsed_url))
            self.log.debug("get_watchlist url_scheme: {}".format(url_scheme))
            file_buffer = None
            if url_scheme == 'http' and self.is_cloud:
                self.log.fatal("MUST ENFORCE SPLUNK CLOUD SSL ONLY")
                exit(200)
            elif url_scheme == 'https':
                # ENFORCE to use HTTPS. By nature of the scheme, only HTTPS calls will be made.
                # WILL TRIGGER FOR ANY CALLS IN SPLUNK CLOUD
                file_buffer = self.fetch_http(True)
            elif url_scheme == 'http' and not self.is_cloud:
                # ONLY do HTTP if NOT CLOUD
                file_buffer = self.fetch_http(False)
            elif url_scheme == 'ftp':
                file_buffer = self.fetch_ftp()
            elif url_scheme == 'file':
                path = os.path.sep.join([parsed_url.netloc, f"{parsed_url.path}".strip("/")]).strip()
                self.log.debug("action=check_file_path path={} file_object={}".format(path, parsed_url))
                if path.startswith("/"):
                    self.log.debug("action=check_absolute_path path={}".format(path))
                    raise CustomMessageError(f"Absolute file paths are not supported. Please use relative paths to the app's directory. {path}")
                else:
                    file_buffer = self.fetch_file(path)
            else:
                if url_scheme == '':
                    if self.settings.get("filetype", "") == l_url:
                        raise CustomMessageError(f"Profile '{l_url}' requires a URL.")
                    else:
                        raise CustomMessageError(f"Invalid URL: {l_url}")
                else:
                    raise CustomMessageError(f"Unsupported protocol: {url_scheme}. Supported: http, https, ftp, file")
            return self.clean_file(file_buffer)
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)

    def fetch_file(self, path=""):
        jailed_path = os.path.join(app_path, 'watchlists')
        self.log.debug(f"action=check_jailed_path filename={jailed_path}")
        if not os.path.exists(jailed_path):
            os.makedirs(jailed_path)
            self.log.debug(f"action=check_jailed_path status=created filename={jailed_path}")
        filename = os.path.abspath(os.path.join(f'{jailed_path}', f'{path}'))
        if not filename.startswith(jailed_path):
            raise CustomMessageError(f"File path is outside jailed directory: {path}")
        self.log.debug(f"action=fetch_file filename={filename}")
        if not os.path.exists(filename):
            raise CustomMessageError(f"File not found: {filename}")
        self.log.debug(f"action=fetch_file status=exists filename={filename}")
        if os.path.isfile(filename):
            self.log.debug(f"action=fetch_file status=isfile filename={filename}")
            return open(filename, 'r')
        else:
            self.log.debug(f"action=fetch_file status=isdir filename={filename}")
            raise CustomMessageError(f"File is not a file: {filename}")

    def fetch_http(self, force_ssl):
        """
        Fetches the requested watchlist using HTTP or HTTPS and returns the
        contents, filtered using the self.settings.
        """
        if force_ssl and self.is_cloud:
            msg = "MUST ENFORCE SSL ON SPLUNK CLOUD"
            self.log.fatal("action=pennywise_cloud is_cloud={} message={}".format(self.is_cloud, msg))
            exit(200)
        try:
            url = self.settings['url']
            auth_user = self.settings['authUser']
            auth_pass = self.settings['authPass']
            proxy_host = self.settings['proxyHost']
            proxy_port = self.settings['proxyPort']

            # if the username or password is not empty, we will use an auth handler
            if auth_user != '' or auth_pass != '':
                pass_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
                pass_manager.add_password(None, url, auth_user, auth_pass)
                auth_handler = urllib.request.HTTPBasicAuthHandler(pass_manager)
                opener = urllib.request.build_opener(auth_handler)
                urllib.request.install_opener(opener)

            # This call does not "perform" the request, it "builds it" for use below.
            request = urllib.request.Request(url)
            if self.settings.get("has_credential", False):
                cv = self.settings.get("credential_value", "")
                if self.settings["credential_type"] == "header":
                    request.add_header("Authorization", cv)
                if self.settings["credential_type"] == "basic":
                    b = base64.b64encode(bytes(cv, 'utf-8')).decode('ascii')
                    request.add_header("Authorization", f'Basic {b}')
                if self.settings["credential_type"] == "param":
                    parsed_url = urlparse(url)
                    start_check = f'{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?'
                    if url.startswith(f'{start_check}'):
                        url = f'{url}&{cv}'
                    else:
                        url = f'{url}?{cv}'
                    request = urllib.request.Request(f'{url}')
                self.log.info("action=create_request credential_added=True type={}".format(self.settings["credential_type"]))
            self.log.info("action=create_request request={}".format(request))
            if proxy_host != '':
                proxy_host = proxy_host + ':' + proxy_port
                request.set_proxy(proxy_host, 'http')
                # request.set_proxy(proxyHost, urlparse(url).scheme)
            self.log.info(f"action=getting_url url={url} is_splunk_cloud={self.is_cloud}")
            # We are only calling this from the "if scheme === https" so it only makes HTTPS requests.
            file_handle = urllib.request.urlopen(request, timeout=self.settings.get('timeout', 15))
            return file_handle
        except TimeoutError as e:
            # Use self.settings['url'] so as not to leak the credential in the modified url variable when using query auth.
            self._return_error(e, f"A timeout occurred fetching the URL at {self.settings['url']}")
        except Exception as e:
            # Use self.settings['url'] so as not to leak the credential in the modified url variable when usin.formag query auth.
            self._return_error(e, f"An error occurred fetching the URL at {self.settings['url']}: <{type(e)}> {str(e)}")

    def fetch_ftp(self):
        """
        Fetches the requested watchlist using FTP and returns the contents,
        filtered using the self.settings.
        """
        try:
            parsed_url = urlparse(self.settings['url'])
            host = parsed_url.hostname
            port = parsed_url.port or 21
            filename = parsed_url.path
            username = self.settings.get('authUser', "anonymous")
            password = self.settings.get('authPass', "pass")
            if self.settings.get("has_credential", False):
                # We can only use a basic credential type for FTP since that's all FTP supports. If the credential type is not basic, we will log a warning and attempt to use the credential value as a username (which may work if the FTP server is configured to allow that).
                if self.settings["credential_type"] != "basic":
                    raise CustomMessageError("Unsupported credential type for FTP. FTP only supports 'basic' authentication credentials.")

                # Get the credential value and verify the format.
                cv = self.settings.get("credential_value", "")
                if not ":" in cv or len(cv.split(":", 1)) != 2:
                    raise CustomMessageError("Invalid credential format for FTP. Expected '<username>:<password>'.")

                username, password = cv.split(":", 1)
                self.log.info(f'action=ftp_credential_added credential_added=True username="{username}"')

            # Setup the FTP connection
            ftp = ftplib.FTP()
            ftp.connect(host, port)
            ftp.login(username, password)
            self.log.info(f'action=ftp_connected host="{host}" username="{username}"')

            # StringIO buffer to hold the file from FTP
            ftp_buffer = StringIO()

            # get the filelines and write them back to our StringIO buffer
            ftp.retrlines("RETR " + filename, lambda s, w=ftp_buffer.write: w(s + '\n'))

            ftp_buffer.seek(0)
            return ftp_buffer
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)

    def get_temporary_file_location(self, filename):
        return os.sep.join([self.temp_data_location, filename])

    def clean_file(self, file_buffer):
        """
        Iterates through the given file-like object and returns a version
        without commented lines (lines with the comment character at the start).
        Also removes empty lines.
        """
        try:
            csvbuffer = ""
            comment = self.settings["comment"]
            file_type = self.settings["filetype"]
            log_preamble = f'parsing_file_type="{file_type}"'
            def add_preamble(log_line):
                return f' {log_preamble} {log_line}'
            ignore_first_line = self.settings["ignoreFirstLine"]
            auto_extract = self.settings["autoExtract"]
            self.log.debug("action=check_file_type file_type={}".format(file_type))
            if  self.settings.get("has_error", False):
                csvbuffer += "ERROR\n{}".format(file_buffer.getvalue())
            elif file_type in ["txt", "csv"]:
                csvbuffer += self._parse_basic_delimited_file(file_buffer)
            elif file_type in ["xls"]:
                self.log.warn("action=xls_parse result=not_implemented")
            elif file_type in ["xlsx"]:
                temp_location_file = self.get_temporary_file_location("xslx_temporary_file.xlsx")
                with open(temp_location_file, 'wb+') as f:
                    f.write(file_buffer.read())
                db = xl.readxl(fn=temp_location_file)
                os.remove(temp_location_file)
                sheets = [x.replace("'", "").replace('"', "") for x in db.ws_names]
                first_sheet = sheets[0]
                if self.settings["sheetIndex"] > 0:
                    first_sheet = sheets[self.settings["sheetIndex"]]
                self.log.info("action=xlsx_parse first_sheet={} sheets_available={}".format(first_sheet, sheets))
                row_count = 0
                for row in db.ws(ws=first_sheet).rows:
                    try:
                        line = '"{}"'.format("\",\"".join(row))
                        self.log.debug(f"action=clean_file line_type={type(line)} line={line} file_type={file_type}")
                        if line.startswith(comment) or not line.strip():
                            self.log.debug(
                                "action=clean_file pass_line=true line={} comment={} strip={}".format(line, comment,
                                                                                                      line.strip()))
                            pass
                        else:
                            self.log.debug(f"action=clean_file line={line} type={type(line)}")
                            if row_count == 0 and ignore_first_line:
                                self.log.debug(
                                    "action=row_0 ignore_first_line={} line={}".format(ignore_first_line, line))
                            else:
                                csvbuffer = csvbuffer + "{}\n".format(line.replace('\n', ' '))
                        row_count += 1
                    except Exception as e:
                        self._return_error(e, str(e))
                        pass
            elif file_type in ["json"]:
                lines = " ".join([l.decode('utf-8') for l in file_buffer.readlines()])
                self.log.debug(add_preamble("action=parsing_json auto_extract={} len_lines={}".format(auto_extract, len(lines))))
                lines = json.loads(lines)
                self.log.debug(add_preamble("action=parsing_json auto_extract={} len_lines={}".format(auto_extract, len(lines))))
                if auto_extract:
                    dk = self.settings.get("dataKey", None)
                    newData = lines
                    if dk:
                        self.log.debug(add_preamble(f"action=parsing_flattend_json dk={dk} lines={lines.keys()}"))
                        if "." in dk:
                            t = dk.split(".")
                            r = lines[t[0]]
                            newData = r
                            self.log.debug(add_preamble(f"action=parsing_flattend_json t={t} type={type(r)} is_dict={isinstance(r, dict)}"))
                            if isinstance(r, dict) and t[1] in r:
                                newData = r[t[1]]
                                if self.settings["flattenJson"]:
                                    newData = self.utils.flatten_json(r[t[1]])
                            elif isinstance(r, list):
                                if self.settings["flattenJson"]:
                                    newData = [self.utils.flatten_json(x[t[1]]) for x in r if t[1] in x]
                                else:
                                    newData = [x[t[1]] for x in r if t[1] in x]
                        else:
                            newData = lines[dk]
                    if type(newData) == list:
                        self.log.debug(add_preamble(f"action=generating_results newData=list"))
                        csvbuffer = "{}\n".format(dk)
                        process_objects = False
                        headers = []
                        for l in newData:
                            self.log.debug(add_preamble("action=parsing_json type={} new_data_line={} flattened={}".format(type(l), l, self.utils.flatten_json(l))))
                            if type(l) == object or type(l) == dict:
                                process_objects = True
                                [headers.append(x) for x in l.keys() if x not in headers]
                            else:
                                csvbuffer += "{}\n".format(json.dumps(l))
                        if process_objects:
                            self.log.debug(add_preamble("action=parsing_json newDataHeaders={}".format(headers)))
                            f = StringIO()
                            w = csv.DictWriter(f, fieldnames=headers)
                            w.writeheader()
                            [w.writerow(
                                {x: json.dumps(r[x]) if type(r[x]) == dict or type(r[x]) == object else f"{r[x]}" for x
                                 in list(r.keys())}) for r in newData]
                            csvbuffer = "{}".format(f.getvalue())
                    elif type(lines) == dict or type(lines) == object:
                        self.log.debug(add_preamble("action=test test='type(lines) == dict or type(lines) == object'"))
                        f = StringIO()
                        expandObjects = self.settings.get("expandObjects", False)
                        if expandObjects:
                            self.log.debug(add_preamble("action=test test='if expandObjects'"))
                            new_rows = []
                            headers = []
                            for k in lines.keys():
                                new_rows.append(lines[k])
                                headers += lines[k].keys()
                            hdrs = list(set(headers))
                            self.log.debug(add_preamble("action=parsing_expanded_json headers={} new_rows_length={}".format(hdrs, len(new_rows))))
                            w = csv.DictWriter(f, fieldnames=headers)
                            w.writeheader()
                            [w.writerow(
                                {x: json.dumps(r[x]) if type(r[x]) == dict or type(r[x]) == object else f"{r[x]}" for x
                                 in list(r.keys())}) for r in new_rows]
                            csvbuffer = f.getvalue()
                            self.log.debug(add_preamble("action=parsing_json writer={}".format(f.getvalue())))
                        else:
                            self.log.debug(add_preamble("action=test test='if expandObjects' else=true"))
                            fields = list(lines.keys())
                            rows = [lines]
                            do_dict_keys = self.settings.get("dictKeys", [])
                            self.log.debug(add_preamble(f"action=parsing_json fields={fields} do_dict_keys={do_dict_keys}"))
                            if len(do_dict_keys) > 0:
                                self.log.debug(add_preamble("action=test test='len(do_dict_keys) > 0'"))
                                for dictKey in do_dict_keys:
                                    if dictKey in lines.keys():
                                        self.log.debug(add_preamble("action=test test='if dictKey in fields'"))
                                        extra_fields = list(lines[dictKey].keys())
                                        self.log.debug(add_preamble(f"action=pulling_extra_fields ef={extra_fields}"))
                                        fields += extra_fields
                                        rows.append(lines[dictKey])
                            tfields = list(set(fields))
                            self.log.debug(add_preamble(f'action=fields_list fields="{tfields}"'))
                            w = csv.DictWriter(f, fieldnames=tfields)
                            w.writeheader()
                            [w.writerow(
                                {x: json.dumps(r[x]) if type(r[x]) == dict or type(r[x]) == object else f"{r[x]}" for x
                                 in list(r.keys())}) for r in rows]
                            csvbuffer = f.getvalue()
                            self.log.debug(add_preamble("action=parsing_json writer={}".format(f.getvalue())))
                    else:
                        self.log.debug(add_preamble("action=test test='type(newData) == list' else=true"))
                        csvbuffer = "{}\n{}".format(self.settings.get("relevantFieldName", "ip_address"), newData)
                    self.log.debug(add_preamble("action=parsing_json newData-Keys={} type={}".format(list(newData.keys()), type(newData))))
                else:
                    self.settings["relevantFieldName"] = "_raw"
                    tmp_delim = "\f"
                    csvbuffer = "{}".format(json.dumps(lines))
                    self.log.debug(add_preamble("action=parsing_json type=_raw tmp_delim={} lines={}".format(tmp_delim, lines)))
                    self.settings["delimiter"] = tmp_delim
            elif file_type in ["archive"]:
                self.log.info("action=url url={}".format(self.settings.get("url", "")))
                split_tup = os.path.splitext(self.settings.get("url", ""))
                # extract the file name and extension
                file_name = split_tup[0]
                file_extension = split_tup[1]
                self.log.debug(f"action=getting_file_extension file_name='{file_name}' file_ext='{file_extension}'")
                temp_location_file = self.get_temporary_file_location(f"{file_type}_temporary_file{file_extension}")
                with open(temp_location_file, 'wb+') as f:
                    f.write(file_buffer.read())
                self.log.info(f"action=writing_temp_file file={temp_location_file}")
                file_mode = "r"
                self.log.info(
                    f"action=reading_temp_file file={temp_location_file} file_extension='{file_extension}' mode={file_mode}")
                temp_data_location = self.get_temporary_file_location("")
                temp_data_file = _FILE_NOT_FOUND_STRING
                if file_extension in [".tar", ".tgz", ".tar.gz"]:
                    if file_extension in [".tgz", ".tar.gz"]:
                        file_mode = "r:gz"
                    with tarfile.open(temp_location_file, file_mode) as tf:
                        members = {m.name: m for m in tf.getmembers()}
                        self.log.debug(
                            "action=listing_tar_file_contents members={}".format(",".join(members.keys())))
                        if len(members) == 0:
                            csvbuffer += "Warning: The file provided ({}{}) does not contain any members.".format(file_name, file_extension)
                        elif len(members) > 0:
                            member_list = list(members.keys())
                            member_name = member_list[0]
                            if len(members) > 1 and self.settings.get("fileName", None) is not None and self.settings.get("fileName", None) in member_list:
                                member_name = self.settings.get("fileName", _FILE_NOT_FOUND_STRING)
                            self.log.info("action=got_member_name member=\"{}\" fileName={}".format(member_name, self.settings.get("fileName", None)))
                            member = members[member_name]
                            temp_data_file = self.get_temporary_file_location(f"{member_name}")
                            tf.extract(member, path=temp_data_location)
                        tf.close()
                elif file_extension in [".zip"]:
                    with zipfile.ZipFile(temp_location_file, 'r') as tf:
                        members = tf.namelist()
                        self.log.info(
                            "action=listing_zip_file_contents members={}".format(",".join(members)))
                        if len(members) == 0:
                            csvbuffer += "Warning: The file provided ({}{}) does not contain any members.\n".format(file_name, file_extension)
                        elif len(members) > 0:
                            member_list = members
                            member_name = member_list[0]
                            if len(members) > 1 and \
                                    self.settings.get("fileName",  None) is not None and \
                                    self.settings.get("fileName", None) in member_list:
                                member_name = self.settings.get("fileName", _FILE_NOT_FOUND_STRING)
                            self.log.info("action=got_member_name member=\"{}\" fileName={}".format(member_name,
                                                                                                    self.settings.get(
                                                                                                        "fileName",
                                                                                                        None)))
                            temp_data_file = self.get_temporary_file_location(f"{member_name}")
                            tf.extract(member_name, temp_data_location)
                else:
                    csvbuffer += f"{file_extension} was not implemented."
                    os.remove(temp_location_file)
                try:
                    if temp_data_file == _FILE_NOT_FOUND_STRING:
                        raise FileNotFoundError("Temporary Data File not found.")
                    self.log.info(f"action=reading_temp_file mode={file_type} temp_data_file={temp_data_file}")
                    with open(temp_data_file, "r") as tdf:
                        csvbuffer += self._parse_basic_delimited_file(tdf)
                    os.remove(temp_data_file)
                except Exception as e:
                    self._return_error(e)
                    csvbuffer += "Exception: {} {}".format(type(e), e)
                    if temp_data_file != _FILE_NOT_FOUND_STRING:
                        os.remove(temp_data_file)
                os.remove(temp_location_file)
            elif file_type in ["gz"]:
                lines = gzip.decompress(file_buffer.read())
                csvbuffer += lines.decode("utf-8")
            elif file_type in ["raw"]:
                csvbuffer += "raw\n"+file_buffer.read()
            else:
                csvbuffer += "Unknown Format\n{}".format(file_type)
            self.log.debug(add_preamble("action=clean_file csvbuffer={}".format(len(csvbuffer))))
            return csvbuffer
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)

    def _parse_basic_delimited_file(self, handle):
        try:
            self.log.info(f"action=parsing_basic_file handle={handle}")
            lbuff = ""
            comment = self.settings["comment"]
            file_type = self.settings["filetype"]
            ignore_first_line = self.settings["ignoreFirstLine"]
            lines = []
            try:
                self.log.info("action=read_file_handle_with_decode")
                lines = [x.decode('utf-8') for x in handle.readlines()]
            except Exception as e:
                self.log.info(f"action=read_file_handle_with_decode exception={e} type={type(e)}")
            if len(lines) == 0:
                try:
                    self.log.info("action=read_file_handle_without_decode")
                    handle.seek(0, 0)
                    lines = [x for x in handle.readlines()]
                except Exception as e:
                    self.log.info(f"action=read_file_handle_without_decode exception={e} type={type(e)}")
            self.log.info("action=read_some_lines line_count={}".format(len(lines)))
            row_count = 0
            for line in lines:
                try:
                    self.log.debug(
                        f"action=clean_file line_type={type(line)} line={line} file_type={file_type}")
                    if line.startswith(comment) or not line.strip():
                        self.log.debug(
                            "action=clean_file pass_line=true line={} comment={} strip={}".format(line,
                                                                                                  comment,
                                                                                                  line.strip()))
                    else:
                        self.log.debug(f"action=clean_file line={line} type={type(line)}")
                        if row_count == 0 and ignore_first_line:
                            self.log.debug(
                                "action=row_0 ignore_first_line={} line={}".format(ignore_first_line, line))
                        else:
                            lbuff = lbuff + "{}".format(line)
                    row_count += 1
                except CustomMessageError as e:
                    self._return_error(e, str(e))
                except Exception as e:
                    self._return_error(e)
            return lbuff
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)

    def output_watchlist(self, csvbuffer):
        """
        Prints the fetched watchlist to stdout as a CSV (comma delimited).
        Uses the passed self.settings for formatting and column names.
        """
        try:
            self.log.debug("action=initial_start settings={}".format(self.settings))
            delimiter = self.settings['delimiter']
            file_type = self.settings['filetype']
            if f"{delimiter}" == "\\t":
                delimiter = '\t'
            if f"{delimiter}" == "\\s":
                delimiter = " "
            if len(f'{delimiter}') < 1:
                delimiter = ','
            self.log.info(f'action=check_delimiter file_type="{file_type}" delimiter="{delimiter}" delimiter_len="{len(delimiter)}"')
            field_names = self.settings['fieldNames'].replace(";", delimiter)
            relevant_field_name = self.settings['relevantFieldName']
            relevant_field_col = self.settings['relevantFieldCol']
            ignore_first_line = self.settings['ignoreFirstLine']
            auto_extract = self.settings["autoExtract"]
            category_col = self.settings['categoryCol']
            ignore_lines = self.settings['ignoreLines']
            reference_col = self.settings['referenceCol']
            date_col = self.settings['dateCol']
            custom_fields = self.settings['customFields']
            add_cols = self.settings['addCols']

            if len(field_names) > 0:
                self.log.debug(
                    "action=setup_fieldnames field_names={} csv_file_object_length={}".format(field_names, len(csvbuffer)))
                csvbuffer = "{}\n{}".format(field_names, csvbuffer)
            # StringIO buffer to fake a file-like object
            csv_file_object = StringIO(csvbuffer)
            # using the passed parameters, a new csv dialect is created
            # and then a reader is created using the new dialect
            csv.register_dialect(
                'passed_params', delimiter=delimiter, skipinitialspace=True)

            # create a fieldname list if the fields exist
            return_rows = []

            if auto_extract:
                csv_reader = csv.DictReader(csv_file_object, dialect="passed_params")
                row_count = 0
                for line in csv_reader:
                    if row_count == 0 and ignore_first_line:
                        self.log.debug(f"action=auto_extract_csv line_skip=True row={row_count}")
                        row_count += 1
                        continue
                    if row_count < ignore_lines:
                        self.log.debug(f"action=auto_extract_csv line_skip=True row={row_count} ignore_lines={ignore_lines}")
                        row_count += 1
                        continue
                    # self.log.debug("row={} line={}".format(row_count, line))
                    for cust in custom_fields.keys():
                        line[cust] = self.format_value(custom_fields[cust])
                    return_rows.append(line)
                    row_count += 1
            else:
                csv_reader = csv.reader(csv_file_object, csv.get_dialect('passed_params'))
                field_list = [relevant_field_name]
                if category_col >= 0:
                    field_list.append('category')
                if reference_col >= 0:
                    field_list.append('reference')
                if date_col >= 0:
                    field_list.append('date')
                # add any custom fields, keep the keys in a list, to remember the order
                custom_keys = []
                self.log.debug(f"customFields={custom_fields}")
                for k in custom_fields:
                    custom_keys.append(k)
                    field_list.append(k)

                # add any additional cols
                add_keys = []
                for k in add_cols:
                    add_keys.append(k)
                    field_list.append(add_cols[k])
                # use our reader to go through the downloaded content
                row_count = 0

                # append field list header
                # return_rows.append(tuple(field_list))
                for row in csv_reader:
                    try:
                        # self.log.debug(f"action=process_row row_count={row_count}")
                        # self.log.debug(f"action=process_row row={row}")
                        row_holder = {}
                        self.log.info(
                            f"action=check_field rfn={relevant_field_name} rfc={relevant_field_col} row={row} ")
                        row_holder[relevant_field_name] = self.format_value(row[relevant_field_col])
                        if category_col >= 0:
                            row_holder['category'] = self.format_value(row[category_col])
                        if reference_col >= 0:
                            row_holder['reference'] = self.format_value(row[reference_col])
                        if date_col >= 0:
                            row_holder['date'] = self.format_value(row[date_col])

                        # Now for custom fields
                        for cust in custom_keys:
                            row_holder[cust] = self.format_value(custom_fields[cust])

                        # and additional cols
                        for add_col in add_keys:
                            row_holder[add_col] = self.format_value(row[int(add_col)])

                        self.log.debug("type row_holder: {}".format(type(row_holder)))
                        # output to the CSV writer, which is using sysout
                        self.log.debug(f"row_holder={row_holder}")
                        return_rows.append(row_holder)
                        row_count += 1
                        self.log.info(f"row_count={row_count}")
                    except CustomMessageError as e:
                        self._return_error(e, str(e))
                    except Exception as e:
                        self._return_error(e)
            return return_rows
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)

    def format_value(self, value):
        """
        Some of the blacklists use bad characters such as ascii 160
        which messes up the display back in splunkweb
        """
        try:
            if isinstance(value, str):
                ret_val = value.strip()
                ret_val = ret_val.replace(chr(160), '')
            else:
                ret_val = value
            return ret_val
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)

    def _return_error(self, e=None, message=None, **kwargs):
        log_preamble = "action=return_error"
        base_msg = "No Error Message Passed."
        if message is None:
            message = base_msg
            kwargs["invalid_message"] = "no_message_passed"
        if e:
            if message == base_msg:
                message = f"An Non-Specific Exception Occurred: {str(e)}"
            self._catch_error(e)
        else:
            kwargs["no_error_object"] = "no_error_object_passed"
        log_data = " ".join([log_preamble]+[f'{k}="{v}"' for k, v in kwargs.items()])
        self.log.error(log_data)
        # Use the Splunk API to return an error message to the Search UI
        self.write_error("{} command: {}".format(_cmd_name, message))
        # Exit gracefully. Exiting with any other status code will break how Splunk presents the error message.
        exit(0)

    def generate(self):
        events = []
        try:
            session_key = "{}".format(self.metadata.searchinfo.session_key)
            self.utils = GWUtilities(app_name=_cmd_name, session_key=session_key)
            self.log = kl.get_logger(app_name=_cmd_name, file_name=_cmd_name, log_level=logging.INFO)
            try:
                self.is_cloud = self.utils.is_cloud()
                self.log.info("action=running_command is_cloud={}".format(self.is_cloud))
            except CustomMessageError as e:
                self._return_error(e, str(e))
            except Exception as e:
                self._return_error(e)
            self.log.debug(
                "action=starting_cmd_transform cmd={} config={} fieldnames={} args={}".format(_cmd_name, self.service,
                                                                                              self.fieldnames,
                                                                                              self.metadata.searchinfo.args))
            self.log.debug("action=checking_for_cloud isCloud={}".format(self.is_cloud))
            if not self.fieldnames:
                raise CustomMessageError("A profile was not provided.")
            profile_name = self.fieldnames.pop(0)
            saved_profile = self.get_saved_profile(profile_name)
            args = self.process_args()
            self.log.debug("action=making_settings profile_name={} saved_profile={} args={}".format(profile_name,
                                                                                                    type(saved_profile),
                                                                                                    args))
            self.settings = {**saved_profile, **args}
            self.log.info("action=final_settings settings={}".format(json.dumps(self.settings)))
            if ("credential" in self.settings
                    and self.settings.get("credential", None) is not None
                    and self.settings.get("credential", "NONE").upper() != "NONE"):
                cred_stz = urllib.parse.unquote(self.settings.get("credential", ""))
                self.log.info("action=retrieving_credential realm=\"{}\" credential_name=\"{}\"".format(
                    _cmd_name, cred_stz
                ))
                encr = self.utils.get_credential(_cmd_name, cred_stz )
                if not encr:
                    raise CustomMessageError(f"The credential for this profile, {cred_stz}, was not found.")
                credential = urllib.parse.unquote(encr)
                t = json.loads(credential)
                self.log.info(
                    'action=retrieving_credential realm="{}" credential_name="{}" credential_value_length="{}"'.format(
                        _cmd_name,
                        cred_stz,
                        len(credential)
                    ))
                self.settings["credential_type"] = f'{t["type"]}'.lower()
                self.settings["credential_value"] = f'{t["value"]}'
                self.settings["credential_name"] = f'{t["name"]}'
                self.log.debug(f'action=show_credential credential_length={len(self.settings["credential_value"])} credential_name="{self.settings["credential_name"]}" credential_guid="{self.settings.get("credential", "")}" ')
                self.settings["has_credential"] = True
            # GET WATCHLIST via requests
            watchlist_content = self.get_watchlist()
            events = self.output_watchlist(watchlist_content)
        except CustomMessageError as e:
            self._return_error(e, str(e))
        except Exception as e:
            self._return_error(e)
        for evt in events:
            try:
                # self.log.debug("action=check_key evt={}, type evt: {}".format(evt, type(evt)))
                yield evt
            except Exception as e:
                yield {"error": self._catch_error(e)}


dispatch(GetWatchlist, sys.argv, sys.stdin, sys.stdout, __name__)
