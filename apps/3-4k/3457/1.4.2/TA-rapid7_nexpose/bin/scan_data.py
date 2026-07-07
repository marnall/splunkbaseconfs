from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import open
from builtins import int
from data_gen.nexpose_data_generator import NexposeDataGenerator
from future import standard_library
standard_library.install_aliases()
import os
import csv
import sys
from tempfile import NamedTemporaryFile

import data_gen.queries.latest_sites_sql as site_query

# This class needs to handle multiple jobs running
# Stop multiple processes writing to the file at the same time
# And avoid a process reading the file while another is writing it
class ScanData(NexposeDataGenerator):
    def __init__(self, logger, save_dir, client, site_ids):
        self.logger = logger
        self.last_scan_ids = {}
        self.latest_scan_ids = {}
        self.client = client
        self.site_ids = site_ids

        self.save_dir = save_dir
        self.logger.info('Checkpoint directory: {}'.format(save_dir))

        self.filename = 'last_scan_data.csv'
        return

    # TODO: Create the file if it doesn't exist
    def load_last_scans(self):
        self.logger.info('Loading last scan data from file.')

        path = os.path.join(self.save_dir, self.filename)

        # Return empty dict as file will be created later
        if not os.path.exists(path):
            self.logger.info('No previous scan data file found')
            return {}

        self.last_scan_ids = self.load_scans_from_csv(path)

        return self.last_scan_ids

    def load_scans_from_csv(self, path):
        self.logger.info('Parsing scan data from CSV: {}'.format(path))

        scan_ids = {}

        if sys.version_info[0] < 3:
            infile = open(path, 'rb')
        else:
            infile = open(path, 'r', encoding='utf8')

        with infile as csvfile:
            csvreader = csv.reader(csvfile, delimiter=str(','), quotechar=str('"'))

            # Work out what each column contains
            header = next(csvreader)
            col = {}
            for idx, val in enumerate(header):
                col[val] = idx

            for row in csvreader:
                try:
                    # A Rather crude but effective way of detecting invalid lines in the CSV file.
                    row[0]
                except Exception as e:
                    error = "Error when trying to parse CSV file, skipping row <{}>; {}".format(row, e)
                    error.format(row)
                    self.logger.error(error)
                    continue

                # TODO: Remove magic numbers
                site_id = str(row[0])
                scan_id = row[1]

                # Only check status if reading report CSV
                if 'status_id' in col:
                    status = row[2]

                    if status != 'C':
                        msg = 'Site {} has scan with status {}. Skipping...'
                        self.logger.info(msg.format(site_id, status))
                        continue

                scan_ids[site_id] = scan_id
        
        self.logger.info('CSV file <{}> parsed.'.format(path))

        return scan_ids

    # Queries Nexpose and returns a dict of site:scan_id pairs
    def get_latest_scans(self):
        self.logger.info('Querying Nexpose for latest scan IDs.')

        query = site_query.query
        query_type = "site"
        report_id = None

        try: 
            report_id = self.create_report(query_type, query)
        except Exception as e:
            self.logger.error("Error creating report for site(s) {}, {} data will not be imported".format(self.site_ids, query_type))
            self.logger.error(e)            
            return

        if report_id is not None:
            try:
                generate_id = self.generate_report(report_id)
                self.poll_report_complete(report_id, generate_id) 
                response = self.download_report(report_id, generate_id)
                self.process_response_data(query_type, response)
            except Exception as e:
                self.logger.error('Error importing report {}'.format(report_id))
                self.logger.error(e)

        query_file = NamedTemporaryFile(delete=False)

        # Saves Exploitable Query to a temporary file
        if sys.version_info[0] < 3:
            outfile = open(query_file.name, 'wb')
        else:
            outfile = open(query_file.name, 'w', newline="")

        try:
            with outfile as myFile:
                if sys.version_info[0] < 3:
                    myFile.write(response)
                else:
                    myFile.write(response.decode('utf-8'))
                myFile.flush()
                os.fsync(myFile.fileno())

            self.latest_scan_ids = self.load_scans_from_csv(query_file.name)
        except Exception as e:
            self.logger.error('Error saving report {} to temporary file {}.'.format(report_id, outfile.name))
            self.logger.error(e)            
        finally:
            query_file.close()
            os.remove(os.path.join(query_file.name))
            self.delete_report(report_id)

        self.logger.info('Completed retrieving the latest scan IDs: {}.'.format(self.latest_scan_ids))

        return self.latest_scan_ids

    # Returns true if a site needs updated
    #TODO: Add in error checking e.g. site id doesn't exist, dict not filled
    def new_scan_exists(self, site_id):
        last_scan = int(self.last_scan_ids.get(site_id, 0))
        latest_scan = int(self.latest_scan_ids.get(site_id, -1))

        site_info = "Site {}: Last Scan: {}, Latest Scan: {}"
        self.logger.info(site_info.format(site_id, last_scan, latest_scan))

        scans_since = latest_scan - last_scan
        return last_scan < latest_scan

    def sites_with_stable_scans(self, site_list):
        self.logger.info('Filtering for sites with stable scans.')
        sites_to_import = []

        self.logger.info("Latest scans: ")
        self.logger.info(str(self.latest_scan_ids))

        for site in site_list:
            latest_scan = int(self.latest_scan_ids.get(site, -1))

            if latest_scan != -1:
                sites_to_import.append(site)

        self.logger.info("Sites with stable scans: {}".format(sites_to_import))

        return sites_to_import

    def sites_with_new_scans(self, site_list):
        self.logger.info('Filtering for sites with new scans' \
                         ' since last execution.')
        sites_to_scan = []
        for site in site_list:
            if self.new_scan_exists(site):
                sites_to_scan.append(site)

        return sites_to_scan

    # Overwrites the last stored scan ID for a site
    def update_last_scans(self, site_ids):
        self.logger.info('Updating scan data historical file')
        self.load_last_scans()

        for site in site_ids:
            if site not in self.latest_scan_ids:
                continue
            self.last_scan_ids[site] = self.latest_scan_ids[site]

        self.write_last_scan_data(self.last_scan_ids)

    def write_last_scan_data(self, last_scans):
        self.logger.info('Writing scan data historical file')
        filepath = os.path.join(self.save_dir, self.filename)

        if sys.version_info[0] < 3:
            outfile = open(filepath, 'wb')
        else:
            outfile = open(filepath, 'w', newline="")

        with outfile as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=str(','), quotechar=str('"'))
            csvwriter.writerow(('site', 'scan_id'))
            for site in last_scans:
                csvwriter.writerow((site, last_scans[site]))
        self.logger.info('Historical file written.')

