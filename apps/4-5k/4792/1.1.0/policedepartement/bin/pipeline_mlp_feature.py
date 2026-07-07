#!/usr/bin/env python

import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline, make_pipeline



class FillEmptySqaurePivotTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, valid_squares):
        self.valid_squares = valid_squares

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        df = X.reset_index().set_index(["Date", "Square"])
        df = pd.pivot_table(df, index=["Date"], columns=["Square"], values=["crime_nb"])

        for nc in np.setdiff1d(self.valid_squares, df.columns.get_level_values(1).values):
            df["crime_nb", nc] = 0

        df.columns = df.columns.droplevel()

        return pd.melt(df.reset_index(), id_vars=["Date"], value_vars=self.valid_squares, value_name="crime_nb")


class MovingAvgTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, avg_days: list):
        self.avg_days = avg_days

    def fit(self, X, y=None):
        return self

    def transform(self, X: pd.DataFrame, y=None) -> pd.DataFrame:
        df = X.set_index(["Date", "Square"])

        df_piv = pd.pivot_table(df, index=["Date"], columns=["Square"], values=["crime_nb"])

        avg_14 = df_piv.rolling(window=14).mean().shift().reset_index()
        cols = avg_14.columns.get_level_values(1).values
        cols[0] = "Date"
        avg_14.columns = cols
        avg_14 = pd.melt(avg_14, id_vars=["Date"])
        avg_14.columns = ["Date", "Square", "cn_avg_14"]

        avg_31 = df_piv.rolling(window=31).mean().shift().reset_index()
        cols = avg_31.columns.get_level_values(1).values
        cols[0] = "Date"
        avg_31.columns = cols
        avg_31 = pd.melt(avg_31, id_vars=["Date"])
        avg_31.columns = ["Date", "Square", "cn_avg_31"]

        avg_14.set_index(["Date", "Square"], inplace=True)
        avg_31.set_index(["Date", "Square"], inplace=True)

        df = df.join(avg_14).join(avg_31)

        # df = df.dropna()

        return pd.pivot_table(df, index=["Date"], columns=["Square"],
                              values=["crime_nb", "cn_avg_31", "cn_avg_14"]).reset_index()


class ColShiftingTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, n_in: int = 1, n_out: int = 1):
        self.n_in = n_in
        self.n_out = n_out

    def fit(self, X, y=None):
        return self

    def series_to_supervised(self, data, n_in=1, n_out=1, dropnan=True):
        n_vars = 1 if type(data) is list else data.shape[1]
        df = pd.DataFrame(data)
        cols, names = list(), list()
        # input sequence (t-n, ... t-1)
        for i in range(n_in, 0, -1):
            cols.append(df.shift(i))
            names += [('var%d(t-%d)' % (j + 1, i)) for j in range(n_vars)]
        # forecast sequence (t, t+1, ... t+n)
        for i in range(0, n_out):
            cols.append(df.shift(-i))
            if i == 0:
                names += [('var%d(t)' % (j + 1)) for j in range(n_vars)]
            else:
                names += [('var%d(t+%d)' % (j + 1, i)) for j in range(n_vars)]
        # put it all together
        agg = pd.concat(cols, axis=1)
        agg.columns = names
        # drop rows with NaN values
        if dropnan:
            agg.dropna(inplace=True)
        return agg

    def transform(self, X: pd.DataFrame, y=None) -> pd.DataFrame:

        avg1 = X[["cn_avg_14"]]
        avg2 = X[["cn_avg_31"]]
        dates = X["Date"]
        df = X.drop(["Date", "cn_avg_14", "cn_avg_31"], axis=1)
        df = self.series_to_supervised(df, n_in=self.n_in, n_out=self.n_out)
        df["Date"] = dates
        df = avg1.join(avg2, how="inner").join(df, how="inner")

        return df.dropna()


class DateTransformer(BaseEstimator, TransformerMixin):

    def fit(self, X, y=None):
        return self

    def transform(self, X: pd.DataFrame, y=None) -> pd.DataFrame:
        df = X.copy()
        df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
        df["week_day"] = df["Date"].dt.dayofweek
        df["Year"] = pd.DatetimeIndex(df["Date"]).year.astype("category")
        df["Month"] = pd.DatetimeIndex(df["Date"]).month.astype("category")
        df["Day"] = pd.DatetimeIndex(df["Date"]).day.astype("category")
        return df.drop(["Date"], axis=1)


class CategoricalHotScalerTransformer(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X: pd.DataFrame, y=None) -> np.array:
        cols = list(X.columns.values)
        cat_cols = ["week_day", "Year", "Month", "Day"]
        label_cols = cols[-99:-4]

        rest_cols = [c for c in cols if c not in cat_cols + label_cols]
        year_cats = [c for c in range(2001, 2020)]
        month_cats = [c for c in range(1, 13)]
        day_cats = [c for c in range(1, 32)]
        week_day_cats = [c for c in range(0, 7)]

        cat_enc = OneHotEncoder(categories=[week_day_cats, year_cats, month_cats, day_cats])
        df_cat = cat_enc.fit_transform(X[cat_cols]).toarray()

        df_rest = X[rest_cols].values

        res = np.hstack((df_rest, df_cat))

        # scaler = StandardScaler()
        # res = scaler.fit_transform(res)

        res = np.hstack((res, X[label_cols]))
        return res[:, :-95] #cutoff real values

