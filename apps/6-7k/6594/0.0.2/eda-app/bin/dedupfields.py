from __future__ import absolute_import, division, print_function, unicode_literals
import os, sys
import exec_anaconda

exec_anaconda.exec_anaconda()
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators


@Configuration()
class DedupFields(EventingCommand):
    dssize = Option(require=False, validate=validators.Integer(0), default=10000)

    def __init__(self):
        super().__init__()
        self.df_all = None

    def transform(self, records):
        default_fields = ["host", "index", "linecount", "punct", "source", "sourcetype", "splunk_server", "timestamp", "date_hour", "date_mday", "date_minute", "date_month", "date_second", "date_wday", "date_year", "date_zone"]
        if self.df_all is None:
            self.df_all = pd.DataFrame.from_records(records)
        else:
            self.df_all = pd.concat([self.df_all, pd.DataFrame.from_records(records)])
        if self.df_all.shape[0] == self.dssize:
            df = self.df_all
            df.drop(default_fields, axis=1, errors='ignore')
            df = df.astype(str)
            for c in df.columns:
                if len(df[c].unique()) < 2:
                    df = df.drop(c, axis=1)
            df_clean = df.T.drop_duplicates().T
            dedup_cols = str(list(df_clean.columns))[1:-1]
            dedup_cols = dedup_cols.replace(",", "").replace("'", "")
            yield {"fields": dedup_cols}
        else:
            yield {}


dispatch(DedupFields, sys.argv, sys.stdin, sys.stdout, __name__)
