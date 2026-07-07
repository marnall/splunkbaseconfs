import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from pandas.tseries.offsets import YearOffset, MonthBegin
import calendar

class CustOffset(YearOffset):
    _prefix = 'AS'
    _day_opt = 'start'
    
    def __init__(self, n=1, normalize=False, month=3):
        object.__setattr__(self, "_default_month", month)
        YearOffset.__init__(self)
        
def rbf(x, alpha = 1, m = 0):
    return np.exp(np.square(x - m) / (-2*alpha))
	
class FeatureRbfMonthBase(BaseEstimator, TransformerMixin):
    def __init__(self, month_list = np.arange(1,13), alpha = 400, day_offset = 15, colnames = None):
        self.alpha = alpha
        self.day_offset = day_offset
        self.month_list = month_list
        self.colnames = colnames if colnames else ['rbf_month_' + str(i)  for i in range(len(month_list))]
        
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        X_new = X.copy()
        for i in range(len(self.month_list)):
            X_new[self.colnames[i]] = \
                self.date_to_rbf_one_month(X.Date, 
                                           month=self.month_list[i], 
                                           day_offset=self.day_offset, 
                                           alpha=self.alpha)
        return X_new
    
    def date_to_rbf_one_month(self, time_series, month, day_offset, alpha):
        diff_1 = np.abs(time_series - (time_series + 
                                       CustOffset(month = month)+ 
                                       pd.DateOffset(day_offset))).dt.days

        diff_2 = np.abs(time_series - (time_series + 
                                       CustOffset(month = month) - 
                                       pd.DateOffset(years=1) + 
                                       pd.DateOffset(day_offset))).dt.days
        return rbf(pd.concat([diff_1, diff_2], axis = 1).min(1), alpha)
		
class FeatureRbfPerMonth(FeatureRbfMonthBase):
    def __init__(self, alpha = 400, day_offset = 15):
        self.alpha = alpha
        self.day_offset = day_offset
        self.month_list = np.arange(1,13)
        self.colnames = [f"rb_month_{calendar.month_abbr[month_nb]}" for month_nb in self.month_list]
        
        FeatureRbfMonthBase.__init__(self, self.month_list, self.alpha, self.day_offset, self.colnames)  
        
        
class FeatureRbfQuarterly(FeatureRbfMonthBase):
    def __init__(self, alpha = 1000, day_offset = 15, month_offset = 0):
        self.alpha = alpha
        self.month_offset = month_offset
        self.day_offset = day_offset  
        self.month_list = np.arange(1,13, 3) #(np.arange(1,13, 3) + self.month_offset -1)%12 + 1
        self.colnames = [f"rb_quarterly_{month_nb}" for month_nb in self.month_list]
        
        FeatureRbfMonthBase.__init__(self, self.month_list, self.alpha, self.day_offset, self.colnames)
		
class FeatureRbfWeekday(BaseEstimator, TransformerMixin):
    def __init__(self, alpha = 0.2):
        self.alpha = alpha
        
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        X_new = X.copy()
        for weekday_nb in range(7):
            X_new[f"rb_weekday_{calendar.day_name[weekday_nb]}"] = \
                self.date_to_rbf_weekly(X.Date, 
                                        day=weekday_nb,
                                        alpha = self.alpha)

        return X_new
    
    def date_to_rbf_weekly(self, time_series, day, alpha):
        diff_1 = (time_series.dt.dayofweek - day) % 7
        diff_2 = np.abs(7 - diff_1)

        return rbf(pd.concat([diff_1, diff_2], axis = 1).min(1), alpha)
		
class FeatureRbfMonthly(BaseEstimator, TransformerMixin):
    def __init__(self, alpha = 30, day_offset = [0,15]):
        self.alpha = alpha
        self.day_offset = day_offset
        
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        X_new = X.copy()
        for i_offset in self.day_offset :
            X_new[f"rb_monthly{i_offset}"] = self.date_to_rbf_monthly(X.Date, day_offset=i_offset, alpha = self.alpha)
        return X_new
    
    def date_to_rbf_monthly(self, time_series, day_offset = 0, alpha = 30):
        diff_1 = np.abs(time_series.dt.days_in_month - time_series.dt.day + day_offset)
        diff_2 = np.abs(time_series.dt.day - day_offset)

        return rbf(pd.concat([diff_1, diff_2], axis = 1).min(1), alpha = alpha)
		
class FeatureTrend(BaseEstimator, TransformerMixin):
    def __init__(self, start_date = "2001-02-01", degree_list = np.arange(4)):
        self.start_date = start_date
        self.degree_list = degree_list
            
    def fit(self, X, y = None):
        return self
    
    def transform(self, X, y = None):
        X_new = X.copy()
                
        for degree in self.degree_list:
            if degree == 0:
                name = "intercept"
            elif degree == 1:
                name = "trend"
            else:
                name = f"trend_{degree}"             
            X_new[name] = self.calc_trend(X.Date, self.start_date, degree)
            
        return X_new
        
    def calc_trend(self, time_series, start_date, degree):
        return np.power((time_series - pd.Timestamp(start_date)).dt.days, degree)
		
class FeatureInteractionTerm(BaseEstimator, TransformerMixin):
    def __init__(self, regex = 'rb|lag|mavg', interaction_col = 'trend'):
        self.regex = regex
        self.interaction_col = interaction_col
        
    def fit(self, X, y = None):
        return self

    def transform(self, X, y = None):
        X_new = X.copy()
        X_new = X_new.join(
                            X\
                                .filter(regex=self.regex)\
                                .multiply(np.array(X[self.interaction_col]), axis = 0)\
                                .rename(lambda x: f"{self.interaction_col}:{x}", axis='columns')
                          )
        return X_new