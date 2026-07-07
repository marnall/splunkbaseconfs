#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script for generating Recorded Future threatlists for Splunk ES. Currently
generates lists for IPs, hashes and domains.
"""

import sys
import os
import shutil
import csv
import logging
import json
import platform
from tempfile import NamedTemporaryFile

# Relative imports for bundled modules and files.
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__),
                 '..', 'lib', 'python')))

# pylint: disable=import-error,wrong-import-position
from app_env import AppEnv, splunk_home  # nopep8
from rfapi import ConnectApiClient  # nopep8
from rfapi.error import AuthenticationError  # nopep8
from rf_integrations import ThreatlistDownloader  # nopep8
import rf_logger  # nopep8
import api_key  # nopep8
import fields  # nopep8

LGR = logging.getLogger()
MAX_EVIDENCE = 5


# pylint: disable=too-few-public-methods,too-many-instance-attributes
class SplunkFeedGenerator(object):
    """Generate various threat feeds for Splunk."""
    data_group = None
    fields = []
    lookup_name = None
    collection_name = None

    # pylint: disable=too-many-arguments
    def __init__(self, api, max_entries, update_itv, dest_dir,
                 ti_dest_dir, tmp_dir, logger, token):
        """
        Translates Recorded Future threatlists into a format compatible with
        the Splunk ES.

        :param api: An instance of `ConnectApiClient`.
        :param max_entries: Maximum number of IOCs to store in the resulting
            file.
        :param dest_dir: The destination directory for the output file.
        :param tidest_dir: The dest directory for the threat intel file.
        :param tmp_dir: Temporary directory for storing the threatlists.
        :param logger: Logger instance.
        :param token: an RF token
        """
        self.downloader = ThreatlistDownloader(self.data_group,
                                               tmp_dir, api,
                                               max_entries=max_entries,
                                               update_itv=update_itv,
                                               logger=logger)
        self.token = token
        self.dest_dir = dest_dir
        self.dest = os.path.join(dest_dir,
                                 '%s_threatlist.csv' % self.data_group)
        self.ti_dest_dir = ti_dest_dir
        self.tidest = os.path.join(ti_dest_dir,
                                   'rf_%s_threatlist.csv' % self.data_group)
        self.all_fields = self.fields + [
            fields.RiskScoreField(),
            fields.RiskStringField(),
            fields.RiskThresholdField(self.downloader),
            fields.EvidenceDetailsRestField(MAX_EVIDENCE),
        ] + [fields.EvidenceDetailsIdxField(i) for i in range(MAX_EVIDENCE)]
        self.ti_fields = self.fields + [
            fields.DescriptionField(self.data_group)
        ]
        self.tmp_dir = tmp_dir

    # pylint: disable=too-many-locals
    def process(self):
        """
        Downloads and processes the Recorded Future threatlist and writes the
        resulting records in the output file.
        """
        with NamedTemporaryFile(dir=self.tmp_dir) as out, \
             NamedTemporaryFile(dir=self.tmp_dir) as tiout:  # nopep8
            fieldnames = [field.name for field in self.all_fields]
            csvout = csv.DictWriter(out, fieldnames=fieldnames)
            csvout.writeheader()
            tifieldnames = [field.name for field in self.ti_fields]
            ticsvout = csv.DictWriter(tiout, fieldnames=tifieldnames)
            ticsvout.writeheader()
            warning_flag = False
            updated = False
            for entry in self.downloader.entries():
                try:
                    row = {f.name: f.build(entry) for f in self.all_fields}
                    csvout.writerow(row)
                except:  # pylint: disable=bare-except
                    # We accept that some lines are lost rather than crashing
                    warning_flag = True
                tirow = {f.name: f.build(entry) for f in self.ti_fields}
                ticsvout.writerow(tirow)
                updated = True
            if warning_flag:
                LGR.warn('Some rows in %s risk list could not be processed',
                         self.data_group)

            # All done, install in target location
            if updated:  # On search heads these dirs may not exist
                if not os.path.exists(self.dest_dir):
                    os.makedirs(self.dest_dir)
                if not os.path.exists(self.ti_dest_dir):
                    os.makedirs(self.ti_dest_dir)

                os.fsync(out)
                out.seek(0)
                with open(self.dest, 'w') as destobj:
                    shutil.copyfileobj(out, destobj)
                LGR.debug('Retrieval of %s risk list completed.',
                          self.data_group)
                os.fsync(tiout)
                tiout.seek(0)
                with open(self.tidest, 'w') as tidestobj:
                    shutil.copyfileobj(tiout, tidestobj)
                LGR.debug('Retrieval of %s threat_intel list completed.',
                          self.data_group)
                info = 'Retrieval of risk list completed.'
            else:
                LGR.info('Retrieval and update of %s risk list skipped, '
                         'no updates.', self.data_group)
                info = 'Retrieval and update of risk list skipped: list ' \
                       'is recent enough.'

        # risk list,was updated,age (s),interval (s),information
        return '%s,%d,%d,%d,%s' % (self.data_group,
                                   updated and 1 or 0,
                                   self.downloader.age,
                                   self.downloader.update_itv,
                                   info)


class IpFeedGenerator(SplunkFeedGenerator):
    """Risk feed generator for IP risks."""
    is_threat_intel = True
    data_group = 'ip'
    collection_name = 'ip_intel'
    lookup_name = 'recordedFutureIpThreatList'
    fields = [fields.IpNameField()]


class HashFeedGenerator(SplunkFeedGenerator):
    """Risk feed generator for Hashes risks."""
    is_threat_intel = True
    data_group = 'hash'
    collection_name = 'file_intel'
    lookup_name = 'recordedFutureHashThreatList'
    fields = [fields.HashNameField()]


class DomainFeedGenerator(SplunkFeedGenerator):
    """Risk feed generator for Domains risks."""
    is_threat_intel = True
    data_group = 'domain'
    collection_name = 'ip_intel'
    lookup_name = 'recordedFutureDomainThreatList'
    fields = [fields.DomainNameField()]


# class VulnerabilityFeedGenerator(SplunkFeedGenerator):
#     """Risk feed generator for Vulnerabilities risks."""
#     is_threat_intel = False
#     data_group = 'vulnerability'
#     fields = [fields.VulnerabilityNameField()]


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def main():
    """Fetch the IP risk list and store in the app's lookup directory."""
    rf_logger.setup_logging(LGR, splunk_home(), 'TA-recorded_future',
                            'get-rf-threatlists.py')
    LGR.setLevel(level=logging.INFO)  # Set log level to default for now.

    # Session key will provide access to stored passwords.
    try:
        session_key = api_key.get_session_key()
        LGR.debug('Got session_key')
    except Exception as err:  # pylint: disable=broad-except
        LGR.error(err, exc_info=True)
        print('This script can only be launched by the Splunk server.')
        print('Launching via command line (CLI) is not supported.')
        sys.exit(2)

    # Api_key is the access to Recorded Future API.
    try:
        token = api_key.get_credentials(session_key, 'TA-recorded_future')
    except Exception as err:  # pylint: disable=broad-except
        LGR.error(err, exc_info=True)
        app_home = os.path.realdir(os.path.join(__file__, '..'))
        if os.path.isfile(os.path.join(app_home,
                                       'local', 'passwords.conf')):
            LGR.error('The passwords.conf file exist.')
        else:
            LGR.error('The passwords.conf file does not exist.')
        sys.exit(3)

    app_env = AppEnv(session_key)

    log_level_txt = app_env.log_level
    if log_level_txt == 'debug':
        LGR.setLevel(level=logging.DEBUG)
    else:
        LGR.setLevel(level=logging.INFO)

    LGR.info('Starting run (%s/%s)', app_env.identifier, platform.platform())

    try:
        splunk_platform = 'Splunk_%s_with_ES_%s' % (app_env.splunk_version,
                                                    app_env.splunk_es_version)
        api = ConnectApiClient(auth=token,
                               app_name=os.path.basename(__file__),
                               app_version=app_env.integration_version,
                               pkg_name=app_env.package_id,
                               pkg_version=app_env.integration_version,
                               platform=splunk_platform,
                               proxies=app_env.proxy)
    except Exception as err:  # pylint: disable=broad-except
        LGR.error(err, exc_info=True)
        sys.exit(4)

    generators = [
        IpFeedGenerator,
        HashFeedGenerator,
        DomainFeedGenerator,
    ]

    try:
        output = []
        output.append(
            'risk list,was updated,age (s),interval (s),information')
        for gen_cls in generators:
            risk_list = "%s_risk_list" % gen_cls.data_group
            if not app_env.get_enabled(risk_list):
                continue
            dest = app_env.lookups
            ti_dest = app_env.threat_intel
            gen = gen_cls(api, app_env.get_max_entries(risk_list),
                          app_env.get_interval(risk_list),
                          dest, ti_dest, app_env.tmpdir, LGR, token)
            output.append(gen.process())
        LGR.debug('File generation done')
        print '\n'.join(output)
    except AuthenticationError as err:
        estruct = json.loads(err.content)
        message = estruct['error']['message']
        code = estruct['error']['status']
        if code == 401:
            print 'Api access failed, the token is invalid: %s' % (message)
        else:
            print 'Authentication problem while accessing the ' \
                'API: %s (%d)' % (message, code)
        LGR.error(err, exc_info=True)
        sys.exit(5)
    except Exception as err:  # pylint: disable=broad-except
        print '%s' % str(err)
        LGR.error(err, exc_info=True)
        sys.exit(6)

    LGR.info('Ending run')


if __name__ == '__main__':
    main()
