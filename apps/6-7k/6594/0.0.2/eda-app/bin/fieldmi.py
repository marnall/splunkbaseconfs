from __future__ import absolute_import, division, print_function, unicode_literals
import os, sys
import exec_anaconda

exec_anaconda.exec_anaconda()
import numpy as np
import pandas as pd
from eda.eda import fieldEDA

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators


@Configuration()
class fieldmi(EventingCommand):
    """
    The fieldmi command computes mutual information across fields and returns a set of field representatives for each
    group of fields containing similar information as well as the information contained in that field alone.
    Example:
    ``| inputlookup BOTS.csv | fieldmi``
    returns a table with columns: field representatives, field information, similar fields (fields containing high
    levels of mutual information).
    """

    frac = Option(require=False, validate=validators.Float(0), default=None)
    mode = Option(require=False, default='report')
    cutoff = Option(require=False, validate=validators.Integer(0, 100), default=0.9)
    dssize = Option(require=False, validate=validators.Integer(0), default=10000)


    def __init__(self):
        super().__init__()
        self.df_all = None

    def process_data(self):
        model = fieldEDA({})
        if self.frac is not None:
            mi, pairs, reps = model.apply(self.df_all, frac=self.frac)
        else:
            mi, pairs, reps = model.apply(self.df_all, frac='log')
        return mi, pairs, reps

    def transform(self, records):
        if self.df_all is None:
            self.df_all = pd.DataFrame.from_records(records)
        else:
            self.df_all = pd.concat([self.df_all, pd.DataFrame.from_records(records)])
        if self.df_all.shape[0] == self.dssize:
            mi, pairs, reps = self.process_data()
            if self.mode == 'report':
                for i in range(len(reps)):
                    yield {
                        "field_representative": str(reps[i][0]),
                        "field_information": reps[i][1],
                        "similar_fields": str(reps[i][2])[1:-1].replace("'", "").replace(",", " ")
                    }
            elif self.mode == 'data':
                for i in range(len(mi)):
                    yield {
                        "field_1": pairs[i][0],
                        "field_2": pairs[i][1],
                        "mutual_information": mi[i]
                    }
        if self._finished:
            self.process_data()
        else:
            yield {}


dispatch(fieldmi, sys.argv, sys.stdin, sys.stdout, __name__)
