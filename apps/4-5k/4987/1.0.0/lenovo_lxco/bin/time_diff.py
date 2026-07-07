import sys
import logging
import json
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from datetime import datetime

@Configuration()
class TimeDiff(StreamingCommand):

    fw = Option(
        doc='''
        **Syntax:** **fw=***<firmware>*
        **Description:** Name of the firmware to calculate age''',
        require=True)    

    lt = Option(
        doc='''
        **Syntax:** **lt=***<less_than>*
        **Description:** Integer value to calculate age less than specified''',
        require=False)    

    gt = Option(
        doc='''
        **Syntax:** **gt=***<greater_than>*
        **Description:** Integer value to calculate age greater than specified''',
        require=False)    

    def stream(self, records):
        for record in records:
            raw_record = json.loads(record['_raw'])
            if 'result' in raw_record:
                time_diff = self.process_device_data(raw_record, self.fw, self.lt, self.gt)
                if time_diff != "":
                    for age_data in time_diff.split(';'):
                        record['Device'], record['age'] = age_data.split(':')
                        yield record

    def calc_old(self, str_fw_date):
        fw_date = datetime.strptime(str_fw_date, "%Y-%m-%dT%H:%M:%SZ")
        today = datetime.now()
        old = today - fw_date
        return old.days

    def process_device_data(self, device_data, fw_type, less_than, older_than):
        device_older = ""
        for res in device_data['result']:
            device_name = res['name']
            if 'firmware' in res:
                for fw in res['firmware']:
                    if fw['type'] == fw_type:
                        days_old = self.calc_old(fw['date'])
                        if less_than is not None and older_than is not None:
                            age_condition = days_old >= int(older_than) and days_old < int(less_than)
                        elif less_than is not None and older_than is None:
                            age_condition = days_old <= int(less_than)
                        elif less_than is None and older_than is not None:
                            age_condition = days_old >= int(older_than)
                        else:
                            age_condition = True
                        if age_condition:
                            device_older = device_older + device_name + ":" + str(days_old) + ";"
        return device_older.rstrip(';')

if __name__ == '__main__':
    dispatch(TimeDiff, argv=sys.argv, input_file=sys.stdin, output_file=sys.stdout, module_name=__name__)
