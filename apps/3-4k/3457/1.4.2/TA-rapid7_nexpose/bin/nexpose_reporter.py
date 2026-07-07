from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
# !/usr/bin/python
from builtins import str
from builtins import object
from future import standard_library
standard_library.install_aliases()
import api.pnexpose as pnx
import platform
import os
import re
from time import strftime, localtime
from api.utils import Utils
import splunk.auth as auth
import splunk.entity as entity
from multiprocessing.dummy import Pool as ThreadPool
from data_gen.asset_data_generator import AssetDataGenerator
from data_gen.vuln_data_generator import VulnDataGenerator
from data_gen.vuln_exception_data_generator import VulnExDataGenerator
from scan_data import ScanData
import time
import threading

# Get Splunk home
SPLUNK_HOME = os.environ['SPLUNK_HOME']
# App name
APPNAME = 'TA-rapid7_nexpose'
# Nexpose Auth token
AUTH_TOKEN = ''
# Default Nexpose API version
API_VER = '2.3.0'

# serveraddr, port, username, password, logger, apiver
# TODO: Add 'self' parameter to methods


class NexposeReporter(object):
    def __init__(self, username, password, serveraddr, port, session_key, index, new_scans_only, import_solution):
        self.logger = Utils.setup_logging()
        
        self.username = username
        self.password = password
        self.serveraddr = serveraddr
        self.port = port
        self.session_key = session_key
        self.new_scans_only = str(new_scans_only) in ['1', 'True', True, 'true']
        self.import_solution = str(import_solution) in ['1', 'True', True, 'true']
        self.index = index
        
        self.root = SPLUNK_HOME + '/etc/apps/' + APPNAME
        
        # Folders for saving formatted Nexpose reports
        self.save_directory = self.to_dir('/lookups/')
        self.vuln_directory = self.to_dir('/lookups/vuln_cim_lookups/')
        self.asset_directory = self.to_dir('/lookups/asset_cim_lookups/')
        
        self.is_windows()
        self.logger.info('Splunk home is <%s>.' % SPLUNK_HOME)
        save_directories = '<{0}>, <{1}>, <{2}>'.format(self.save_directory,
                                                        self.vuln_directory,
                                                        self.asset_directory
                                                        )   
        self.logger.info('Save directories are: %s' % save_directories)

        self.create_directories()

    def connect_client(self):
        self.logger.info("Connecting Nexpose client")
        return pnx.nexposeClient(self.serveraddr, self.port, 
                                        self.username, self.password, 
                                        self.logger, API_VER)

    def set_sites(self, site_string):
        self.logger.info("Setting sites")
        site_string = re.sub(r"\s+", ',', site_string)
        site_string = re.sub(r"[^0-9,]", "", site_string)
        self.sites = set(re.sub(r",+", ",", site_string).split(','))

        # Extract valid site IDs
        client = self.connect_client()
        all_sites = set(client.site_id_listing())

        # '0' is equivalent to all sites
        if '0' in self.sites:
            self.sites.remove('0')

        if len(self.sites) == 0 or self.sites == set(['']):
            self.logger.info("Querying all sites.")
            self.sites = all_sites

            # Remove Rapid7 Insight Agents from self.sites if set to all sites
            agent_site_id = client.rapid7_agent_site()
            if agent_site_id is not None:
                self.logger.info("All sites in scope; filtering out Rapid7 Insight Agents site [{}]".format(agent_site_id))
                self.sites.remove(agent_site_id)

        valid_sites = all_sites & self.sites
        invalid_sites = self.sites - valid_sites

        self.sites = valid_sites
        self.logger.info("Valid sites:\t%s" % str(valid_sites))
        self.logger.info("Invalid sites:\t%s" % str(invalid_sites))

        # Logout and invalidate console session
        client.logout()

        return self.sites

    def make_dir(self, name, directory):
        try:
            os.makedirs(directory)
            self.logger.info("Created %s directory successfully!" % name)
        except OSError:
            if not os.path.isdir(directory):
                self.logger.info("Failed to create %s directory!" % name)
                raise
            else:
                self.logger.info("%s directory already exists!" % name)

    def create_directories(self):   
        self.logger.info("Creating save directories.")         
        self.make_dir('save', self.save_directory)
        self.make_dir('vulnerability save', self.vuln_directory)
        self.make_dir('asset save', self.asset_directory)

    def to_dir(self, folder):
        return os.path.normcase(self.root + folder)

    def is_windows(self):
        system_os = platform.system()

        if system_os.lower().find("wind") > -1:
            self.logger.info('Platform is Windows.')
        else:
            self.logger.info('Platform is Linux or Mac')

    # TODO: Insert more logging
    def execute_site_query(self, query_options):            
        site_id, sleep_time = query_options

        time.sleep(sleep_time)
        client = self.connect_client()
        asset_importer = AssetDataGenerator([site_id],
                                            client,
                                            self.index)
        asset_importer.import_data()
        client.logout()

        time.sleep(sleep_time)
        client = self.connect_client()
        vuln_importer = VulnDataGenerator([site_id], 
                                          client,
                                          self.index)
        vuln_importer.set_server_address(self.serveraddr)
        vuln_importer.import_data(self.import_solution)

        client.logout()

        # Update last scan data here
        lock = threading.RLock()
        lock.acquire()
        try:
            self.update_history(site_id)
        finally:
            lock.release()

    def execute_exception_query(self, query_options):
        client = self.connect_client()
        vuln_exception_importer = VulnExDataGenerator([],
                                                      client,
                                                      self.index)
        vuln_exception_importer.import_data()
        client.logout()

    def run_exception_query(self):
        self.execute_exception_query([])

    def run_site_queries(self, concurrency):
        settings = []

        for i, site in enumerate(self.sites):
            settings.append((site, (i * 40)%240))                

        pool = ThreadPool(concurrency)
        pool.map(self.execute_site_query, settings)
        pool.close
        pool.join

        # All the threads are finished here

    # Returns true if there are sites to scan
    def check_history(self, checkpoint_dir):
        client = self.connect_client()
        self.scan_data = ScanData(self.logger, checkpoint_dir, client, [])
        self.scan_data.load_last_scans()
        self.scan_data.get_latest_scans()

        if self.new_scans_only:
            self.sites = self.scan_data.sites_with_new_scans(self.sites)
        else:
            self.logger.info('Not filtering for sites with new scans.')
            self.sites = self.scan_data.sites_with_stable_scans(self.sites)

        if len(self.sites) == 0:
            self.logger.info('No new scans for selected sites.')

        client.logout()
        return len(self.sites) > 1

    def update_history(self, site_id):
        self.scan_data.update_last_scans([site_id])
        return


