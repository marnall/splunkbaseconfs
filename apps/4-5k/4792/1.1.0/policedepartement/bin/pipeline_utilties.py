import pandas as pd
import numpy as np
import re
import copy

from sklearn.base import BaseEstimator, TransformerMixin

class ColumnRegSelector(BaseEstimator, TransformerMixin):
    def __init__(self, regex = 'rb|lag|mavg|trend|Square'):
        self.regex = regex
    
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        X_new = X.filter(regex=self.regex)
        return X_new


		
class CustomScaler(BaseEstimator, TransformerMixin):
    def __init__(self, scaler, include_list = ['float64']):
        self.scaler = scaler
        self.include_list = include_list
        
    def fit(self, X, y = None):
        self.index_list = X.select_dtypes(include=self.include_list).columns
        self.scaler.fit(X[self.index_list])
        return self
    
    def transform(self, X, y = None):
        X_new = X.copy()
        X_new[self.index_list] = self.scaler.transform(X_new[self.index_list])
        return X_new
		

		
class CalcSampleWeights(BaseEstimator, TransformerMixin):
    def __init__(self, beta=35e-5):
        self.beta = beta
        self.end_ts = pd.Timestamp("2019-01-01")
        
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        X_new = X.copy()
        sample_weight = np.exp((X.Date - self.end_ts).dt.days * self.beta)
        X_new["sample_weight"] = sample_weight
        return X_new
		
		
class SelectSquare():
    def __init__(self, square):
        self.square = square
    
    def transform(self, X, y):
        X_new = X[X.Square == self.square]
        y_index = X_new.index
        X_new = X_new.set_index("Date")
        y_new = y[X.Square == self.square]
        return X_new, y_new, y_index
		
		
class RandomFilter():
    def __init__(self, groups):
        self.groups = groups

    def rvs(self, *args, **kwargs):
        rand_choice = np.random.choice(self.groups, 5, replace=False)
        rand_choice = np.append(rand_choice, r'^intercept')

        regex_filter = '|'.join(rand_choice)

        return regex_filter

class SquarewiseScaler(BaseEstimator, TransformerMixin):
    def __init__(self, scaler, column = 'crime_nb'):
        self.scaler = scaler
        self.column = column
        self.scaler_dict = {}

    def fit(self, X, y = None):
        for square, X_square in X.groupby('Square'):
            square_scaler = copy.deepcopy(self.scaler)
            square_scaler.fit(X[[self.column]])

            self.scaler_dict[square] = square_scaler
        return self

    def transform(self, X, y = None):
        for s in self.scaler_dict.keys():
            X.loc[X.Square == s, [self.column]] = self.scaler_dict[s].transform(X.loc[X.Square == s, [self.column]])
        return X


class Splitter(BaseEstimator, TransformerMixin):
    def __init__(self, reg_y, reg_X):
        self.reg_y = reg_y
        self.reg_X = reg_X

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        return X.filter(regex=self.reg_X), X.filter(regex=self.reg_y).values.flatten()