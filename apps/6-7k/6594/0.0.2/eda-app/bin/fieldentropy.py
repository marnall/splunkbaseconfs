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
class FieldEntropy(EventingCommand):
    """
    The for every field calculates Shannon's entropy.
    Example:
    ``| inputlookup BOTS.csv |  fieldentropy cutoff=5.0``
    returns all fields with entropy above the cutoff and the number of bits of information contained in the field.
    """
    cutoff = Option(require=True, validate=validators.Float(0))
    dssize = Option(require=False, validate=validators.Integer(0), default=10000)


    def __init__(self):
        super().__init__()
        self.df_all = None

    def process_data(self):
        df = self.df_all
        model = fieldEDA({})
        df = model.clean_data(df)
        h_vec, cols = model.calc_H(df, self.cutoff)
        return h_vec, cols


    def transform(self, records):
        if self.df_all is None:
            self.df_all = pd.DataFrame.from_records(records)
        else:
            self.df_all = pd.concat([self.df_all, pd.DataFrame.from_records(records)])
        if self.df_all.shape[0] == self.dssize:
            h_vec, cols = self.process_data()
            for i in range(len(h_vec)):
                yield {"field": cols[i], "entropy": h_vec[i]}
        if self._finished:
            self.process_data()
        else:
            yield {}


dispatch(FieldEntropy, sys.argv, sys.stdin, sys.stdout, __name__)
