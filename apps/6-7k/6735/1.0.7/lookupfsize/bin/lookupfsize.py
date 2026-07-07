import sys, os, csv
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class lookupfsizeCommand(StreamingCommand):

    file_path = Option(
        doc='''
        **Syntax:** **file_path=***<field name that contains the full path of the lookup table>*
        **Description:** The full path of the CSV lookup file.''',
        require=True, validate=validators.Fieldname())
    
    verbose = Option(
        doc='''
        **Syntax:** **verbose=***(0|1|false|true)*
        **Description:** Set to true if user needs additional information other than the size of the CSV file.''',
        require=False, default=False, validate=validators.Boolean())
    
    prefix = Option(
        doc='''
        **Syntax:** **prefix=***<string>*
        **Description:** Defaults to "lookup_", set this parameter specify the prefix for the field that will be generated.''',
        require=False, default="lookup_")

    def stream(self, events):
        
        for event in events:
            
            fpath = event[self.file_path]
            
            if not os.path.isfile(fpath): 
                event[f'{self.prefix}error_msg'] = 'No such lookup table exists.'
                yield event
                continue
            
            if str(fpath).endswith('.csv'):
                try:
                    file_size = os.path.getsize(fpath)    
                    matrix = self.rc_count(fpath)
                    
                    event[f'{self.prefix}file_size'] = str(file_size)
                    event[f'{self.prefix}fsiz_unit'] = "bytes"
                    
                    # When Verbose option is true
                    if self.verbose:                    
                        event[f'{self.prefix}file_lastmod'] = os.path.getmtime(fpath)
                        event[f'{self.prefix}row_count'] = str(matrix[0])
                        event[f'{self.prefix}col_count'] = str(matrix[1])
                        
                except Exception as e:
                    event[f'{self.prefix}error_msg'] = e
            
                yield event

    @staticmethod
    def rc_count(_file_path):
        
        file_path = _file_path
        row_count = 0
        col_count = 0

        with open(file_path) as file:
            
            csv_reader = csv.reader(file)

            for row in csv_reader:
                row_count += 1
                col_count = max(col_count, len(row))

        return row_count, col_count


dispatch(lookupfsizeCommand, sys.argv, sys.stdin, sys.stdout, __name__)