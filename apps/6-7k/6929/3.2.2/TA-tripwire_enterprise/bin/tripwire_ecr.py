#!/usr/bin/python

import configparser
import inspect
import logging
import os
import shutil
import subprocess  # nosec

import splunk_helper
from tripwire import ReportData, is_windows, make_sure_path_exists, check_te_connection, pyDes_decrypt
from tripwire_logging import setup_logger

logger = logging.getLogger('tripwire')


class ECR(ReportData):
    def do_soap(self, file_name, report_name=None, ecr_parse_sql=False):
        args = [self.script_start] + self.python_cmd.split(' ') + [self.script_loc]
        if not self.te_sslverify:
            args.append('-k')  # insecure, don't validate TE certificates
        args += [
            '-s',
            self.ip_address,
            '-u',
            self.username,
            '-p',
            self.password,
            'report',
            '-T',
            report_name,
            '-F',
            'CSV',
            '-o',
            file_name,
        ]
        if ecr_parse_sql:
            args.append('-E')
        subprocess.check_call([a for a in args if a])  # nosec


def main():
    setup_logger()
    logger.info('tripwire_ecr.py starting')
    session_token = splunk_helper.token_from_stdin()

    # get path of app
    cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    addon_path = os.path.split(os.path.split(cwd)[0])
    app = addon_path[1]

    # ensure there is access to working directory
    subprocess.check_output('cd .', shell=True)  # nosec

    cfg = configparser.ConfigParser()
    configpath = os.path.join(os.path.split(cwd)[0], 'local', 'te_setup.conf')
    cfg.read(configpath, encoding="utf-8-sig")

    # gather parameters for command line call to Tripwire
    username = cfg.get('te_parameters', 'te_username', fallback='')
    ip_address = cfg.get('te_parameters', 'workflow_host', fallback='127.0.0.1')  # default/te_setup.conf uses 0.0.0.0
    directory = cfg.get('te_parameters', 'data_location', fallback='/opt/teexports')
    te_sslverify = cfg.get('te_parameters', 'te_sslverify', fallback='0') == '1'
    ecr_parse_sql = cfg.get('te_parameters', 'ecr_parse_sql', fallback='0') == '1'
    rpt_names = cfg.get('te_parameters', 'ecr_rpt_names', fallback='').split(',')
    rpt_names = [r for r in rpt_names if r]
    if not rpt_names:
        logger.info('No ECR reports specified.  Finished.')
        return
    logger.info('Running the following ECR reports: "%s"', '", "'.join(rpt_names))

    # make sure data directory exists
    save_dir = os.path.join(directory, 'ECR')
    tmp_dir = os.path.join(save_dir, 'tmp')
    make_sure_path_exists(save_dir)
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    make_sure_path_exists(tmp_dir)

    # Decrypt Password
    pm = splunk_helper.PasswordManager(auth_token=session_token)
    password = pm.get_password(username=username)
    if not password:  # if password is an empty string, fallback to DES password
        password = cfg.get("te_parameters", "te_pass", fallback="")
        password = pyDes_decrypt(password)

    check_te_connection(ip_address, username, password, te_sslverify, logger)

    homepath = os.environ.get("SPLUNK_HOME")
    script_loc = os.path.join(homepath, 'etc', 'apps', app, 'bin', 'tripwire.py')
    script_start = 'splunk'
    if not is_windows():
        homepath = os.environ.get("SPLUNK_HOME")
        script_start = os.path.join(homepath, 'bin', 'splunk')

    ecr = ECR(
        ip_address,
        username,
        password,
        script_loc=script_loc,
        first_run=False,
        script_start=script_start,
        python_cmd='cmd python',
        te_sslverify=te_sslverify,
    )

    for rpt in rpt_names:
        # setup file names for command line call
        rpt_filename = rpt.replace(' ', '_')
        file_name = os.path.join(tmp_dir, '%s.csv' % rpt_filename)

        logger.info('Starting SOAP API retrieval for "%s"', rpt)
        ecr.do_soap(file_name, rpt, ecr_parse_sql=ecr_parse_sql)
        ecr.save(tmp_dir, save_dir)
        logger.info('Retrieval complete for "%s"', rpt)
    logger.info('tripwire_ecr.py done')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logger.exception("Exception in tripwire_ecr.py")
