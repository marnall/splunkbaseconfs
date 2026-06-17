from collections import deque
import json
import logging

import excel_export.xlwt as xlwt

logger = logging.getLogger('splunk')

FLUSH_COUNT = 1000
MAX_ROWS = 65000

class WBClient(object):
    """ consumer class for asycore client callback """

    def __init__(self, field_names, row_number=0, sheet_index=1, wb=None, isNewFormat=None):
        self.field_names = field_names
        self.row_num = int(row_number)
        self.sheet_index = int(sheet_index)
        self.decoder = json.JSONDecoder()
        self.input_buffer = deque() 
        self.output_buffer = [] 
        self.result_count = 0
        self.is_new_format = isNewFormat

        if not wb:
            self.wb = xlwt.Workbook(encoding="utf-8")
        else:
            self.wb = wb

        self.result_sheet = self.wb.add_sheet('splunk_results_%s' % self.sheet_index)
        self.write_header()

    def add_data(self, json_obj):
        """
        adds data to the current wb sheet
        if row count exceeds threshold, rolls over to new sheet 
        """
        for i, field in enumerate(self.field_names):
            if self.is_new_format is not None:
                tmp = json_obj['result'].get(field)
            else:
                tmp = json_obj.get(field)
            if tmp:
                if isinstance(tmp, list):
                    tmp = unicode(','.join(tmp))
                    self.result_sheet.write(self.row_num,i,self.max_len(tmp, i))
                else:
                    tmp = unicode(tmp)
                    self.result_sheet.write(self.row_num,i,self.typer(self.max_len(tmp, i)))
        self.row_num += 1
        if self.row_num%FLUSH_COUNT == 0:
            # http://blog.insightvr.com/python/hacking-xlwt/
            self.result_sheet.flush_row_data()
        if self.row_num > MAX_ROWS:
            self.add_new_sheet()

    def add_new_sheet(self):
        """
        increment the sheet index
        set result_sheet and write header
        """
        self.sheet_index += 1
        self.result_sheet = self.wb.add_sheet('splunk_results_%s' % self.sheet_index)
        self.write_header()

    def close(self):
        """
        callback for asyncore json client handle_close()
        calls parse to ensure we have parsed all of our buffer
        """
        self.parse()
        logger.info('request completed successfully, parsed %s results' % self.result_count)

    def max_len(self, data, index):
        """
        excel does now allow any cell to be > 32767 characters
        """
        if len(data) > 32767:
            logger.warn('sheet: %s row:%s column: %s - reducing to 32767 characters' \
                            % (self.result_sheet.get_name(), self.row_num, index))
            data = data[:32766]
        return data

    def parse(self):
        """ 
        looks for JSON in the input buffer
        if found, will remove chunk from buffer and commit it to excel
        iterates until we can't find any more json
        """
        while 1:
            if len(self.input_buffer) < 1:
                break
            line = self.input_buffer.popleft()
            self.output_buffer.append(line)
            if line.endswith('}'):
                self.parse_buffer()

    def parse_buffer(self):
        """
        try to decode the given buffer
        log an error on decode fail
        otherwise, add the resultant obj data to the xls
        """

        data = ''.join(self.output_buffer).strip(' \r\n').replace('\t', '')

        try:
            (json_obj, index) = self.decoder.raw_decode(
                                    ''.join(self.output_buffer).strip(' \r\n').replace('\t', '')
                                )
            self.output_buffer = []
            self.result_count += 1
        except:
            logger.error('json decode failed')
        else:
            self.add_data(json_obj) 
 
    def read(self, data):
        """ 
        callback for asyncore json client handle_read()
        appends data to input buffer deque 
        calls parse to start handling the data
        """
        self.input_buffer.extend(data)
        self.parse()

    def typer(self, field):
        """provides very weak tying"""
        if field:
            field = unicode(field)
            while 1:
                try:
                    field = int(field)
                    break
                except:
                    pass
                try:
                    field = float(field)
                except:
                    pass
                break
        else:
            field = ''
        return field

    def write_header(self):
        """
        writes the excel header
        """
        self.row_num = 0
        for i, field in enumerate(self.field_names):
            self.result_sheet.write(self.row_num,i,field)
        self.row_num += 1

