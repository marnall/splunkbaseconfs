from __future__ import absolute_import, division, print_function, unicode_literals
import os, sys
import exec_anaconda

exec_anaconda.exec_anaconda()
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators

@Configuration()
class AddWildcards(EventingCommand):

    dssize = Option(require=False, validate=validators.Integer(0), default=10000)

    def __init__(self):
        super().__init__()
        self.df_all = None

    def ireplace(self, old, new, text):
        index_l = text.lower().index(old.lower())
        return text[:index_l] + new + text[index_l + len(old):]

    def list_to_string(self, value):
        if type(value) is list:
            return str(value)
        else:
            return value

    def string_to_numeric(self, x):
        if x[0].isdigit() or x == '0':
            return int(x)
        else:
            return x


    def transform(self, records):
        if self.dssize > 10000:
            self.dssize = 10000
        if self.df_all is None:
            self.df_all = pd.DataFrame.from_records(records)
        else:
            self.df_all = pd.concat([self.df_all, pd.DataFrame.from_records(records)])
        if self.df_all.shape[0] == self.dssize:
            df = self.df_all
            cols_drop = []
            for c in df.columns:
                if c[0] == "_" and "raw" not in c:
                    cols_drop.append(c)
            df = df.drop(columns=cols_drop)
            cluster_index = df.cluster_label.unique()
            for i in cluster_index:
                subset = df[df.cluster_label == i]
                subset.dropna(how='all', axis=1)
                cols = list(subset.columns)
                base_log = list(subset['_raw'])[0]
                cols.remove("_raw")
                wildcard_cols = []
                for c in cols:
                    subset[c] = [self.list_to_string(x) for x in list(subset[c])]
                    vals = subset[c].unique()
                    if vals.shape[0] > 1:
                        sorted_vals = list(vals)
                        sorted_vals.sort(reverse=True, key=len)
                        if (sorted_vals[0].isdigit() is False and len(sorted_vals[0]) > 0) or len(str(sorted_vals[0])) > 2:
                            wildcard_cols.append(c)
                            for val in sorted_vals:
                                val = str(val)
                                if len(val) < 3:
                                    break
                                if val.lower() in base_log.lower():
                                    base_log = self.ireplace(val, "[" + c + "]", base_log)
                                    break
                yield {
                    "cluster_label": list(subset["cluster_label"])[0],
                    "_raw": base_log,
                    "cluster_count": list(subset["cluster_count"])[0],
                    "fields": str(wildcard_cols)[1:-1]
                }
        if self._finished:
            print("done")
        else:
            yield {}


dispatch(AddWildcards, sys.argv, sys.stdin, sys.stdout, __name__)
