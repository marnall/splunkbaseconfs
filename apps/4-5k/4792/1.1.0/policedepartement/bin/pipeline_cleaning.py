import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

class ColumnSelector(BaseEstimator, TransformerMixin):
    def __init__(self, colnames):
        self.__colnames = colnames
    
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        return X[self.__colnames]

		
class MissingDropper(BaseEstimator, TransformerMixin):
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        return X.dropna()



class SquareSummarizer(BaseEstimator, TransformerMixin):
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        df_by_squares = X \
            .groupby(["Date", "Square"]) \
            .size() \
            .to_frame('crime_nb')

        # reindex and fill with 0
        start_date = df_by_squares.reset_index().Date.min()
        end_date = df_by_squares.reset_index().Date.max()

        relevant_grids = df_by_squares.reset_index().Square.unique()  # muss vlt geändert werden

        index_iterables = [pd.date_range(start=start_date, end=end_date), relevant_grids]

        df_by_squares = df_by_squares \
            .reindex(pd.MultiIndex.from_product(index_iterables, names=['Date', 'Square'])) \
            .fillna(0)

        df_by_squares.crime_nb = df_by_squares.crime_nb.astype(int)

        df_by_squares = df_by_squares \
            .reset_index()
        
        return df_by_squares


class LatLongTransformer(BaseEstimator, TransformerMixin):
    def __init__(self,
                 x_gridsize=10,
                 y_gridsize=10,
                 lat_high=42.02271,
                 lat_low=41.64459,
                 lon_high=-87.52453,
                 lon_low=-87.93432):
        self.lat_high = 42.02271
        self.lat_low = 41.64459

        self.lon_high = -87.52453
        self.lon_low = -87.93432

        self.x_gridsize = x_gridsize
        self.y_gridsize = y_gridsize

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        trans_df = X[(X.Latitude < self.lat_high) & (X.Latitude >= self.lat_low)]
        trans_df = trans_df[(trans_df.Longitude < self.lon_high) & (trans_df.Longitude >= self.lon_low)]

        # calculate the square
        calc_y_grid_pos = lambda lat: int((lat - self.lat_low) / (self.lat_high - self.lat_low) * self.y_gridsize)
        calc_x_grid_pos = lambda lon: int((lon - self.lon_low) / (self.lon_high - self.lon_low) * self.x_gridsize)

        trans_df['y_grid_pos'] = trans_df['Latitude'].apply(calc_y_grid_pos)
        trans_df['x_grid_pos'] = trans_df['Longitude'].apply(calc_x_grid_pos)

        trans_df['Square'] = trans_df['y_grid_pos'] * self.x_gridsize + trans_df['x_grid_pos']

        return trans_df


class FeatureEngLag(BaseEstimator, TransformerMixin):
    def __init__(self, lag_days = 4):
        self.lag_days = lag_days
    
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        eng_df = X.copy()
        for i in range(1, self.lag_days + 1):
            eng_df[f"lag_{i}d"] = eng_df \
                .groupby('Square') \
                .crime_nb \
                .shift(i)
        
        return eng_df


class FeatureEngMavg(BaseEstimator, TransformerMixin):
    def __init__(self, mavg_days=[2, 3, 7, 14, 31]):
        self.mavg_days = mavg_days

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        eng_df = X.copy()
        for i in self.mavg_days:
            eng_df[f'mavg_{i}d'] = eng_df.groupby("Square") \
                .crime_nb \
                .rolling(i) \
                .mean() \
                .reset_index(level=0) \
                .groupby("Square") \
                .shift(1)

        return eng_df


		
class FeatureEngDate(BaseEstimator, TransformerMixin):
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        eng_df = X.copy()
        eng_df["day_of_week"] = eng_df.Date.dt.strftime('%a')
        eng_df["month"] = eng_df.Date.dt.strftime('%b')
        eng_df["day_of_month"] = eng_df.Date.dt.strftime('%d')
        return eng_df
		
	
class NaDropper(BaseEstimator, TransformerMixin):
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        return X.dropna()
	
	
class DateTransformer(BaseEstimator, TransformerMixin):
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        trans_df = X.copy()
        trans_df['Date'] = pd.to_datetime(X['Date'], format='%m/%d/%Y %X %p').dt.normalize()
        return trans_df